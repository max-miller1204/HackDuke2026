"""Student models for knowledge distillation to Jetson TK1.

All students take post-spatial-pool input (B, S, 128) and produce (B, S, 5) logits.
StudentBase handles masked spatial mean-pooling from (B, 4, S, 128) teacher-format input.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class StudentBase(nn.Module):
    """Base class for student models.

    Provides masked spatial mean-pooling to reduce (B, C, S, E) → (B, S, E),
    avoiding the teacher's 132K-param AttentionPooling.
    """

    def spatial_mean_pool(self, x, mask):
        """Masked mean over channels.

        Args:
            x: (B, C, S, E) pre-embedded patches
            mask: (B, C, S) where 0=real, 1=padded

        Returns:
            pooled: (B, S, E)
            temporal_mask: (B, S) where 0=real, 1=padded
        """
        # mask: 0=real, 1=padded → invert for weighting
        valid = (1.0 - mask.float()).unsqueeze(-1)  # (B, C, S, 1)
        pooled = (x * valid).sum(dim=1) / valid.sum(dim=1).clamp(min=1)  # (B, S, E)

        # Temporal mask: position is padded if ALL channels are padded
        temporal_mask = mask[:, 0, :]  # (B, S) — use first channel as proxy
        return pooled, temporal_mask

    def forward(self, x, mask):
        """Full forward: spatial pool → student backbone.

        Args:
            x: (B, C, S, E) or (B, S, E) if pre-pooled
            mask: (B, C, S) or (B, S)

        Returns:
            logits: (B, S, num_classes)
            temporal_mask: (B, S)
        """
        if x.dim() == 4:
            x, temporal_mask = self.spatial_mean_pool(x, mask)
        else:
            temporal_mask = mask
        logits = self.backbone(x)
        return logits, temporal_mask

    def backbone(self, x):
        """Override in subclass. x: (B, S, E) → (B, S, num_classes)."""
        raise NotImplementedError


class SmallGRU(StudentBase):
    """Linear(128→48) → GRU(48, hidden=24, bidir) → Linear(48→5).

    ~17K params, ~68KB.
    """

    def __init__(self, embed_dim=128, num_classes=5, proj_dim=48, hidden_dim=24,
                 bidirectional=True):
        super().__init__()
        self.proj = nn.Linear(embed_dim, proj_dim)
        self.gru = nn.GRU(
            input_size=proj_dim,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=bidirectional,
        )
        gru_out_dim = hidden_dim * 2 if bidirectional else hidden_dim
        self.head = nn.Linear(gru_out_dim, num_classes)

    def backbone(self, x):
        x = F.relu(self.proj(x))
        x, _ = self.gru(x)
        return self.head(x)


class Conv1dStack(StudentBase):
    """Conv1d(128→32, k=5) → Conv1d(32→32, k=5) → Conv1d(32→5, k=1).

    ~26K params, ~104KB.
    """

    def __init__(self, embed_dim=128, num_classes=5, hidden_channels=32,
                 kernel_size=5):
        super().__init__()
        pad = kernel_size // 2
        self.conv1 = nn.Conv1d(embed_dim, hidden_channels, kernel_size, padding=pad)
        self.bn1 = nn.BatchNorm1d(hidden_channels)
        self.conv2 = nn.Conv1d(hidden_channels, hidden_channels, kernel_size, padding=pad)
        self.bn2 = nn.BatchNorm1d(hidden_channels)
        self.conv3 = nn.Conv1d(hidden_channels, num_classes, 1)

    def backbone(self, x):
        # x: (B, S, E) → transpose to (B, E, S) for Conv1d
        x = x.transpose(1, 2)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.conv3(x)
        return x.transpose(1, 2)  # (B, S, num_classes)


class MLPPerPatch(StudentBase):
    """Linear(128→64) → ReLU → Linear(64→5) + AvgPool1d(k=3) smoothing.

    ~8.6K params, ~35KB.
    """

    def __init__(self, embed_dim=128, num_classes=5, hidden_dim=64,
                 smooth_kernel=3):
        super().__init__()
        self.fc1 = nn.Linear(embed_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, num_classes)
        self.smooth_kernel = smooth_kernel

    def backbone(self, x):
        x = F.relu(self.fc1(x))
        x = self.fc2(x)  # (B, S, num_classes)
        if self.smooth_kernel > 1 and x.size(1) >= self.smooth_kernel:
            # Temporal smoothing via AvgPool1d
            pad = self.smooth_kernel // 2
            x = x.transpose(1, 2)  # (B, C, S)
            x = F.avg_pool1d(x, self.smooth_kernel, stride=1, padding=pad)
            x = x.transpose(1, 2)
        return x


STUDENT_REGISTRY = {
    "SmallGRU": SmallGRU,
    "Conv1dStack": Conv1dStack,
    "MLPPerPatch": MLPPerPatch,
}


def build_student(arch_name, config):
    """Build a student model from config.

    Args:
        arch_name: Key in STUDENT_REGISTRY
        config: Full distillation config dict

    Returns:
        Student model instance
    """
    cls = STUDENT_REGISTRY[arch_name]
    arch_params = config["students"][arch_name]
    return cls(
        embed_dim=config["embed_dim"],
        num_classes=config["num_classes"],
        **arch_params,
    )
