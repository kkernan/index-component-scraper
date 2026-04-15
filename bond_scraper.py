"""Fetch bond positions and current prices from all Schwab accounts.

Outputs data/bonds.csv with columns: cusip, price
Price is quoted as % of par (e.g., 97.5 = $97.50 per $100 face value).

Usage:
    python bond_scraper.py

Credentials are loaded from (in priority order):
  1. .env in this project directory
  2. ../TradingEngine/.env (shared credentials)

The Schwab token file defaults to ../TradingEngine/schwab_token.json.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
import schwab

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

_SCRIPT_DIR = Path(__file__).resolve().parent
_TRADING_ENGINE_ROOT = _SCRIPT_DIR.parent / "TradingEngine"

# Load env: this project's .env first, fall back to TradingEngine's
load_dotenv(_SCRIPT_DIR / ".env", override=False)
load_dotenv(_TRADING_ENGINE_ROOT / ".env", override=False)


def _require_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise EnvironmentError(
            f"Missing required environment variable: {key}\n"
            f"Add it to {_SCRIPT_DIR / '.env'} or {_TRADING_ENGINE_ROOT / '.env'}"
        )
    return val


def get_client() -> schwab.client.Client:
    token_path = _TRADING_ENGINE_ROOT / "schwab_token.json"
    if not token_path.exists():
        raise FileNotFoundError(
            f"Schwab token not found: {token_path}\n"
            "Run the TradingEngine auth flow (auth_test.py) to generate a token."
        )
    return schwab.auth.client_from_token_file(
        token_path=str(token_path),
        api_key=_require_env("SCHWAB_API_KEY"),
        app_secret=_require_env("SCHWAB_APP_SECRET"),
    )


def _is_bond(instrument: dict) -> bool:
    """Return True for individual bonds, Treasuries, and CDs."""
    asset_type = instrument.get("assetType", "")
    symbol = instrument.get("symbol", "")
    if asset_type in ("BOND", "FIXED_INCOME"):
        return True
    # CUSIP: 9 alphanumeric characters — used as symbol for bonds in Schwab
    if len(symbol) == 9 and symbol.isalnum():
        return True
    return False


def fetch_bonds(client: schwab.client.Client) -> dict[str, float]:
    """Return {cusip: mark} across all accounts using position data.

    Mark is taken directly from the position: marketValue / longQuantity,
    which Schwab reports as price per unit (% of par for standard bonds).
    Deduplicates by CUSIP; first occurrence wins (price is market-derived
    and should agree across accounts).
    """
    resp = client.get_accounts(fields=[client.Account.Fields.POSITIONS])
    resp.raise_for_status()

    bonds: dict[str, float] = {}
    for acct in resp.json():
        sec = acct.get("securitiesAccount", {})
        for pos in sec.get("positions", []):
            instrument = pos.get("instrument", {})
            if not _is_bond(instrument):
                continue
            cusip = instrument.get("cusip") or instrument.get("symbol", "")
            if not cusip or cusip in bonds:
                continue
            long_qty = pos.get("longQuantity", 0.0)
            market_value = pos.get("marketValue", 0.0)
            mark = round(market_value / long_qty / 10, 4) if long_qty else 0.0
            bonds[cusip] = mark

    return bonds


def main() -> None:
    print("Connecting to Schwab ...")
    client = get_client()

    print("Fetching bond positions from all accounts ...")
    bonds = fetch_bonds(client)

    if not bonds:
        print("No bond positions found.")
        return

    df = pd.DataFrame(
        sorted(bonds.items()),
        columns=["cusip", "price"],
    )

    out = DATA_DIR / "bonds.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} bond(s) -> {out}")


if __name__ == "__main__":
    main()