"""Modal runner for the full distillation pipeline.

Mirrors src/modal_app.py.  Runs on a T4 GPU with a 1-hour timeout.

Pipeline steps:
  1. Generate soft labels from teacher
  2. Run distillation sweep (train student models)
  3. Export best student to TorchScript + ONNX
  4. Generate comparison report

Usage:
    modal run src/modal_distill.py
"""

import modal

app = modal.App("circadia-distill")

volume = modal.Volume.from_name("circadia-data", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "torch>=2.0",
        "mne>=1.6",
        "pyedflib>=0.1.35",
        "h5py>=3.10",
        "scipy>=1.12",
        "einops>=0.7",
        "loguru>=0.7",
        "pyyaml>=6.0",
        "pandas>=2.1",
        "numpy>=1.26",
        "scikit-learn>=1.4",
        "tqdm>=4.66",
        "matplotlib>=3.8",
        "onnxruntime>=1.17",
        "onnxscript",
    )
    .add_local_dir("src", remote_path="/app/src")
    .add_local_dir(
        "sleepfm-clinical/sleepfm",
        remote_path="/app/sleepfm-clinical/sleepfm",
    )
    .add_local_dir("data/processed", remote_path="/app/data/processed")
    .add_local_file("pyproject.toml", remote_path="/app/pyproject.toml")
)


@app.function(
    image=image,
    gpu="T4",
    timeout=60 * 60,
    volumes={"/data": volume},
)
def run_pipeline():
    """Run soft-labels -> sweep -> export -> report on GPU."""
    import json
    import os
    import shutil
    import sys
    from pathlib import Path

    os.chdir("/app")
    sys.path.insert(0, "/app")

    from loguru import logger

    # ------------------------------------------------------------------
    # Step 0: Copy teacher checkpoint from Modal volume
    # ------------------------------------------------------------------
    teacher_vol = Path("/data/checkpoints/sleepfm-sleepEDF")
    teacher_local = Path("/app/checkpoints/sleepfm-sleepEDF")
    if teacher_vol.exists():
        teacher_local.mkdir(parents=True, exist_ok=True)
        for f in teacher_vol.iterdir():
            if f.is_file():
                shutil.copy2(f, teacher_local / f.name)
        logger.info(f"Copied teacher checkpoint from volume: {list(teacher_local.glob('*'))}")
    else:
        logger.error("Teacher checkpoint not found on volume. Run modal_app.py first.")
        return {"status": "error", "message": "No teacher checkpoint on volume"}

    from src.distill.soft_labels import load_distill_config
    config = load_distill_config()

    # ------------------------------------------------------------------
    # Step 1: Generate soft labels from teacher
    # ------------------------------------------------------------------
    logger.info("=== Step 1: Generating soft labels ===")
    from src.distill.soft_labels import generate_soft_labels
    generate_soft_labels(config)
    logger.info("Soft labels generated.")

    # ------------------------------------------------------------------
    # Step 2: Run distillation sweep
    # ------------------------------------------------------------------
    logger.info("=== Step 2: Running distillation sweep ===")
    from src.distill.train_distill import main as train_distill_main
    train_distill_main()
    logger.info("Distillation sweep complete.")

    # ------------------------------------------------------------------
    # Step 3: Export best student model
    # ------------------------------------------------------------------
    logger.info("=== Step 3: Exporting best student ===")
    from src.distill.export import main as export_main
    export_main()
    logger.info("Export complete.")

    # ------------------------------------------------------------------
    # Step 4: Generate comparison report
    # ------------------------------------------------------------------
    logger.info("=== Step 4: Generating report ===")
    from src.distill.report import main as report_main

    report_main()
    logger.info("Report generated.")

    # ------------------------------------------------------------------
    # Copy outputs to Modal volume for persistence
    # ------------------------------------------------------------------
    distill_ckpt = Path("/app/checkpoints/distill")
    if distill_ckpt.exists():
        output_vol = Path("/data/checkpoints/distill")
        output_vol.mkdir(parents=True, exist_ok=True)
        for item in distill_ckpt.rglob("*"):
            if item.is_file():
                dest = output_vol / item.relative_to(distill_ckpt)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)
        logger.info("Distill checkpoints saved to volume at /data/checkpoints/distill/")

    volume.commit()

    # Build summary
    result = {"status": "success"}
    sweep_path = distill_ckpt / "sweep_results.json"
    if sweep_path.exists():
        with open(sweep_path) as f:
            result["sweep"] = json.load(f)

    # Include report path if it exists
    report_path = distill_ckpt / "report.png"
    if report_path.exists():
        result["report"] = "/data/checkpoints/distill/report.png"

    return result


@app.local_entrypoint()
def main():
    """Local entrypoint: modal run src/modal_distill.py"""
    import json

    result = run_pipeline.remote()
    print(json.dumps(result, indent=2))
