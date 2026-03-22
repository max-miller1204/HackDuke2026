"""Dataset for Sleep-EDF finetuning with SleepEventLSTMClassifier.

Loads pre-embedded HDF5 files (per-modality-group embeddings) + CSV labels.
Matches the interface expected by sleep_event_finetune_full_collate_fn.
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


class SleepEDFDataset(Dataset):
    """Dataset for Sleep-EDF embedded data.

    Each sample returns (x_data, y_data, max_channels, max_seq_len, hdf5_path)
    matching the interface of SleepEventClassificationDataset.
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
        self.context = -1  # load full recording

        self.index_map = []
        processed_path = Path(processed_dir)

        for subject_id in subject_ids:
            hdf5_path = processed_path / f"{subject_id}.hdf5"
            csv_path = processed_path / f"{subject_id}.csv"

            if not hdf5_path.exists() or not csv_path.exists():
                logger.warning(f"Missing files for {subject_id}, skipping")
                continue

            self.index_map.append((str(hdf5_path), str(csv_path)))

        logger.info(f"SleepEDFDataset: {len(self.index_map)} subjects loaded")

    def __len__(self):
        return len(self.index_map)

    def __getitem__(self, idx):
        hdf5_path, csv_path = self.index_map[idx]

        # Load labels
        labels_df = pd.read_csv(csv_path)
        y_data = labels_df["StageNumber"].to_numpy()

        # Load per-modality embeddings
        x_data = []
        with h5py.File(hdf5_path, "r") as hf:
            for group in GROUP_ORDER:
                if group in hf:
                    x_data.append(hf[group][:])
                else:
                    logger.warning(f"Missing group {group} in {hdf5_path}")
                    # Create zeros with shape matching other groups
                    ref_shape = x_data[0].shape if x_data else (1, 128)
                    x_data.append(np.zeros(ref_shape, dtype=np.float32))

        # Stack: (C=4, S=num_patches, E=embed_dim)
        x_data = np.stack(x_data)
        x_data = torch.tensor(x_data, dtype=torch.float32)
        y_data = torch.tensor(y_data, dtype=torch.float32)

        # Apply augmentations if training
        if self.augment:
            # Create a basic mask (all real for our data since all 4 groups exist)
            C, S, E = x_data.shape
            mask = torch.zeros(C, S)
            x_data, mask = apply_augmentations(x_data, mask, self.aug_config)

        return x_data, y_data, self.max_channels, self.max_seq_len, hdf5_path


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
