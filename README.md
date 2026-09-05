# Local MFT

A local-first medium-frequency trading research system. It uses completed hourly
candles, trades long/flat, and defaults to simulation. It **does not place real
orders**.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

# Run a deterministic backtest immediately
mft backtest --source synthetic --bars 2000

# Download public BTC/USDT hourly candles, then backtest them
mft download --symbol BTCUSDT --interval 1h --limit 1000 --out data/btcusdt.csv
mft backtest --source data/btcusdt.csv

# Advance a persistent local paper account over the same file
mft paper --source data/btcusdt.csv --state state/paper.json

# Start the local dashboard
python -m mft.server
# Then open http://127.0.0.1:8787
```

Run tests with `python -m unittest discover -s tests -v`.

## Strategy

The default signal is a 24/96-bar moving-average crossover with a 20-bar
volatility filter. Position exposure is volatility-targeted and capped at 95%.
Trades include configurable fees and slippage. Risk controls stop new exposure
after a 12% peak-to-trough drawdown or 3% daily loss.

The included parameters are engineering defaults, not optimized recommendations.
The strategy may lose money—as the bundled deterministic sample demonstrates.

This is research software, not investment advice. Backtests omit many live-market
effects and cannot establish future profitability. Keep it in paper mode until it
has survived out-of-sample testing and extended forward testing.
