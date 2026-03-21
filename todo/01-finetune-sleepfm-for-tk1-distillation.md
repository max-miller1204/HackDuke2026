Finetune the SleepFM model so we can distill it for the NVIDIA Jetson TK1

## Steps
- Set up finetuning pipeline for SleepFM
- Train/finetune on target sleep data
- Prepare distillation workflow targeting TK1 constraints (memory, compute)
- Distill finetuned model to a smaller architecture suitable for TK1 deployment
