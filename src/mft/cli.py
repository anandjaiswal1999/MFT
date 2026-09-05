from __future__ import annotations

import argparse
import json

from .core import Config, backtest
from .data import download_binance, read_csv, synthetic_bars, write_csv
from .paper import run_paper


def load_source(value: str, bars: int):
    return synthetic_bars(bars) if value == "synthetic" else read_csv(value)


def main() -> None:
    parser = argparse.ArgumentParser(prog="mft", description="Local medium-frequency trading research")
    sub = parser.add_subparsers(dest="command", required=True)
    dl = sub.add_parser("download")
    dl.add_argument("--symbol", default="BTCUSDT")
    dl.add_argument("--interval", default="1h")
    dl.add_argument("--limit", type=int, default=1000)
    dl.add_argument("--out", default="data/market.csv")
    bt = sub.add_parser("backtest")
    bt.add_argument("--source", default="synthetic")
    bt.add_argument("--bars", type=int, default=2000)
    bt.add_argument("--cash", type=float, default=10_000)
    pp = sub.add_parser("paper")
    pp.add_argument("--source", required=True)
    pp.add_argument("--state", default="state/paper.json")
    pp.add_argument("--cash", type=float, default=10_000)
    args = parser.parse_args()
    cfg = Config()
    if args.command == "download":
        data = download_binance(args.symbol, args.interval, args.limit)
        write_csv(args.out, data)
        print(f"saved {len(data)} bars to {args.out}")
    elif args.command == "backtest":
        result = backtest(load_source(args.source, args.bars), cfg, args.cash)
        print(json.dumps({"starting_cash": result.starting_cash, "ending_equity": round(result.ending_equity, 2),
                          "total_return_pct": round(result.total_return * 100, 2),
                          "max_drawdown_pct": round(result.max_drawdown * 100, 2),
                          "sharpe": round(result.sharpe, 2), "trades": result.trades}, indent=2))
    else:
        print(json.dumps(run_paper(read_csv(args.source), args.state, cfg, args.cash), indent=2))


if __name__ == "__main__":
    main()

