"""Dataset for Sleep-EDF finetuning with SleepEventLSTMClassifier.

Loads pre-embedded HDF5 files (per-modality-group embeddings) + CSV labels.
Supports windowed slicing and minority-class oversampling for training.
"""

import os
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from loguru import logger

from src.augment import apply_augmentations
from src.channel_map import GROUP_ORDER

# 6 patches per 30s epoch (128Hz, patch_size=640 → 5s per patch)
PATCHES_PER_EPOCH = 6


class SleepEDFDataset(Dataset):
    """Dataset for Sleep-EDF embedded data.

    When window_epochs > 0 (training), slices recordings into fixed-length
    windows and oversamples windows containing minority sleep stages.
    When window_epochs <= 0 (val/test), returns full recordings.
    """

    def __init__(
        self,
        processed_dir: str,
        subject_ids: list[str],
        config: dict,
        augment: bool = False,
    ):
        self.config = config
        self.augment = augment
        self.max_channels = config["max_channels"]  # 4 (modality groups)
        self.max_seq_len = config["model_params"]["max_seq_length"]
        self.aug_config = config.get("augmentation", {})

        window_config = config.get("windowing", {})
        self.window_epochs = window_config.get("window_epochs", 0) if augment else 0
        self.window_stride_epochs = window_config.get("stride_epochs", 0)
        self.oversample_factor = window_config.get("oversample_factor", 3) if augment else 1
        # Minority classes: REM=1, N1=2, N3=4
        self.minority_classes = set(window_config.get("minority_classes", [1, 2, 4]))

        # Load all subject data into memory
        self.subjects = []
        processed_path = Path(processed_dir)

        for subject_id in subject_ids:
            hdf5_path = processed_path / f"{subject_id}.hdf5"
            csv_path = processed_path / f"{subject_id}.csv"

            if not hdf5_path.exists() or not csv_path.exists():
                logger.warning(f"Missing files for {subject_id}, skipping")
                continue

            # Load embeddings
            x_data = []
            with h5py.File(hdf5_path, "r") as hf:
                for group in GROUP_ORDER:
                    if group in hf:
                        x_data.append(hf[group][:])
                    else:
                        ref_shape = x_data[0].shape if x_data else (1, 128)
                        x_data.append(np.zeros(ref_shape, dtype=np.float32))
            x_data = np.stack(x_data)  # (C, S, E)

            # Load epoch labels
            labels_df = pd.read_csv(csv_path)
            y_epochs = labels_df["StageNumber"].to_numpy()

            self.subjects.append({
                "x_data": x_data,
                "y_epochs": y_epochs,
                "path": str(hdf5_path),
            })

        # Build index
        if self.window_epochs > 0 and len(self.subjects) > 0:
            self._build_windowed_index()
        else:
            self._build_full_index()

        logger.info(
            f"SleepEDFDataset: {len(self.subjects)} subjects, "
            f"{len(self.index_map)} samples"
            f"{' (windowed + oversampled)' if self.window_epochs > 0 else ''}"
        )

    def _build_full_index(self):
        """One sample per subject (val/test mode)."""
        self.index_map = []
        for i in range(len(self.subjects)):
            num_patches = self.subjects[i]["x_data"].shape[1]
            self.index_map.append((i, 0, num_patches))

    def _build_windowed_index(self):
        """Slice into windows and oversample minority-heavy ones."""
        window_patches = self.window_epochs * PATCHES_PER_EPOCH
        stride_epochs = self.window_stride_epochs or (self.window_epochs // 2)
        stride_patches = stride_epochs * PATCHES_PER_EPOCH

        self.index_map = []
        minority_windows = []

        for subj_idx, subj in enumerate(self.subjects):
            num_patches = subj["x_data"].shape[1]
            num_epochs = len(subj["y_epochs"])

            start_epoch = 0
            while start_epoch + self.window_epochs <= num_epochs:
                start_p = start_epoch * PATCHES_PER_EPOCH
                end_p = min(start_p + window_patches, num_patches)
                entry = (subj_idx, start_p, end_p)
                self.index_map.append(entry)

                # Check if window contains minority classes
                window_labels = subj["y_epochs"][start_epoch:start_epoch + self.window_epochs]
                has_minority = bool(set(window_labels.tolist()) & self.minority_classes)
                if has_minority:
                    minority_windows.append(entry)

                start_epoch += stride_epochs

        # Oversample minority windows
        if self.oversample_factor > 1 and minority_windows:
            extra = minority_windows * (self.oversample_factor - 1)
            logger.info(
                f"Oversampling: {len(minority_windows)} minority windows "
                f"x{self.oversample_factor} → +{len(extra)} samples"
            )
            self.index_map.extend(extra)

    def __len__(self):
        return len(self.index_map)

    def __getitem__(self, idx):
        subj_idx, start_p, end_p = self.index_map[idx]
        subj = self.subjects[subj_idx]

        # Slice window
        x_data = torch.tensor(
            subj["x_data"][:, start_p:end_p, :], dtype=torch.float32
        )

        # Get epoch-level labels for this window, then repeat to patch level
        start_epoch = start_p // PATCHES_PER_EPOCH
        end_epoch = (end_p + PATCHES_PER_EPOCH - 1) // PATCHES_PER_EPOCH
        y_epochs = subj["y_epochs"][start_epoch:end_epoch]
        y_data = np.repeat(y_epochs, PATCHES_PER_EPOCH)
        y_data = y_data[: x_data.shape[1]]
        y_data = torch.tensor(y_data, dtype=torch.float32)

        # Apply augmentations if training
        if self.augment:
            C, S, E = x_data.shape
            mask = torch.zeros(C, S)
            x_data, mask = apply_augmentations(x_data, mask, self.aug_config)

        return x_data, y_data, self.max_channels, self.max_seq_len, subj["path"]


def collate_fn(batch):
    """Collate function matching sleep_event_finetune_full_collate_fn interface.

    Returns: (x_data, y_data, padded_mask, hdf5_path_list)
    """
    x_data, y_data, max_channels_list, max_seq_len_list, hdf5_path_list = zip(*batch)

    num_channels = max(max_channels_list)
    max_seq_len_temp = max(item.size(1) for item in x_data)
    max_seq_len = (
        max_seq_len_temp
        if max_seq_len_list[0] is None
        else min(max_seq_len_temp, max_seq_len_list[0])
    )

    padded_x_data = []
    padded_y_data = []
    padded_mask = []

    for x_item, y_item in zip(x_data, y_data):
        c, s, e = x_item.size()
        c = min(c, num_channels)
        s = min(s, max_seq_len)

        padded_x = torch.zeros((num_channels, max_seq_len, e))
        mask = torch.ones((num_channels, max_seq_len))

        padded_x[:c, :s, :e] = x_item[:c, :s, :e]
        mask[:c, :s] = 0  # 0 = real, 1 = padded

        padded_y = torch.zeros(max_seq_len)
        padded_y[:s] = y_item[:s]

        padded_x_data.append(padded_x)
        padded_y_data.append(padded_y)
        padded_mask.append(mask)

    return (
        torch.stack(padded_x_data),
        torch.stack(padded_y_data),
        torch.stack(padded_mask),
        hdf5_path_list,
    )
