# Android Deployment

Deploy the distilled sleep staging model to an Android device for on-device inference.

## Key Tasks

- Export distilled model to ONNX format (if not already done in distillation step)
- Integrate ONNX Runtime Mobile (`onnxruntime-android` AAR) into an Android app
- Implement signal preprocessing pipeline in Kotlin/Java (resampling, z-score normalization, channel mapping)
- Implement `computeSleepQualityScore()` in Kotlin/Java (port from Python — simple arithmetic)
- Handle input from Bluetooth EEG wearable (e.g., Muse, OpenBCI) or adapt channel mapping for available sensors
- Apply INT8 quantization for performance on older Android devices
- Benchmark inference latency and memory on target device

## Dependencies

- Depends on: distillation (todo 02) — needs the distilled ONNX model
