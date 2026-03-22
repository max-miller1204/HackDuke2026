# Circadia

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Clone the repo and set up the environment:
   ```sh
   git clone --recurse-submodules <repo-url>
   cd circadia
   uv venv
   uv sync
   source .venv/bin/activate
   ```

## Data

1. Download the Sleep-EDF Expanded dataset (SC subjects) from [PhysioNet](https://physionet.org/content/sleep-edfx/1.0.0/) and place the `.edf` files in `data/`:
   ```sh
   data/
   ├── SC4001E0-PSG.edf
   ├── SC4001EC-Hypnogram.edf
   ├── SC4002E0-PSG.edf
   ├── SC4002EC-Hypnogram.edf
   └── ...
   ```

2. Run preprocessing to generate embeddings and labels in `data/processed/`:
   ```sh
   uv run python -m src.preprocess
   ```

## Running

### Teacher finetuning

Train the teacher model on Modal (requires a [Modal](https://modal.com/) account and `modal token set`):

```sh
uv run modal run src/modal_app.py
```

Outputs the finetuned `SleepEventLSTMClassifier` (~2.7M params) to `checkpoints/sleepfm-sleepEDF/best.pth`.

### Knowledge distillation (SleepFM → Jetson TK1)

The teacher model is too large for the NVIDIA Jetson TK1 (2GB shared RAM, 192 Kepler CUDA cores). The distillation pipeline compresses it into tiny student models (8K–26K params) using soft-label knowledge distillation.

**Student architectures:**

| Architecture | Params | Size | Description |
|---|---|---|---|
| SmallGRU | ~17K | ~68KB | Linear(128→48) → GRU(48, hidden=24, bidir) → Linear(48→5) |
| Conv1dStack | ~26K | ~104KB | Conv1d(128→32, k=5) → Conv1d(32→32, k=5) → Conv1d(32→5, k=1) |
| MLPPerPatch | ~8.6K | ~35KB | Linear(128→64) → ReLU → Linear(64→5) + AvgPool1d(k=3) smoothing |

**Distillation loss:**
```
L = α · KL(softmax(student/T), softmax(teacher/T)) · T² + (1−α) · CE(student, hard_labels)
```
Sweep: 3 architectures × 3 temperatures (T ∈ {2, 4, 8}) × 3 alphas (α ∈ {0.3, 0.5, 0.7}) = 27 experiments.

**Pareto frontier (accuracy vs model size):**

![Pareto frontier](checkpoints/distill/pareto.png)

Stars mark the Pareto-optimal model for each architecture. Since latency is proportional to size for these fixed architectures, a single plot captures the full tradeoff.

**Pareto-optimal models:**

| Architecture | T | α | Accuracy | Size | Est. Latency (TK1) |
|---|---|---|---|---|---|
| Conv1dStack | 2 | 0.3 | **75.2%** | 103KB | 0.19ms |
| SmallGRU | 8 | 0.3 | **67.4%** | 68KB | 0.12ms |
| MLPPerPatch | 8 | 0.7 | **35.6%** | 35KB | 0.06ms |

Conv1dStack dominates on accuracy (~69–75%), SmallGRU is the middle ground (~62–67%), and MLPPerPatch is smallest/fastest but struggles (~25–35%). Within each architecture, lower alpha (more weight on KL divergence from teacher) generally performs better.

All three Pareto-optimal models fit comfortably on the Jetson TK1 (2GB shared RAM), with sub-millisecond estimated inference latency.

**Run locally (step by step):**

```sh
# 1. Generate teacher soft labels (cached as .npy per subject)
uv run python -m src.distill.soft_labels

# 2. Run the 27-experiment sweep
uv run python -m src.distill.train_distill

# 3. Export best candidates to ONNX + TorchScript
uv run python -m src.distill.export

# 4. Generate Pareto frontier plot (accuracy vs size/latency)
uv run python -m src.distill.report
```

**Run on Modal (full pipeline):**

```sh
uv run modal run src/modal_distill.py
```

**Benchmark on Jetson TK1 (or any device):**

```sh
# Copy the standalone script + exported model to the device, then:
python scripts/benchmark_jetson.py --model best_model.pt --format torchscript
python scripts/benchmark_jetson.py --model best_model.onnx --format onnx
```

**Outputs:**
- `checkpoints/distill/sweep_results.json` — metrics for all 27 experiments
- `checkpoints/distill/pareto.png` — Pareto frontier (accuracy vs size, accuracy vs latency)
- `checkpoints/distill/<arch>_T<t>_a<a>.onnx` / `.pt` — exported models

### Project structure

```
src/
├── preprocess.py          # EDF → embeddings → HDF5 + CSV
├── dataset.py             # SleepEDFDataset (windowed, oversampled)
├── train.py               # Teacher finetuning
├── evaluate.py            # Evaluation (accuracy, confusion matrix, sleep quality)
├── modal_app.py           # Modal runner for teacher training
├── modal_distill.py       # Modal runner for distillation pipeline
├── distill/
│   ├── config_distill.yaml    # Distillation config (sweep, training, export, TK1 specs)
│   ├── student_models.py      # StudentBase + SmallGRU, Conv1dStack, MLPPerPatch
│   ├── soft_labels.py         # Teacher inference → .npy caching
│   ├── dataset_distill.py     # DistillSleepEDFDataset + collate_fn
│   ├── train_distill.py       # Distillation loss + 27-experiment sweep
│   ├── export.py              # ONNX (opset 11) + TorchScript export
│   └── report.py              # Pareto frontier plot + summary table
scripts/
└── benchmark_jetson.py    # Standalone TK1 benchmark (no project imports)
```

### Auto-activation (optional)

Install [direnv](https://direnv.net/) so the venv activates automatically when you `cd` into the project:

```sh
brew install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc
direnv allow
```