---
name: circadia-project-context
description: Hackathon project — SleepFM distillation for Jetson TK1 + breathing mini-game, team of 4
type: project
---

Circadia is a hackathon project (team of 4 including Max) building a sleep improvement app.

**Two workstreams:**
1. Fine-tune SleepFM on N1/transitional sleep data → distill to tiny model → deploy on NVIDIA Jetson TK1
2. Breathing mini-game (HRV biofeedback at 0.1 Hz) that starts at user's actual sleep score

**Key constraints:**
- Jetson TK1: 2GB RAM, Kepler GPU (SM 3.2), CUDA 6.5, no modern PyTorch/TensorRT
- Must distill to tiny CNN (<5MB) and export to ONNX or C++ for TK1 inference
- Frontend: vanilla HTML/CSS/JS on external display (kiosk mode)
- Backend: FastAPI
- Fine-tuning budget: $5–$20 (cloud GPU)
- Dataset: possibly MESA (not decided yet)

**Why:** The TK1 hardware constraint drives the entire architecture — can't just deploy SleepFM directly.
**How to apply:** Always consider TK1 limitations when making model/deployment decisions.
