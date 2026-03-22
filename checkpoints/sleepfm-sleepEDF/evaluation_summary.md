# Teacher Model Evaluation (SleepEventLSTMClassifier)

**Overall:** 40.8% accuracy | Sleep Quality Score: 74.6

### Classification Report

| Stage | Precision | Recall | F1-Score | Support |
| ----- | --------- | ------ | -------- | ------- |
| Wake  | 0.23      | 0.94   | 0.37     | 408     |
| REM   | 0.55      | 0.85   | 0.67     | 978     |
| N1    | 0.22      | 0.36   | 0.27     | 564     |
| N2    | 0.77      | 0.22   | 0.34     | 3,270   |
| N3    | 0.30      | 0.39   | 0.34     | 570     |

### Confusion Matrix

| Predicted &rarr; | Wake    | REM     | N1      | N2      | N3      |
| ----------------- | ------- | ------- | ------- | ------- | ------- |
| **Wake**          | **385** | 0       | 21      | 2       | 0       |
| **REM**           | 4       | **835** | 22      | 114     | 3       |
| **N1**            | 269     | 61      | **201** | 31      | 2       |
| **N2**            | 873     | 585     | 564     | **718** | 530     |
| **N3**            | 131     | 28      | 114     | 72      | **225** |
