from __future__ import annotations

import csv
import json
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .core import Bar, utc_from_ms


def read_csv(path: str | Path) -> list[Bar]:
    with Path(path).open(newline="") as handle:
        rows = csv.DictReader(handle)
        return [Bar(datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")),
                    float(r["open"]), float(r["high"]), float(r["low"]),
                    float(r["close"]), float(r["volume"])) for r in rows]


def write_csv(path: str | Path, bars: list[Bar]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="") as handle:
        out = csv.writer(handle)
        out.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for b in bars:
            out.writerow([b.timestamp.isoformat(), b.open, b.high, b.low, b.close, b.volume])


def synthetic_bars(count: int = 2000, seed: int = 7) -> list[Bar]:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    price, bars = 100.0, []
    for i in range(count):
        drift = 0.00018 if (i // 350) % 2 == 0 else -0.00008
        new_price = price * (1 + drift + rng.gauss(0, 0.006))
        high, low = max(price, new_price) * 1.002, min(price, new_price) * 0.998
        bars.append(Bar(now - timedelta(hours=count - i), price, high, low, new_price, 1000 + rng.random() * 500))
        price = new_price
    return bars


def download_binance(symbol: str, interval: str, limit: int) -> list[Bar]:
    if not 1 <= limit <= 1000:
        raise ValueError("Binance limit must be between 1 and 1000")
    params = urlencode({"symbol": symbol.upper(), "interval": interval, "limit": limit})
    url = f"https://data-api.binance.vision/api/v3/klines?{params}"
    request = Request(url, headers={"User-Agent": "local-mft/0.1"})
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    if isinstance(payload, dict):
        raise RuntimeError(payload.get("msg", "market data request failed"))
    return [Bar(utc_from_ms(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])) for r in payload]


def download_indian_stock(symbol: str, interval: str = "1h", days: int = 365) -> list[Bar]:
    symbol = symbol.upper().strip()
    if not re.fullmatch(r"[A-Z0-9&-]{1,24}\.(NS|BO)", symbol):
        raise ValueError("use an NSE/BSE symbol such as RELIANCE.NS or TCS.NS")
    end = int(time.time())
    params = urlencode({"period1": end - days * 86_400, "period2": end, "interval": interval, "events": "history"})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{params}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 local-mft/0.1"})
    with urlopen(request, timeout=25) as response:
        payload = json.load(response)
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(chart["error"].get("description", "market data request failed"))
    results = chart.get("result") or []
    if not results:
        raise RuntimeError(f"no market data returned for {symbol}")
    result = results[0]
    quote = result["indicators"]["quote"][0]
    bars = []
    for i, timestamp in enumerate(result.get("timestamp", [])):
        values = [quote.get(name, [None])[i] for name in ("open", "high", "low", "close", "volume")]
        if all(value is not None for value in values):
            bars.append(Bar(datetime.fromtimestamp(timestamp, tz=timezone.utc), *(float(v) for v in values)))
    if len(bars) < 100:
        raise RuntimeError(f"only {len(bars)} usable candles returned for {symbol}")
    return bars
