# Archived Plan

**Source:** `inherited-squishing-raven.md`
**Session:** `9b022d98-5632-428e-9690-6cf304ec8902`
**Trigger:** `clear`
**Archived:** 2026-03-22 14:54:56

---

# Plan: Deploy Distillation to Hugging Face

## Context
The distillation sweep is complete with 27 experiments. The best model (Conv1dStack_T2_a0.3, 75.2% accuracy, 103KB) needs to be published to Hugging Face Hub for public sharing. This is a prerequisite for the Android deployment and front-end integration todos.

## Approach
Create a single standalone script `src/distill/upload_hf.py` that auto-generates a model card from existing sweep results/config and uploads the best model's ONNX + TorchScript files.

## Steps

1. **Check `huggingface_hub` dependency** — Verify it's in `pyproject.toml`, add if missing
2. **Create `src/distill/upload_hf.py`** — Full implementation:
   - `find_best_model()` — locate Conv1dStack_T2_a0.3 in sweep results
   - `generate_model_card()` — build README.md with HF frontmatter, architecture details, metrics, limitations, inline inference examples, citation
   - `upload_to_hub()` — stage files in tempdir, create repo, upload_folder
   - `main()` — argparse CLI with `--repo-id`, `--dry-run`, `--checkpoint-dir`
3. **Test with `--dry-run`** — Verify model card output looks correct
4. **Verify** — Check HF page renders correctly (if user wants to do actual upload)

## Critical Files
- Create: `src/distill/upload_hf.py`
- Read: `src/distill/export.py` (file naming pattern)
- Read: `src/distill/soft_labels.py` (reuse `load_distill_config()`)
- Read: `src/distill/config_distill.yaml` (config values)
- Read: `checkpoints/distill/sweep_results.json` (metrics)
- Maybe modify: `pyproject.toml` (add huggingface_hub dep)

## Verification
1. `python -m src.distill.upload_hf --repo-id test/test --dry-run` — model card renders correctly
2. Actual upload + verify HF page (model card, files, tags, license)
3. Download + inference test with onnxruntime
