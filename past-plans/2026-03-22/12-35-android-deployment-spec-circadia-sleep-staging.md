# Archived Plan

**Source:** `humble-skipping-bird.md`
**Session:** `1f385bb1-a812-421b-976a-74b00fb65774`
**Trigger:** `clear`
**Archived:** 2026-03-22 12:35:19

---

# Android Deployment Spec — Circadia Sleep Staging

## Context

The circadia distillation pipeline has produced tiny student models (8.6K-26K params) exported as ONNX, but they consume pre-embedded 128-dim vectors from a SetTransformer — not raw EEG. To run on Android with a Muse 2 headband, the full pipeline (raw EEG → embeddings → sleep stage) must execute on-device. The existing React web frontend needs to be hosted in a WebView with a Kotlin native inference backend.

## Architecture

**Hybrid app**: Android WebView hosts the existing React frontend. Kotlin handles BLE acquisition (Muse SDK) and ML inference (ONNX Runtime). Communication via `addJavascriptInterface`.

```
┌─────────────────────────────────────────────────┐
│ Android App (API 33+, Kotlin, Gradle KTS)       │
│                                                  │
│  ┌──────────────┐     ┌───────────────────────┐ │
│  │  WebView      │◄───►│  InferenceBridge      │ │
│  │  (React app)  │ JS  │  @JavascriptInterface │ │
│  └──────────────┘     └───────────┬───────────┘ │
│                                    │              │
│  ┌─────────────┐  ┌──────────────▼────────────┐ │
│  │ MuseSource  │──►│ EpochBuffer → SleepStager │ │
│  │ (libmuse)   │  │  SignalProcessor           │ │
│  └─────────────┘  │  OnnxEngine (ST + Student) │ │
│                    └───────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## On-Device Pipeline (every 30s)

```
Muse 2 (256Hz, AF7 + TP10 channels)
  → Buffer 30s (7,680 samples/channel)
  → Resample 256→128Hz (3,840 samples/channel)
  → Z-score normalize per channel
  → Map to BAS 10-ch tensor: [AF7, TP10, 0...0] × 3,840
  → SetTransformer Tokenizer: (1, 10, 3840) → (1, 10, 6, 128)
  → AttentionPooling (BAS only): (6, 10, 128) → (6, 128)
  → Student model: (1, 6, 128) → (1, 6, 5)
  → Majority vote across 6 patches → single SleepStage
  → JS bridge → WebView renders hypnogram
```

**Channel mapping**: AF7 → BAS slot 0 (≈ Fpz-Cz), TP10 → BAS slot 1 (≈ Pz-Oz), slots 2-9 zero-padded. Only BAS group runs through SetTransformer; RESP/EKG/EMG skipped (zero embeddings).

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding location | On-device | Full offline capability; bundle models in APK |
| Target EEG device | Muse 2/S | Best consumer SDK, 4-channel EEG at 256Hz |
| Missing modalities | Zero-pad | Model trained with zero-padded EKG already; safe default |
| Min API level | 33 (Android 13) | Best ML runtime + BLE support |
| Muse integration | Official SDK (libmuse) | Easiest path; revisit if breaks on API 33+ |
| Inference cadence | Every 30s epoch | Matches clinical convention |
| Epoch voting | Majority vote over 6 patches | Simple, robust to single-patch noise |
| Quantization | Skip for v1 | Models are 35-104KB float32; trivial on API 33+ |
| JS bridge | addJavascriptInterface | Built-in, no framework dependency |
| Data storage | None, real-time only | Privacy-first; predictions in memory only |

## Deliverables

### Python-side (extend existing code)

1. **SetTransformer ONNX export investigation** (`src/distill/test_st_export.py`)
   - Test export of Tokenizer + AttentionPooling at opset 11/13/17
   - If mask-based attention fails: bake Muse channel mask as constant buffer
   - Fallback: replace AttentionPooling with masked mean pool
   - Reference: `sleepfm-clinical/sleepfm/models/models.py:65-145`

2. **BAS-only SetTransformer export** (extend `src/distill/export.py`)
   - New `BASEmbedder(nn.Module)` wrapping `patch_embedding` + `spatial_pooling`
   - Fixed input: `(1, 10, 3840)`, fixed output: `(1, 6, 128)`
   - Baked channel mask `[F,F,T,T,T,T,T,T,T,T]`
   - Validates ONNX vs PyTorch within atol=1e-5
   - Reference: `src/preprocess.py:132-189` (embed_modality_groups)

### Android app

3. **Project scaffold** (`android/`)
   - Gradle KTS, AGP 8.x, Kotlin 1.9+, minSdk 33
   - Dependencies: `onnxruntime-android`, `androidx.webkit`, `kotlinx-coroutines`
   - `aaptOptions { noCompress += "onnx" }`

4. **WebView host** (`android/.../MainActivity.kt`)
   - Loads `file:///android_asset/web/index.html`
   - Configures JS, DOM storage, registers bridge
   - Handles Bluetooth permission flow (BLUETOOTH_CONNECT, BLUETOOTH_SCAN)

5. **Muse BLE integration** (`android/.../sensor/MuseSource.kt`)
   - Wraps libmuse MuseManager/MuseDataListener
   - Filters to AF7 + TP10 channels only
   - Feeds raw samples into EpochBuffer via callback
   - Exposes `StateFlow<ConnectionState>`

6. **Signal preprocessing** (`android/.../preprocessing/`)
   - `EpochBuffer.kt` — 30s ring buffer (7,680 samples × 2 channels), thread-safe
   - `SignalProcessor.kt`:
     - `resample(signal, 256, 128)` — linear interpolation (ref: `src/preprocess.py:87-99`)
     - `zScoreNormalize(signal)` — per-channel (ref: `src/preprocess.py:44-49`)
     - `buildBASInput(af7, tp10)` — `(1, 10, 3840)` flat tensor

7. **ONNX inference** (`android/.../inference/`)
   - `OnnxEngine.kt` — manages two OrtSessions (SetTransformer + student), preallocated buffers
   - `SleepStager.kt` — orchestrates full pipeline, majority vote, maintains epoch history
   - Ports `compute_sleep_quality_score()` from `src/evaluate.py:37-70`:
     ```
     score = 0.7 * sleepEfficiency + 0.2 * (deepRatio / 0.25) + 0.1 * (remRatio / 0.25)
     clamped 0-100
     ```

8. **JS bridge** (`android/.../bridge/InferenceBridge.kt`)
   - `@JavascriptInterface` methods: `getConnectionStatus()`, `getLatestEpoch()`, `getHypnogram()`, `getSleepQuality()`, `startSession()`, `stopSession()`
   - Returns JSON strings consumed by React

### Frontend adaptations

9. **Bridge consumer hook** (`frontend/.../src/hooks/use-circadia-bridge.ts`)
   - Detects `window.CircadiaBridge`, polls bridge methods
   - Falls back to mock data in browser

10. **Data-driven components**
    - `HypnogramChart.tsx` — accept `data` prop instead of hardcoded mock (ref: lines 15-33)
    - `AnalysisDashboard.tsx` — use bridge hook, show real sleep quality + connection status
    - `App.tsx` — `BrowserRouter` → `HashRouter` for `file://`
    - `vite.config.ts` — add `base: './'`

## Project Structure

```
android/
├── build.gradle.kts
├── settings.gradle.kts
├── app/
│   ├── build.gradle.kts
│   ├── libs/libmuse.aar
│   ├── src/main/
│   │   ├── AndroidManifest.xml
│   │   ├── assets/
│   │   │   ├── student_model.onnx
│   │   │   ├── set_transformer_bas.onnx
│   │   │   └── web/  (React build output)
│   │   └── kotlin/com/circadia/
│   │       ├── MainActivity.kt
│   │       ├── bridge/InferenceBridge.kt
│   │       ├── sensor/MuseSource.kt
│   │       ├── preprocessing/
│   │       │   ├── EpochBuffer.kt
│   │       │   └── SignalProcessor.kt
│   │       ├── inference/
│   │       │   ├── OnnxEngine.kt
│   │       │   └── SleepStager.kt
│   │       └── model/SleepTypes.kt
│   └── src/test/kotlin/com/circadia/
│       ├── SignalProcessorTest.kt
│       ├── SleepStagerTest.kt
│       └── EpochBufferTest.kt
```

## Verification

1. **SetTransformer export**: Run `python -m src.distill.test_st_export` — confirms ONNX export + validation passes
2. **Unit tests**: `./gradlew test` — SignalProcessor resampling/z-score matches Python reference, majority vote logic, sleep quality score matches `evaluate.py` output
3. **APK build**: `./gradlew assembleDebug` — builds clean
4. **On-device smoke test**: Install APK, connect Muse 2, verify:
   - BLE connection establishes
   - First epoch prediction appears after ~30s
   - Hypnogram updates in WebView
   - Sleep quality score computes and displays
5. **Latency budget**: SetTransformer < 5s, student < 100ms, full pipeline < 10s (within 30s budget)

---

## Work Units

### Execution Strategy
Foundation → Parallel (concurrent worktrees)

**Rationale:** The SetTransformer ONNX export (foundation) must succeed before the inference engine can be finalized, and the exported `.onnx` artifacts must exist before bundling into assets. Once foundation completes, the four parallel units have no file conflicts or runtime dependencies — they implement independent layers (BLE, preprocessing, inference, frontend) against shared interfaces defined in foundation.

### Foundation Unit (Phase 1)

**Files:**
- Create: `src/distill/test_st_export.py`
- Modify: `src/distill/export.py`
- Create: `android/build.gradle.kts`
- Create: `android/settings.gradle.kts`
- Create: `android/app/build.gradle.kts`
- Create: `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/kotlin/com/circadia/model/SleepTypes.kt`

**Tasks:**
- Investigate SetTransformer (Tokenizer + AttentionPooling) ONNX export at opset 11/13/17
- Implement fallbacks if AttentionPooling mask export fails (baked mask or masked mean pool)
- Create `BASEmbedder` wrapper and export to `set_transformer_bas.onnx`
- Validate ONNX output vs PyTorch (atol=1e-5)
- Scaffold Android project (Gradle KTS, build files, manifest with BT permissions)
- Create shared `SleepTypes.kt` (SleepStage enum, EpochResult, SleepQuality data classes)

**Done when:**
- `set_transformer_bas.onnx` exists in `checkpoints/distill/` and passes validation
- `./gradlew tasks` runs successfully in `android/`
- `SleepTypes.kt` compiles

### Parallel Units (Phase 2)

| # | Unit Name | Files (create/modify) | Description | E2E Test |
|---|-----------|----------------------|-------------|----------|
| 1 | WebView Host + Bridge | Create: `android/.../MainActivity.kt`, `android/.../bridge/InferenceBridge.kt` | WebView loads React build, registers JS bridge with stub data, handles lifecycle + permissions | APK installs, WebView renders React app, `CircadiaBridge` accessible from JS console |
| 2 | Muse BLE Integration | Create: `android/.../sensor/MuseSource.kt`; add `android/app/libs/libmuse.aar` | Muse SDK wrapper: scan, connect, stream AF7+TP10, expose StateFlow | Connect to Muse 2, log raw EEG samples from AF7 + TP10 |
| 3 | Signal Processing + Inference | Create: `android/.../preprocessing/EpochBuffer.kt`, `android/.../preprocessing/SignalProcessor.kt`, `android/.../inference/OnnxEngine.kt`, `android/.../inference/SleepStager.kt`; Create: `android/.../test/.../SignalProcessorTest.kt`, `android/.../test/.../SleepStagerTest.kt`, `android/.../test/.../EpochBufferTest.kt` | EpochBuffer, resample, z-score, channel map, ONNX session management, majority vote, sleep quality score | `./gradlew test` passes; feed synthetic 30s epoch through SleepStager, get valid SleepStage + quality score |
| 4 | Frontend Adaptation | Create: `frontend/.../src/hooks/use-circadia-bridge.ts`; Modify: `frontend/.../HypnogramChart.tsx`, `frontend/.../AnalysisDashboard.tsx`, `frontend/.../App.tsx`, `frontend/.../vite.config.ts` | Bridge consumer hook, data-driven charts, HashRouter, relative base path | `npm run build` succeeds; app renders in browser with mock data fallback; bridge methods called when `window.CircadiaBridge` exists |

### Dependency & Conflict Analysis
- **File conflicts:** None — each unit owns exclusive files. Foundation creates the shared `SleepTypes.kt` and build scaffolding that all units import but don't modify. No file appears in more than one parallel unit.
- **Runtime dependencies:** None between parallel units. Unit 1 (bridge) stubs its dependencies on Unit 2 (MuseSource) and Unit 3 (SleepStager) with mock/null references. Unit 3 imports `SleepTypes.kt` from foundation. Unit 4 works entirely in the frontend codebase.

### Post-Merge Verification
After all units merge:
1. Wire `MainActivity.onCreate()`: `OnnxEngine` → `SleepStager` → `MuseSource` → `InferenceBridge` → WebView
2. Copy `set_transformer_bas.onnx` + best student ONNX into `android/app/src/main/assets/`
3. Build React frontend: `cd frontend/zen-rhythm-display-main && npm run build`
4. Copy `dist/` → `android/app/src/main/assets/web/`
5. `./gradlew assembleDebug` → install on device
6. Connect Muse 2 → wait 30s → verify first epoch prediction appears in hypnogram
7. Run for 5+ minutes → verify sleep quality score updates, hypnogram grows
8. Measure latency: full pipeline < 10s per epoch
