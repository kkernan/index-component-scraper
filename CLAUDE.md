# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Weekly scrapes S&P 500 and NASDAQ 100 component tables from slickcharts.com and commits them as CSVs to this repo. A GitHub Actions workflow runs every Monday and auto-commits any changes. The raw CSV URLs can be consumed directly from Google Sheets via `=IMPORTDATA(...)`.

## Environment

Python 3.12, `.venv` managed by PyCharm.

```bash
source .venv/bin/activate       # Linux/macOS
source .venv/Scripts/activate   # Git Bash on Windows
pip install -r requirements.txt
```

## Commands

```bash
# Run the scraper locally
python scraper.py

# Output lands in data/sp500.csv and data/nasdaq100.csv
```

## Architecture

- `scraper.py` — fetches each source, normalizes to a common CSV shape, writes to `data/`. Three source families:
  - **slickcharts** (`sp500`, `nasdaq100`) — `pandas.read_html()` on the first HTML table
  - **Invesco** (`xlg`) — JSON holdings API on `dng-api.invesco.com`, keyed by CUSIP
  - **VanEck** (`smh`) — the fund's holdings `.xlsx` download
- `data/sp500.csv`, `data/nasdaq100.csv`, `data/xlg.csv`, `data/smh.csv` — committed output files
- `.github/workflows/update.yml` — cron workflow (Mondays 12:00 UTC); runs scraper, commits changes back using the built-in `GITHUB_TOKEN` (no secrets needed)

ETF holdings come straight from the fund provider rather than an aggregator. XLG and SMH previously used stockanalysis.com, which silently caps its holdings table at 25 rows for non-subscribers ("Showing 25 of 53 holdings") — XLG was quietly publishing 25 of its 51 stocks.

The scraper deliberately prefers fresh-but-partial data over stale data, and never blocks the commit:
- Each source is fetched independently; a failure logs and leaves that CSV at its last good version instead of aborting the run.
- `EXPECTED_ROWS` is a warning threshold only. A short read is still written and committed — every one of these files is sorted by weight, so NVDA is row 1 and the main downstream consumer keeps working even off a truncated file. The warning exists because the XLG truncation went unnoticed for months, not to gate the data.

If you ever want a short read to be loud rather than just logged, fail the workflow *after* the commit step rather than reinstating a write barrier — that keeps the data landing.

Cash, currency and money-market lines are filtered out of the ETF feeds — the CSVs track index components only, so weights sum to slightly under 100%. Symbols are normalized to the `BRK.B` form (Invesco publishes `BRK/B`) so all four files join on symbol.

## Google Sheets integration

After the repo is public (or you grant access), use in a Google Sheet:

```
=IMPORTDATA("https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/sp500.csv")
=IMPORTDATA("https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/nasdaq100.csv")
```
