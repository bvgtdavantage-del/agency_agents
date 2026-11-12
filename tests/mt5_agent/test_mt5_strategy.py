"""Entry, trailing and exit rules of the two strategies."""

from datetime import datetime, timedelta

import pytest

from mt5_agent.data import Bars
from mt5_agent.strategy import (
    LONG, SHORT, Breakout, BreakoutParams, MeanReversion, MeanReversionParams, build_strategy,
)


def make_bars(closes, spread=0.5, highs=None, lows=None):
    bars = Bars()
    start = datetime(2020, 1, 1)
    for i, c in enumerate(closes):
        h = highs[i] if highs else c + spread
        l = lows[i] if lows else c - spread
        bars.append(start + timedelta(days=i), c, h, l, c)
    return bars


SMALL_BO = BreakoutParams(entry_period=3, exit_period=2, trend_period=3, atr_period=2, stop_atr=2.0)
SMALL_MR = MeanReversionParams(rsi_period=2, rsi_entry=10.0, trend_period=4, exit_period=2, atr_period=2,
                               stop_atr=3.0, max_hold_bars=3)
LONG_MR = MeanReversionParams(rsi_period=2, rsi_entry=10.0, trend_period=20, exit_period=2, atr_period=2,
                              stop_atr=3.0, max_hold_bars=3)
# 30-bar rally then four 1-point down closes: RSI(2) goes 50, 25, 12.5, 6.25 while price stays above SMA(20).
DIP_IN_UPTREND = [10 + i for i in range(30)] + [38, 37, 36, 35]
RALLY_IN_DOWNTREND = [40 - i for i in range(30)] + [12, 13, 14, 15]


def test_breakout_long_on_close_above_prior_channel_in_uptrend():
    bars = make_bars([10, 10.2, 10.4, 10.6, 10.8, 12.0])
    s = Breakout(bars, SMALL_BO)
    sig = s.entry_signal(5)
    assert sig is not None and sig.direction == LONG
    assert sig.stop_distance == pytest.approx(2.0 * s.atr[5])


def test_breakout_needs_close_beyond_channel():
    bars = make_bars([10, 10.2, 10.4, 10.6, 10.8, 11.0])
    assert Breakout(bars, SMALL_BO).entry_signal(5) is None


def test_breakout_short_on_close_below_channel_in_downtrend():
    bars = make_bars([12, 11.8, 11.6, 11.4, 11.2, 10.0])
    sig = Breakout(bars, SMALL_BO).entry_signal(5)
    assert sig is not None and sig.direction == SHORT


def test_breakout_respects_direction_switches():
    bars = make_bars([12, 11.8, 11.6, 11.4, 11.2, 10.0])
    params = BreakoutParams(entry_period=3, exit_period=2, trend_period=3, atr_period=2, allow_short=False)
    assert Breakout(bars, params).entry_signal(5) is None


def test_breakout_trend_filter_blocks_counter_trend_breakouts():
    # Close breaks the 3-bar high but stays under a long falling EMA.
    closes = [20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 10.1, 10.2, 11.5]
    params = BreakoutParams(entry_period=3, exit_period=2, trend_period=10, atr_period=2)
    s = Breakout(make_bars(closes), params)
    assert closes[13] > max(c + 0.5 for c in closes[10:13])
    assert s.entry_signal(13) is None


def test_breakout_no_signal_during_warmup():
    bars = make_bars([10, 10.2, 12.0])
    assert Breakout(bars, SMALL_BO).entry_signal(2) is None


def test_breakout_trailing_stop_only_ratchets_in_trade_direction():
    lows = [9, 9.5, 10, 9.8, 10.5]
    bars = make_bars([10, 10, 10, 10, 10], lows=lows, highs=[11] * 5)
    s = Breakout(bars, SMALL_BO)
    assert s.trail_stop(2, LONG, 8.0) == 9.5
    assert s.trail_stop(3, LONG, 9.9) == 9.9
    assert s.trail_stop(4, LONG, 9.0) == 9.8
    highs = [11, 10.5, 10.2, 10.4, 10.0]
    bars = make_bars([10] * 5, highs=highs, lows=[9] * 5)
    s = Breakout(bars, SMALL_BO)
    assert s.trail_stop(2, SHORT, 12.0) == 10.5
    assert s.trail_stop(4, SHORT, 10.3) == 10.3


def test_breakout_has_no_discretionary_exit():
    s = Breakout(make_bars([10] * 5), SMALL_BO)
    assert s.exit_signal(4, LONG, 100) is False


def test_meanrev_buys_oversold_dip_above_trend():
    bars = make_bars(DIP_IN_UPTREND)
    s = MeanReversion(bars, LONG_MR)
    assert s.rsi[32] == pytest.approx(12.5)
    assert s.entry_signal(32) is None
    assert s.rsi[33] == pytest.approx(6.25) and bars.close[33] > s.trend[33]
    sig = s.entry_signal(33)
    assert sig is not None and sig.direction == LONG
    assert sig.stop_distance == pytest.approx(3.0 * s.atr[33])


def test_meanrev_ignores_dips_below_trend():
    bars = make_bars([14, 13, 12, 11, 10, 9.5])
    assert MeanReversion(bars, SMALL_MR).entry_signal(5) is None


def test_meanrev_long_only_by_default():
    bars = make_bars(RALLY_IN_DOWNTREND)
    s = MeanReversion(bars, LONG_MR)
    assert s.rsi[33] == pytest.approx(93.75) and bars.close[33] < s.trend[33]
    assert s.entry_signal(33) is None
    shorting = MeanReversionParams(rsi_period=2, trend_period=20, exit_period=2, atr_period=2, allow_long=False,
                                   allow_short=True)
    sig = MeanReversion(bars, shorting).entry_signal(33)
    assert sig is not None and sig.direction == SHORT


def test_meanrev_exits_on_close_above_exit_average_or_time_stop():
    bars = make_bars([10, 10, 10, 10, 9, 11])
    s = MeanReversion(bars, SMALL_MR)
    assert s.exit_signal(4, LONG, 1) is False
    assert s.exit_signal(5, LONG, 2) is True
    assert s.exit_signal(4, LONG, 3) is True
    assert s.exit_signal(4, SHORT, 1) is True
    assert s.trail_stop(4, LONG, 7.5) == 7.5


def test_build_strategy_applies_overrides_and_rejects_unknown_names():
    bars = make_bars([10] * 5)
    s = build_strategy("breakout", bars, entry_period=7)
    assert isinstance(s, Breakout) and s.p.entry_period == 7
    assert isinstance(build_strategy("meanrev", bars), MeanReversion)
    with pytest.raises(ValueError, match="unknown strategy"):
        build_strategy("martingale", bars)


def test_default_parameters_match_the_expert_advisor_inputs():
    from pathlib import Path
    import re
    source = (Path(__file__).resolve().parents[2] / "mt5_agent" / "mql5" / "AgencyMT5Agent.mq5").read_text()

    def ea_input(name):
        return float(re.search(rf"input\s+\w+\s+{name}\s*=\s*([\d.]+)", source).group(1))

    bo, mr = BreakoutParams(), MeanReversionParams()
    assert (ea_input("InpBoEntryPeriod"), ea_input("InpBoExitPeriod"), ea_input("InpBoTrendPeriod"),
            ea_input("InpBoAtrPeriod"), ea_input("InpBoStopAtr")) == (
        bo.entry_period, bo.exit_period, bo.trend_period, bo.atr_period, bo.stop_atr)
    assert (ea_input("InpMrRsiPeriod"), ea_input("InpMrRsiEntry"), ea_input("InpMrTrendPeriod"),
            ea_input("InpMrExitPeriod"), ea_input("InpMrAtrPeriod"), ea_input("InpMrStopAtr"),
            ea_input("InpMrMaxHoldBars")) == (
        mr.rsi_period, mr.rsi_entry, mr.trend_period, mr.exit_period, mr.atr_period, mr.stop_atr, mr.max_hold_bars)
