# Fine-tune SleepFM on N1/transitional sleep data

Fine-tune SleepFM with sleep staging head focused on N1 fragmentation (very light sleep / transitional data). Budget: $5–$20.

## SleepFM Dataset Metadata

| Field | Description |
|---|---|
| SiteID | Unique identifier of the hospital where the PSG was recorded |
| BDSPPatientID | Unique identifier of the patient |
| CreationTime | De-identified timestamp when the PSG was recorded |
| BidsFolder | Folder where studies for a specific patient are available in the BDSP OpenData Repository |
| SessionID | Folder in the BDSP OpenData Repository containing a specific study and its auxiliary files |
| PreSleepQuestionnaire | Flag indicating if the study has a pre-sleep questionnaire |
| HasAnnotations | Flag indicating if the study has annotations |
