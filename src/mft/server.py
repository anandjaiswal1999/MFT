from __future__ import annotations

import json
from dataclasses import asdict, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .core import Config, backtest
from .data import download_indian_stock, read_csv, synthetic_bars


STATIC = Path(__file__).with_name("static")


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/status":
            self.send_json({"status": "ready", "mode": "paper", "liveTrading": False})
            return
        asset = STATIC / ("index.html" if path == "/" else path.lstrip("/"))
        if not asset.is_file() or STATIC not in asset.resolve().parents:
            self.send_error(404)
            return
        content = asset.read_bytes()
        mime = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript"}.get(asset.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/backtest":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            values = json.loads(self.rfile.read(size) or b"{}")
            cfg = replace(Config(), fast_window=int(values.get("fast", 24)), slow_window=int(values.get("slow", 96)),
                          annual_vol_target=float(values.get("volTarget", 20)) / 100,
                          max_drawdown=float(values.get("maxDrawdown", 12)) / 100)
            market = values.get("market", "india")
            if market == "india":
                bars = download_indian_stock(values.get("symbol", "RELIANCE.NS"))
                cfg = replace(cfg, bars_per_year=252 * 7)
            elif values.get("source"):
                bars = read_csv(values["source"])
            else:
                bars = synthetic_bars(int(values.get("bars", 2000)))
            requested_bars = int(values.get("bars", 1000))
            if requested_bars < cfg.slow_window + 2:
                raise ValueError(f"test period must be at least {cfg.slow_window + 2} market hours")
            bars = bars[-requested_bars:]
            result = backtest(bars, cfg, float(values.get("cash", 10000)))
            split = max(cfg.slow_window + 2, int(len(bars) * 0.60))
            validation_bars = bars[split - cfg.slow_window:]
            validation = backtest(validation_bars, cfg, float(values.get("cash", 10000)))
            scored_hours = len(bars) - split
            benchmark_return = bars[-1].close / bars[split].close - 1 - (cfg.fee_bps * 2 / 10_000)
            checks = [
                {"label": "Profitable on unseen data", "passed": validation.total_return > 0},
                {"label": "Better than buy and hold", "passed": validation.total_return > benchmark_return},
                {"label": "Drawdown within your limit", "passed": validation.max_drawdown <= cfg.max_drawdown},
                {"label": "Risk-adjusted return is acceptable", "passed": validation.sharpe >= 0.5},
                {"label": "Enough trades to evaluate", "passed": validation.trades >= 5},
            ]
            qualified = all(item["passed"] for item in checks)
            stride = max(1, len(result.equity_curve) // 220)
            self.send_json({"summary": {"endingEquity": result.ending_equity, "returnPct": result.total_return * 100,
                                         "maxDrawdownPct": result.max_drawdown * 100, "sharpe": result.sharpe,
                                         "trades": result.trades},
                            "curve": [{"time": t.isoformat(), "value": v} for t, v in result.equity_curve[::stride]],
                            "config": asdict(cfg), "symbol": values.get("symbol") if market == "india" else "SIMULATED",
                            "hoursTested": len(bars), "validation": {"hours": scored_hours,
                            "returnPct": validation.total_return * 100, "benchmarkPct": benchmark_return * 100,
                            "maxDrawdownPct": validation.max_drawdown * 100, "sharpe": validation.sharpe,
                            "trades": validation.trades}, "checks": checks, "qualified": qualified})
        except (ValueError, KeyError, OSError, RuntimeError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)

    def log_message(self, format: str, *args: object) -> None:
        pass


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    print(f"MFT dashboard running at http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
