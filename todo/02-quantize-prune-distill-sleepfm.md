# Quantize / Prune / Distill SleepFM (teacher + student)

Compress the fine-tuned SleepFM model. Recommended sequence:

1. **FP16** — easy memory savings
2. **INT8 PTQ** — post-training quantization with representative calibration set
3. **QAT** — quantization-aware training if PTQ hurts accuracy
4. **Distillation** — teacher (full SleepFM) → student (smaller 1D CNN + shallow transformer or CNN + BiLSTM)
5. **Pruning** — only as secondary optimization

## Architecture notes
- SleepFM: 1D CNN encoder + attention-based channel pooling + small temporal transformer
- 5-second signal tokens at 128 Hz, 5-minute temporal context
- 128-dim embeddings per modality
- Compression-friendly due to regular input shapes

## Distillation targets
- 5-second token embeddings
- Pooled modality embeddings
- Downstream outputs (sleep staging / apnea / disease-risk)

## Watch out for
- Attention pooling sensitivity to quantization
- Biosignal detail loss with bad activation range calibration
- Need representative calibration set across channel configurations
