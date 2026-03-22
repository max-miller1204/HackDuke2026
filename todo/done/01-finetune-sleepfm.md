# Finetune SleepFM on Sleep-EDF for Sleep Staging + Quality Score

## Context

Circadia is a hackathon project building a sleep improvement app powered by SleepFM, targeting deployment on an NVIDIA Jetson TK1. This spec covers the finetuning step: adapt the pretrained SleepFM SetTransformer to perform 5-class sleep staging on Sleep-EDF data, derive a sleep quality score, and export a checkpoint bundle for a teammate who handles distillation.

The pretrained SleepFM model (from `sleepfm-clinical/`) was trained on the Stanford Sleep Dataset with 23 channels across 4 modality groups (BAS, RESP, EKG, EMG). The target dataset — Sleep-EDF Expanded (PhysioNet, sleep-cassette) — has only 5 physiological channels at 100Hz. This channel mismatch is the core technical challenge.

---

## Dataset

**Source:** [Sleep-EDF Expanded v1.0.0](https://physionet.org/content/sleep-edfx/1.0.0/sleep-cassette/) — 5 subjects downloaded, stored in `data/`.

**Files (already downloaded):**

| Subject | PSG File | Hypnogram File |
|---------|----------|----------------|
| SC4001 | `SC4001E0-PSG.edf` | `SC4001EC-Hypnogram.edf` |
| SC4002 | `SC4002E0-PSG.edf` | `SC4002EC-Hypnogram.edf` |
| SC4011 | `SC4011E0-PSG.edf` | `SC4011EH-Hypnogram.edf` |
| SC4012 | `SC4012E0-PSG.edf` | `SC4012EC-Hypnogram.edf` |
| SC4021 | `SC4021E0-PSG.edf` | `SC4021EH-Hypnogram.edf` |

**Sleep-EDF channels (all at 100Hz except Event marker at 1Hz):**
- `EEG Fpz-Cz` — frontal-central EEG
- `EEG Pz-Oz` — parietal-occipital EEG
- `EOG horizontal` — horizontal electrooculography
- `Resp oro-nasal` — oro-nasal respiration
- `EMG submental` — submental electromyography
- `Temp rectal` — rectal temperature (not used)
- `Event marker` — event annotations (not used)

**Hypnogram format:** EDF+ annotations with labels `Sleep stage W`, `Sleep stage 1`, `Sleep stage 2`, `Sleep stage 3`, `Sleep stage 4`, `Sleep stage R`, `Sleep stage ?`, `Movement time`. Each annotation has a start time and duration (always 30s epochs).

---

## Channel Mapping Strategy

SleepFM expects 4 modality groups with up to 23 channels total. Sleep-EDF only has 5 usable channels. Strategy: **map available channels to their closest SleepFM counterparts, zero-pad the rest.**

| SleepFM Modality | Max Channels | Sleep-EDF Mapping | Padding |
|------------------|-------------|-------------------|---------|
| BAS (brain/EEG) | 10 | `EEG Fpz-Cz` → slot 0, `EEG Pz-Oz` → slot 1, `EOG horizontal` → slot 2 | 7 zero-padded |
| RESP | 7 | `Resp oro-nasal` → slot 0 | 6 zero-padded |
| EKG | 2 | (none available) | 2 zero-padded |
| EMG | 4 | `EMG submental` → slot 0 | 3 zero-padded |

The channel mask (used by SleepFM's attention pooling) marks zero-padded channels as padding so the attention mechanism ignores them. This is already how SleepFM handles variable channel counts across recordings.

---

## Preprocessing Pipeline

### Steps
1. **Read PSG EDF** — Extract physiological channels using `mne.io.read_raw_edf()` (already used in sleepfm-clinical's preprocessing.py)
2. **Auto-detect channels** — Match channel names against a hardcoded map for Sleep-EDF naming convention; skip `Temp rectal` and `Event marker`
3. **Resample 100Hz → 128Hz** — SleepFM expects 128Hz. Use scipy `resample` with anti-aliasing (matches sleepfm-clinical's `EDFToHDF5Converter.resample_signals()`)
4. **Z-score normalize** per channel (matches sleepfm-clinical's `safe_standardize()`)
5. **Parse hypnogram** — Read EDF+ annotations from the hypnogram file, convert to 30-second epoch labels
6. **Stage mapping:**
   - `Sleep stage W` → 0 (Wake)
   - `Sleep stage R` → 1 (REM)
   - `Sleep stage 1` → 2 (N1)
   - `Sleep stage 2` → 3 (N2)
   - `Sleep stage 3` → 4 (N3)
   - `Sleep stage 4` → 4 (N3) — **merge N3+N4** per AASM standard
   - `Sleep stage ?` → drop epoch
   - `Movement time` → drop epoch
7. **Save to HDF5** — One HDF5 per subject with channel datasets at 128Hz
8. **Save labels CSV** — Per subject, columns: `Start`, `Stop`, `StageName`, `StageNumber` (matches SleepFM's expected label format)

### Output structure
```
data/processed/
├── SC4001E0-PSG.hdf5
├── SC4001E0-PSG.csv    # sleep staging labels
├── SC4002E0-PSG.hdf5
├── SC4002E0-PSG.csv
├── ...
```

---

## Data Augmentation

With only 5 subjects, overfitting is a real risk. Apply these augmentations during training:

1. **Temporal jitter** — Random shift of ±5 samples (±39ms at 128Hz) on chunk boundaries
2. **Gaussian noise injection** — Add N(0, σ=0.05) noise to signal channels
3. **Random channel masking** — With probability 0.2, zero out one random non-padded channel and mark it as padding in the mask (simulates missing channels)

---

## Model Architecture

Use the existing `SleepEventLSTMClassifier` from `sleepfm-clinical/sleepfm/models/models.py`. This model:
- Takes tokenized input from the pretrained `Tokenizer` (1D CNN)
- Applies `AttentionPooling` across channels (spatial dimension)
- Uses a 1-layer transformer encoder for temporal context
- Feeds through a bidirectional LSTM for sequence modeling
- Outputs per-epoch 5-class predictions via a linear head

### Training approach: **Full end-to-end finetuning**
- Load pretrained weights from `sleepfm-clinical/sleepfm/checkpoints/model_base/best.pt` into the SetTransformer backbone (tokenizer + spatial pooling + positional encoding + transformer encoder)
- Initialize the LSTM and linear head randomly
- Train all parameters jointly with AdamW

### Key hyperparameters (from existing config, adapted for small dataset)
```yaml
model: SleepEventLSTMClassifier
model_params:
  embed_dim: 128
  num_heads: 4
  num_layers: 1
  num_classes: 5
  pooling_head: 4
  dropout: 0.3
  max_seq_length: 8196

batch_size: 4          # smaller for 5 subjects
epochs: 20             # more epochs since dataset is tiny
lr: 0.0001             # lower LR for finetuning pretrained model
sampling_freq: 128
```

### Loss function
Weighted cross-entropy (from existing `masked_cross_entropy_loss`) with class weights to handle stage imbalance:
- Wake: 1, REM: 4, N1: 2, N2: 4, N3: 3

---

## Sleep Quality Score

Derived **post-hoc from staging predictions** using a sleep-efficiency-focused formula:

```python
def compute_sleep_quality_score(staging_predictions: list[int]) -> float:
    """
    Compute 0-100 sleep quality score from epoch-level staging predictions.
    Heavily weighted toward sleep efficiency (time asleep / total time).

    staging_predictions: list of int, one per 30s epoch
        0=Wake, 1=REM, 2=N1, 3=N2, 4=N3
    """
    total_epochs = len(staging_predictions)
    if total_epochs == 0:
        return 0.0

    wake_epochs = staging_predictions.count(0)
    rem_epochs = staging_predictions.count(1)
    n3_epochs = staging_predictions.count(4)
    sleep_epochs = total_epochs - wake_epochs

    # Sleep efficiency: 0-100, weighted 70%
    sleep_efficiency = (sleep_epochs / total_epochs) * 100

    # Deep sleep ratio: N3 should be ~15-25% of sleep, score 0-100, weighted 20%
    deep_ratio = (n3_epochs / max(sleep_epochs, 1)) * 100
    deep_score = min(deep_ratio / 0.25, 100)  # peaks at 25%

    # REM ratio: should be ~20-25% of sleep, score 0-100, weighted 10%
    rem_ratio = (rem_epochs / max(sleep_epochs, 1)) * 100
    rem_score = min(rem_ratio / 0.25, 100)  # peaks at 25%

    score = 0.70 * sleep_efficiency + 0.20 * deep_score + 0.10 * rem_score
    return round(max(0, min(100, score)), 1)
```

This function runs on the staging output — no additional model head needed.

---

## Training Infrastructure: Modal

Single Modal function that runs the full pipeline end-to-end:

1. Upload raw EDF files + pretrained checkpoint to Modal volume
2. Preprocess → HDF5 + label CSVs
3. Train with stdout logging (no wandb/tensorboard)
4. Evaluate on held-out subjects
5. Export checkpoint bundle

### Modal setup
- **GPU:** A10G or T4 (sufficient for this model size)
- **Image:** Python 3.10 + PyTorch 2.0 + mne + pyedflib + h5py + scipy + einops + loguru
- **Volume:** Persistent Modal volume for data + checkpoints
- **Timeout:** 30 minutes (generous for 5 subjects)

### Data split (5 subjects)
- Train: SC4001, SC4002, SC4011 (3 subjects)
- Validation: SC4012 (1 subject)
- Test: SC4021 (1 subject)

---

## Checkpoint Export

Export a **full bundle** directory for the distillation teammate:

```
checkpoints/sleepfm-sleepEDF/
├── best.pth                    # model state_dict
├── config.yaml                 # training config (hyperparams, channel mapping, etc.)
├── channel_mapping.json        # Sleep-EDF channel → SleepFM modality/slot mapping
├── training_log.txt            # stdout training log
└── metadata.json               # training metadata
    {
      "dataset": "sleep-edf-expanded-cassette",
      "num_subjects_train": 3,
      "num_subjects_val": 1,
      "num_subjects_test": 1,
      "num_epochs_trained": 20,
      "best_val_loss": <float>,
      "model_class": "SleepEventLSTMClassifier",
      "pretrained_from": "sleepfm-clinical/checkpoints/model_base/best.pt",
      "sampling_freq": 128,
      "num_classes": 5,
      "sleep_stages": {"Wake": 0, "REM": 1, "N1": 2, "N2": 3, "N3": 4}
    }
```

---

## Success Criteria

**Pipeline runs end-to-end without errors and produces a valid checkpoint bundle.** Accuracy is secondary — this is a hackathon proof-of-concept with 5 subjects. The checkpoint just needs to be loadable by the distillation teammate.

Specifically:
- [ ] Preprocessing converts all 5 EDF files to HDF5 + label CSVs
- [ ] Training completes all epochs, loss decreases over time
- [ ] Best checkpoint is saved and loadable
- [ ] Sleep quality score function produces reasonable 0-100 values
- [ ] Checkpoint bundle contains all required files

---

## File Structure

New files to create in the `circadia/` project root:

```
src/
├── __init__.py
├── preprocess.py          # EDF→HDF5 converter for Sleep-EDF
├── dataset.py             # Custom dataset/dataloader for Sleep-EDF + SleepFM format
├── train.py               # Training loop (adapted from sleepfm finetune_sleep_staging.py)
├── evaluate.py            # Evaluation + sleep quality score computation
├── augment.py             # Data augmentation transforms
├── channel_map.py         # Sleep-EDF → SleepFM channel mapping config
├── config.yaml            # Training configuration
└── modal_app.py           # Modal function that runs the full pipeline
```

---

## Work Units

### Execution Strategy
Sequential (single worker)

**Rationale:** This is a tightly coupled ML pipeline where each stage depends on the output of the previous one. The dataset module imports the channel mapping. The training script imports the dataset and augmentation. The evaluation imports the model and quality score function. The Modal app imports everything. There is no meaningful way to parallelize without creating circular dependencies or duplicating shared state.

### Foundation Unit (Phase 1)

**Files:**
- Create: `src/__init__.py`
- Create: `src/channel_map.py`
- Create: `src/config.yaml`
- Modify: `pyproject.toml` (add dependencies: torch, mne, pyedflib, h5py, scipy, einops, loguru, modal, pyyaml, pandas, numpy, scikit-learn, tqdm)

**Tasks:**
- Create `src/__init__.py` (empty)
- Create `src/channel_map.py` with Sleep-EDF → SleepFM modality mapping dict and channel filtering logic
- Create `src/config.yaml` with all training hyperparameters, paths, and data split configuration
- Update `pyproject.toml` with all required dependencies

**Done when:** `from src.channel_map import CHANNEL_MAP` works and `src/config.yaml` is valid YAML loadable by PyYAML.

### Sequential Units

| Order | Unit Name | Files (create/modify) | Depends On | Description |
|-------|-----------|----------------------|------------|-------------|
| 1 | Preprocessing | `src/preprocess.py` | Foundation (imports `channel_map`) | Read Sleep-EDF EDFs, auto-detect channels, resample 100→128Hz, parse hypnograms, merge N3/N4, output HDF5 + label CSVs to `data/processed/` |
| 2 | Dataset + Augmentation | `src/dataset.py`, `src/augment.py` | Unit 1 (reads HDF5/CSV files it produces) | Custom PyTorch Dataset that loads preprocessed HDF5 + CSVs, applies channel padding/masking for SleepFM format, and augmentation transforms (jitter, noise, channel mask) |
| 3 | Training | `src/train.py` | Unit 2 (imports `dataset.py`, `augment.py`) | Training loop: load pretrained weights, build SleepEventLSTMClassifier, train with masked cross-entropy, save best checkpoint, stdout logging |
| 4 | Evaluation + Quality Score | `src/evaluate.py` | Unit 3 (loads checkpoint from training) | Load best checkpoint, run inference on test set, compute accuracy/confusion matrix, compute sleep quality score, print results |
| 5 | Modal Integration | `src/modal_app.py` | Units 1-4 (imports all modules) | Single Modal function that uploads data, runs preprocess→train→evaluate→export, downloads checkpoint bundle |

### Dependency & Conflict Analysis
- **File conflicts:** None — each unit owns its files exclusively.
- **Runtime dependencies:** Tight sequential chain. `preprocess.py` imports `channel_map`. `dataset.py` reads files produced by `preprocess.py`. `train.py` imports `dataset` and `augment`. `evaluate.py` loads checkpoints saved by `train.py`. `modal_app.py` orchestrates all of the above. These cannot be parallelized.

### Post-Merge Verification
Run the full pipeline end-to-end via Modal:
```bash
modal run src/modal_app.py
```
Verify:
1. All 5 EDF files preprocessed to HDF5 + CSV in `data/processed/`
2. Training completes 20 epochs, loss logged to stdout
3. `checkpoints/sleepfm-sleepEDF/` contains `best.pth`, `config.yaml`, `channel_mapping.json`, `metadata.json`
4. `best.pth` is loadable: `torch.load("checkpoints/sleepfm-sleepEDF/best.pth")`
5. Sleep quality score returns a number between 0-100 for test set predictions
