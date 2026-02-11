# Day Trade Indicator Tracker + Weekly Growth Scanner

This repository includes:

1. A browser app to score a custom watchlist with intraday indicators.
2. A Python scanner to sweep U.S. stocks for **weekly growth** indicators.
3. A Windows desktop wrapper that can be built into a `.exe`.

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

## 2) Weekly growth market scanner (CLI)

Use `scan_weekly_growth.py` to scan many U.S.-listed symbols and rank likely weekly momentum candidates.

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

## 3) Windows `.exe` desktop app

The file `windows_stock_scanner_app.py` is a desktop GUI wrapper around the scanner.

### Build EXE on Windows

1. Open **Command Prompt** in this repo folder.
2. Run:

```bat
build_windows_exe.bat
```

This creates:

```text
dist\WeeklyGrowthScanner.exe
```

### Manual build command (alternative)

```bat
python -m pip install -r windows_requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --name WeeklyGrowthScanner windows_stock_scanner_app.py
```

## Important disclaimer

This project is for **education and research** only and is **not financial advice**. Indicator signals can fail, data can be delayed or incomplete, and markets are risky.
