# Archived Plan

**Source:** `precious-prancing-teapot.md`
**Session:** `381be74c-b77c-4914-819a-d99d60448ca7`
**Trigger:** `resume`
**Archived:** 2026-03-21 17:14:50

---

# Plan: Circadia — SleepFM Distillation + Dual Frontend (Jetson + Web)

## Context

Circadia is a hackathon project (team of 4) building a sleep improvement app powered by SleepFM. Two deployment targets:
1. **Jetson TK1** — local inference with barebones HTML/CSS/JS on an external display
2. **Web app** — polished React + TypeScript version

The app includes a breathing mini-game (HRV biofeedback at 0.1 Hz) that starts at the user's actual sleep score.

**Critical constraint:** Jetson TK1 (2GB RAM, Kepler GPU SM 3.2, CUDA 6.5) cannot run PyTorch. Must distill SleepFM into a tiny model and export to ONNX/C++.

---

## Step 1: Run the Demo Notebook

Demo at `sleepfm-clinical/notebooks/demo.ipynb` with synthetic data + pre-trained checkpoints.

**CPU patches needed** (notebook hardcodes CUDA):

| Line | Change |
|---|---|
| 210 | `device = torch.device("cuda")` → `torch.device("cuda" if torch.cuda.is_available() else "cpu")` |
| 317, 576, 1145 | `torch.load(...)` → add `map_location=device` |
| 533, 1112 | `nn.DataParallel(model)` → wrap in `if torch.cuda.is_available():` |

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

# Node.js (for React web frontend)
nvm use 20  # or nvm install 20
```

Everything project-local: `.venv/` and `node_modules/` gitignored. No home folder clutter.

---

## Step 3: Project Structure

```
circadia/
  sleepfm-clinical/              # git submodule (read-only)

  ml/                            # ML pipeline (runs on cloud GPU)
    __init__.py
    config/
      finetune_n1.yaml
      distill.yaml
    training/
      __init__.py
      finetune.py                # N1-focused fine-tuning
      distill.py                 # teacher (SleepFM) → student (tiny CNN)
      export_onnx.py             # export student to ONNX
    inference/
      __init__.py
      predictor.py               # Python inference wrapper

  api/                           # FastAPI backend (shared by both frontends)
    __init__.py
    main.py
    routers/
      sleep.py                   # POST /predict → sleep stages
      game.py                    # GET/POST /game → breathing game state

  # ---- TWO FRONTENDS ----

  frontend-jetson/               # Jetson TK1: vanilla HTML/CSS/JS (ultra-light)
    index.html
    css/style.css
    js/
      app.js
      breathing-circle.js        # 0.1 Hz expanding/contracting SVG circle
      tap-zone.js                # rhythmic tapping input
      api-client.js              # fetch calls to local API

  frontend-web/                  # Web app: React + TypeScript (polished)
    package.json
    tsconfig.json
    src/
      App.tsx
      components/
        BreathingCircle.tsx      # animated breathing circle with transitions
        TapZone.tsx              # tapping input with haptic feedback
        ScoreDisplay.tsx         # sleep score dashboard
        Hypnogram.tsx            # sleep stage visualization
      hooks/
        useBreathingSync.ts      # timing logic for breathing patterns
        useGameState.ts          # game state management
      api/
        client.ts                # typed API client

  jetson/                        # Jetson TK1 deployment
    inference/
      main.cpp                   # ONNX Runtime or C++ inference
      CMakeLists.txt
    server.py                    # lightweight server for static files + inference
    deploy.sh                    # build + deploy to Jetson

  scripts/
    patch_demo_cpu.py
  pyproject.toml
  .gitignore
```

**Key decision: shared API, two frontends.** Both frontends hit the same FastAPI endpoints. The Jetson version runs the API locally on the TK1 (with the tiny distilled model). The web version hits a hosted API (with the full or lightly compressed model).

---

## Step 4: Distillation Strategy for Jetson TK1

1. **Fine-tune SleepFM** (cloud GPU) — N1-focused class weighting on sleep staging head
2. **Distill to tiny student**:
   - 3-4 layer 1D CNN (no transformer/attention)
   - Single-channel EEG input (not full multimodal)
   - 5-class output (Wake, N1, N2, N3, REM)
   - Target: <5MB
3. **Export to ONNX** — `torch.onnx.export()`
4. **Run on TK1** via ONNX Runtime (ARM), OpenCV DNN, or custom C++

CPU fallback: student is small enough for <100ms inference on Cortex-A15.

---

## Step 5: Serving on Jetson TK1

- Lightweight Python HTTP server on the Jetson
- Serves `frontend-jetson/` static files
- Exposes `/api/predict` with the tiny student model
- Chromium kiosk mode on external display

---

## Step 6: Verification

1. **Demo notebook**: Runs end-to-end on CPU with synthetic data
2. **Venv**: `python -c "import sleepfm"` works
3. **API**: `uvicorn api.main:app` → `GET /docs` shows endpoints
4. **Jetson frontend**: Open `frontend-jetson/index.html` → breathing circle animates
5. **Web frontend**: `cd frontend-web && npm run dev` → full React app on localhost:3000
6. **Export**: `python ml/training/export_onnx.py` → `student.onnx` < 5MB
7. **Jetson**: `ssh jetson && python server.py` → game on external display

---

## Files to Create

| File | Purpose |
|---|---|
| `pyproject.toml` | Dependencies + package config |
| `.gitignore` | data/, .venv/, __pycache__/, node_modules/ |
| **ML** | |
| `ml/__init__.py` | Package init |
| `ml/config/finetune_n1.yaml` | N1 fine-tuning config |
| `ml/config/distill.yaml` | Distillation config |
| `ml/training/__init__.py` | Package init |
| `ml/training/finetune.py` | N1 fine-tuning script |
| `ml/training/distill.py` | Teacher-student distillation |
| `ml/training/export_onnx.py` | ONNX export |
| `ml/inference/__init__.py` | Package init |
| `ml/inference/predictor.py` | Python inference wrapper |
| **API** | |
| `api/__init__.py` | Package init |
| `api/main.py` | FastAPI app |
| `api/routers/sleep.py` | Sleep prediction endpoints |
| `api/routers/game.py` | Game state endpoints |
| **Jetson Frontend** | |
| `frontend-jetson/index.html` | Main page |
| `frontend-jetson/css/style.css` | Styles |
| `frontend-jetson/js/app.js` | Entry point |
| `frontend-jetson/js/breathing-circle.js` | 0.1 Hz breathing animation |
| `frontend-jetson/js/tap-zone.js` | Tap handler |
| `frontend-jetson/js/api-client.js` | API fetch wrapper |
| **Web Frontend** | |
| `frontend-web/package.json` | React project config |
| `frontend-web/tsconfig.json` | TypeScript config |
| `frontend-web/src/App.tsx` | Root component |
| `frontend-web/src/components/BreathingCircle.tsx` | Breathing animation |
| `frontend-web/src/components/TapZone.tsx` | Tap input |
| `frontend-web/src/components/ScoreDisplay.tsx` | Score dashboard |
| `frontend-web/src/components/Hypnogram.tsx` | Sleep stage viz |
| `frontend-web/src/hooks/useBreathingSync.ts` | Breathing timing |
| `frontend-web/src/hooks/useGameState.ts` | Game state |
| `frontend-web/src/api/client.ts` | Typed API client |
| **Jetson Deploy** | |
| `jetson/server.py` | Lightweight inference server |
| `jetson/deploy.sh` | Deploy script |
| **Scripts** | |
| `scripts/patch_demo_cpu.py` | Auto-patch demo notebook for CPU |

## Key Reference Files (sleepfm-clinical, read-only)

- `sleepfm-clinical/notebooks/demo.ipynb` — inference pipeline
- `sleepfm-clinical/sleepfm/models/models.py` — SetTransformer, Tokenizer, SleepEventLSTMClassifier
- `sleepfm-clinical/sleepfm/pipeline/finetune_sleep_staging.py` — fine-tuning reference
- `sleepfm-clinical/sleepfm/configs/config_finetune_sleep_events.yaml` — config template
- `sleepfm-clinical/requirements.txt` — pinned dependencies
