# Day Trade Indicator Tracker + Weekly Growth Scanner

This repository includes:

1. A browser app to score a custom watchlist with intraday indicators.
2. A Python scanner to sweep U.S. stocks for **weekly growth** indicators.

## 1) Browser app (watchlist analyzer)

### Features

- Comma-separated ticker input
- Pulls **intraday 5m candles** from Yahoo Finance chart API
- Computes indicator snapshot:
  - RSI(14)
  - MACD(12, 26, 9)
  - EMA(9) vs EMA(21)
  - Session VWAP
- Applies a weighted score to label each symbol as:
  - **Buy Candidate**
  - **Watch**
  - **Avoid**

### Run locally

Because this app uses `fetch`, serve it over HTTP:

```bash
python3 -m http.server 4173
```

Then open:

```text
http://localhost:4173
```

## 2) Weekly growth market scanner

Use `scan_weekly_growth.py` to scan many U.S.-listed symbols and rank likely weekly momentum candidates.

### What it scans

- U.S. symbol universe from Nasdaq Trader symbol directories (or a local symbol file)
- Daily candles (6 months) from Yahoo Finance chart API
- Indicator rules:
  - Positive 1-week return (stronger score at >= 2%)
  - Close > EMA20 > EMA50
  - RSI(14) in 50–75
  - MACD above signal
  - Latest volume >= 1.2x 20-day average

### Run scanner

Scan all symbols (can take a while):

```bash
python3 scan_weekly_growth.py --top 50 --workers 24 --csv weekly_growth_scan.csv
```

Use a local symbol list if exchange directory downloads are blocked:

```bash
python3 scan_weekly_growth.py --symbols-file symbols.txt --top 50 --workers 24 --csv weekly_growth_scan.csv
```

Offline/CI fixture mode (no network):

```bash
python3 scan_weekly_growth.py --symbols-file fixtures/symbols.txt --fixture-dir fixtures/yahoo --top 20 --csv weekly_growth_sample.csv
```

## Important disclaimer

This project is for **education and research** only and is **not financial advice**. Indicator signals can fail, data can be delayed or incomplete, and markets are risky.
