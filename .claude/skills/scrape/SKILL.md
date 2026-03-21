---
name: scrape
description: Scrape data from a sports website and save as CSV to scraped_data/
disable-model-invocation: true
---

# Web Scraping Skill

Scrape tabular data from a sports analytics website and save it as a clean CSV in `scraped_data/`.

## Usage

`/scrape <url> <description of what data to extract>`

## Workflow

1. **Fetch the page** using WebFetch to understand the page structure and identify the data tables/elements
2. **Write a Python script** in `scripts/` that:
   - Uses `requests` + `beautifulsoup4` + `lxml` (already in requirements.txt)
   - Has a descriptive filename like `scrape_<source>_<data>.py`
   - Saves output CSV(s) to `scraped_data/`
   - Follows the same patterns as existing scrapers (see `scripts/scrape_net_teamsheets.py` for reference)
   - Includes error handling for HTTP failures and missing elements
   - Prints progress: what was scraped, row counts, output file paths
3. **Run the script** with `python3 scripts/<script_name>.py`
4. **Validate the output** by reading the first few rows of the CSV and confirming the data looks correct
5. **Run the data-reviewer subagent** on the new CSV to check data quality

## Conventions

- Output directory: `scraped_data/`
- CSV files should have clean column names (lowercase, underscores)
- Include a `#!/usr/bin/env python3` shebang and module docstring
- Use `csv.DictWriter` for output (consistent with existing scripts)
- Allowed scraping domains are configured in `.claude/settings.local.json` — if the target domain isn't listed, ask the user before proceeding

## Arguments

- `$1`: URL to scrape
- `$2`: Description of what data to extract (e.g., "team efficiency ratings", "game results by round")
