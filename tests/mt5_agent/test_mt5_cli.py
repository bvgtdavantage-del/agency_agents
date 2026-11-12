"""Metrics, CSV loading and the mt5-agent command line."""

import csv
import math
from datetime import datetime

import pytest

from mt5_agent.backtest import BacktestResult, Trade
from mt5_agent.cli import main
from mt5_agent.data import load_csv, parse_time
from mt5_agent.metrics import compute_metrics, max_drawdown_pct, sharpe_ratio


def _trade(pnl, r):
    t = datetime(2021, 1, 1)
    return Trade("X", 1, t, 1.0, t, 1.0, 1.0, pnl, r, 1, "stop")


def test_max_drawdown_is_worst_peak_to_trough():
    assert max_drawdown_pct([100, 120, 90, 130, 117]) == pytest.approx(25.0)
    assert max_drawdown_pct([100, 110, 120]) == 0.0


def test_metrics_cagr_profit_factor_and_win_rate():
    curve = [(datetime(2020, 1, 1), 10_000.0), (datetime(2020, 7, 1), 9_000.0), (datetime(2021, 1, 1), 12_100.0)]
    result = BacktestResult(10_000.0, curve, [_trade(300.0, 3.0), _trade(-100.0, -1.0), _trade(-100.0, -1.0)])
    m = compute_metrics(result)
    assert m.total_return_pct == pytest.approx(21.0)
    assert m.cagr_pct == pytest.approx(100 * (1.21 ** (365.25 / 366) - 1), rel=1e-6)
    assert m.max_drawdown_pct == pytest.approx(10.0)
    assert m.profit_factor == pytest.approx(1.5)
    assert m.win_rate_pct == pytest.approx(100 / 3)
    assert m.avg_r == pytest.approx(1 / 3)
    assert m.worst_r == -1.0


def test_metrics_edge_cases():
    m = compute_metrics(BacktestResult(1_000.0, [], []))
    assert (m.trades, m.profit_factor, m.cagr_pct, m.final_equity) == (0, 0.0, 0.0, 1_000.0)
    winners_only = BacktestResult(1.0, [(datetime(2020, 1, 1), 1.0)], [_trade(5.0, 1.0)])
    assert math.isinf(compute_metrics(winners_only).profit_factor)


def test_sharpe_needs_variation():
    flat = [(datetime(2020, 1, d), 100.0) for d in range(1, 10)]
    assert sharpe_ratio(flat) == 0.0
    rising = [(datetime(2020, 1, d), 100.0 + d + (d % 2)) for d in range(1, 20)]
    assert sharpe_ratio(rising) > 0


def test_load_mt5_export_with_split_date_and_time(tmp_path):
    path = tmp_path / "EURUSD_H1.csv"
    path.write_text(
        "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
        "2020.01.02\t01:00:00\t1.1210\t1.1215\t1.1205\t1.1212\t100\t0\t5\n"
        "2020.01.02\t00:00:00\t1.1200\t1.1220\t1.1190\t1.1210\t120\t0\t5\n",
        encoding="utf-8",
    )
    bars = load_csv(path)
    assert bars.time == [datetime(2020, 1, 2, 0), datetime(2020, 1, 2, 1)]
    assert bars.close == [1.1210, 1.1212]


def test_load_mt5_daily_export_without_time_column(tmp_path):
    path = tmp_path / "XAUUSD_D1.csv"
    path.write_text("<DATE>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\n2020.01.02\t1520\t1530\t1510\t1525\n", encoding="utf-8")
    bars = load_csv(path)
    assert bars.time == [datetime(2020, 1, 2)]
    assert len(bars) == 1


def test_load_generic_csv_and_since(tmp_path):
    path = tmp_path / "bars.csv"
    path.write_text("time,open,high,low,close\n2020-01-01,1,2,0.5,1.5\n2020-01-02,1.5,2,1,1.8\n")
    bars = load_csv(path)
    assert bars.since(datetime(2020, 1, 2)).close == [1.8]


def test_load_rejects_missing_columns(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("time,open,close\n2020-01-01,1,2\n")
    with pytest.raises(ValueError, match="missing columns"):
        load_csv(path)
    path.write_text("open,high,low,close\n1,2,0,1\n")
    with pytest.raises(ValueError, match="no time"):
        load_csv(path)


def test_parse_time_rejects_garbage():
    with pytest.raises(ValueError):
        parse_time("yesterday")


def _write_trend(path, n=320):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time", "open", "high", "low", "close"])
        price = 100.0
        for k in range(n):
            day = datetime(2019, 1, 1).toordinal() + k
            o = price
            price *= 1.004 if (k // 15) % 3 else 0.995
            w.writerow([datetime.fromordinal(day).strftime("%Y-%m-%d"), o, max(o, price) * 1.002, min(o, price) * 0.998, price])


def test_cli_backtest_prints_report_and_writes_trades(tmp_path, capsys):
    data = tmp_path / "GOLD.csv"
    _write_trend(data)
    trades = tmp_path / "trades.csv"
    code = main(["backtest", "--market", "GOLD", "breakout", str(data), "--spread", "GOLD=0.05",
                 "--param", "breakout.entry_period=20", "--param", "breakout.allow_short=false",
                 "--risk", "1", "--trades-csv", str(trades)])
    out = capsys.readouterr().out
    assert code == 0
    assert "CAGR" in out and "Max drawdown" in out and "Profit factor" in out
    rows = list(csv.DictReader(trades.open()))
    assert rows and all(r["direction"] == "long" for r in rows)


def test_cli_start_date_trims_the_report(tmp_path, capsys):
    data = tmp_path / "IDX.csv"
    _write_trend(data)
    assert main(["backtest", "--market", "IDX", "meanrev", str(data), "--start", "2019-10-01"]) == 0
    assert "2019-10-01" in capsys.readouterr().out


@pytest.mark.parametrize("args, message", [
    (["--param", "breakout.nope=1"], "no parameter"),
    (["--param", "scalper.x=1"], "unknown strategy"),
    (["--spread", "GOLD"], "KEY=VALUE"),
])
def test_cli_rejects_bad_arguments(tmp_path, args, message):
    data = tmp_path / "G.csv"
    _write_trend(data, 50)
    with pytest.raises(SystemExit, match=message):
        main(["backtest", "--market", "GOLD", "breakout", str(data)] + args)


def test_cli_rejects_unknown_strategy(tmp_path):
    data = tmp_path / "G.csv"
    _write_trend(data, 50)
    with pytest.raises(SystemExit, match="unknown strategy"):
        main(["backtest", "--market", "GOLD", "grid", str(data)])
