# Spec: Multi-Source Data Pipeline

## Context
Build a data pipeline that scrapes three independent data sources, processes each into CSVs, and produces a combined analysis notebook.

## Deliverables

1. **`scripts/scrape_source_a.py`** — Scraper for source A, outputs `scraped_data/source_a.csv`
2. **`scripts/scrape_source_b.py`** — Scraper for source B, outputs `scraped_data/source_b.csv`
3. **`scripts/scrape_source_c.py`** — Scraper for source C, outputs `scraped_data/source_c.csv`
4. **`analysis.ipynb`** — Notebook that loads all 3 CSVs and produces combined analysis
5. **`requirements.txt`** — Add `requests`, `beautifulsoup4`, `pandas`

## Implementation Details

### Source A Scraper
- Fetch from example.com/api/a
- Parse JSON response into DataFrame
- Output columns: id, name, value, timestamp

### Source B Scraper
- Fetch from example.com/api/b
- Parse HTML table with BeautifulSoup
- Output columns: id, category, score

### Source C Scraper
- Fetch from example.com/api/c
- Parse CSV download link
- Output columns: id, region, metric, date

### Analysis Notebook
- Load all 3 CSVs
- Merge on `id` column
- Produce summary statistics and visualizations

## Verification
1. Each scraper runs independently: `python scripts/scrape_source_X.py`
2. Notebook runs end-to-end after all CSVs exist
