#!/usr/bin/env python3
"""Scan U.S. stocks for weekly growth indicators.

This script:
1) Downloads symbol lists for U.S.-listed equities.
2) Pulls recent daily candles from Yahoo Finance chart API.
3) Computes momentum/trend indicators.
4) Scores and ranks symbols that look strong for the week.

Educational use only. Not financial advice.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=6mo"


@dataclass
class ScanResult:
    symbol: str
    score: int
    close: float
    weekly_return_pct: float
    rsi14: float
    macd: float
    macd_signal: float
    ema20: float
    ema50: float
    vol_ratio: float
    reasons: str


def fetch_text(url: str, timeout: int = 20) -> str:
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str, timeout: int = 20) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_json_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_us_symbols() -> List[str]:
    try:
        nasdaq_raw = fetch_text(NASDAQ_LISTED_URL)
        other_raw = fetch_text(OTHER_LISTED_URL)
    except URLError as exc:
        raise RuntimeError(
            "Could not download exchange symbol directories. "
            "Use --symbols-file to provide a local symbol list."
        ) from exc

    symbols: set[str] = set()

    # nasdaqlisted columns include: Symbol|Security Name|...|Test Issue|...
    nasdaq_lines = nasdaq_raw.splitlines()
    if nasdaq_lines:
        header = nasdaq_lines[0].split("|")
        symbol_idx = header.index("Symbol") if "Symbol" in header else 0
        test_idx = header.index("Test Issue") if "Test Issue" in header else -1

        for line in nasdaq_lines[1:]:
            if "File Creation Time" in line:
                continue
            parts = line.split("|")
            if len(parts) <= symbol_idx:
                continue
            if test_idx >= 0 and len(parts) > test_idx and parts[test_idx] == "Y":
                continue
            symbol = parts[symbol_idx].strip()
            if _is_common_stock_symbol(symbol):
                symbols.add(symbol)

    # otherlisted columns include: ACT Symbol|Security Name|Exchange|...|Test Issue
    other_lines = other_raw.splitlines()
    if other_lines:
        header = other_lines[0].split("|")
        symbol_idx = header.index("ACT Symbol") if "ACT Symbol" in header else 0
        test_idx = header.index("Test Issue") if "Test Issue" in header else -1

        for line in other_lines[1:]:
            if "File Creation Time" in line:
                continue
            parts = line.split("|")
            if len(parts) <= symbol_idx:
                continue
            if test_idx >= 0 and len(parts) > test_idx and parts[test_idx] == "Y":
                continue
            symbol = parts[symbol_idx].strip()
            if _is_common_stock_symbol(symbol):
                symbols.add(symbol)

    return sorted(symbols)


def _is_common_stock_symbol(symbol: str) -> bool:
    if not symbol:
        return False
    # Skip warrants/units/preferred/etc. Keep standard equity symbols.
    # This is heuristic and intentionally conservative.
    bad_chars = set("$^/ ")
    if any(ch in bad_chars for ch in symbol):
        return False
    if len(symbol) > 5:
        return False
    return symbol.isalpha()


def ema(values: List[float], period: int) -> List[float]:
    k = 2 / (period + 1)
    out = [values[0]]
    for price in values[1:]:
        out.append(price * k + out[-1] * (1 - k))
    return out


def rsi(values: List[float], period: int = 14) -> float:
    if len(values) <= period:
        return 50.0

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses += abs(diff)

    avg_gain = gains / period
    avg_loss = losses / period

    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = diff if diff > 0 else 0.0
        loss = abs(diff) if diff < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values: List[float], short: int = 12, long: int = 26, signal: int = 9) -> tuple[float, float]:
    short_ema = ema(values, short)
    long_ema = ema(values, long)
    macd_series = [s - l for s, l in zip(short_ema, long_ema)]
    signal_series = ema(macd_series, signal)
    return macd_series[-1], signal_series[-1]


def load_symbol_data(symbol: str, fixture_dir: str = "") -> Optional[ScanResult]:
    try:
        if fixture_dir:
            payload = load_json_file(f"{fixture_dir}/{symbol}.json")
        else:
            url = YAHOO_CHART_URL.format(symbol=quote(symbol))
            payload = fetch_json(url, timeout=15)
    except (HTTPError, URLError, TimeoutError, ValueError, FileNotFoundError, OSError):
        return None

    result = payload.get("chart", {}).get("result")
    if not result:
        return None

    quote_data = result[0].get("indicators", {}).get("quote", [{}])[0]
    closes_raw = quote_data.get("close") or []
    volumes_raw = quote_data.get("volume") or []

    closes = [v for v in closes_raw if isinstance(v, (int, float))]
    volumes = [v for v in volumes_raw if isinstance(v, (int, float))]

    length = min(len(closes), len(volumes))
    if length < 60:
        return None

    closes = closes[-length:]
    volumes = volumes[-length:]

    close = closes[-1]
    weekly_return_pct = ((close / closes[-6]) - 1) * 100
    ema20_series = ema(closes, 20)
    ema50_series = ema(closes, 50)
    ema20_last = ema20_series[-1]
    ema50_last = ema50_series[-1]
    rsi14 = rsi(closes, 14)
    macd_val, macd_signal = macd(closes, 12, 26, 9)

    vol20 = statistics.fmean(volumes[-20:]) if len(volumes) >= 20 else volumes[-1]
    vol_ratio = (volumes[-1] / vol20) if vol20 else 1.0

    score = 0
    reasons = []

    if weekly_return_pct >= 2:
        score += 25
        reasons.append("1W return >= 2%")
    elif weekly_return_pct > 0:
        score += 10
        reasons.append("1W return > 0")

    if close > ema20_last > ema50_last:
        score += 25
        reasons.append("Close > EMA20 > EMA50")

    if 50 <= rsi14 <= 75:
        score += 20
        reasons.append("RSI in 50-75")

    if macd_val > macd_signal:
        score += 20
        reasons.append("MACD above signal")

    if vol_ratio >= 1.2:
        score += 10
        reasons.append("Volume >= 1.2x 20d avg")

    if score < 45:
        return None

    return ScanResult(
        symbol=symbol,
        score=score,
        close=close,
        weekly_return_pct=weekly_return_pct,
        rsi14=rsi14,
        macd=macd_val,
        macd_signal=macd_signal,
        ema20=ema20_last,
        ema50=ema50_last,
        vol_ratio=vol_ratio,
        reasons=", ".join(reasons),
    )


def scan_symbols(symbols: Iterable[str], workers: int, fixture_dir: str = "") -> List[ScanResult]:
    results: List[ScanResult] = []
    symbol_list = list(symbols)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(load_symbol_data, symbol, fixture_dir): symbol for symbol in symbol_list
        }

        completed = 0
        total = len(symbol_list)
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            item = future.result()
            if item:
                results.append(item)
            if completed % 200 == 0 or completed == total:
                print(f"Scanned {completed}/{total} symbols...", file=sys.stderr)

    results.sort(key=lambda x: (x.score, x.weekly_return_pct), reverse=True)
    return results


def write_csv(results: List[ScanResult], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "symbol",
                "score",
                "close",
                "weekly_return_pct",
                "rsi14",
                "macd",
                "macd_signal",
                "ema20",
                "ema50",
                "vol_ratio",
                "reasons",
            ]
        )
        for row in results:
            writer.writerow(
                [
                    row.symbol,
                    row.score,
                    f"{row.close:.2f}",
                    f"{row.weekly_return_pct:.2f}",
                    f"{row.rsi14:.2f}",
                    f"{row.macd:.4f}",
                    f"{row.macd_signal:.4f}",
                    f"{row.ema20:.2f}",
                    f"{row.ema50:.2f}",
                    f"{row.vol_ratio:.2f}",
                    row.reasons,
                ]
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan U.S. stocks for weekly growth indicators.")
    parser.add_argument("--limit", type=int, default=0, help="Limit symbols scanned (0 = all).")
    parser.add_argument("--top", type=int, default=25, help="How many top results to print.")
    parser.add_argument("--workers", type=int, default=24, help="Concurrent requests.")
    parser.add_argument(
        "--symbols-file",
        type=str,
        default="",
        help="Optional local file with one ticker per line (used instead of downloading symbol directories).",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="weekly_growth_scan.csv",
        help="Output CSV path for all passing symbols.",
    )
    parser.add_argument(
        "--fixture-dir",
        type=str,
        default="",
        help="Optional folder of local Yahoo chart payloads named <TICKER>.json for offline testing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.time()

    if args.symbols_file:
        print(f"Loading symbols from file: {args.symbols_file}", file=sys.stderr)
        with open(args.symbols_file, "r", encoding="utf-8") as handle:
            symbols = [line.strip().upper() for line in handle if line.strip()]
    else:
        print("Loading U.S. symbols...", file=sys.stderr)
        symbols = load_us_symbols()
    if args.limit > 0:
        symbols = symbols[: args.limit]

    print(f"Symbols to scan: {len(symbols)}", file=sys.stderr)
    results = scan_symbols(symbols, workers=max(1, args.workers), fixture_dir=args.fixture_dir)

    write_csv(results, args.csv)

    print(f"\nTop {min(args.top, len(results))} weekly growth candidates:\n")
    for item in results[: args.top]:
        print(
            f"{item.symbol:5} score={item.score:3d} 1W={item.weekly_return_pct:6.2f}% "
            f"RSI={item.rsi14:5.1f} MACD={item.macd:7.3f}/{item.macd_signal:7.3f} "
            f"Volx={item.vol_ratio:4.2f}"
        )

    elapsed = time.time() - start
    print(f"\nFound {len(results)} candidates. CSV written to {args.csv}.")
    print(f"Elapsed: {elapsed:.1f}s")
    print("\nEducational use only. Not financial advice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
