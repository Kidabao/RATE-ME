#!/usr/bin/env python3
"""
Hong Leong Bank forex rate scraper and converter.

Usage:
    python rate_exchange.py                          # print full table
    python rate_exchange.py 1000 CNY sell            # send 1000 MYR, receive CNY
    python rate_exchange.py 1000 CNY buy             # send 1000 CNY, receive MYR

Direction:
    sell = you send MYR and receive foreign currency (bank sells FX to you)
    buy  = you send foreign currency and receive MYR  (bank buys FX from you)
"""

import re
import sys

import requests
from bs4 import BeautifulSoup

URL = "https://www.hlb.com.my/en/global-markets/forex-rates.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.hlb.com.my/",
}

_SECTION_1  = "RINGGIT TO 1 UNIT OF FOREIGN CURRENCY"
_SECTION_100 = "RINGGIT TO 100 UNITS OF FOREIGN CURRENCY"


def _extract_number(text: str) -> float | None:
    """Pull the last decimal number out of a mixed label+value string."""
    matches = re.findall(r"\d+\.\d+", text)
    try:
        return float(matches[-1])
    except (IndexError, ValueError):
        return None


def fetch_rates() -> dict[str, dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    rates: dict[str, dict] = {}
    current_unit = 1

    for row in soup.select("table.forex-rates-table tr"):
        cells = [td.get_text(strip=True) for td in row.select("td, th")]
        if not cells:
            continue

        label = cells[1] if len(cells) > 1 else ""

        # Detect section header to track the unit base
        if _SECTION_100 in label:
            current_unit = 100
        elif _SECTION_1 in label and _SECTION_100 not in label:
            current_unit = 1

        # Currency row: label contains a 3-letter code in parentheses, e.g. "(AUD)"
        code_match = re.search(r"\(([A-Z]{3})\)", label)
        if not code_match:
            continue
        code = code_match.group(1)

        sell = _extract_number(cells[2]) if len(cells) > 2 else None
        buy  = _extract_number(cells[3]) if len(cells) > 3 else None

        rates[code] = {
            "sell": sell,
            "buy":  buy,
            "unit": current_unit,
        }

    return rates


def _rate_str(value: float | None) -> str:
    return f"{value:.4f}" if value is not None else "  --  "


def print_table(rates: dict[str, dict]) -> None:
    print(f"\n{'Currency':<10} {'Unit':<6} {'Sell (MYR)':<14} {'Buy TT (MYR)':<14}")
    print("-" * 50)
    for code, r in sorted(rates.items()):
        print(f"{code:<10} {r['unit']:<6} {_rate_str(r['sell']):<14} {_rate_str(r['buy']):<14}")
    print()


def convert(amount: float, currency: str, direction: str, rates: dict[str, dict]) -> None:
    code = currency.upper()
    if code not in rates:
        available = ", ".join(sorted(rates))
        print(f"Currency '{code}' not found.\nAvailable: {available}")
        sys.exit(1)

    r = rates[code]
    unit = r["unit"]

    if direction == "sell":
        rate_myr = r["sell"]
        if rate_myr is None:
            print(f"No sell rate available for {code}.")
            sys.exit(1)
        # rate_myr = MYR per `unit` FX → FX per MYR = unit / rate_myr
        received = amount * (unit / rate_myr)
        print(f"\n  {amount:,.2f} MYR  →  {received:,.4f} {code}")
        print(f"  Rate: {unit} {code} = {rate_myr:.4f} MYR  (bank sell rate)\n")

    elif direction == "buy":
        rate_myr = r["buy"]
        if rate_myr is None:
            print(f"No buy rate available for {code}.")
            sys.exit(1)
        # rate_myr = MYR per `unit` FX → MYR per 1 FX = rate_myr / unit
        received = amount * (rate_myr / unit)
        print(f"\n  {amount:,.2f} {code}  →  {received:,.4f} MYR")
        print(f"  Rate: {unit} {code} = {rate_myr:.4f} MYR  (bank buy rate)\n")

    else:
        print("Direction must be 'sell' (MYR→FX) or 'buy' (FX→MYR).")
        sys.exit(1)


def main() -> None:
    args = sys.argv[1:]

    print("Fetching HLB forex rates...", end=" ", flush=True)
    rates = fetch_rates()
    if not rates:
        print("FAILED\nNo rates parsed — page structure may have changed.")
        sys.exit(1)
    print(f"OK ({len(rates)} currencies)\n")

    if len(args) == 0:
        print_table(rates)
    elif len(args) == 3:
        amount_str, currency, direction = args
        try:
            amount = float(amount_str.replace(",", ""))
        except ValueError:
            print(f"Invalid amount: {amount_str}")
            sys.exit(1)
        convert(amount, currency, direction.lower(), rates)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
