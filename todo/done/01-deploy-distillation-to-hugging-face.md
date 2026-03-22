# Deploy Distillation to Hugging Face

Upload the best distilled sleep staging model (Conv1dStack_T2_a0.3, 75.2% accuracy, 103KB) to Hugging Face Hub with an auto-generated model card.

## Decisions

- **Model scope**: Best model only (Conv1dStack_T2_a0.3)
- **Format**: Both ONNX (opset 11) and TorchScript
- **Script**: Standalone `src/distill/upload_hf.py`, decoupled from Modal
- **Auth**: Cached `huggingface-cli login` token first, fallback to `HF_TOKEN` env var
- **License**: MIT
- **Model card**: Auto-generated with full transparency (exact subject IDs, class weights, limited evaluation caveat)
- **Input dependency**: Document that model requires pre-pooled embeddings from SleepFM, link to sleepfm-clinical
- **Example code**: Inline ONNX Runtime + TorchScript snippets in model card
- **Excluded**: Teacher checkpoint, teacher logits, other sweep variants, Pareto plot

## Deliverables

### 1. `src/distill/upload_hf.py` — Upload Script

**CLI interface:**
```bash
python -m src.distill.upload_hf \
  --repo-id "username/circadia-sleep-staging" \
  [--dry-run]          # print model card + file list, don't upload
  [--checkpoint-dir checkpoints/distill]  # override default
```

No `--token` arg (avoids leaking tokens in shell history).

**Functions:**

- `find_best_model(sweep_results) -> dict` — Locate Conv1dStack_T2_a0.3 by experiment_id. Fail explicitly if not found.

- `generate_model_card(best_result, config, sweep_data) -> str` — Build full README.md markdown string. Pulls metrics from sweep_results.json and config from config_distill.yaml.

- `upload_to_hub(repo_id, checkpoint_dir, model_card_text, best_result, dry_run=False)` — Create/reuse repo via `HfApi.create_repo(exist_ok=True)`, stage files in a temp dir (README.md + ONNX + TorchScript), upload with `api.upload_folder()`.

- `main()` — argparse CLI entry point.

**Upload flow:**
1. `load_distill_config()` → config dict
2. Load `sweep_results.json` from checkpoint_dir
3. `find_best_model()` → best experiment dict
4. Verify `Conv1dStack_T2_a0.3.onnx` and `.pt` exist (fail with "run export first" if missing)
5. `generate_model_card()` → README.md string
6. If `--dry-run`: print model card + file list, exit
7. `HfApi()` → create repo → stage files in tempdir → `upload_folder()` → log URL

**Auth resolution:** `HfApi` handles this natively — checks cached login token, then HF_TOKEN env var.

**Error messages:**
- Missing `.onnx`/`.pt`: "Run `python -m src.distill.export` first"
- Missing `sweep_results.json`: "Run `python -m src.distill.train_distill` first"
- Auth failure: Let huggingface_hub raise its own error (good built-in messages)

### 2. Model Card Content

HF YAML frontmatter:
```yaml
license: mit
tags: [sleep-staging, EEG, distillation, ONNX, edge-deployment, pytorch]
library_name: pytorch
pipeline_tag: other
datasets: [physionet/sleep-edf]
```

Sections:
1. **Title + one-line description** — "Distilled from SleepFM for edge deployment"
2. **Input dependency callout** — Pre-pooled embeddings (B, S, 128) required, link to sleepfm-clinical
3. **Model Details table** — Architecture, params, size, input/output shapes, ONNX opset
4. **Distillation Config table** — Teacher, temperature, alpha, loss formula, optimizer, epochs, class weights
5. **Performance table** — Val accuracy, val loss, train loss (from sweep_results.json)
6. **Limitations** — Exact subject IDs for train/val/test splits, 7 subjects total, single-subject validation caveat
7. **Usage: ONNX Runtime** — Inline Python snippet
8. **Usage: TorchScript** — Inline Python snippet
9. **Files table** — ONNX and TorchScript with sizes
10. **Citation** — SleepFM Nature Medicine BibTeX

### Files Uploaded to HF

| File | Source |
|---|---|
| `README.md` | Auto-generated model card |
| `Conv1dStack_T2_a0.3.onnx` | From `checkpoints/distill/` |
| `Conv1dStack_T2_a0.3.pt` | From `checkpoints/distill/` |

## Key Implementation Details

- Reuse `load_distill_config()` from `src/distill/soft_labels.py`
- Resolve project root with `Path(__file__).resolve().parent.parent.parent` (same as export.py)
- File naming convention: `{arch}_T{temp}_a{alpha}` (from export.py)
- Use `loguru.logger` for consistency with other distill scripts
- Imports: `huggingface_hub.HfApi`, `json`, `argparse`, `shutil`, `tempfile`, `pathlib.Path`

## Verification

1. `python -m src.distill.upload_hf --repo-id test/test --dry-run` — Verify model card renders correctly
2. `python -m src.distill.upload_hf --repo-id {username}/circadia-sleep-staging` — Upload and verify at `https://huggingface.co/{username}/circadia-sleep-staging`
3. Verify on HF: model card renders, files downloadable, tags visible, license correct
4. Test download + inference: `onnxruntime.InferenceSession` loads the ONNX file from HF

---

## Work Units

### Execution Strategy
Sequential (single worker)

**Rationale:** This is a single new file (`upload_hf.py`) with no independent parallel components. The model card generation and upload logic are tightly coupled and must be in the same file. Not worth splitting.

### Foundation Unit (Phase 1)

> N/A — single file, no shared scaffolding needed.

### Sequential Units

| Order | Unit Name | Files (create/modify) | Depends On | Description |
|-------|-----------|----------------------|------------|-------------|
| 1 | Upload script + model card | Create: `src/distill/upload_hf.py` | Existing export.py, soft_labels.py, config_distill.yaml | Implement CLI, model card generation, and HF upload |

### Dependency & Conflict Analysis
- **File conflicts:** None — single new file created
- **Runtime dependencies:** Imports `load_distill_config` from `src/distill/soft_labels.py` (existing, stable). Reads `checkpoints/distill/sweep_results.json` (existing). Requires `huggingface_hub` package.

### Post-Merge Verification
1. Ensure `huggingface_hub` is in `pyproject.toml` dependencies
2. Run `python -m src.distill.upload_hf --repo-id test/test --dry-run` to verify model card output
3. Run actual upload and verify the HF repo page renders correctly with all sections, files, and metadata
