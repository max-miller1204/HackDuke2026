"""Distillation training: sweep over student architectures, temperatures, and alphas.

Trains 27 experiments (3 architectures x 3 temperatures x 3 alphas) with per-experiment
checkpointing and structured JSON metrics output.
"""

import json
import os
import time
from datetime import datetime
from itertools import product
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim
from loguru import logger
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.distill.dataset_distill import DistillSleepEDFDataset, distill_collate_fn
from src.distill.soft_labels import load_distill_config
from src.distill.student_models import STUDENT_REGISTRY, build_student
from src.train import masked_cross_entropy_loss


def distillation_loss(student_logits, teacher_logits, hard_labels, temporal_mask,
                      class_weights, temperature, alpha):
    """Combined KL-divergence (soft) + cross-entropy (hard) distillation loss.

    L = alpha * KL(softmax(student/T), softmax(teacher/T)) * T^2
        + (1 - alpha) * CE(student, hard_labels)

    Args:
        student_logits: (B, S, num_classes) raw student logits
        teacher_logits: (B, S, num_classes) raw teacher logits (cached)
        hard_labels: (B, S) integer class labels
        temporal_mask: (B, S) where 0=real, 1=padded
        class_weights: list of per-class weights for CE term
        temperature: softmax temperature for KL term
        alpha: weight for KL term (1-alpha for CE term)

    Returns:
        Scalar combined loss
    """
    B, S, C = student_logits.shape

    # --- Mask: 0=real, 1=padded ---
    valid = (temporal_mask == 0).float()  # (B, S)
    num_valid = valid.sum().clamp(min=1)

    # --- KL divergence on soft targets ---
    student_log_soft = F.log_softmax(student_logits / temperature, dim=-1)  # (B, S, C)
    teacher_soft = F.softmax(teacher_logits / temperature, dim=-1)          # (B, S, C)

    # Per-position KL: sum over classes
    kl_per_pos = F.kl_div(student_log_soft, teacher_soft, reduction="none").sum(dim=-1)  # (B, S)
    kl_loss = (kl_per_pos * valid).sum() / num_valid * (temperature ** 2)

    # --- CE on hard labels (reuse existing masked_cross_entropy_loss) ---
    # masked_cross_entropy_loss expects mask as (B, C_channels, S) or (B, S)
    ce_loss = masked_cross_entropy_loss(student_logits, hard_labels, temporal_mask, class_weights)

    return alpha * kl_loss + (1 - alpha) * ce_loss


def train_one_epoch(model, loader, optimizer, device, class_weights, temperature, alpha,
                    scaler=None):
    """Train for one epoch.

    Returns:
        Average training loss for the epoch.
    """
    model.train()
    running_loss = 0.0
    use_amp = scaler is not None

    for x_data, y_data, teacher_logits, padded_mask, _ in loader:
        x_data = x_data.to(device)
        y_data = y_data.to(device)
        teacher_logits = teacher_logits.to(device)
        padded_mask = padded_mask.to(device)

        with torch.amp.autocast("cuda", enabled=use_amp):
            student_logits, temporal_mask = model(x_data, padded_mask)
            loss = distillation_loss(
                student_logits, teacher_logits, y_data, temporal_mask,
                class_weights, temperature, alpha,
            )

        if use_amp:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()
        optimizer.zero_grad()

        running_loss += loss.item()

    return running_loss / max(len(loader), 1)


def validate(model, loader, device, class_weights):
    """Validate with loss and accuracy on non-padded positions.

    Returns:
        (val_loss, val_accuracy)
    """
    model.eval()
    val_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for x_data, y_data, teacher_logits, padded_mask, _ in loader:
            x_data = x_data.to(device)
            y_data = y_data.to(device)
            padded_mask = padded_mask.to(device)

            student_logits, temporal_mask = model(x_data, padded_mask)
            loss = masked_cross_entropy_loss(
                student_logits, y_data, temporal_mask, class_weights,
            )
            val_loss += loss.item()

            # Accuracy on valid (non-padded) positions
            valid = temporal_mask == 0
            preds = student_logits.argmax(dim=-1)
            correct += ((preds == y_data.long()) & valid).sum().item()
            total += valid.sum().item()

    avg_loss = val_loss / max(len(loader), 1)
    accuracy = correct / max(total, 1)
    return avg_loss, accuracy


def compute_class_weights(train_dataset, num_classes):
    """Compute inverse-frequency class weights normalized to mean=1.0."""
    all_labels = np.concatenate([s["y_epochs"] for s in train_dataset.subjects])
    counts = np.bincount(all_labels.astype(int), minlength=num_classes).astype(float)
    counts = np.maximum(counts, 1.0)
    inv_freq = 1.0 / counts
    weights = inv_freq / inv_freq.mean()
    return weights.tolist()


def run_sweep(config):
    """Run the full 27-experiment distillation sweep.

    Creates datasets once, then iterates over all (architecture, temperature, alpha)
    combinations. Saves per-experiment checkpoints and a summary JSON.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # Seed
    seed = config["training"]["seed"]
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # Output directory
    output_dir = project_root / config["export"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    # Datasets (created once, shared across all experiments)
    processed_dir = str(project_root / config["data"]["processed_dir"])
    train_dataset = DistillSleepEDFDataset(
        processed_dir, config["data"]["train_subjects"], config, augment=True,
    )
    val_dataset = DistillSleepEDFDataset(
        processed_dir, config["data"]["val_subjects"], config, augment=False,
    )

    # Class weights
    num_classes = config["num_classes"]
    if config["class_weights"] == "auto":
        class_weights = compute_class_weights(train_dataset, num_classes)
        stage_names = ["W", "R", "N1", "N2", "N3"]
        logger.info(
            f"Auto class weights (inv-freq): "
            f"{dict(zip(stage_names, [f'{w:.2f}' for w in class_weights]))}"
        )
    else:
        class_weights = config["class_weights"]

    # Data loaders
    training_cfg = config["training"]
    batch_size = training_cfg["batch_size"]
    num_workers = training_cfg.get("num_workers", 4)

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, collate_fn=distill_collate_fn,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, collate_fn=distill_collate_fn,
    )

    # Sweep parameters
    architectures = list(STUDENT_REGISTRY.keys())
    temperatures = config["sweep"]["temperatures"]
    alphas = config["sweep"]["alphas"]

    total_experiments = len(architectures) * len(temperatures) * len(alphas)
    logger.info(
        f"Starting sweep: {len(architectures)} architectures x "
        f"{len(temperatures)} temperatures x {len(alphas)} alphas = "
        f"{total_experiments} experiments"
    )

    # AMP
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda") if use_amp else None

    sweep_results = []
    exp_num = 0

    for arch_name, temperature, alpha in product(architectures, temperatures, alphas):
        exp_num += 1
        exp_id = f"{arch_name}_T{temperature}_a{alpha}"
        logger.info(
            f"\n{'='*60}\n"
            f"Experiment {exp_num}/{total_experiments}: {exp_id}\n"
            f"{'='*60}"
        )

        # Build fresh student model
        torch.manual_seed(seed)  # deterministic init per experiment
        model = build_student(arch_name, config).to(device)
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        logger.info(f"Student: {arch_name}, params: {param_count:,}")

        # Optimizer + scheduler
        optimizer = optim.AdamW(model.parameters(), lr=training_cfg["lr"])
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=training_cfg["scheduler_factor"],
            patience=training_cfg["scheduler_patience"],
        )

        # Training loop with early stopping
        num_epochs = training_cfg["epochs"]
        patience = training_cfg["early_stopping_patience"]
        best_val_loss = float("inf")
        best_epoch = -1
        epochs_no_improve = 0
        start_time = time.time()

        for epoch in range(num_epochs):
            train_loss = train_one_epoch(
                model, train_loader, optimizer, device,
                class_weights, temperature, alpha, scaler,
            )

            val_loss, val_acc = validate(model, val_loader, device, class_weights)
            scheduler.step(val_loss)

            current_lr = optimizer.param_groups[0]["lr"]
            logger.info(
                f"[{exp_id}] Epoch {epoch + 1}/{num_epochs} — "
                f"Train: {train_loss:.4f}, Val: {val_loss:.4f}, "
                f"Acc: {val_acc:.4f}, LR: {current_lr:.6f}"
            )

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_val_acc = val_acc
                best_epoch = epoch + 1
                epochs_no_improve = 0
                # Save best checkpoint
                ckpt_path = output_dir / f"{exp_id}.pth"
                torch.save(model.state_dict(), ckpt_path)
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    logger.info(
                        f"[{exp_id}] Early stopping at epoch {epoch + 1} "
                        f"(no improvement for {patience} epochs)"
                    )
                    break

        elapsed = time.time() - start_time

        # Model size on disk
        ckpt_path = output_dir / f"{exp_id}.pth"
        model_size_bytes = ckpt_path.stat().st_size if ckpt_path.exists() else 0

        result = {
            "experiment_id": exp_id,
            "architecture": arch_name,
            "temperature": temperature,
            "alpha": alpha,
            "param_count": param_count,
            "model_size_bytes": model_size_bytes,
            "best_epoch": best_epoch,
            "train_loss": round(train_loss, 6),
            "val_loss": round(best_val_loss, 6),
            "val_accuracy": round(best_val_acc, 6),
            "training_time_s": round(elapsed, 1),
        }
        sweep_results.append(result)
        logger.info(f"[{exp_id}] Done — best val_loss: {best_val_loss:.4f}, "
                     f"val_acc: {best_val_acc:.4f} @ epoch {best_epoch}")

    # Save sweep summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "device": str(device),
        "num_experiments": len(sweep_results),
        "training_config": {
            "optimizer": training_cfg["optimizer"],
            "lr": training_cfg["lr"],
            "epochs": training_cfg["epochs"],
            "batch_size": batch_size,
            "early_stopping_patience": patience,
            "seed": seed,
        },
        "class_weights": class_weights,
        "results": sweep_results,
    }

    results_path = output_dir / "sweep_results.json"
    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Sweep results saved to {results_path}")

    # Log best overall
    best = min(sweep_results, key=lambda r: r["val_loss"])
    logger.info(
        f"\nBest experiment: {best['experiment_id']} — "
        f"val_loss: {best['val_loss']:.4f}, val_acc: {best['val_accuracy']:.4f}, "
        f"params: {best['param_count']:,}"
    )

    return sweep_results


def main():
    """Entry point: load config and run distillation sweep."""
    config = load_distill_config()
    run_sweep(config)


if __name__ == "__main__":
    main()
