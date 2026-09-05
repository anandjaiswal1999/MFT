import tempfile
import unittest
from pathlib import Path

from mft.core import Config, backtest, target_exposure
from mft.data import read_csv, synthetic_bars, write_csv
from mft.paper import run_paper


class EngineTests(unittest.TestCase):
    def test_backtest_is_finite(self):
        result = backtest(synthetic_bars(500), Config())
        self.assertGreater(result.ending_equity, 0)
        self.assertGreaterEqual(result.trades, 1)
        self.assertLessEqual(result.max_drawdown, 1)

    def test_signal_needs_history(self):
        self.assertEqual(target_exposure([1.0] * 20, Config()), 0)

    def test_csv_and_paper_state(self):
        bars = synthetic_bars(150)
        with tempfile.TemporaryDirectory() as folder:
            csv_path, state_path = Path(folder) / "bars.csv", Path(folder) / "paper.json"
            write_csv(csv_path, bars)
            loaded = read_csv(csv_path)
            state = run_paper(loaded, str(state_path), Config())
            self.assertEqual(len(loaded), len(bars))
            self.assertTrue(state_path.exists())
            self.assertGreater(state["equity"], 0)


if __name__ == "__main__":
    unittest.main()
