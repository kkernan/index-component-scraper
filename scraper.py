import html
import io
import re

import cloudscraper
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


SLICKCHARTS_SOURCES = {
    "sp500": "https://www.slickcharts.com/sp500",
    "nasdaq100": "https://www.slickcharts.com/nasdaq100",
}

# XLG and SMH used to come from stockanalysis.com, which caps its holdings
# table at 25 rows for non-subscribers ("Showing 25 of 53 holdings") with no
# error - XLG was silently losing 26 of its 51 stocks. Both now come straight
# from the fund provider instead.
INVESCO_SOURCES = {
    "xlg": "46137V233",  # CUSIP, Invesco S&P 500 Top 50 ETF
}

VANECK_SOURCES = {
    "smh": "https://www.vaneck.com/us/en/etf/equity/smh/holdings/download/xlsx/",
}

# Sanity floors. A short read still gets written - NVDA is row 1 of every one
# of these files and downstream consumers only read that, so partial data is
# more useful than last week's data. This just makes the truncation visible in
# the workflow log, since the XLG version of it went unnoticed for months.
EXPECTED_ROWS = {
    "sp500": 490,
    "nasdaq100": 95,
    "xlg": 50,
    "smh": 25,
}

# Holdings feeds carry cash, currency and money-market lines alongside the
# equities; the CSVs track index components only.
CASH_LIKE = re.compile(r"cash|currency|money market", re.I)


def clean_symbol(ticker: str) -> str:
    # Invesco writes share classes as BRK/B; slickcharts and the older files
    # use BRK.B, so keep the whole data/ directory joinable on symbol.
    return html.unescape(str(ticker)).strip().replace('/', '.')


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


def fetch_invesco(cusip: str) -> pd.DataFrame:
    url = (
        "https://dng-api.invesco.com/cache/v1/accounts/en_US/shareclasses/"
        f"{cusip}/holdings/fund?idType=cusip&productType=ETF"
    )
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url, timeout=30, headers={'Accept': 'application/json'})
    response.raise_for_status()

    rows = []
    for holding in response.json()['holdings']:
        weight = holding.get('percentageOfTotalNetAssets')
        ticker = holding.get('ticker')
        if not ticker or weight is None:
            continue
        if CASH_LIKE.search(holding.get('securityTypeName') or ''):
            continue
        rows.append({
            'Symbol': clean_symbol(ticker),
            '% Weight': f"{weight:.2f}%",
            'Shares': int(holding['units']),
        })
    return pd.DataFrame(rows)


def fetch_vaneck(url: str) -> pd.DataFrame:
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    # Row 0 is an "as of" banner; the real header sits on row 2.
    df = pd.read_excel(io.BytesIO(response.content), header=2)
    df = df[df['Ticker'].notna() & df['Shares'].notna()]
    df = df[~df['Asset Class'].astype(str).str.contains(CASH_LIKE)]
    return pd.DataFrame({
        'Symbol': df['Ticker'].map(clean_symbol),
        '% Weight': df['% of Net Assets'].astype(str).str.strip(),
        'Shares': df['Shares'].astype(str).str.replace(',', '', regex=False).astype('int64'),
    }).reset_index(drop=True)


def save(name: str, fetch) -> None:
    # One unreachable source shouldn't stop the others from updating, so a
    # failed fetch just leaves that CSV at its last good version.
    try:
        df = fetch()
    except Exception as exc:
        print(f"  ERROR: fetch failed ({exc}) - keeping existing file")
        return

    if len(df) < EXPECTED_ROWS[name]:
        print(f"  WARNING: got {len(df)} rows, expected at least {EXPECTED_ROWS[name]} - source may be truncating")

    out = DATA_DIR / f"{name}.csv"
    df.to_csv(out, index=False)
    print(f"  Saved {len(df)} rows -> {out}")


def main():
    for name, url in SLICKCHARTS_SOURCES.items():
        print(f"Fetching {name} from {url} ...")
        save(name, lambda url=url: fetch_slickcharts(url))

    for name, cusip in INVESCO_SOURCES.items():
        print(f"Fetching {name} from Invesco (CUSIP {cusip}) ...")
        save(name, lambda cusip=cusip: fetch_invesco(cusip))

    for name, url in VANECK_SOURCES.items():
        print(f"Fetching {name} from {url} ...")
        save(name, lambda url=url: fetch_vaneck(url))


if __name__ == "__main__":
    main()
