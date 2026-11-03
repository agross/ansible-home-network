#!/usr/bin/env python3
"""Produce the weekday ETF summary."""
import json
from datetime import datetime
from urllib.request import Request, urlopen

TICKERS = (
    ('AAPL', 'Apple (US0378331005)'),
    ('KO', 'Coca-Cola (US1912161007)'),
    ('AVGO', 'Broadcom (US11102F1032)'),
    ('WELD.DE', 'Amundi S&P Global Utilities'),
    ('VGWL.DE', 'Vanguard FTSE All-World'),
)


def quote(ticker):
    request = Request(
        f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d',
        headers={'User-Agent': 'Hermes ETF Morning Check/1.0'},
    )
    with urlopen(request, timeout=10) as response:
        data = json.load(response)
    meta = data['chart']['result'][0]['meta']
    price = meta['regularMarketPrice']
    previous = meta['chartPreviousClose']
    currency = meta.get('currency') or '?'
    return price, price - previous, (price - previous) / previous * 100, currency


def main():
    print(f'📈 ETF Morning Check – {datetime.now().strftime("%d.%m.%Y")}')
    print('=' * 45)
    for ticker, name in TICKERS:
        print(name)
        try:
            price, change, percent, currency = quote(ticker)
            indicator = '📈' if change > 0 else '📉' if change < 0 else '➡️'
            sign = '+' if change > 0 else ''
            print(f'  {price:.2f} {currency} ({sign}{change:.2f} / {sign}{percent:.2f}%) {indicator}')
        except Exception as error:
            print(f'  ⚠️ Fehler: {error}')
        print()


if __name__ == '__main__':
    main()
