"""Training script for SleepFM finetuning on Sleep-EDF.

Loads pretrained SetTransformer weights into compatible layers of
SleepEventLSTMClassifier, then finetunes end-to-end on Sleep-EDF embeddings.
"""

import sys
import os
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import yaml
from loguru import logger
from torch.utils.data import DataLoader
from tqdm import tqdm

# Add sleepfm-clinical to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sleepfm-clinical" / "sleepfm"))
from models.models import SleepEventLSTMClassifier

import numpy as np

from src.dataset import SleepEDFDataset, collate_fn


def load_config():
    config_path = Path(__file__).resolve().parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def masked_cross_entropy_loss(outputs, y_data, mask, class_weights):
    """Cross entropy loss with masking for padded positions.

    outputs: (B, S, num_classes)
    y_data:  (B, S)
    mask:    (B, C, S) — we use mask[:, 0, :] for temporal mask
    class_weights: list of floats
    """
    B, seq_len, num_classes = outputs.shape
    outputs = outputs.float().reshape(B * seq_len, num_classes)
    y_data = y_data.reshape(B * seq_len).long()

    # Use temporal mask (first channel dimension)
    if mask.dim() == 3:
        temporal_mask = mask[:, 0, :]  # (B, S)
    else:
        temporal_mask = mask
    temporal_mask = temporal_mask.reshape(B * seq_len)

    weights_tensor = torch.tensor(class_weights, device=outputs.device, dtype=torch.float32)
    loss = F.cross_entropy(outputs, y_data, weight=weights_tensor, reduction="none")

    # mask == 0 means real data
    loss = loss * (temporal_mask == 0).float()
    num_valid = (temporal_mask == 0).float().sum()

    if num_valid > 0:
        return loss.sum() / num_valid
    return loss.sum()


def train_one_epoch(model, loader, optimizer, device, config, epoch, num_epochs, scaler=None):
    model.train()
    running_loss = 0.0
    log_interval = config.get("log_interval", 10)
    use_amp = scaler is not None

    for i, (x_data, y_data, padded_mask, _) in enumerate(
        tqdm(loader, desc=f"Epoch {epoch + 1}/{num_epochs}")
    ):
        x_data = x_data.to(device)
        y_data = y_data.to(device)
        padded_mask = padded_mask.to(device)

        with torch.amp.autocast("cuda", enabled=use_amp):
            outputs, mask = model(x_data, padded_mask)
            loss = masked_cross_entropy_loss(outputs, y_data, mask, config["class_weights"])

        if use_amp:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()
        optimizer.zero_grad()

        running_loss += loss.item()

        if (i + 1) % log_interval == 0:
            avg_loss = running_loss / (i + 1)
            logger.info(
                f"Epoch [{epoch + 1}/{num_epochs}], "
                f"Step [{i + 1}/{len(loader)}], Loss: {avg_loss:.4f}"
            )

    return running_loss / max(len(loader), 1)


def validate(model, loader, device, config, use_amp=False):
    model.eval()
    val_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for x_data, y_data, padded_mask, _ in loader:
            x_data = x_data.to(device)
            y_data = y_data.to(device)
            padded_mask = padded_mask.to(device)

            with torch.amp.autocast("cuda", enabled=use_amp):
                outputs, mask = model(x_data, padded_mask)
            loss = masked_cross_entropy_loss(outputs, y_data, mask, config["class_weights"])
            val_loss += loss.item()

            # Accuracy on non-padded positions
            if mask.dim() == 3:
                temporal_mask = mask[:, 0, :]
            else:
                temporal_mask = mask
            valid = temporal_mask == 0

            preds = outputs.argmax(dim=-1)
            correct += ((preds == y_data.long()) & valid).sum().item()
            total += valid.sum().item()

    avg_loss = val_loss / max(len(loader), 1)
    accuracy = correct / max(total, 1)
    return avg_loss, accuracy


def main():
    config = load_config()
    project_root = Path(__file__).resolve().parent.parent
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # Directories
    processed_dir = str(project_root / config["processed_dir"])
    save_dir = project_root / config["save_dir"]
    save_dir.mkdir(parents=True, exist_ok=True)

    # Datasets
    train_dataset = SleepEDFDataset(
        processed_dir, config["train_subjects"], config, augment=True
    )
    val_dataset = SleepEDFDataset(
        processed_dir, config["val_subjects"], config, augment=False
    )

    # Compute class weights
    if config["class_weights"] == "auto":
        all_labels = np.concatenate([s["y_epochs"] for s in train_dataset.subjects])
        num_classes = config["num_classes"]
        counts = np.bincount(all_labels.astype(int), minlength=num_classes).astype(float)
        counts = np.maximum(counts, 1.0)  # avoid div-by-zero
        inv_freq = 1.0 / counts
        # Normalize so mean weight = 1.0
        weights = inv_freq / inv_freq.mean()
        config["class_weights"] = weights.tolist()
        logger.info(f"Auto class weights (inv-freq): {dict(zip(['W','R','N1','N2','N3'], [f'{w:.2f}' for w in weights]))}")
    else:
        logger.info(f"Manual class weights: {config['class_weights']}")

    batch_size = config["batch_size"]
    num_workers = config.get("num_workers", 4)

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, collate_fn=collate_fn,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, collate_fn=collate_fn,
    )

    # Model
    model_params = config["model_params"]
    model = SleepEventLSTMClassifier(**model_params).to(device)
    logger.info(f"Model: SleepEventLSTMClassifier")
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Trainable parameters: {total_params / 1e6:.2f}M")

    # Optimizer + scheduler
    optimizer = optim.AdamW(model.parameters(), lr=config["lr"])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=config.get("scheduler_factor", 0.5),
        patience=config.get("scheduler_patience", 3),
    )

    # Mixed precision
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda") if use_amp else None

    # Training loop
    num_epochs = config["epochs"]
    best_val_loss = float("inf")
    training_log = []

    for epoch in range(num_epochs):
        train_loss = train_one_epoch(
            model, train_loader, optimizer, device, config, epoch, num_epochs, scaler
        )

        val_loss, val_acc = validate(model, val_loader, device, config, use_amp)
        scheduler.step(val_loss)

        current_lr = optimizer.param_groups[0]["lr"]
        log_entry = (
            f"Epoch {epoch + 1}/{num_epochs} — "
            f"Train Loss: {train_loss:.4f}, "
            f"Val Loss: {val_loss:.4f}, "
            f"Val Acc: {val_acc:.4f}, "
            f"LR: {current_lr:.6f}"
        )
        logger.info(log_entry)
        training_log.append(log_entry)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_path = save_dir / "best.pth"
            torch.save(model.state_dict(), best_path)
            logger.info(f"Best model saved at {best_path}")

        # Periodic checkpoint
        checkpoint_path = save_dir / "checkpoint.pth"
        torch.save(
            {
                "epoch": epoch + 1,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
                "val_acc": val_acc,
            },
            checkpoint_path,
        )

    # Save training log
    log_path = save_dir / "training_log.txt"
    with open(log_path, "w") as f:
        f.write("\n".join(training_log))

    # Save config
    config_save_path = save_dir / "config.yaml"
    with open(config_save_path, "w") as f:
        yaml.dump(config, f)

    logger.info(f"Training complete! Best val loss: {best_val_loss:.4f}")


if __name__ == "__main__":
    main()
