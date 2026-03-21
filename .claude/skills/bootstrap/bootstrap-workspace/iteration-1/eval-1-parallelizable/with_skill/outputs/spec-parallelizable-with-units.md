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

---

## Work Units

### Execution Strategy
Foundation → Mixed (parallel + sequential)

**Rationale:** The three scrapers are fully independent — they each own exclusive files, share no imports between them, and produce separate CSV outputs. However, `analysis.ipynb` has a runtime dependency on all three scrapers' CSV output files (`scraped_data/source_a.csv`, `scraped_data/source_b.csv`, `scraped_data/source_c.csv`), so it must run after the scrapers complete. The `requirements.txt` is shared infrastructure needed by all units and belongs in the foundation phase.

### Foundation Unit (Phase 1)

**Files:**
- Modify: `requirements.txt`
- Create: `scripts/` (directory scaffold)
- Create: `scraped_data/` (directory scaffold)

**Tasks:**
- Add `requests`, `beautifulsoup4`, and `pandas` to `requirements.txt`
- Ensure `scripts/` and `scraped_data/` directories exist

**Done when:** `requirements.txt` contains all three dependencies and both directories exist.

### Parallel Units (Phase 2)

| # | Unit Name | Files (create/modify) | Description | E2E Test |
|---|-----------|----------------------|-------------|----------|
| 1 | Source A Scraper | Create: `scripts/scrape_source_a.py`, `scraped_data/source_a.csv` (output) | Fetch JSON from example.com/api/a, parse into DataFrame, write CSV with columns: id, name, value, timestamp | `python scripts/scrape_source_a.py` produces valid `scraped_data/source_a.csv` |
| 2 | Source B Scraper | Create: `scripts/scrape_source_b.py`, `scraped_data/source_b.csv` (output) | Fetch HTML from example.com/api/b, parse table with BeautifulSoup, write CSV with columns: id, category, score | `python scripts/scrape_source_b.py` produces valid `scraped_data/source_b.csv` |
| 3 | Source C Scraper | Create: `scripts/scrape_source_c.py`, `scraped_data/source_c.csv` (output) | Fetch CSV download link from example.com/api/c, parse and write CSV with columns: id, region, metric, date | `python scripts/scrape_source_c.py` produces valid `scraped_data/source_c.csv` |

### Sequential Units

| Order | Unit Name | Files (create/modify) | Depends On | Description |
|-------|-----------|----------------------|------------|-------------|
| 1 | Analysis Notebook | Create: `analysis.ipynb` | Phase 2 Units 1-3 (reads `scraped_data/source_a.csv`, `scraped_data/source_b.csv`, `scraped_data/source_c.csv`) | Load all 3 CSVs, merge on `id` column, produce summary statistics and visualizations |

### Dependency & Conflict Analysis
- **File conflicts:** None. Each parallel unit owns exclusive script and CSV files. No file is touched by more than one unit. `requirements.txt` is isolated in the foundation phase.
- **Runtime dependencies:** `analysis.ipynb` reads the CSV files produced by all three scrapers. It cannot execute until all three scraper units have completed and their output CSVs exist. The three scrapers have no runtime or import dependencies on each other — they are independently executable.

### Post-Merge Verification
1. Install dependencies: `pip install -r requirements.txt`
2. Run all three scrapers: `python scripts/scrape_source_a.py && python scripts/scrape_source_b.py && python scripts/scrape_source_c.py`
3. Verify all CSVs exist with expected columns in `scraped_data/`
4. Run `analysis.ipynb` end-to-end and confirm it produces summary statistics and visualizations from the merged data
