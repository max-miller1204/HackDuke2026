"""Upload best distilled student model to Hugging Face Hub.

Generates a model card from sweep results and uploads ONNX + TorchScript files.
"""

import argparse
import json
import tempfile
from pathlib import Path

from loguru import logger

from src.distill.soft_labels import load_distill_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def find_best_model(config):
    """Find the best model from sweep results by validation accuracy.

    Returns:
        Tuple of (experiment_info dict, checkpoint_dir Path).
    """
    checkpoint_dir = PROJECT_ROOT / config["export"]["output_dir"]
    results_path = checkpoint_dir / "sweep_results.json"

    if not results_path.exists():
        raise FileNotFoundError(f"sweep_results.json not found at {results_path}")

    with open(results_path) as f:
        sweep_data = json.load(f)

    results = sweep_data.get("results", sweep_data)
    best = max(results, key=lambda r: r["val_accuracy"])

    logger.info(
        f"Best model: {best['experiment_id']} — "
        f"accuracy={best['val_accuracy']:.4f}, "
        f"size={best['model_size_bytes'] / 1024:.1f}KB"
    )
    return best, checkpoint_dir


def generate_model_card(best, config):
    """Build a Hugging Face model card README.md from sweep results and config."""
    exp_id = best["experiment_id"]
    arch = best["architecture"]
    accuracy = best["val_accuracy"]
    params = best["param_count"]
    size_kb = best["model_size_bytes"] / 1024

    student_config = config["students"][arch]
    sweep_cfg = config["sweep"]
    jetson = config["jetson_tk1"]

    card = f"""\
---
license: apache-2.0
library_name: onnxruntime
tags:
  - sleep-staging
  - knowledge-distillation
  - onnx
  - torchscript
  - edge-deployment
  - eeg
  - polysomnography
datasets:
  - sleep-edf
metrics:
  - accuracy
pipeline_tag: tabular-classification
model-index:
  - name: {exp_id}
    results:
      - task:
          type: tabular-classification
          name: Sleep Stage Classification
        dataset:
          type: sleep-edf
          name: Sleep-EDF
        metrics:
          - type: accuracy
            value: {accuracy}
            name: Validation Accuracy
---

# {exp_id} — Distilled Sleep Stage Classifier

A tiny ({size_kb:.0f}KB, {params:,} params) sleep stage classifier distilled from
[SleepFM](https://arxiv.org/abs/2311.07919) for real-time edge deployment on
NVIDIA Jetson TK1 and similar constrained devices.

## Model Details

| Property | Value |
|----------|-------|
| Architecture | {arch} |
| Parameters | {params:,} |
| Model size | {size_kb:.1f} KB |
| Distillation temperature | {best['temperature']} |
| Alpha (hard label weight) | {best['alpha']} |
| Validation accuracy | {accuracy:.1%} |
| Input shape | `(B, S, 128)` — pre-pooled embeddings |
| Output | 5-class logits (Wake, REM, N1, N2, N3) |
| ONNX opset | {config['export']['onnx_opset']} |

### Student Architecture Config

```yaml
{arch}:
"""
    for k, v in student_config.items():
        card += f"  {k}: {v}\n"

    card += f"""\
```

### Distillation Setup

- **Teacher**: SleepFM (SleepEventLSTMClassifier) — biLSTM, 128-dim embeddings
- **Sweep**: {len(sweep_cfg['temperatures'])} temperatures × {len(sweep_cfg['alphas'])} alphas × {len(config['students'])} architectures = {len(sweep_cfg['temperatures']) * len(sweep_cfg['alphas']) * len(config['students'])} experiments
- **Training**: {config['training']['epochs']} epochs, AdamW lr={config['training']['lr']}, early stopping (patience={config['training']['early_stopping_patience']})
- **Data**: Sleep-EDF ({len(config['data']['train_subjects'])} train / {len(config['data']['val_subjects'])} val / {len(config['data']['test_subjects'])} test subjects)

### Target Hardware

| Spec | Value |
|------|-------|
| Device | NVIDIA Jetson TK1 |
| CUDA cores | {jetson['cuda_cores']} |
| RAM | {jetson['ram_gb']} GB |
| Compute capability | {jetson['compute_capability']} |

## Usage

### ONNX Runtime

```python
import numpy as np
import onnxruntime as ort

session = ort.InferenceSession("{exp_id}.onnx")

# Input: pre-pooled embeddings (batch, seq_len, 128)
embeddings = np.random.randn(1, 120, 128).astype(np.float32)
logits = session.run(None, {{"input": embeddings}})[0]
predicted_stages = np.argmax(logits, axis=-1)

# Stage mapping: 0=Wake, 1=REM, 2=N1, 3=N2, 4=N3
print(predicted_stages)
```

### TorchScript

```python
import torch

model = torch.jit.load("{exp_id}.pt")
embeddings = torch.randn(1, 120, 128)
logits = model(embeddings)
predicted_stages = logits.argmax(dim=-1)
```

## Files

| File | Format | Description |
|------|--------|-------------|
| `{exp_id}.onnx` | ONNX (opset {config['export']['onnx_opset']}) | For ONNX Runtime / TensorRT |
| `{exp_id}.pt` | TorchScript | For PyTorch / LibTorch on-device |

## Limitations

- Trained on Sleep-EDF only (7 subjects) — may not generalize to other PSG datasets
- Expects pre-pooled 128-dim embeddings from SleepFM's encoder, not raw EEG
- No per-class metrics reported (overall accuracy only)
- Distilled from a single teacher checkpoint

## Citation

```bibtex
@misc{{circadia-distill-2026,
  title={{Distilled Sleep Stage Classifier for Edge Deployment}},
  year={{2026}},
  url={{https://github.com/circadia}}
}}
```
"""
    return card


def upload_to_hub(best, checkpoint_dir, config, repo_id, dry_run=False):
    """Stage model files and upload to Hugging Face Hub.

    Args:
        best: Best experiment info dict.
        checkpoint_dir: Path containing exported model files.
        config: Full distillation config.
        repo_id: HF repo ID (e.g. "username/model-name").
        dry_run: If True, print model card and skip upload.
    """
    exp_id = best["experiment_id"]
    model_card = generate_model_card(best, config)

    if dry_run:
        logger.info("=== DRY RUN — Model card preview ===")
        print(model_card)

        onnx_path = checkpoint_dir / f"{exp_id}.onnx"
        ts_path = checkpoint_dir / f"{exp_id}.pt"
        logger.info(f"Would upload ONNX:        {onnx_path} (exists={onnx_path.exists()})")
        logger.info(f"Would upload TorchScript: {ts_path} (exists={ts_path.exists()})")
        logger.info(f"Would upload to:          https://huggingface.co/{repo_id}")
        return

    from huggingface_hub import HfApi

    onnx_path = checkpoint_dir / f"{exp_id}.onnx"
    ts_path = checkpoint_dir / f"{exp_id}.pt"

    missing = []
    if not onnx_path.exists():
        missing.append(str(onnx_path))
    if not ts_path.exists():
        missing.append(str(ts_path))
    if missing:
        raise FileNotFoundError(
            f"Export files missing (run export first): {', '.join(missing)}"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Write model card
        (tmp / "README.md").write_text(model_card)

        # Copy model files
        import shutil
        shutil.copy2(onnx_path, tmp / onnx_path.name)
        shutil.copy2(ts_path, tmp / ts_path.name)

        # Upload
        api = HfApi()
        api.create_repo(repo_id, exist_ok=True)
        api.upload_folder(folder_path=str(tmp), repo_id=repo_id)

    logger.info(f"Uploaded to https://huggingface.co/{repo_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload best distilled model to Hugging Face Hub"
    )
    parser.add_argument(
        "--repo-id", required=True,
        help="HF repo ID, e.g. 'username/circadia-sleep-student'"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print model card and list files without uploading"
    )
    parser.add_argument(
        "--checkpoint-dir",
        help="Override checkpoint directory (default: from config)"
    )
    args = parser.parse_args()

    config = load_distill_config()
    best, checkpoint_dir = find_best_model(config)

    if args.checkpoint_dir:
        checkpoint_dir = Path(args.checkpoint_dir)

    upload_to_hub(best, checkpoint_dir, config, args.repo_id, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
