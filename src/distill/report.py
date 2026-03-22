"""Pareto analysis and reporting for distillation sweep results.

Generates accuracy vs size and accuracy vs latency plots with Pareto frontiers,
targeting Jetson TK1 deployment constraints.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from loguru import logger

from src.distill.soft_labels import load_distill_config
from src.distill.student_models import build_student


def estimate_flops(model, seq_len=120, embed_dim=128):
    """Estimate FLOPs for a student backbone forward pass.

    Uses manual calculation based on layer types rather than profiler
    for reliability and reproducibility.

    Args:
        model: Student model instance.
        seq_len: Sequence length to estimate for.
        embed_dim: Input embedding dimension.

    Returns:
        Estimated FLOPs (int).
    """
    flops = 0
    dummy = torch.randn(1, seq_len, embed_dim)

    for name, module in model.named_modules():
        if isinstance(module, torch.nn.Linear):
            # FLOPs = 2 * in_features * out_features (multiply-add)
            # Applied per sequence position if input is 3D
            flops += 2 * module.in_features * module.out_features * seq_len

        elif isinstance(module, torch.nn.GRU):
            # GRU: 3 gates, each with input and hidden projections
            # Per timestep: 3 * (2 * input_size * hidden_size + 2 * hidden_size * hidden_size)
            input_size = module.input_size
            hidden_size = module.hidden_size
            num_directions = 2 if module.bidirectional else 1
            per_step = 3 * (2 * input_size * hidden_size + 2 * hidden_size * hidden_size)
            flops += per_step * seq_len * num_directions

        elif isinstance(module, torch.nn.Conv1d):
            # FLOPs = 2 * in_channels * out_channels * kernel_size * seq_len
            flops += 2 * module.in_channels * module.out_channels * module.kernel_size[0] * seq_len

        elif isinstance(module, torch.nn.BatchNorm1d):
            # ~4 ops per element (subtract mean, divide std, scale, shift)
            flops += 4 * module.num_features * seq_len

    return flops


def estimate_latency_ms(flops, config):
    """Estimate inference latency on Jetson TK1.

    Args:
        flops: Estimated FLOP count.
        config: Full distillation config dict (needs jetson_tk1 section).

    Returns:
        Estimated latency in milliseconds.
    """
    peak_gflops = config["jetson_tk1"]["peak_gflops"]
    efficiency = config["jetson_tk1"]["efficiency_factor"]
    effective_flops_per_sec = peak_gflops * efficiency * 1e9
    return (flops / effective_flops_per_sec) * 1000


def find_pareto_front(points):
    """Find Pareto-optimal indices (minimize x, maximize y).

    For our use case: x = model size or latency (minimize),
    y = accuracy (maximize). A point is Pareto-optimal if no other
    point is both smaller/faster AND more accurate.

    Args:
        points: List of (x, y) tuples.

    Returns:
        List of indices on the Pareto frontier, sorted by x.
    """
    if not points:
        return []

    pts = np.array(points)
    n = len(pts)
    is_pareto = np.ones(n, dtype=bool)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # j dominates i if j has <= x AND >= y, with at least one strict
            if pts[j, 0] <= pts[i, 0] and pts[j, 1] >= pts[i, 1]:
                if pts[j, 0] < pts[i, 0] or pts[j, 1] > pts[i, 1]:
                    is_pareto[i] = False
                    break

    pareto_indices = np.where(is_pareto)[0]
    # Sort by x for plotting
    pareto_indices = pareto_indices[np.argsort(pts[pareto_indices, 0])]
    return pareto_indices.tolist()


def generate_report(config=None):
    """Load sweep results, compute estimates, generate Pareto plots and summary.

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
        sweep_results = json.load(f)

    if not sweep_results:
        logger.error("sweep_results.json is empty")
        return

    # Compute FLOP estimates and latency for each result
    architectures = sorted(set(r["arch"] for r in sweep_results))
    arch_colors = {}
    color_cycle = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800", "#00BCD4"]
    for i, arch in enumerate(architectures):
        arch_colors[arch] = color_cycle[i % len(color_cycle)]

    enriched = []
    for r in sweep_results:
        model = build_student(r["arch"], config)
        flops = estimate_flops(model, seq_len=120, embed_dim=config["embed_dim"])
        latency = estimate_latency_ms(flops, config)
        size_kb = r["model_size_bytes"] / 1024

        enriched.append({
            **r,
            "flops": flops,
            "latency_ms": latency,
            "size_kb": size_kb,
        })

    # Build point arrays for Pareto analysis
    size_acc_points = [(e["size_kb"], e["val_accuracy"]) for e in enriched]
    latency_acc_points = [(e["latency_ms"], e["val_accuracy"]) for e in enriched]

    pareto_size = find_pareto_front(size_acc_points)
    pareto_latency = find_pareto_front(latency_acc_points)

    # --- Generate plots ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Plot 1: Accuracy vs Model Size
    for arch in architectures:
        indices = [i for i, e in enumerate(enriched) if e["arch"] == arch]
        sizes = [enriched[i]["size_kb"] for i in indices]
        accs = [enriched[i]["val_accuracy"] for i in indices]
        ax1.scatter(sizes, accs, c=arch_colors[arch], label=arch, s=60, alpha=0.7, zorder=2)

    # Mark Pareto-optimal with stars
    for idx in pareto_size:
        e = enriched[idx]
        ax1.scatter(e["size_kb"], e["val_accuracy"], marker="*", s=200,
                    c=arch_colors[e["arch"]], edgecolors="black", linewidths=0.8, zorder=3)

    # Connect Pareto frontier
    if len(pareto_size) > 1:
        px = [enriched[i]["size_kb"] for i in pareto_size]
        py = [enriched[i]["val_accuracy"] for i in pareto_size]
        ax1.plot(px, py, "k--", alpha=0.4, linewidth=1, zorder=1)

    ax1.set_xlabel("Model Size (KB)")
    ax1.set_ylabel("Validation Accuracy")
    ax1.set_title("Accuracy vs Model Size")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Accuracy vs Estimated Latency
    for arch in architectures:
        indices = [i for i, e in enumerate(enriched) if e["arch"] == arch]
        lats = [enriched[i]["latency_ms"] for i in indices]
        accs = [enriched[i]["val_accuracy"] for i in indices]
        ax2.scatter(lats, accs, c=arch_colors[arch], label=arch, s=60, alpha=0.7, zorder=2)

    for idx in pareto_latency:
        e = enriched[idx]
        ax2.scatter(e["latency_ms"], e["val_accuracy"], marker="*", s=200,
                    c=arch_colors[e["arch"]], edgecolors="black", linewidths=0.8, zorder=3)

    if len(pareto_latency) > 1:
        px = [enriched[i]["latency_ms"] for i in pareto_latency]
        py = [enriched[i]["val_accuracy"] for i in pareto_latency]
        ax2.plot(px, py, "k--", alpha=0.4, linewidth=1, zorder=1)

    ax2.set_xlabel("Estimated Latency (ms) — Jetson TK1")
    ax2.set_ylabel("Validation Accuracy")
    ax2.set_title("Accuracy vs Latency")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    pareto_path = output_dir / "pareto.png"
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(pareto_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Pareto plot saved: {pareto_path}")

    # --- Print summary table ---
    print("\n" + "=" * 90)
    print("DISTILLATION SWEEP SUMMARY")
    print("=" * 90)
    header = f"{'Arch':<14} {'T':>3} {'alpha':>5} {'Acc':>6} {'Size(KB)':>9} {'Latency(ms)':>12} {'FLOPs':>12} {'Pareto':>7}"
    print(header)
    print("-" * 90)

    for i, e in enumerate(enriched):
        is_pareto = i in pareto_size or i in pareto_latency
        pareto_mark = "*" if is_pareto else ""
        print(
            f"{e['arch']:<14} {e['temperature']:>3} {e['alpha']:>5} "
            f"{e['val_accuracy']:>6.3f} {e['size_kb']:>9.1f} "
            f"{e['latency_ms']:>12.4f} {e['flops']:>12,} {pareto_mark:>7}"
        )

    print("-" * 90)
    print("\nPareto-optimal models (size):")
    for idx in pareto_size:
        e = enriched[idx]
        print(f"  {e['arch']} T={e['temperature']} alpha={e['alpha']}: "
              f"acc={e['val_accuracy']:.3f}, size={e['size_kb']:.1f}KB")

    print("\nPareto-optimal models (latency):")
    for idx in pareto_latency:
        e = enriched[idx]
        print(f"  {e['arch']} T={e['temperature']} alpha={e['alpha']}: "
              f"acc={e['val_accuracy']:.3f}, latency={e['latency_ms']:.4f}ms")

    print()


def main():
    generate_report()


if __name__ == "__main__":
    main()
