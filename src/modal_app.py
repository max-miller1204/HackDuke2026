"""Modal integration for running the full SleepFM finetuning pipeline.

Single Modal function that:
1. Uploads raw EDFs + pretrained checkpoint to Modal volume
2. Runs preprocess → train → evaluate → export
3. Downloads checkpoint bundle
"""

import modal

app = modal.App("circadia-finetune")

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
    )
    .add_local_dir("src", remote_path="/app/src")
    .add_local_dir(
        "sleepfm-clinical/sleepfm",
        remote_path="/app/sleepfm-clinical/sleepfm",
    )
    .add_local_file("pyproject.toml", remote_path="/app/pyproject.toml")
)


@app.function(
    image=image,
    gpu="T4",
    timeout=30 * 60,
    volumes={"/data": volume},
)
def run_pipeline():
    """Run full pipeline: preprocess → train → evaluate."""
    import os
    import shutil
    import sys
    from pathlib import Path

    os.chdir("/app")
    sys.path.insert(0, "/app")

    from loguru import logger

    # Check if data exists on volume, if not copy from local
    data_dir = Path("/data/raw")
    if not data_dir.exists():
        logger.error("No raw data found on volume at /data/raw/")
        logger.info("Upload EDF files first: modal volume put circadia-data <local-path> /raw/")
        return {"status": "error", "message": "No raw data on volume"}

    # Also need pretrained checkpoint on volume
    checkpoint_vol = Path("/data/pretrained")
    if not checkpoint_vol.exists():
        logger.error("No pretrained checkpoint on volume at /data/pretrained/")
        logger.info("Upload: modal volume put circadia-data <checkpoint-dir> /pretrained/")
        return {"status": "error", "message": "No pretrained checkpoint on volume"}

    # Symlink data and checkpoint to expected paths
    app_data = Path("/app/data")
    app_data.mkdir(exist_ok=True)

    # Copy raw EDFs
    for edf_file in data_dir.glob("*.edf"):
        shutil.copy2(edf_file, app_data / edf_file.name)

    # Symlink pretrained checkpoint
    pretrained_dst = Path("/app/sleepfm-clinical/sleepfm/checkpoints/model_base")
    pretrained_dst.mkdir(parents=True, exist_ok=True)
    for f in checkpoint_vol.iterdir():
        dst = pretrained_dst / f.name
        if not dst.exists():
            shutil.copy2(f, dst)

    # Step 1: Preprocess
    logger.info("=== Step 1: Preprocessing ===")
    from src.preprocess import main as preprocess_main
    preprocess_main()

    # Step 2: Train
    logger.info("=== Step 2: Training ===")
    from src.train import main as train_main
    train_main()

    # Step 3: Evaluate
    logger.info("=== Step 3: Evaluation ===")
    from src.evaluate import main as evaluate_main
    evaluate_main()

    # Step 4: Export checkpoint bundle to volume
    logger.info("=== Step 4: Exporting checkpoint bundle ===")
    from src.channel_map import export_channel_mapping

    save_dir = Path("/app/checkpoints/sleepfm-sleepEDF")
    export_channel_mapping(save_dir / "channel_mapping.json")

    # Save metadata
    import json
    from datetime import datetime

    metadata = {
        "trained_at": datetime.now().isoformat(),
        "model": "SleepEventLSTMClassifier",
        "dataset": "Sleep-EDF",
        "subjects_train": ["SC4001", "SC4002", "SC4011"],
        "subjects_val": ["SC4012"],
        "subjects_test": ["SC4021"],
    }
    with open(save_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Copy bundle to volume
    output_vol = Path("/data/checkpoints/sleepfm-sleepEDF")
    output_vol.mkdir(parents=True, exist_ok=True)
    for f in save_dir.iterdir():
        shutil.copy2(f, output_vol / f.name)

    volume.commit()
    logger.info("Checkpoint bundle saved to volume at /data/checkpoints/sleepfm-sleepEDF/")

    # Load and return results
    results_path = save_dir / "evaluation_results.json"
    if results_path.exists():
        with open(results_path) as f:
            results = json.load(f)
        return {"status": "success", **results}

    return {"status": "success", "message": "Pipeline complete"}


@app.local_entrypoint()
def main():
    """Local entrypoint: modal run src/modal_app.py"""
    import json

    result = run_pipeline.remote()
    print(json.dumps(result, indent=2))
