"""Preprocess Sleep-EDF EDF files into embedded HDF5 + CSV labels.

Pipeline:
1. Read raw PSG EDF → extract 5 usable channels
2. Resample 100Hz → 128Hz, z-score normalize per channel
3. Parse companion hypnogram EDF+ → 30s epoch labels
4. Create 23-channel padded tensor (grouped by BAS/RESP/EKG/EMG)
5. Embed using pretrained SetTransformer tokenizer + spatial pooling
6. Save per-modality-group embeddings to HDF5 + epoch labels to CSV
"""

import sys
import os
from pathlib import Path

import h5py
import mne
import numpy as np
import pandas as pd
import torch
import yaml
from loguru import logger
from scipy.signal import resample

from src.channel_map import (
    GROUP_ORDER,
    GROUP_SIZES,
    SKIP_CHANNELS,
    SLEEP_EDF_MAPPING,
    get_channel_indices,
)

# Add sleepfm-clinical to path for model imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sleepfm-clinical" / "sleepfm"))
from models.models import SetTransformer


def load_config():
    config_path = Path(__file__).resolve().parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def safe_standardize(signal: np.ndarray) -> np.ndarray:
    mean = np.mean(signal)
    std = np.std(signal)
    if std == 0:
        return signal - mean
    return (signal - mean) / std


def read_psg_edf(edf_path: str) -> dict[str, np.ndarray]:
    """Read PSG EDF and return dict of channel_name → signal array."""
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    channels = {}
    for ch_name in raw.ch_names:
        if ch_name in SKIP_CHANNELS:
            continue
        if ch_name in SLEEP_EDF_MAPPING:
            channels[ch_name] = raw.get_data(picks=[ch_name])[0]
    return channels, raw.info["sfreq"]


def parse_hypnogram(hypnogram_path: str, config: dict) -> np.ndarray:
    """Parse Sleep-EDF hypnogram EDF+ annotations into integer labels per 30s epoch."""
    raw_annot = mne.read_annotations(hypnogram_path)
    stage_mapping = config["stage_mapping"]
    drop_stages = set(config["drop_stages"])

    epochs = []
    for annot in raw_annot:
        description = annot["description"].strip()
        if description in drop_stages:
            epochs.append(-1)  # placeholder, will be filtered
        elif description in stage_mapping:
            duration = annot["duration"]
            num_epochs = int(duration / 30)
            for _ in range(num_epochs):
                epochs.append(stage_mapping[description])
        else:
            # Unknown annotation, skip
            epochs.append(-1)

    return np.array(epochs)


def resample_and_normalize(
    channels: dict[str, np.ndarray],
    original_freq: float,
    target_freq: int,
) -> dict[str, np.ndarray]:
    """Resample all channels to target_freq and z-score normalize."""
    result = {}
    for ch_name, signal in channels.items():
        duration = len(signal) / original_freq
        new_n_samples = int(duration * target_freq)
        resampled = resample(signal, new_n_samples)
        result[ch_name] = safe_standardize(resampled)
    return result


def build_modality_tensors(
    channels: dict[str, np.ndarray],
    total_samples: int,
) -> dict[str, np.ndarray]:
    """Build per-modality-group arrays with zero-padding for missing channels.

    Returns dict: group_name → array of shape (num_channels_in_group, total_samples).
    """
    channel_indices = get_channel_indices()
    group_offsets = {}
    offset = 0
    for group in GROUP_ORDER:
        group_offsets[group] = offset
        offset += GROUP_SIZES[group]

    tensors = {}
    for group in GROUP_ORDER:
        n_ch = GROUP_SIZES[group]
        arr = np.zeros((n_ch, total_samples), dtype=np.float32)
        tensors[group] = arr

    for ch_name, signal in channels.items():
        group, slot = SLEEP_EDF_MAPPING[ch_name]
        # Trim or pad signal to match total_samples
        n = min(len(signal), total_samples)
        tensors[group][slot, :n] = signal[:n]

    return tensors


def embed_modality_groups(
    modality_tensors: dict[str, np.ndarray],
    pretrained_model: SetTransformer,
    device: torch.device,
    patch_size: int = 640,
) -> dict[str, np.ndarray]:
    """Run pretrained SetTransformer tokenizer + spatial pooling per modality group.

    For each group, creates per-channel tokenized embeddings, then pools across
    channels to produce (num_patches, embed_dim) embedding.
    """
    embeddings = {}

    with torch.no_grad():
        for group in GROUP_ORDER:
            arr = modality_tensors[group]  # (num_channels, total_samples)
            n_ch, total_samples = arr.shape

            # Skip groups with no real channels (e.g. EKG in Sleep-EDF)
            has_any_data = any(arr[ch].any() for ch in range(n_ch))
            if not has_any_data:
                num_patches = (total_samples // patch_size) * patch_size // patch_size
                embed_dim = pretrained_model.patch_embedding.output_size
                logger.info(f"Group {group}: no real channels, outputting zeros ({num_patches}, {embed_dim})")
                embeddings[group] = np.zeros((num_patches, embed_dim), dtype=np.float32)
                continue

            # Trim to multiple of patch_size
            usable_samples = (total_samples // patch_size) * patch_size
            if usable_samples == 0:
                logger.warning(f"Group {group}: not enough samples for a single patch")
                continue
            arr = arr[:, :usable_samples]

            # Create input tensor: (1, num_channels, usable_samples)
            x = torch.from_numpy(arr).float().unsqueeze(0).to(device)

            # Tokenize: (1, num_channels, usable_samples) → (1, num_channels, num_patches, embed_dim)
            tokens = pretrained_model.patch_embedding(x)
            B, C, S, E = tokens.shape

            # Build channel mask: True for zero-padded channels (no real signal)
            # A channel is "zero-padded" if its data is all zeros
            channel_has_data = torch.tensor(
                [arr[ch].any() for ch in range(n_ch)], dtype=torch.bool, device=device
            )
            # mask: True = padded (to mask out), False = real
            channel_mask = ~channel_has_data  # (num_channels,)

            # Spatial pooling across channels for each time step
            # Reshape: (B*S, C, E)
            tokens_flat = tokens.squeeze(0).permute(1, 0, 2)  # (S, C, E)
            mask_expanded = channel_mask.unsqueeze(0).expand(S, -1)  # (S, C)

            pooled = pretrained_model.spatial_pooling(tokens_flat, mask_expanded)  # (S, E)
            embeddings[group] = pooled.cpu().numpy()

    return embeddings


def load_pretrained_set_transformer(config: dict, device: torch.device) -> SetTransformer:
    """Load the pretrained SetTransformer model."""
    checkpoint_path = Path(__file__).resolve().parent.parent / config["pretrained_checkpoint"]
    pretrained_config_path = checkpoint_path.parent / "config.json"

    import json
    with open(pretrained_config_path) as f:
        pt_config = json.load(f)

    model = SetTransformer(
        in_channels=pt_config["in_channels"],
        patch_size=pt_config["patch_size"],
        embed_dim=pt_config["embed_dim"],
        num_heads=pt_config["num_heads"],
        num_layers=pt_config["num_layers"],
        pooling_head=pt_config["pooling_head"],
        dropout=pt_config["dropout"],
        max_seq_length=8196,
    )

    state_dict = torch.load(checkpoint_path, map_location=device, weights_only=False)
    # Handle potential DataParallel prefix
    cleaned = {}
    for k, v in state_dict.items():
        cleaned[k.replace("module.", "")] = v
    model.load_state_dict(cleaned, strict=False)
    model.to(device)
    model.eval()
    return model


def process_subject(
    psg_path: str,
    hypnogram_path: str,
    subject_id: str,
    config: dict,
    pretrained_model: SetTransformer,
    device: torch.device,
    output_dir: Path,
):
    """Process a single subject: EDF → embedded HDF5 + labels CSV."""
    logger.info(f"Processing {subject_id}: {psg_path}")

    # 1. Read raw EDF channels
    channels, original_freq = read_psg_edf(psg_path)
    logger.info(f"  Found {len(channels)} channels at {original_freq}Hz")

    # 2. Resample and normalize
    target_freq = config["sampling_freq"]
    channels = resample_and_normalize(channels, original_freq, target_freq)

    # 3. Parse hypnogram
    labels = parse_hypnogram(hypnogram_path, config)

    # 4. Filter out invalid epochs (label == -1)
    valid_mask = labels != -1
    valid_labels = labels[valid_mask]

    # 4b. Trim excessive Wake epochs — keep only sleep period + buffer
    wake_trim_buffer = config.get("wake_trim_buffer_epochs", 30)  # 15 min each side
    non_wake_indices = np.where(valid_labels != 0)[0]
    if len(non_wake_indices) > 0:
        sleep_start = max(0, non_wake_indices[0] - wake_trim_buffer)
        sleep_end = min(len(valid_labels), non_wake_indices[-1] + 1 + wake_trim_buffer)
        trimmed_labels = valid_labels[sleep_start:sleep_end]
        logger.info(
            f"  Wake trimming: {len(valid_labels)} → {len(trimmed_labels)} epochs "
            f"(kept epochs {sleep_start}–{sleep_end})"
        )
        # Adjust signal to match trimmed epoch range
        samples_per_epoch = target_freq * config["epoch_duration_sec"]  # 3840
        trim_start_sample = sleep_start * samples_per_epoch
        trim_end_sample = sleep_end * samples_per_epoch
        channels = {
            ch: sig[trim_start_sample:trim_end_sample]
            for ch, sig in channels.items()
        }
        valid_labels = trimmed_labels

    # 5. Build per-modality tensors
    total_samples = min(len(sig) for sig in channels.values())
    modality_tensors = build_modality_tensors(channels, total_samples)

    # 6. Embed using pretrained model
    patch_size = 640  # from pretrained config
    embeddings = embed_modality_groups(modality_tensors, pretrained_model, device, patch_size)

    # 7. Align embeddings with epoch labels
    # Each patch covers patch_size/target_freq seconds = 5 seconds
    # Each epoch is 30 seconds = 6 patches
    patches_per_epoch = 30 * target_freq // patch_size  # 6
    num_complete_epochs = min(
        len(valid_labels),
        min(emb.shape[0] for emb in embeddings.values()) // patches_per_epoch,
    )
    valid_labels = valid_labels[:num_complete_epochs]

    # Trim embeddings to align with labels
    max_patches = num_complete_epochs * patches_per_epoch
    for group in GROUP_ORDER:
        embeddings[group] = embeddings[group][:max_patches]

    logger.info(f"  {num_complete_epochs} valid epochs, {max_patches} patches")

    # 8. Save HDF5 (per-modality embeddings)
    output_dir.mkdir(parents=True, exist_ok=True)
    hdf5_path = output_dir / f"{subject_id}.hdf5"
    with h5py.File(hdf5_path, "w") as hf:
        for group in GROUP_ORDER:
            hf.create_dataset(group, data=embeddings[group], dtype="float32")

    # 9. Save labels CSV
    csv_path = output_dir / f"{subject_id}.csv"
    df = pd.DataFrame({"Epoch": range(num_complete_epochs), "StageNumber": valid_labels})
    df.to_csv(csv_path, index=False)

    logger.info(f"  Saved {hdf5_path} and {csv_path}")


def find_subject_files(data_dir: Path) -> list[tuple[str, str, str]]:
    """Find PSG/Hypnogram EDF pairs in the data directory.

    Returns list of (psg_path, hypnogram_path, subject_id).
    """
    psg_files = sorted(data_dir.glob("*-PSG.edf"))
    pairs = []
    for psg_path in psg_files:
        subject_id = psg_path.name[:6]  # e.g., "SC4001"
        # Find matching hypnogram
        hypno_files = list(data_dir.glob(f"{subject_id}*-Hypnogram.edf"))
        if hypno_files:
            pairs.append((str(psg_path), str(hypno_files[0]), subject_id))
        else:
            logger.warning(f"No hypnogram found for {subject_id}")
    return pairs


def main():
    config = load_config()
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / config["data_dir"]
    output_dir = project_root / config["processed_dir"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # Load pretrained model
    pretrained_model = load_pretrained_set_transformer(config, device)
    logger.info("Loaded pretrained SetTransformer")

    # Find and process all subjects
    pairs = find_subject_files(data_dir)
    logger.info(f"Found {len(pairs)} subjects")

    for psg_path, hypno_path, subject_id in pairs:
        process_subject(
            psg_path, hypno_path, subject_id,
            config, pretrained_model, device, output_dir,
        )

    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
