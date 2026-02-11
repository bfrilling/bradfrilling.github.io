# Day Trade Indicator Tracker

A lightweight browser app that scores a stock watchlist for same-day momentum setups using common technical indicators.

## Features

- Comma-separated ticker input
- Pulls **intraday 5m candles** from Yahoo Finance chart API
- Computes indicator snapshot:
  - RSI(14)
  - MACD(12, 26, 9)
  - EMA(9) vs EMA(21)
  - Session VWAP
- Applies a simple weighted score to label each symbol as:
  - **Buy Candidate**
  - **Watch**
  - **Avoid**

## Run locally

Because this app uses `fetch`, serve it over HTTP:

```bash
python3 -m http.server 4173
```

Then open:

```text
http://localhost:4173
```

## Important disclaimer

This project is for **education and research** only and is **not financial advice**. Indicator signals can fail and markets are risky.
