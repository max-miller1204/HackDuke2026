# Archived Plan

**Source:** `unified-waddling-aurora.md`
**Session:** `0db027f5-77a0-4fce-9130-d6319f9f29de`
**Trigger:** `clear`
**Archived:** 2026-03-22 09:57:46

---

# Knowledge Distillation: SleepFM → Jetson TK1

## Context

The finetuned SleepEventLSTMClassifier (~2.7M params, 8.9MB) is too heavy for the NVIDIA Jetson TK1 (2GB shared RAM, 192 Kepler CUDA cores, CUDA 6.5, no TensorRT). We need to distill it into a tiny student model (8K-25K params) that runs comfortably on-device, using soft-label knowledge distillation with a hyperparameter sweep across 3 architectures, 3 temperatures, and 3 alpha values (27 experiments). The system produces a Pareto frontier plot (accuracy vs latency vs size) and exports the best candidates in both ONNX and TorchScript.

---

## Spec

### Input/Output Contract
- **Teacher**: `SleepEventLSTMClassifier` from `checkpoints/sleepfm-sleepEDF/best.pth`
  - Input: `(B, 4, S, 128)` pre-embedded patches + mask
  - Output: `(B, S, 5)` logits + temporal mask
- **Student**: Takes `(B, S, 128)` (post spatial mean-pool) → `(B, S, 5)` logits
  - Spatial reduction: masked mean over 4 channels (trivial, avoids replicating the teacher's 132K-param AttentionPooling)
- **Data**: Same 7 subjects, existing HDF5 files. Short 10-min windows (20 epochs = 120 patches)

### Student Architectures

| Architecture | Params | Size | Description |
|---|---|---|---|
| SmallGRU | ~17K | ~68KB | Linear(128→48) → GRU(48, hidden=24, bidir) → Linear(48→5) |
| Conv1dStack | ~26K | ~104KB | Conv1d(128→32, k=5) → Conv1d(32→32, k=5) → Conv1d(32→5, k=1) |
| MLPPerPatch | ~8.6K | ~35KB | Linear(128→64) → ReLU → Linear(64→5) + AvgPool1d(k=3) smoothing |

All inherit from `StudentBase` which implements masked spatial mean-pooling.

### Distillation Loss
```
L = α * KL(softmax(student/T), softmax(teacher/T)) * T² + (1-α) * CE(student, hard_labels)
```
- Sweep: T ∈ {2, 4, 8}, α ∈ {0.3, 0.5, 0.7}
- Hard labels use inverse-frequency class weights (matching existing training)
- Mask handling: ignore padded positions in both loss terms

### Soft Label Strategy
- Pre-generate teacher logits once on full recordings (no windowing → teacher gets max context from biLSTM)
- Cache as `.npy` files per subject in `data/processed/teacher_logits/`
- Student training slices into these cached logits at the window's patch indices
- This lets students learn from teacher's long-range temporal knowledge despite only seeing 10-min windows

### Training Config
- Optimizer: AdamW, lr=1e-3
- Scheduler: ReduceLROnPlateau (patience=5, factor=0.5)
- Epochs: 50 with early stopping (patience=10)
- Batch size: 16
- AMP supported
- Windows: 20 epochs (10 min), stride 10, 3x minority oversampling

### Export
- ONNX (opset 11) + TorchScript for all sweep results
- Dynamic axes on batch and sequence length
- Post-export validation: verify outputs match PyTorch within atol=1e-5

### Benchmarking
- **Estimated**: FLOP count / (TK1 peak 326 GFLOPS * 0.1 efficiency) for latency; param count * 4 bytes for RAM
- **Real hardware**: Standalone `scripts/benchmark_jetson.py` — loads model, runs 100 timed inferences, reports mean/p50/p95 latency + peak memory

### Reporting
- `sweep_results.json`: structured metrics per experiment
- Pareto frontier PNG: accuracy vs model size, accuracy vs estimated latency, color-coded by architecture

---

## Implementation Plan

### New Files
1. `src/distill/__init__.py` — package marker
2. `src/distill/student_models.py` — StudentBase + SmallGRU + Conv1dStack + MLPPerPatch
3. `src/distill/soft_labels.py` — teacher inference + .npy caching
4. `src/distill/dataset_distill.py` — DistillSleepEDFDataset (loads cached soft labels)
5. `src/distill/train_distill.py` — distillation loss + sweep loop + metrics collection
6. `src/distill/export.py` — ONNX + TorchScript export + validation
7. `src/distill/report.py` — Pareto plot generation + sweep_results.json
8. `src/distill/config_distill.yaml` — all distillation config
9. `src/modal_distill.py` — Modal runner (mirrors modal_app.py)
10. `scripts/benchmark_jetson.py` — standalone TK1 benchmark

### Modified Files
- None. The distill package is self-contained, importing from `src/dataset.py` and `sleepfm-clinical` without modifying them.

### Key Reuse
- `src/dataset.py:SleepEDFDataset` — subclassed in dataset_distill.py for soft label loading
- `src/train.py:masked_cross_entropy_loss` — imported directly for the CE term
- `src/dataset.py:collate_fn` — pattern replicated with teacher logits padding
- `src/modal_app.py` — pattern for Modal runner
- `src/config.yaml` — referenced for teacher model_params and data paths

### Execution Order
1. **Foundation**: `__init__.py`, `config_distill.yaml`, `student_models.py`
2. **Data pipeline**: `soft_labels.py`, `dataset_distill.py`
3. **Training**: `train_distill.py`
4. **Export + reporting**: `export.py`, `report.py`
5. **Deployment**: `benchmark_jetson.py`, `modal_distill.py`

---

## Work Units

### Execution Strategy
Foundation → Parallel (concurrent worktrees)

**Rationale:** After the foundation (shared models + config + dataset), the training loop, export/reporting, and deployment scripts are independent — they don't import from each other and own distinct files.

### Foundation Unit (Phase 1)

**Files:**
- Create: `src/distill/__init__.py`
- Create: `src/distill/config_distill.yaml`
- Create: `src/distill/student_models.py`
- Create: `src/distill/soft_labels.py`
- Create: `src/distill/dataset_distill.py`

**Tasks:**
- Define `StudentBase` with masked spatial mean-pool + forward interface
- Implement `SmallGRU`, `Conv1dStack`, `MLPPerPatch` with exact param budgets
- Implement `generate_soft_labels()` — load teacher, run full-recording inference, cache .npy
- Implement `DistillSleepEDFDataset` subclassing `SleepEDFDataset` — load cached soft labels, slice to windows
- Implement `distill_collate_fn` that pads teacher logits alongside x/y data
- Write full config YAML (teacher path, architectures, sweep params, training, windowing, export, TK1 specs)

**Done when:** `python -c "from src.distill.student_models import SmallGRU, Conv1dStack, MLPPerPatch; from src.distill.dataset_distill import DistillSleepEDFDataset"` imports cleanly, and soft label generation runs on a test subject.

### Parallel Units (Phase 2)

| # | Unit Name | Files (create/modify) | Description | E2E Test |
|---|-----------|----------------------|-------------|----------|
| 1 | Training Loop | Create: `src/distill/train_distill.py` | Distillation loss function, sweep loop over 27 configs, per-experiment checkpointing, structured JSON metrics | Run sweep on 1 arch x 1 temp x 1 alpha, verify checkpoint + metrics JSON saved |
| 2 | Export & Reporting | Create: `src/distill/export.py`, `src/distill/report.py` | ONNX + TorchScript export with validation, Pareto plot generation from sweep_results.json | Export a dummy student to both formats, generate plot from sample JSON |
| 3 | Deployment Scripts | Create: `scripts/benchmark_jetson.py`, `src/modal_distill.py` | Standalone Jetson benchmark (TorchScript + ONNX, latency/memory), Modal runner for full pipeline | Run benchmark on local CPU with a dummy model; verify modal_distill.py imports cleanly |

### Dependency & Conflict Analysis
- **File conflicts:** None — each parallel unit creates distinct files with no overlap.
- **Runtime dependencies:** None between parallel units. Unit 1 produces checkpoints that Unit 2's export consumes, but Unit 2's export code is tested independently with dummy models. Unit 3's Modal runner calls functions from Units 1+2 but is tested for import cleanliness only. Full integration is verified post-merge.

### Post-Merge Verification
1. Generate soft labels: `python -m src.distill.soft_labels`
2. Run full 27-experiment sweep: `python -m src.distill.train_distill`
3. Export top candidates: `python -m src.distill.export`
4. Generate Pareto plot: `python -m src.distill.report`
5. Run local benchmark: `python scripts/benchmark_jetson.py --model checkpoints/distill/best_model.pt --format torchscript`
6. Verify all outputs exist: `checkpoints/distill/sweep_results.json`, `checkpoints/distill/pareto.png`, ONNX/TorchScript files
