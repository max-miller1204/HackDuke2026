"""Export student models to ONNX and TorchScript for Jetson TK1 deployment.

Exports the backbone only (pre-pooled input B, S, E=128) since spatial
mean-pooling is trivial and handled in preprocessing on-device.
"""

import json
from pathlib import Path

import numpy as np
import torch
from loguru import logger

from src.distill.soft_labels import load_distill_config
from src.distill.student_models import build_student


def export_student(model, config, experiment_info, output_dir):
    """Export a single student model to ONNX and TorchScript.

    Args:
        model: Student model instance (already loaded with weights).
        config: Full distillation config dict.
        experiment_info: Dict with arch, temperature, alpha, etc.
        output_dir: Path to write exported files.

    Returns:
        Dict with export paths and validation results.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    arch = experiment_info.get("architecture", experiment_info.get("arch"))
    temp = experiment_info["temperature"]
    alpha = experiment_info["alpha"]
    base_name = f"{arch}_T{temp}_a{alpha}"

    onnx_path = output_dir / f"{base_name}.onnx"
    ts_path = output_dir / f"{base_name}.pt"

    embed_dim = config["embed_dim"]
    model.eval()

    # Wrap backbone in a standalone module for tracing/export
    class BackboneWrapper(torch.nn.Module):
        def __init__(self, student):
            super().__init__()
            self.student = student

        def forward(self, x):
            return self.student.backbone(x)

    wrapper = BackboneWrapper(model)
    wrapper.eval()

    # Dummy input for backbone: (B, S, E) — pre-pooled
    dummy_input = torch.randn(1, 120, embed_dim)

    # --- TorchScript export ---
    with torch.no_grad():
        traced = torch.jit.trace(wrapper, dummy_input)
    traced.save(str(ts_path))
    logger.info(f"TorchScript saved: {ts_path}")

    # --- ONNX export ---
    opset = config["export"]["onnx_opset"]
    torch.onnx.export(
        wrapper,
        dummy_input,
        str(onnx_path),
        opset_version=opset,
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={
            "input": {0: "batch", 1: "seq_len"},
            "logits": {0: "batch", 1: "seq_len"},
        },
        dynamo=False,
    )
    logger.info(f"ONNX saved: {onnx_path} (opset {opset})")

    # --- Validate ONNX output ---
    validation_ok = _validate_onnx(model, onnx_path, embed_dim, config)

    return {
        "onnx_path": str(onnx_path),
        "torchscript_path": str(ts_path),
        "validation_passed": validation_ok,
    }


def _validate_onnx(model, onnx_path, embed_dim, config):
    """Compare ONNX output against PyTorch within atol tolerance.

    Returns True if validation passes, False otherwise.
    """
    try:
        import onnxruntime as ort
    except ImportError:
        logger.warning("onnxruntime not installed — skipping ONNX validation")
        return None

    atol = config["export"]["validation_atol"]

    # Run PyTorch
    test_input = torch.randn(2, 60, embed_dim)
    model.eval()
    with torch.no_grad():
        pt_output = model.backbone(test_input).numpy()

    # Run ONNX
    session = ort.InferenceSession(str(onnx_path))
    ort_output = session.run(None, {"input": test_input.numpy()})[0]

    max_diff = np.max(np.abs(pt_output - ort_output))
    passed = bool(max_diff < atol)

    if passed:
        logger.info(f"  ONNX validation PASSED (max_diff={max_diff:.2e}, atol={atol})")
    else:
        logger.error(f"  ONNX validation FAILED (max_diff={max_diff:.2e}, atol={atol})")

    return passed


def export_all(config=None):
    """Load sweep_results.json and export all student checkpoints.

    Args:
        config: Full distillation config dict. Loaded from yaml if None.
    """
    if config is None:
        config = load_distill_config()

    project_root = Path(__file__).resolve().parent.parent.parent
    output_dir = project_root / config["export"]["output_dir"]
    results_path = output_dir / "sweep_results.json"

    if not results_path.exists():
        logger.error(f"sweep_results.json not found at {results_path}")
        return

    with open(results_path) as f:
        sweep_data = json.load(f)

    # sweep_results.json has a "results" key wrapping the experiment list
    sweep_results = sweep_data["results"] if "results" in sweep_data else sweep_data

    logger.info(f"Exporting {len(sweep_results)} student models...")
    export_results = []

    for info in sweep_results:
        arch = info["architecture"]
        exp_id = info["experiment_id"]
        checkpoint_path = output_dir / f"{exp_id}.pth"

        if not checkpoint_path.exists():
            logger.warning(f"Checkpoint missing: {checkpoint_path}, skipping")
            continue

        # Build model and load weights
        model = build_student(arch, config)
        state_dict = torch.load(str(checkpoint_path), map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        model.eval()

        logger.info(f"Exporting {arch} T={info['temperature']} alpha={info['alpha']}")
        result = export_student(model, config, info, output_dir)
        result["arch"] = arch
        result["temperature"] = info["temperature"]
        result["alpha"] = info["alpha"]
        export_results.append(result)

    # Save export summary
    summary_path = output_dir / "export_results.json"
    with open(summary_path, "w") as f:
        json.dump(export_results, f, indent=2)
    logger.info(f"Export summary saved: {summary_path}")

    # Report
    passed = sum(1 for r in export_results if r.get("validation_passed") is True)
    failed = sum(1 for r in export_results if r.get("validation_passed") is False)
    skipped = sum(1 for r in export_results if r.get("validation_passed") is None)
    logger.info(f"Export complete: {passed} passed, {failed} failed, {skipped} skipped validation")


def main():
    export_all()


if __name__ == "__main__":
    main()
