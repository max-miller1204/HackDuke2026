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

## Work Units

### Dependency Analysis

The project has a two-layer dependency structure:

- **Layer 1 (Foundation):** `requirements.txt` must exist before any scraper or the notebook can run, since all Python code depends on the declared packages. This is a single shared file, so it must be completed first and merged into the base branch before parallel work begins.
- **Layer 2 (Parallel scrapers):** The three scrapers are fully independent of each other. Each owns its own script file and its own output CSV. They share no code and have no cross-dependencies.
- **Layer 3 (Integration):** The analysis notebook depends on all three scrapers having produced their CSV outputs. It cannot be fully verified until the scrapers are merged, but it can be authored in parallel as long as it assumes the CSV schemas defined in the spec.

### Unit 1 — Foundation: Requirements (must complete first)

| Attribute | Value |
|-----------|-------|
| **Files owned** | `requirements.txt` |
| **Depends on** | Nothing |
| **Blocked by** | Nothing |
| **Blocks** | Units 2, 3, 4, 5 (all downstream units need packages installed) |

**Scope:** Add `requests`, `beautifulsoup4`, and `pandas` to `requirements.txt`. This unit must be merged into the base branch before the parallel units begin, so that each worktree can install dependencies.

### Unit 2 — Scraper A

| Attribute | Value |
|-----------|-------|
| **Files owned** | `scripts/scrape_source_a.py`, `scraped_data/source_a.csv` |
| **Depends on** | Unit 1 (requirements) |
| **Blocks** | Unit 5 (analysis notebook needs `source_a.csv`) |

**Scope:** Implement the Source A scraper. Fetch JSON from example.com/api/a, parse into a DataFrame, and write to `scraped_data/source_a.csv` with columns: id, name, value, timestamp.

### Unit 3 — Scraper B

| Attribute | Value |
|-----------|-------|
| **Files owned** | `scripts/scrape_source_b.py`, `scraped_data/source_b.csv` |
| **Depends on** | Unit 1 (requirements) |
| **Blocks** | Unit 5 (analysis notebook needs `source_b.csv`) |

**Scope:** Implement the Source B scraper. Fetch HTML from example.com/api/b, parse the table with BeautifulSoup, and write to `scraped_data/source_b.csv` with columns: id, category, score.

### Unit 4 — Scraper C

| Attribute | Value |
|-----------|-------|
| **Files owned** | `scripts/scrape_source_c.py`, `scraped_data/source_c.csv` |
| **Depends on** | Unit 1 (requirements) |
| **Blocks** | Unit 5 (analysis notebook needs `source_c.csv`) |

**Scope:** Implement the Source C scraper. Fetch from example.com/api/c, follow the CSV download link, and write to `scraped_data/source_c.csv` with columns: id, region, metric, date.

### Unit 5 — Analysis Notebook

| Attribute | Value |
|-----------|-------|
| **Files owned** | `analysis.ipynb` |
| **Depends on** | Units 2, 3, 4 (needs all three CSVs to verify end-to-end) |
| **Blocks** | Nothing |

**Scope:** Create the Jupyter notebook that loads all three CSVs, merges them on the `id` column, and produces summary statistics and visualizations. This unit can be coded in parallel with the scrapers by assuming the CSV schemas from the spec, but final verification requires all scrapers to be merged first.

### Execution Plan

```
Timeline:
  Phase 1 (sequential):  Unit 1 — requirements.txt
                              |
                         merge to base
                              |
  Phase 2 (parallel):    Unit 2 ──┐
                         Unit 3 ──┼── (all run in separate worktrees)
                         Unit 4 ──┤
                         Unit 5 ──┘
                              |
  Phase 3 (sequential):  merge all, verify notebook end-to-end
```

- **Maximum parallelism:** 4 worktrees in Phase 2 (3 scrapers + notebook).
- **No file conflicts:** Every unit owns exclusive files, so merges will be conflict-free.
- **Unit 5 caveat:** The notebook can be written during Phase 2 since it only reads CSVs at runtime, not at merge time. However, its verification step (running the notebook end-to-end) must wait until after Units 2-4 are merged and their scrapers have been executed to produce the CSV files.
