"""Distillation dataset: extends SleepEDFDataset with cached teacher soft labels.

Loads pre-cached teacher logits (.npy) alongside the standard HDF5 embeddings
and CSV labels. Windows slice into both the embeddings and the cached logits
at the same patch indices.
"""

from pathlib import Path

import numpy as np
import torch
from loguru import logger

from src.dataset import SleepEDFDataset, PATCHES_PER_EPOCH


class DistillSleepEDFDataset(SleepEDFDataset):
    """SleepEDFDataset extended with teacher soft labels for distillation.

    Each sample additionally returns teacher logits for the window's patches.
    """

    def __init__(self, processed_dir, subject_ids, config, augment=False,
                 teacher_logits_dir=None):
        """
        Args:
            processed_dir: Path to HDF5/CSV files.
            subject_ids: List of subject IDs.
            config: Distillation config dict (uses 'windowing' key for windows).
            augment: Whether to apply augmentations.
            teacher_logits_dir: Path to cached teacher logits. If None, uses
                config["data"]["teacher_logits_dir"].
        """
        # Initialize base dataset (loads embeddings + labels, builds index)
        super().__init__(processed_dir, subject_ids, config, augment=augment)

        # Load cached teacher logits
        project_root = Path(__file__).resolve().parent.parent.parent
        if teacher_logits_dir is None:
            teacher_logits_dir = project_root / config["data"]["teacher_logits_dir"]
        else:
            teacher_logits_dir = Path(teacher_logits_dir)

        self.teacher_logits = []
        for i, subj in enumerate(self.subjects):
            subject_id = Path(subj["path"]).stem
            logits_path = teacher_logits_dir / f"{subject_id}.npy"
            if logits_path.exists():
                logits = np.load(logits_path)  # (S, num_classes)
                self.teacher_logits.append(logits)
            else:
                logger.warning(
                    f"No cached teacher logits for {subject_id} at {logits_path}. "
                    f"Using zeros — run soft_labels.py first."
                )
                num_patches = subj["x_data"].shape[1]
                num_classes = config["num_classes"]
                self.teacher_logits.append(np.zeros((num_patches, num_classes), dtype=np.float32))

    def __getitem__(self, idx):
        subj_idx, start_p, end_p = self.index_map[idx]
        subj = self.subjects[subj_idx]

        # Slice window — same as parent
        x_data = torch.tensor(
            subj["x_data"][:, start_p:end_p, :], dtype=torch.float32
        )

        # Epoch-level labels → patch-level
        start_epoch = start_p // PATCHES_PER_EPOCH
        end_epoch = (end_p + PATCHES_PER_EPOCH - 1) // PATCHES_PER_EPOCH
        y_epochs = subj["y_epochs"][start_epoch:end_epoch]
        y_data = np.repeat(y_epochs, PATCHES_PER_EPOCH)
        y_data = y_data[: x_data.shape[1]]
        y_data = torch.tensor(y_data, dtype=torch.float32)

        # Slice teacher logits for the same window
        teacher_logits = torch.tensor(
            self.teacher_logits[subj_idx][start_p:end_p], dtype=torch.float32
        )

        # Apply augmentations if training (to embeddings only, not teacher logits)
        if self.augment:
            from src.augment import apply_augmentations
            C, S, E = x_data.shape
            mask = torch.zeros(C, S)
            x_data, mask = apply_augmentations(x_data, mask, self.aug_config)

        return x_data, y_data, teacher_logits, self.max_channels, self.max_seq_len, subj["path"]


def distill_collate_fn(batch):
    """Collate function that pads teacher logits alongside x/y data.

    Returns: (x_data, y_data, teacher_logits, padded_mask, hdf5_path_list)
    """
    x_data, y_data, teacher_logits, max_channels_list, max_seq_len_list, hdf5_path_list = zip(*batch)

    num_channels = max(max_channels_list)
    max_seq_len_temp = max(item.size(1) for item in x_data)
    max_seq_len = (
        max_seq_len_temp
        if max_seq_len_list[0] is None
        else min(max_seq_len_temp, max_seq_len_list[0])
    )
    num_classes = teacher_logits[0].size(-1)

    padded_x_data = []
    padded_y_data = []
    padded_teacher = []
    padded_mask = []

    for x_item, y_item, t_item in zip(x_data, y_data, teacher_logits):
        c, s, e = x_item.size()
        c = min(c, num_channels)
        s = min(s, max_seq_len)

        # Pad embeddings
        padded_x = torch.zeros((num_channels, max_seq_len, e))
        mask = torch.ones((num_channels, max_seq_len))
        padded_x[:c, :s, :e] = x_item[:c, :s, :e]
        mask[:c, :s] = 0  # 0 = real, 1 = padded

        # Pad labels
        padded_y = torch.zeros(max_seq_len)
        padded_y[:s] = y_item[:s]

        # Pad teacher logits
        padded_t = torch.zeros((max_seq_len, num_classes))
        t_len = min(t_item.size(0), s)
        padded_t[:t_len] = t_item[:t_len]

        padded_x_data.append(padded_x)
        padded_y_data.append(padded_y)
        padded_teacher.append(padded_t)
        padded_mask.append(mask)

    return (
        torch.stack(padded_x_data),      # (B, C, S, E)
        torch.stack(padded_y_data),       # (B, S)
        torch.stack(padded_teacher),      # (B, S, num_classes)
        torch.stack(padded_mask),         # (B, C, S)
        hdf5_path_list,
    )
