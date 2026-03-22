"""Modal integration for running SleepFM finetuning pipeline.

Bundles preprocessed data into the image, runs train → evaluate on GPU,
and exports the checkpoint bundle to a Modal volume.
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
    .add_local_dir("data/processed", remote_path="/app/data/processed")
    .add_local_file("pyproject.toml", remote_path="/app/pyproject.toml")
)


@app.function(
    image=image,
    gpu="T4",
    timeout=30 * 60,
    volumes={"/data": volume},
)
def run_pipeline():
    """Run train → evaluate on preprocessed data."""
    import json
    import os
    import shutil
    import sys
    from datetime import datetime
    from pathlib import Path

    os.chdir("/app")
    sys.path.insert(0, "/app")

    from loguru import logger

    # Verify preprocessed data is present
    processed_dir = Path("/app/data/processed")
    hdf5_files = list(processed_dir.glob("*.hdf5"))
    csv_files = list(processed_dir.glob("*.csv"))
    logger.info(f"Found {len(hdf5_files)} HDF5 + {len(csv_files)} CSV files in {processed_dir}")

    if not hdf5_files:
        return {"status": "error", "message": "No preprocessed data found"}

    # Step 1: Train
    logger.info("=== Step 1: Training ===")
    from src.train import main as train_main
    train_main()

    # Step 2: Evaluate
    logger.info("=== Step 2: Evaluation ===")
    from src.evaluate import main as evaluate_main
    evaluate_main()

    # Step 3: Export checkpoint bundle
    logger.info("=== Step 3: Exporting checkpoint bundle ===")
    from src.channel_map import export_channel_mapping

    save_dir = Path("/app/checkpoints/sleepfm-sleepEDF")
    export_channel_mapping(save_dir / "channel_mapping.json")

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

    # Copy bundle to volume for persistence
    output_vol = Path("/data/checkpoints/sleepfm-sleepEDF")
    output_vol.mkdir(parents=True, exist_ok=True)
    for f in save_dir.iterdir():
        shutil.copy2(f, output_vol / f.name)

    volume.commit()
    logger.info("Checkpoint bundle saved to volume at /data/checkpoints/sleepfm-sleepEDF/")

    # Return results
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
