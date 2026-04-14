import io
import re
import urllib.request

import cloudscraper
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


SLICKCHARTS_SOURCES = {
    "sp500": "https://www.slickcharts.com/sp500",
    "nasdaq100": "https://www.slickcharts.com/nasdaq100",
}

STOCKANALYSIS_SOURCES = {
    "smh": "https://stockanalysis.com/etf/smh/holdings/",
}


def fetch_slickcharts(url: str) -> pd.DataFrame:
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    tables = pd.read_html(io.StringIO(response.text))
    df = tables[0]
    # Strip non-ASCII characters from column names and string values
    df.columns = [re.sub(r'[^\x20-\x7E]', '', c).strip() for c in df.columns]
    for col in df.select_dtypes(include=['object', 'str']).columns:
        df[col] = df[col].astype(str).apply(lambda x: re.sub(r'[^\x20-\x7E]', '', x).strip())
    df = df.drop(columns=['Company'])
    df['% Chg'] = df['% Chg'].astype(str).str.replace(r'[()]', '', regex=True)
    return df


def fetch_stockanalysis(url: str) -> pd.DataFrame:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        html = response.read().decode('utf-8')
    tables = pd.read_html(io.StringIO(html))
    df = tables[0]
    df = df.drop(columns=['No.', 'Name'])
    return df


def main():
    for name, url in SLICKCHARTS_SOURCES.items():
        print(f"Fetching {name} from {url} ...")
        df = fetch_slickcharts(url)
        out = DATA_DIR / f"{name}.csv"
        df.to_csv(out, index=False)
        print(f"  Saved {len(df)} rows -> {out}")

    for name, url in STOCKANALYSIS_SOURCES.items():
        print(f"Fetching {name} from {url} ...")
        df = fetch_stockanalysis(url)
        out = DATA_DIR / f"{name}.csv"
        df.to_csv(out, index=False)
        print(f"  Saved {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
