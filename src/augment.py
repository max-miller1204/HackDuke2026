"""Data augmentations for Sleep-EDF finetuning.

Applied only during training. Operates on embedded tensors.
"""

import torch
import numpy as np


def temporal_jitter(x: torch.Tensor, max_shift: int = 5) -> torch.Tensor:
    """Randomly shift temporal dimension by ±max_shift patches."""
    if max_shift == 0:
        return x
    shift = np.random.randint(-max_shift, max_shift + 1)
    if shift == 0:
        return x
    return torch.roll(x, shifts=shift, dims=0)


def gaussian_noise(x: torch.Tensor, std: float = 0.05) -> torch.Tensor:
    """Add Gaussian noise to embeddings."""
    if std <= 0:
        return x
    return x + torch.randn_like(x) * std


def random_channel_mask(
    x: torch.Tensor, mask: torch.Tensor, prob: float = 0.2
) -> tuple[torch.Tensor, torch.Tensor]:
    """Randomly zero out one non-padded channel with probability prob.

    x: (C, S, E)
    mask: (C, S) where 0=real, 1=padded
    """
    if np.random.rand() > prob:
        return x, mask

    # Find real channels (mask == 0 at first time step)
    real_channels = (mask[:, 0] == 0).nonzero(as_tuple=True)[0]
    if len(real_channels) <= 1:
        return x, mask

    # Pick one real channel to mask
    idx = real_channels[np.random.randint(len(real_channels))].item()
    x = x.clone()
    mask = mask.clone()
    x[idx] = 0.0
    mask[idx] = 1.0
    return x, mask


def apply_augmentations(
    x: torch.Tensor,
    mask: torch.Tensor,
    aug_config: dict,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Apply all augmentations to a single sample.

    x: (C, S, E)
    mask: (C, S)
    """
    C, S, E = x.shape

    # Per-channel temporal jitter
    jitter = aug_config.get("temporal_jitter_samples", 0)
    if jitter > 0:
        for c in range(C):
            x[c] = temporal_jitter(x[c], max_shift=jitter)

    # Gaussian noise
    noise_std = aug_config.get("gaussian_noise_std", 0.0)
    if noise_std > 0:
        x = gaussian_noise(x, std=noise_std)

    # Random channel masking
    mask_prob = aug_config.get("random_channel_mask_prob", 0.0)
    if mask_prob > 0:
        x, mask = random_channel_mask(x, mask, prob=mask_prob)

    return x, mask
