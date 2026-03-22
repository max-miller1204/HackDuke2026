# Connect Front End

Connect the front-end UI to the on-device sleep staging inference pipeline, enabling users to view real-time or post-session sleep stage results.

## Key Tasks

- Wire up the Android UI to the ONNX inference backend (display sleep stage predictions)
- Implement a results screen showing hypnogram and sleep quality score
- Handle data flow from sensor input → preprocessing → inference → UI display
- Add loading/error states for model initialization and inference

## Dependencies

- Depends on: Android deployment (todo 02) — needs the on-device inference pipeline working
