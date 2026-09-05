from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
from statistics import mean, pstdev


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Config:
    fast_window: int = 24
    slow_window: int = 96
    vol_window: int = 20
    annual_vol_target: float = 0.20
    max_exposure: float = 0.95
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
    max_drawdown: float = 0.12
    max_daily_loss: float = 0.03
    min_rebalance: float = 0.05
    bars_per_year: int = 24 * 365

    def validate(self) -> None:
        if not (1 <= self.fast_window < self.slow_window):
            raise ValueError("windows must satisfy 1 <= fast < slow")
        if self.vol_window < 2:
            raise ValueError("vol_window must be at least 2")
        for name in ("annual_vol_target", "max_exposure", "max_drawdown", "max_daily_loss", "min_rebalance"):
            if not 0 < getattr(self, name) <= 1:
                raise ValueError(f"{name} must be in (0, 1]")


@dataclass
class Result:
    starting_cash: float
    ending_equity: float
    total_return: float
    max_drawdown: float
    sharpe: float
    trades: int
    equity_curve: list[tuple[datetime, float]]


def target_exposure(closes: list[float], cfg: Config) -> float:
    if len(closes) < max(cfg.slow_window, cfg.vol_window + 1):
        return 0.0
    fast = mean(closes[-cfg.fast_window:])
    slow = mean(closes[-cfg.slow_window:])
    if fast <= slow:
        return 0.0
    returns = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - cfg.vol_window, len(closes))]
    bar_vol = pstdev(returns)
    if bar_vol <= 1e-12:
        return 0.0
    annual_vol = bar_vol * sqrt(cfg.bars_per_year)
    return min(cfg.max_exposure, cfg.annual_vol_target / annual_vol)


def backtest(bars: list[Bar], cfg: Config, starting_cash: float = 10_000.0) -> Result:
    cfg.validate()
    if len(bars) < cfg.slow_window + 2:
        raise ValueError(f"need at least {cfg.slow_window + 2} bars")
    cash, units, trades = starting_cash, 0.0, 0
    peak = starting_cash
    halted = False
    current_day = None
    day_start = starting_cash
    curve: list[tuple[datetime, float]] = []
    closes: list[float] = []
    cost_rate = (cfg.fee_bps + cfg.slippage_bps) / 10_000

    for bar in bars:
        closes.append(bar.close)
        equity = cash + units * bar.close
        if current_day != bar.timestamp.date():
            current_day, day_start = bar.timestamp.date(), equity
        peak = max(peak, equity)
        drawdown = 1 - equity / peak
        daily_loss = 1 - equity / day_start if day_start else 0
        if drawdown >= cfg.max_drawdown or daily_loss >= cfg.max_daily_loss:
            halted = True

        desired = 0.0 if halted else target_exposure(closes, cfg)
        target_value = equity * desired
        delta_value = target_value - units * bar.close
        if abs(delta_value) >= max(1.0, equity * cfg.min_rebalance):
            cost = abs(delta_value) * cost_rate
            units += delta_value / bar.close
            cash -= delta_value + cost
            trades += 1
        curve.append((bar.timestamp, cash + units * bar.close))

    equities = [v for _, v in curve]
    returns = [equities[i] / equities[i - 1] - 1 for i in range(1, len(equities)) if equities[i - 1]]
    sigma = pstdev(returns) if len(returns) > 1 else 0
    sharpe = mean(returns) / sigma * sqrt(cfg.bars_per_year) if sigma else 0.0
    running_peak = equities[0]
    max_dd = 0.0
    for value in equities:
        running_peak = max(running_peak, value)
        max_dd = max(max_dd, 1 - value / running_peak)
    end = equities[-1]
    return Result(starting_cash, end, end / starting_cash - 1, max_dd, sharpe, trades, curve)


def utc_from_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
