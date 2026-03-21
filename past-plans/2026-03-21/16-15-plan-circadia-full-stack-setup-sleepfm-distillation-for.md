# Archived Plan

**Source:** `precious-prancing-teapot.md`
**Session:** `ee4c87a0-2df3-4e52-a9e3-b4912c1596b6`
**Trigger:** `resume`
**Archived:** 2026-03-21 16:15:08

---

# Plan: Circadia — Full-Stack Setup + SleepFM Distillation for Jetson TK1

## Context

Circadia is a hackathon project (team of 4) building a sleep improvement app powered by SleepFM. The end goal is **local inference on an NVIDIA Jetson TK1** with a barebones HTML/CSS/JS UI on an external display. The app includes a breathing mini-game that starts at the user's actual sleep score.

**Critical hardware constraint:** Jetson TK1 has 2GB RAM, Kepler GPU (SM 3.2), CUDA 6.5, and no modern PyTorch/TensorRT support. SleepFM cannot run on it directly. We must distill into a tiny model and export to ONNX or C++ for inference.

---

## Step 1: Run the Demo Notebook

The demo at `sleepfm-clinical/notebooks/demo.ipynb` uses synthetic data in `demo_data/`. Checkpoints are already present in `sleepfm-clinical/sleepfm/checkpoints/`.

**CPU patches needed** (notebook hardcodes CUDA):

| Line | Change |
|---|---|
| 210 | `device = torch.device("cuda")` → `torch.device("cuda" if torch.cuda.is_available() else "cpu")` |
| 317, 576, 1145 | `torch.load(...)` → add `map_location=device` |
| 533, 1112 | `nn.DataParallel(model)` → wrap in `if torch.cuda.is_available():` |

Create `scripts/patch_demo_cpu.py` to apply these automatically.

```bash
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r sleepfm-clinical/requirements.txt
cd sleepfm-clinical/notebooks && jupyter notebook demo.ipynb
```

---

## Step 2: Local Dev Environment (venv + nvm, no Docker)

```bash
# Python
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r sleepfm-clinical/requirements.txt
pip install -e ".[dev]"

# Node.js (if nvm installed)
nvm use 20  # or nvm install 20
```

Everything stays project-local: `.venv/` and `node_modules/` in the repo dir, both gitignored. No home folder clutter.

---

## Step 3: Project Structure

```
circadia/
  sleepfm-clinical/              # submodule (read-only)

  ml/                            # ML pipeline (runs on cloud GPU)
    __init__.py
    config/
      finetune_n1.yaml
      distill.yaml
    training/
      __init__.py
      finetune.py                # N1-focused fine-tuning of sleep staging head
      distill.py                 # teacher (SleepFM) → student (tiny CNN)
      export_onnx.py             # export student model to ONNX
    inference/
      __init__.py
      predictor.py               # Python inference (dev/cloud)

  api/                           # FastAPI — serves both API + static files
    __init__.py
    main.py
    routers/
      sleep.py                   # POST /predict → sleep stage prediction
      game.py                    # GET/POST /game → breathing game state

  frontend/                      # Vanilla HTML/CSS/JS
    index.html                   # Main page
    css/
      style.css
    js/
      app.js                     # Main entry
      breathing-circle.js        # 0.1 Hz expanding/contracting circle
      tap-zone.js                # Rhythmic tapping input
      api-client.js              # Fetch calls to API

  jetson/                        # Jetson TK1 deployment
    inference/
      main.cpp                   # ONNX Runtime or custom C++ inference
      CMakeLists.txt
    server.py                    # Lightweight Flask/http.server for static files + inference
    deploy.sh                    # Script to build + deploy to Jetson

  scripts/
    patch_demo_cpu.py
  pyproject.toml
  .gitignore
```

---

## Step 4: Distillation Strategy for Jetson TK1

The TK1 cannot run PyTorch. The plan:

1. **Fine-tune SleepFM** (on cloud GPU) — add N1-focused class weighting to sleep staging head
2. **Distill to tiny student** — student architecture:
   - 3-4 layer 1D CNN (no transformer, no attention)
   - Input: single-channel EEG (not full multimodal — TK1 can't handle it)
   - Output: 5-class sleep stage probabilities
   - Target size: <5MB parameters
3. **Export to ONNX** — `torch.onnx.export()` the student
4. **Run on TK1** via one of:
   - **ONNX Runtime** (has ARM builds, may work on TK1's Cortex-A15 CPU)
   - **Custom C++ with Eigen** (most portable, no framework dependency)
   - **OpenCV DNN module** (can load ONNX, available on ARM)

**Fallback if GPU inference fails on TK1:** Run on CPU only. The student model is tiny enough (~5MB) that CPU inference on a 5-second window should take <100ms.

---

## Step 5: Serving Model on Jetson TK1

**Recommended: Local web server + browser kiosk**

- Lightweight Python HTTP server (or Go binary) on the Jetson
- Serves the `frontend/` static HTML/CSS/JS files
- Exposes `/api/predict` endpoint that runs the tiny student model
- Chromium in kiosk mode on the external display
- The breathing game runs entirely in the browser, calls the local API for sleep score

---

## Step 6: Verification

1. **Demo notebook**: Runs end-to-end on CPU with synthetic data
2. **Venv**: `source .venv/bin/activate && python -c "import sleepfm"` works
3. **API**: `uvicorn api.main:app` → `GET /docs` shows endpoints
4. **Frontend**: Open `frontend/index.html` → breathing circle animates
5. **Export**: `python ml/training/export_onnx.py` produces `student.onnx` < 5MB
6. **Jetson**: `ssh jetson && python server.py` → browser shows game on external display

---

## Files to Create

| File | Purpose |
|---|---|
| `pyproject.toml` | Dependencies + package config |
| `.gitignore` | data/, .venv/, __pycache__/, node_modules/ |
| `ml/__init__.py` | Package init |
| `ml/config/finetune_n1.yaml` | N1 fine-tuning config (from sleepfm template) |
| `ml/config/distill.yaml` | Distillation config |
| `ml/training/__init__.py` | Package init |
| `ml/training/finetune.py` | N1 fine-tuning script |
| `ml/training/distill.py` | Teacher-student distillation |
| `ml/training/export_onnx.py` | ONNX export |
| `ml/inference/__init__.py` | Package init |
| `ml/inference/predictor.py` | Python inference wrapper |
| `api/__init__.py` | Package init |
| `api/main.py` | FastAPI app (serves API + static frontend) |
| `api/routers/sleep.py` | Sleep prediction endpoints |
| `api/routers/game.py` | Game state endpoints |
| `frontend/index.html` | Main HTML page |
| `frontend/css/style.css` | Styles |
| `frontend/js/app.js` | Main JS entry |
| `frontend/js/breathing-circle.js` | 0.1 Hz breathing animation |
| `frontend/js/tap-zone.js` | Tap input handler |
| `frontend/js/api-client.js` | API fetch wrapper |
| `scripts/patch_demo_cpu.py` | CPU-patch demo notebook |

## Key Reference Files (sleepfm-clinical, read-only)

- `sleepfm-clinical/notebooks/demo.ipynb` — inference pipeline
- `sleepfm-clinical/sleepfm/models/models.py` — SetTransformer, Tokenizer, SleepEventLSTMClassifier
- `sleepfm-clinical/sleepfm/pipeline/finetune_sleep_staging.py` — fine-tuning reference
- `sleepfm-clinical/sleepfm/configs/config_finetune_sleep_events.yaml` — config template
- `sleepfm-clinical/requirements.txt` — pinned dependencies
