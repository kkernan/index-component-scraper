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

- `scraper.py` — fetches both URLs with a browser User-Agent, uses `pandas.read_html()` to parse the first HTML table on each page, writes CSVs to `data/`
- `data/sp500.csv`, `data/nasdaq100.csv` — committed output files
- `.github/workflows/update.yml` — cron workflow (Mondays 12:00 UTC); runs scraper, commits changes back using the built-in `GITHUB_TOKEN` (no secrets needed)

## Google Sheets integration

After the repo is public (or you grant access), use in a Google Sheet:

```
=IMPORTDATA("https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/sp500.csv")
=IMPORTDATA("https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/nasdaq100.csv")
```
