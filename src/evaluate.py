"""Evaluation script for finetuned SleepFM on Sleep-EDF.

Loads best checkpoint, runs inference on test subject, computes:
- Per-class accuracy + confusion matrix
- Sleep quality score (0-100)
"""

import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from loguru import logger
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sleepfm-clinical" / "sleepfm"))
from models.models import SleepEventLSTMClassifier

from src.dataset import SleepEDFDataset, collate_fn


STAGE_NAMES = ["Wake", "REM", "N1", "N2", "N3"]


def load_config():
    config_path = Path(__file__).resolve().parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def compute_sleep_quality_score(predictions: np.ndarray) -> float:
    """Rule-based sleep quality score from staging predictions.

    Score = 70% sleep_efficiency + 20% deep_sleep_ratio + 10% rem_ratio
    Range: 0-100

    Stage mapping: W=0, R=1, N1=2, N2=3, N3=4
    """
    total_epochs = len(predictions)
    if total_epochs == 0:
        return 0.0

    wake_epochs = (predictions == 0).sum()
    rem_epochs = (predictions == 1).sum()
    n3_epochs = (predictions == 4).sum()
    sleep_epochs = total_epochs - wake_epochs

    # Sleep efficiency: ratio of sleep to total time
    sleep_efficiency = sleep_epochs / total_epochs

    # Deep sleep ratio: N3 as fraction of total sleep
    deep_sleep_ratio = n3_epochs / max(sleep_epochs, 1)

    # REM ratio: REM as fraction of total sleep
    rem_ratio = rem_epochs / max(sleep_epochs, 1)

    # Weighted score (0-100)
    score = (
        0.70 * min(sleep_efficiency, 1.0)
        + 0.20 * min(deep_sleep_ratio / 0.25, 1.0)  # ~25% deep sleep is ideal
        + 0.10 * min(rem_ratio / 0.25, 1.0)  # ~25% REM is ideal
    ) * 100

    return round(min(max(score, 0), 100), 1)


def evaluate_model(model, loader, device):
    """Run inference and collect predictions + ground truth."""
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for x_data, y_data, padded_mask, _ in loader:
            x_data = x_data.to(device)
            padded_mask = padded_mask.to(device)

            outputs, mask = model(x_data, padded_mask)

            # Get temporal mask
            if mask.dim() == 3:
                temporal_mask = mask[:, 0, :]
            else:
                temporal_mask = mask

            preds = outputs.argmax(dim=-1)

            # Collect only non-padded predictions
            for b in range(preds.shape[0]):
                valid = temporal_mask[b] == 0
                all_preds.append(preds[b][valid].cpu().numpy())
                all_labels.append(y_data[b][valid.cpu()].long().numpy())

    return np.concatenate(all_preds), np.concatenate(all_labels)


def main():
    config = load_config()
    project_root = Path(__file__).resolve().parent.parent
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load model
    model_params = config["model_params"]
    model = SleepEventLSTMClassifier(**model_params).to(device)

    checkpoint_path = project_root / config["save_dir"] / "best.pth"
    if not checkpoint_path.exists():
        logger.error(f"No checkpoint found at {checkpoint_path}")
        return

    state_dict = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(state_dict)
    logger.info(f"Loaded checkpoint from {checkpoint_path}")

    # Test dataset
    processed_dir = str(project_root / config["processed_dir"])
    test_dataset = SleepEDFDataset(
        processed_dir, config["test_subjects"], config, augment=False
    )
    test_loader = DataLoader(
        test_dataset, batch_size=1, shuffle=False,
        num_workers=0, collate_fn=collate_fn,
    )

    # Run evaluation
    predictions, labels = evaluate_model(model, test_loader, device)
    logger.info(f"Evaluated {len(predictions)} epochs")

    # Classification report
    report = classification_report(
        labels, predictions, target_names=STAGE_NAMES, zero_division=0
    )
    logger.info(f"\nClassification Report:\n{report}")

    # Confusion matrix
    cm = confusion_matrix(labels, predictions, labels=list(range(5)))
    logger.info(f"\nConfusion Matrix:\n{cm}")

    # Overall accuracy
    acc = accuracy_score(labels, predictions)
    logger.info(f"Overall Accuracy: {acc:.4f}")

    # Sleep quality score
    quality_score = compute_sleep_quality_score(predictions)
    logger.info(f"Sleep Quality Score: {quality_score}/100")

    # Save results
    save_dir = project_root / config["save_dir"]
    results = {
        "accuracy": float(acc),
        "sleep_quality_score": quality_score,
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "num_epochs_evaluated": len(predictions),
    }

    import json
    results_path = save_dir / "evaluation_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {results_path}")


if __name__ == "__main__":
    main()
