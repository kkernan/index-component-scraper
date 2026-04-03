import io
import re

import cloudscraper
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


SOURCES = {
    "sp500": "https://www.slickcharts.com/sp500",
    "nasdaq100": "https://www.slickcharts.com/nasdaq100",
}


def fetch_table(url: str) -> pd.DataFrame:
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    # slickcharts puts the components table first on each page
    tables = pd.read_html(io.StringIO(response.text))
    df = tables[0]
    # Strip non-ASCII characters from column names and string values
    df.columns = [re.sub(r'[^\x20-\x7E]', '', c).strip() for c in df.columns]
    for col in df.select_dtypes(include=['object', 'str']).columns:
        df[col] = df[col].astype(str).apply(lambda x: re.sub(r'[^\x20-\x7E]', '', x).strip())
    return df.drop(columns=['Company'])


def main():
    for name, url in SOURCES.items():
        print(f"Fetching {name} from {url} ...")
        df = fetch_table(url)
        out = DATA_DIR / f"{name}.csv"
        df.to_csv(out, index=False)
        print(f"  Saved {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
