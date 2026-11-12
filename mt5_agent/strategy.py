"""Signal rules shared by the Python backtester and the MQL5 Expert Advisor (mql5/AgencyMT5Agent.mq5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from mt5_agent import indicators as ind
from mt5_agent.data import Bars

LONG = 1
SHORT = -1


@dataclass(frozen=True)
class Entry:
    direction: int
    stop_distance: float


@dataclass(frozen=True)
class BreakoutParams:
    entry_period: int = 55
    exit_period: int = 20
    trend_period: int = 200
    atr_period: int = 20
    stop_atr: float = 2.0
    allow_long: bool = True
    allow_short: bool = True


@dataclass(frozen=True)
class MeanReversionParams:
    rsi_period: int = 2
    rsi_entry: float = 10.0
    trend_period: int = 200
    exit_period: int = 5
    atr_period: int = 20
    stop_atr: float = 3.0
    max_hold_bars: int = 10
    allow_long: bool = True
    allow_short: bool = False


class Breakout:
    """Close beyond the prior N-bar channel in the direction of the EMA trend; trail on the opposite M-bar channel."""

    name = "breakout"

    def __init__(self, bars: Bars, params: BreakoutParams = BreakoutParams()):
        self.bars = bars
        self.p = params
        self.trend = ind.ema(bars.close, params.trend_period)
        self.atr = ind.atr(bars.high, bars.low, bars.close, params.atr_period)
        self.warmup = max(params.trend_period, params.entry_period + 1, params.atr_period + 1, params.exit_period)

    def entry_signal(self, i: int) -> Optional[Entry]:
        if i < self.warmup:
            return None
        b, p = self.bars, self.p
        close, trend, vol = b.close[i], self.trend[i], self.atr[i]
        if p.allow_long and close > trend and close > ind.highest(b.high, i, p.entry_period):
            return Entry(LONG, p.stop_atr * vol)
        if p.allow_short and close < trend and close < ind.lowest(b.low, i, p.entry_period):
            return Entry(SHORT, p.stop_atr * vol)
        return None

    def trail_stop(self, i: int, direction: int, stop: float) -> float:
        if direction == LONG:
            return max(stop, ind.lowest(self.bars.low, i + 1, self.p.exit_period))
        return min(stop, ind.highest(self.bars.high, i + 1, self.p.exit_period))

    def exit_signal(self, i: int, direction: int, bars_held: int) -> bool:
        return False


class MeanReversion:
    """Buy short-term oversold dips (RSI) inside a long-term uptrend (SMA); exit on the first close above a short SMA."""

    name = "meanrev"

    def __init__(self, bars: Bars, params: MeanReversionParams = MeanReversionParams()):
        self.bars = bars
        self.p = params
        self.trend = ind.sma(bars.close, params.trend_period)
        self.exit_ma = ind.sma(bars.close, params.exit_period)
        self.rsi = ind.rsi(bars.close, params.rsi_period)
        self.atr = ind.atr(bars.high, bars.low, bars.close, params.atr_period)
        self.warmup = max(params.trend_period, params.exit_period, params.rsi_period + 1, params.atr_period + 1)

    def entry_signal(self, i: int) -> Optional[Entry]:
        if i < self.warmup:
            return None
        p = self.p
        close, trend, osc = self.bars.close[i], self.trend[i], self.rsi[i]
        if p.allow_long and close > trend and osc < p.rsi_entry:
            return Entry(LONG, p.stop_atr * self.atr[i])
        if p.allow_short and close < trend and osc > 100.0 - p.rsi_entry:
            return Entry(SHORT, p.stop_atr * self.atr[i])
        return None

    def trail_stop(self, i: int, direction: int, stop: float) -> float:
        return stop

    def exit_signal(self, i: int, direction: int, bars_held: int) -> bool:
        if bars_held >= self.p.max_hold_bars:
            return True
        close = self.bars.close[i]
        return close > self.exit_ma[i] if direction == LONG else close < self.exit_ma[i]


STRATEGIES = {
    Breakout.name: (Breakout, BreakoutParams),
    MeanReversion.name: (MeanReversion, MeanReversionParams),
}


def build_strategy(name: str, bars: Bars, **overrides):
    try:
        cls, params_cls = STRATEGIES[name]
    except KeyError:
        raise ValueError(f"unknown strategy {name!r}; choose from {sorted(STRATEGIES)}") from None
    return cls(bars, params_cls(**overrides))
