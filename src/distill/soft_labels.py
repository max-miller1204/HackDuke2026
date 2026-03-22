"""Generate and cache teacher soft labels for distillation.

Runs the teacher (SleepEventLSTMClassifier) on full recordings — no windowing —
so the biLSTM sees maximum temporal context. Caches raw logits as .npy per subject.
Students later slice into these cached logits at their window's patch indices.
"""

import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import torch
import yaml
from loguru import logger

# Add sleepfm-clinical to path
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "sleepfm-clinical" / "sleepfm"))
from models.models import SleepEventLSTMClassifier

from src.channel_map import GROUP_ORDER


def load_distill_config():
    config_path = Path(__file__).resolve().parent / "config_distill.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_teacher(config, device):
    """Load the finetuned teacher model."""
    project_root = Path(__file__).resolve().parent.parent.parent
    teacher_params = config["teacher"]["model_params"]
    model = SleepEventLSTMClassifier(**teacher_params).to(device)

    checkpoint_path = project_root / config["teacher"]["checkpoint"]
    state_dict = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()

    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Teacher loaded: {total_params / 1e6:.2f}M params from {checkpoint_path}")
    return model


def generate_soft_labels(config=None, device=None):
    """Generate teacher logits for all subjects and cache as .npy files.

    Args:
        config: Distillation config dict. Loaded from yaml if None.
        device: Torch device. Auto-detected if None.
    """
    if config is None:
        config = load_distill_config()
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    project_root = Path(__file__).resolve().parent.parent.parent
    processed_dir = project_root / config["data"]["processed_dir"]
    output_dir = project_root / config["data"]["teacher_logits_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    # All subjects
    all_subjects = (
        config["data"]["train_subjects"]
        + config["data"]["val_subjects"]
        + config["data"]["test_subjects"]
    )

    teacher = load_teacher(config, device)
    max_channels = config["max_channels"]

    for subject_id in all_subjects:
        output_path = output_dir / f"{subject_id}.npy"
        if output_path.exists():
            logger.info(f"Skipping {subject_id} — cached logits exist at {output_path}")
            continue

        hdf5_path = processed_dir / f"{subject_id}.hdf5"
        if not hdf5_path.exists():
            logger.warning(f"Missing HDF5 for {subject_id}, skipping")
            continue

        # Load full recording embeddings
        x_data = []
        with h5py.File(hdf5_path, "r") as hf:
            for group in GROUP_ORDER:
                if group in hf:
                    x_data.append(hf[group][:])
                else:
                    ref_shape = x_data[0].shape if x_data else (1, 128)
                    x_data.append(np.zeros(ref_shape, dtype=np.float32))
        x_data = np.stack(x_data)  # (C, S, E)

        C, S, E = x_data.shape
        max_seq = config["teacher"]["model_params"]["max_seq_length"]

        # Chunk long recordings to fit within teacher's positional encoding limit.
        # Use 50% overlap and average logits in overlapping regions so the biLSTM
        # still gets good context at chunk boundaries.
        stride = max_seq // 2
        all_logits = np.zeros((S, config["num_classes"]), dtype=np.float64)
        counts = np.zeros(S, dtype=np.float64)

        with torch.no_grad(), torch.amp.autocast("cuda", enabled=device.type == "cuda"):
            start = 0
            while start < S:
                end = min(start + max_seq, S)
                chunk = torch.tensor(
                    x_data[:, start:end, :], dtype=torch.float32
                ).unsqueeze(0).to(device)
                chunk_mask = torch.zeros(1, max_channels, end - start, device=device)
                chunk_logits, _ = teacher(chunk, chunk_mask)
                chunk_np = chunk_logits.squeeze(0).cpu().float().numpy()
                all_logits[start:end] += chunk_np
                counts[start:end] += 1.0
                if end >= S:
                    break
                start += stride

        logits_np = (all_logits / counts[:, None]).astype(np.float32)
        np.save(output_path, logits_np)
        logger.info(f"Cached teacher logits for {subject_id}: shape {logits_np.shape} → {output_path}")

    logger.info(f"Soft label generation complete. Output dir: {output_dir}")


if __name__ == "__main__":
    generate_soft_labels()
