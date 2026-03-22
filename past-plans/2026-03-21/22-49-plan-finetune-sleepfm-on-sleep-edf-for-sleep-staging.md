# Archived Plan

**Source:** `whimsical-cuddling-ember.md`
**Session:** `bb8dbe29-4d39-42b6-bdc5-f10c695fb10c`
**Trigger:** `clear`
**Archived:** 2026-03-21 22:49:56

---

# Plan: Finetune SleepFM on Sleep-EDF for Sleep Staging + Quality Score

## Context

Circadia is a hackathon project building a sleep improvement app powered by SleepFM, targeting deployment on an NVIDIA Jetson TK1. A teammate handles distillation separately — this plan covers finetuning: adapt the pretrained SleepFM SetTransformer to perform 5-class sleep staging on Sleep-EDF data, derive a sleep quality score, and export a checkpoint bundle.

The core technical challenge is a **channel mismatch**: SleepFM was pretrained on 23 channels across 4 modality groups (BAS/RESP/EKG/EMG), but Sleep-EDF only has 5 channels at 100Hz. Solution: zero-pad missing channels and let the attention masking handle it.

## Implementation Steps

### Step 1: Foundation — Config, Channel Map, Dependencies

**Files:**
- Create: `src/__init__.py` (empty)
- Create: `src/channel_map.py` — Sleep-EDF channel → SleepFM modality mapping
- Create: `src/config.yaml` — All hyperparameters, paths, data split
- Modify: `pyproject.toml` — Add deps: torch, mne, pyedflib, h5py, scipy, einops, loguru, modal, pyyaml, pandas, numpy, scikit-learn, tqdm

**Channel mapping logic:**
- `EEG Fpz-Cz` → BAS slot 0, `EEG Pz-Oz` → BAS slot 1, `EOG horizontal` → BAS slot 2 (7 zero-padded)
- `Resp oro-nasal` → RESP slot 0 (6 zero-padded)
- EKG: fully zero-padded (2 channels)
- `EMG submental` → EMG slot 0 (3 zero-padded)

**Config (key values):**
- `batch_size: 4`, `epochs: 20`, `lr: 0.0001`, `embed_dim: 128`, `num_classes: 5`, `sampling_freq: 128`
- Train: SC4001, SC4002, SC4011 | Val: SC4012 | Test: SC4021

### Step 2: Preprocessing — `src/preprocess.py`

**Reuse:** `EDFToHDF5Converter.resample_signals()` pattern from `sleepfm-clinical/sleepfm/preprocessing/preprocessing.py` (scipy resample + safe_standardize)

**What it does:**
1. Read PSG EDF via `mne.io.read_raw_edf()`
2. Auto-detect channels by name, skip `Temp rectal` and `Event marker`
3. Resample 100Hz → 128Hz
4. Z-score normalize per channel
5. Parse hypnogram EDF+ annotations → 30s epoch labels
6. Stage mapping: W→0, R→1, N1→2, N2→3, N3→4, N4→4 (merge), drop `?` and `Movement time`
7. Save HDF5 + CSV labels to `data/processed/`

### Step 3: Dataset + Augmentation — `src/dataset.py`, `src/augment.py`

**Reuse:** `SleepEventClassificationDataset` pattern from `sleepfm-clinical/sleepfm/models/dataset.py` and `sleep_event_finetune_full_collate_fn` collate function

**Dataset:** Load HDF5 + CSV, apply channel padding/masking per `channel_map.py`, return `(x_data, y_data, max_channels, max_seq_len, hdf5_path)` matching the existing collate function interface.

**Augmentations (applied during training):**
- Temporal jitter: ±5 samples on chunk boundaries
- Gaussian noise: N(0, 0.05)
- Random channel masking: p=0.2, zero out one non-padded channel

### Step 4: Training — `src/train.py`

**Reuse:** `finetune_sleep_staging.py` from `sleepfm-clinical/sleepfm/pipeline/` — adapt the training loop, loss function (`masked_cross_entropy_loss` with class weights W:1/R:4/N1:2/N2:4/N3:3), checkpoint saving

**Key differences from original:**
- Load pretrained weights from `sleepfm-clinical/sleepfm/checkpoints/model_base/best.pt` into backbone
- Use `SleepEventLSTMClassifier` from `sleepfm-clinical/sleepfm/models/models.py` (import directly, don't copy)
- Full end-to-end finetuning (no frozen layers)
- No wandb — stdout logging only
- AdamW with ReduceLROnPlateau scheduler

### Step 5: Evaluation + Quality Score — `src/evaluate.py`

- Load best checkpoint, run inference on test subject (SC4021)
- Compute per-class accuracy + confusion matrix
- Compute sleep quality score (rule-based from staging): 70% sleep efficiency + 20% deep sleep ratio + 10% REM ratio → 0-100 score

### Step 6: Modal Integration — `src/modal_app.py`

Single Modal function that:
1. Uploads raw EDFs + pretrained checkpoint to Modal volume
2. Runs preprocess → train → evaluate → export
3. Downloads checkpoint bundle

**Modal config:** A10G or T4 GPU, Python 3.10 image, 30min timeout

**Checkpoint bundle output:**
```
checkpoints/sleepfm-sleepEDF/
├── best.pth              # model state_dict
├── config.yaml           # training config
├── channel_mapping.json  # channel map
├── training_log.txt      # stdout log
└── metadata.json         # training metadata
```

## Critical Files to Reference

| File | What to reuse |
|------|--------------|
| `sleepfm-clinical/sleepfm/models/models.py` | `SleepEventLSTMClassifier`, `Tokenizer`, `AttentionPooling`, `SetTransformer` classes — import directly |
| `sleepfm-clinical/sleepfm/pipeline/finetune_sleep_staging.py` | `masked_cross_entropy_loss`, training loop structure, checkpoint saving pattern |
| `sleepfm-clinical/sleepfm/models/dataset.py` | `SleepEventClassificationDataset` pattern, `sleep_event_finetune_full_collate_fn` interface |
| `sleepfm-clinical/sleepfm/preprocessing/preprocessing.py` | `resample_signals()`, `safe_standardize()`, `read_edf()` patterns |
| `sleepfm-clinical/sleepfm/configs/config_finetune_sleep_events.yaml` | Config structure reference |
| `sleepfm-clinical/sleepfm/configs/channel_groups.json` | Channel name → modality mapping reference |
| `sleepfm-clinical/sleepfm/checkpoints/model_base/best.pt` | Pretrained weights to load |

## Verification

1. Run preprocessing locally: `python -m src.preprocess` → verify 5 HDF5 + 5 CSV files in `data/processed/`
2. Run full pipeline via Modal: `modal run src/modal_app.py`
3. Verify checkpoint bundle exists and is loadable: `torch.load("checkpoints/sleepfm-sleepEDF/best.pth")`
4. Verify sleep quality score produces 0-100 for test set predictions
5. Success = pipeline runs E2E without errors, checkpoint is valid for distillation handoff
