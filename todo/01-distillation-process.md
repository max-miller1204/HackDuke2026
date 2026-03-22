# Distillation Process

Distill the finetuned SleepFM model into a smaller, efficient model suitable for deployment on the NVIDIA Jetson TK1. Takes the checkpoint bundle from the finetuning step (`checkpoints/sleepfm-sleepEDF/`) as input.

## Key Tasks

- Design a lightweight student model architecture (e.g., small CNN or MLP) that fits Jetson TK1 memory/compute constraints
- Implement knowledge distillation training loop (teacher=finetuned SleepFM, student=lightweight model)
- Use soft label distillation (KL divergence on teacher logits) + hard label cross-entropy
- Validate that the distilled model maintains acceptable sleep staging accuracy
- Export the distilled model in a deployment-ready format (ONNX or TorchScript)
- Benchmark inference latency and memory usage against Jetson TK1 specs

## Dependencies

- Depends on: finetuning (todo 01) — needs the checkpoint bundle with `best.pth` and config
