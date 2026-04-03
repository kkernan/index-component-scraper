import requests
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

SOURCES = {
    "sp500": "https://www.slickcharts.com/sp500",
    "nasdaq100": "https://www.slickcharts.com/nasdaq100",
}


def fetch_table(url: str) -> pd.DataFrame:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    # slickcharts puts the components table first on each page
    tables = pd.read_html(response.text)
    return tables[0]


def main():
    for name, url in SOURCES.items():
        print(f"Fetching {name} from {url} ...")
        df = fetch_table(url)
        out = DATA_DIR / f"{name}.csv"
        df.to_csv(out, index=False)
        print(f"  Saved {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
