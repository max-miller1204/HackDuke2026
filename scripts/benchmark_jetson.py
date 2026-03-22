#!/usr/bin/env python3
"""Standalone benchmark script for student models on Jetson TK1 (or any device).

Loads a TorchScript or ONNX model, runs timed inferences, and reports
latency statistics.  No project imports — works on a bare device with
torch/numpy and optionally onnxruntime.

Usage:
    python benchmark_jetson.py --model model.pt --format torchscript
    python benchmark_jetson.py --model model.onnx --format onnx --device cpu
"""

from __future__ import annotations

import argparse
import time
from typing import List

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(values: List[float], p: float) -> float:
    """Return the p-th percentile of *values* (0-100 scale)."""
    arr = np.array(values)
    return float(np.percentile(arr, p))


def _fmt_ms(seconds: float) -> str:
    return f"{seconds * 1000:.2f} ms"


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

def _run_torchscript(model_path: str, dummy_input, device: str,
                     warmup: int, num_runs: int):
    import torch

    model = torch.jit.load(model_path, map_location=device)
    model.eval()

    x = torch.from_numpy(dummy_input).float().to(device)

    # Warm-up
    with torch.no_grad():
        for _ in range(warmup):
            model(x)
    if device == "cuda":
        torch.cuda.synchronize()

    # Timed runs
    latencies: List[float] = []
    with torch.no_grad():
        for _ in range(num_runs):
            if device == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            model(x)
            if device == "cuda":
                torch.cuda.synchronize()
            latencies.append(time.perf_counter() - t0)

    # Peak memory
    peak_mem_mb = None
    if device == "cuda":
        peak_mem_mb = torch.cuda.max_memory_allocated() / (1024 ** 2)

    return latencies, peak_mem_mb


def _run_onnx(model_path: str, dummy_input, device: str,
              warmup: int, num_runs: int):
    import onnxruntime as ort

    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if device == "cuda" \
        else ["CPUExecutionProvider"]

    sess = ort.InferenceSession(model_path, providers=providers)
    input_name = sess.get_inputs()[0].name

    feed = {input_name: dummy_input.astype(np.float32)}

    # Warm-up
    for _ in range(warmup):
        sess.run(None, feed)

    # Timed runs
    latencies: List[float] = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        sess.run(None, feed)
        latencies.append(time.perf_counter() - t0)

    return latencies, None


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _print_report(args, latencies: List[float], peak_mem_mb):
    mean_lat = np.mean(latencies)
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)
    min_lat = min(latencies)
    max_lat = max(latencies)

    w = 48
    print()
    print("=" * w)
    print("  Jetson Benchmark Results")
    print("=" * w)
    print(f"  Model        : {args.model}")
    print(f"  Format       : {args.format}")
    print(f"  Device       : {args.device}")
    print(f"  Batch size   : {args.batch_size}")
    print(f"  Seq length   : {args.seq_len}")
    print(f"  Num runs     : {args.num_runs}")
    print("-" * w)
    print(f"  Mean latency : {_fmt_ms(mean_lat)}")
    print(f"  P50  latency : {_fmt_ms(p50)}")
    print(f"  P95  latency : {_fmt_ms(p95)}")
    print(f"  P99  latency : {_fmt_ms(p99)}")
    print(f"  Min  latency : {_fmt_ms(min_lat)}")
    print(f"  Max  latency : {_fmt_ms(max_lat)}")
    if peak_mem_mb is not None:
        print(f"  Peak CUDA mem: {peak_mem_mb:.1f} MB")
    print("=" * w)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark a student model (TorchScript or ONNX).",
    )
    parser.add_argument("--model", required=True, help="Path to model file")
    parser.add_argument("--format", required=True, choices=["torchscript", "onnx"],
                        help="Model format")
    parser.add_argument("--seq-len", type=int, default=120,
                        help="Sequence length (default: 120)")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="Batch size (default: 1)")
    parser.add_argument("--num-runs", type=int, default=100,
                        help="Number of timed inference runs (default: 100)")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu",
                        help="Device to run on (default: cpu)")
    args = parser.parse_args()

    warmup = 10
    input_channels = 128
    dummy_input = np.random.randn(
        args.batch_size, args.seq_len, input_channels,
    ).astype(np.float32)

    print(f"Running {args.format} benchmark on {args.device} "
          f"(warmup={warmup}, runs={args.num_runs}) ...")

    if args.format == "torchscript":
        latencies, peak_mem_mb = _run_torchscript(
            args.model, dummy_input, args.device, warmup, args.num_runs,
        )
    else:
        latencies, peak_mem_mb = _run_onnx(
            args.model, dummy_input, args.device, warmup, args.num_runs,
        )

    _print_report(args, latencies, peak_mem_mb)


if __name__ == "__main__":
    main()
