from __future__ import annotations

import json
from pathlib import Path

from .core import Bar, Config, target_exposure


def run_paper(bars: list[Bar], state_path: str, cfg: Config, starting_cash: float = 10_000.0) -> dict:
    path = Path(state_path)
    if path.exists():
        state = json.loads(path.read_text())
    else:
        state = {"cash": starting_cash, "units": 0.0, "last_timestamp": None, "trades": [],
                 "peak_equity": starting_cash, "day": None, "day_start_equity": starting_cash, "halted": False}
    unseen = [b for b in bars if state["last_timestamp"] is None or b.timestamp.isoformat() > state["last_timestamp"]]
    closes = [b.close for b in bars]
    if not unseen:
        return state
    bar = unseen[-1]
    equity = state["cash"] + state["units"] * bar.close
    state.setdefault("peak_equity", equity)
    state.setdefault("day", None)
    state.setdefault("day_start_equity", equity)
    state.setdefault("halted", False)
    if state["day"] != bar.timestamp.date().isoformat():
        state["day"] = bar.timestamp.date().isoformat()
        state["day_start_equity"] = equity
    state["peak_equity"] = max(state["peak_equity"], equity)
    drawdown = 1 - equity / state["peak_equity"]
    daily_loss = 1 - equity / state["day_start_equity"]
    if drawdown >= cfg.max_drawdown or daily_loss >= cfg.max_daily_loss:
        state["halted"] = True
    exposure = 0.0 if state["halted"] else target_exposure(closes[:bars.index(bar) + 1], cfg)
    target_value = equity * exposure
    delta = target_value - state["units"] * bar.close
    cost = abs(delta) * (cfg.fee_bps + cfg.slippage_bps) / 10_000
    if abs(delta) >= max(1.0, equity * cfg.min_rebalance):
        state["units"] += delta / bar.close
        state["cash"] -= delta + cost
        state["trades"].append({"timestamp": bar.timestamp.isoformat(), "notional": delta, "price": bar.close, "cost": cost})
    state["last_timestamp"] = bar.timestamp.isoformat()
    state["equity"] = state["cash"] + state["units"] * bar.close
    state["exposure"] = exposure
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")
    return state
