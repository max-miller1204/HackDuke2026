"""Channel mapping from Sleep-EDF channels to SleepFM modality groups.

SleepFM expects 4 modality groups with fixed channel counts:
  BAS:  10 channels (EEG + EOG)
  RESP:  7 channels
  EKG:   2 channels
  EMG:   4 channels
Total: 23 channels

Sleep-EDF provides 5 usable channels at 100Hz (resampled to 128Hz):
  EEG Fpz-Cz, EEG Pz-Oz, EOG horizontal, Resp oro-nasal, EMG submental
"""

import json
from pathlib import Path

# Number of channels per modality group in the pretrained SleepFM model
GROUP_SIZES = {"BAS": 10, "RESP": 7, "EKG": 2, "EMG": 4}
TOTAL_CHANNELS = sum(GROUP_SIZES.values())  # 23

# Sleep-EDF channel name -> (modality_group, slot_index)
SLEEP_EDF_MAPPING = {
    "EEG Fpz-Cz": ("BAS", 0),
    "EEG Pz-Oz": ("BAS", 1),
    "EOG horizontal": ("BAS", 2),
    "Resp oro-nasal": ("RESP", 0),
    "EMG submental": ("EMG", 0),
}

# Channels to skip when reading Sleep-EDF files
SKIP_CHANNELS = {"Temp rectal", "Event marker"}

# Ordered list of modality groups (must match pretrained model order)
GROUP_ORDER = ["BAS", "RESP", "EKG", "EMG"]


def get_channel_indices():
    """Return a dict mapping Sleep-EDF channel names to their global index
    in the 23-channel padded tensor.

    Global index = sum of sizes of preceding groups + slot index within group.
    """
    group_offsets = {}
    offset = 0
    for group in GROUP_ORDER:
        group_offsets[group] = offset
        offset += GROUP_SIZES[group]

    indices = {}
    for ch_name, (group, slot) in SLEEP_EDF_MAPPING.items():
        indices[ch_name] = group_offsets[group] + slot
    return indices


def get_attention_mask():
    """Return a boolean mask of shape (TOTAL_CHANNELS,).
    True = real channel, False = zero-padded.
    """
    mask = [False] * TOTAL_CHANNELS
    indices = get_channel_indices()
    for idx in indices.values():
        mask[idx] = True
    return mask


def export_channel_mapping(path: Path):
    """Export channel mapping as JSON for the checkpoint bundle."""
    mapping = {
        "group_sizes": GROUP_SIZES,
        "group_order": GROUP_ORDER,
        "sleep_edf_mapping": {
            k: {"group": v[0], "slot": v[1]} for k, v in SLEEP_EDF_MAPPING.items()
        },
        "total_channels": TOTAL_CHANNELS,
        "active_indices": get_channel_indices(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(mapping, f, indent=2)
