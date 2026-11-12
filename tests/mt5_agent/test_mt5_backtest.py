"""Execution model and risk controls of the portfolio backtester."""

from datetime import datetime, timedelta

import pytest

from mt5_agent.backtest import Costs, Market, RiskConfig, run_backtest
from mt5_agent.data import Bars
from mt5_agent.strategy import LONG, SHORT, Entry

NO_LIMITS = RiskConfig(risk_pct=1.0, max_daily_loss_pct=0.0, max_drawdown_pct=0.0)


class Scripted:
    """Strategy stub: enter on given bars, exit on given bars, fixed stop distance."""

    def __init__(self, entries=None, exits=(), stop_distance=1.0):
        self.entries = entries or {}
        self.exits = set(exits)
        self.stop_distance = stop_distance
        self.seen_held = []

    def entry_signal(self, i):
        direction = self.entries.get(i)
        return Entry(direction, self.stop_distance) if direction else None

    def trail_stop(self, i, direction, stop):
        return stop

    def exit_signal(self, i, direction, bars_held):
        self.seen_held.append(bars_held)
        return i in self.exits


def make_bars(rows, start=datetime(2021, 1, 4), step=timedelta(days=1)):
    bars = Bars()
    for k, (o, h, l, c) in enumerate(rows):
        bars.append(start + k * step, o, h, l, c)
    return bars


FLAT = (100.0, 100.5, 99.5, 100.0)


def run_one(rows, strategy, costs=Costs(), risk=NO_LIMITS, equity=10_000.0):
    return run_backtest([Market("TEST", make_bars(rows), strategy, costs)], risk, equity)


def test_signal_fills_next_open_and_stop_loses_exactly_the_risk():
    res = run_one([FLAT, FLAT, (100.0, 100.2, 98.0, 98.5)], Scripted({0: LONG}))
    (trade,) = res.trades
    assert trade.entry_time == datetime(2021, 1, 5)
    assert trade.entry_price == 100.0
    assert trade.exit_price == 99.0
    assert trade.reason == "stop"
    assert trade.pnl == pytest.approx(-100.0)
    assert trade.r_multiple == pytest.approx(-1.0)
    assert res.equity_curve[-1][1] == pytest.approx(9_900.0)


def test_gap_through_stop_fills_at_the_open():
    res = run_one([FLAT, FLAT, (97.0, 97.5, 96.5, 97.2)], Scripted({0: LONG}))
    (trade,) = res.trades
    assert trade.exit_price == 97.0
    assert trade.r_multiple == pytest.approx(-3.0)


def test_short_stop_and_profit_are_mirrored():
    rows = [FLAT, FLAT, (99.0, 99.2, 97.0, 97.5), (97.5, 101.5, 97.4, 101.0)]
    res = run_one(rows, Scripted({0: SHORT}, stop_distance=1.0))
    (trade,) = res.trades
    assert trade.direction == SHORT
    assert trade.exit_price == 101.0
    assert trade.pnl == pytest.approx(-100.0)


def test_exit_signal_closes_at_next_open_with_spread():
    rows = [FLAT, FLAT, (100.0, 102.2, 99.9, 102.0), (103.0, 103.5, 102.5, 103.0)]
    res = run_one(rows, Scripted({0: LONG}, exits={2}, stop_distance=2.0), Costs(spread=0.2))
    (trade,) = res.trades
    assert trade.entry_price == pytest.approx(100.1)
    assert trade.exit_price == pytest.approx(102.9)
    assert trade.reason == "signal"
    assert trade.bars_held == 3
    units = 100.0 / 2.0
    assert trade.pnl == pytest.approx(units * (102.9 - 100.1))


def test_bars_held_counts_the_entry_bar():
    strat = Scripted({0: LONG}, exits={3}, stop_distance=5.0)
    run_one([FLAT] * 5, strat)
    assert strat.seen_held == [1, 2, 3]


def test_entry_and_stop_inside_the_same_bar_is_a_loss():
    res = run_one([FLAT, (100.0, 101.0, 98.5, 100.8)], Scripted({0: LONG}))
    (trade,) = res.trades
    assert trade.entry_time == trade.exit_time
    assert trade.r_multiple == pytest.approx(-1.0)


def test_signals_are_ignored_while_a_position_is_open():
    res = run_one([FLAT] * 6, Scripted({0: LONG, 1: LONG, 2: SHORT}, stop_distance=5.0))
    assert len(res.trades) == 1
    assert res.trades[0].reason == "end_of_data"


def test_open_position_is_closed_at_end_of_data_and_curve_ends_on_cash():
    rows = [FLAT, FLAT, (100.0, 101.0, 99.8, 101.0)]
    res = run_one(rows, Scripted({0: LONG}, stop_distance=2.0), Costs(spread=0.2))
    (trade,) = res.trades
    assert trade.reason == "end_of_data"
    assert trade.exit_price == pytest.approx(100.9)
    assert res.equity_curve[-1][1] == pytest.approx(10_000.0 + trade.pnl)


def test_swap_is_charged_per_calendar_day_on_notional():
    rows = [FLAT] * 4
    res = run_one(rows, Scripted({0: LONG}, stop_distance=2.0), Costs(swap_annual_pct=36.5))
    (trade,) = res.trades
    units = 100.0 / 2.0
    daily_fee = units * 100.0 * 0.365 / 365.0
    assert trade.pnl == pytest.approx(-2 * daily_fee)


def test_position_size_uses_marked_to_market_equity():
    rows_a = [FLAT, FLAT, (100.0, 110.0, 99.9, 110.0), (110.0, 110.5, 109.5, 110.0), (110.0, 110.5, 109.5, 110.0)]
    rows_b = [FLAT, FLAT, FLAT, FLAT, FLAT]
    a = Market("A", make_bars(rows_a), Scripted({0: LONG}, stop_distance=10.0))
    b = Market("B", make_bars(rows_b), Scripted({2: LONG}, stop_distance=10.0))
    res = run_backtest([a, b], NO_LIMITS, 10_000.0)
    by_symbol = {t.symbol: t for t in res.trades}
    # A is up 10/10 R = +100 when B's signal fills, so B risks 1% of 10,100.
    assert by_symbol["B"].units == pytest.approx(101.0 / 10.0)


def test_daily_loss_limit_blocks_new_entries():
    rows = [FLAT, FLAT, (100.0, 100.0, 90.0, 90.0), FLAT, FLAT]
    a = Market("A", make_bars(rows), Scripted({0: LONG}, stop_distance=50.0))
    b = Market("B", make_bars([FLAT] * 5), Scripted({2: LONG}, stop_distance=1.0))
    risk = RiskConfig(risk_pct=50.0, max_daily_loss_pct=3.0, max_drawdown_pct=0.0)
    res = run_backtest([a, b], risk, 10_000.0)
    assert [t.symbol for t in res.trades] == ["A"]


def test_drawdown_halt_flattens_and_stops_trading():
    rows = [FLAT, FLAT, (100.0, 100.0, 80.0, 80.0), FLAT, FLAT, FLAT]
    strat = Scripted({0: LONG, 4: LONG}, stop_distance=50.0)
    res = run_one(rows, strat, risk=RiskConfig(risk_pct=50.0, max_daily_loss_pct=0.0, max_drawdown_pct=5.0))
    assert res.halted_at == datetime(2021, 1, 6)
    (trade,) = res.trades
    assert trade.reason == "halt"
    assert trade.exit_time == datetime(2021, 1, 7)


def test_max_positions_caps_concurrent_trades():
    markets = [Market(s, make_bars([FLAT] * 4), Scripted({0: LONG}, stop_distance=5.0)) for s in ("A", "B", "C")]
    res = run_backtest(markets, RiskConfig(1.0, 0.0, 0.0, max_positions=2), 10_000.0)
    assert sorted(t.symbol for t in res.trades) == ["A", "B"]


def test_duplicate_symbols_are_rejected():
    m = Market("X", make_bars([FLAT]), Scripted())
    with pytest.raises(ValueError, match="unique"):
        run_backtest([m, Market("X", make_bars([FLAT]), Scripted())])


def test_markets_with_different_calendars_share_one_timeline():
    a = Market("A", make_bars([FLAT] * 3), Scripted())
    b = Market("B", make_bars([FLAT] * 3, start=datetime(2021, 1, 5)), Scripted())
    res = run_backtest([a, b], NO_LIMITS)
    assert [t for t, _ in res.equity_curve] == [datetime(2021, 1, d) for d in (4, 5, 6, 7)]
