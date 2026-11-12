"""Indicators reproducing MetaTrader 5's built-in formulas, so the Python backtest and the EA agree."""

from __future__ import annotations

from typing import List, Optional, Sequence

Series = List[Optional[float]]


def sma(values: Sequence[float], period: int) -> Series:
    out: Series = [None] * len(values)
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= period:
            total -= values[i - period]
        if i >= period - 1:
            out[i] = total / period
    return out


def ema(values: Sequence[float], period: int) -> Series:
    # iMA(MODE_EMA) seeds with the first price; values before `period` bars are still warming up.
    out: Series = [None] * len(values)
    if not values:
        return out
    k = 2.0 / (period + 1.0)
    prev = values[0]
    for i, v in enumerate(values):
        prev = v if i == 0 else v * k + prev * (1.0 - k)
        if i >= period - 1:
            out[i] = prev
    return out


def true_range(high: Sequence[float], low: Sequence[float], close: Sequence[float]) -> List[float]:
    tr = []
    for i in range(len(close)):
        if i == 0:
            tr.append(high[0] - low[0])
        else:
            tr.append(max(high[i], close[i - 1]) - min(low[i], close[i - 1]))
    return tr


def atr(high: Sequence[float], low: Sequence[float], close: Sequence[float], period: int) -> Series:
    # MT5's iATR is a simple average of true range (not Wilder smoothing), first defined at index `period`.
    tr = true_range(high, low, close)
    out: Series = [None] * len(tr)
    for i in range(period, len(tr)):
        out[i] = sum(tr[i - period + 1:i + 1]) / period
    return out


def rsi(values: Sequence[float], period: int) -> Series:
    # Same seeding and Wilder recursion as MT5's RSI.mq5, including its 100/50 conventions when losses are zero.
    n = len(values)
    out: Series = [None] * n
    if n <= period:
        return out

    def _value(gain: float, loss: float) -> float:
        if loss != 0.0:
            return 100.0 - 100.0 / (1.0 + gain / loss)
        return 100.0 if gain != 0.0 else 50.0

    gain = loss = 0.0
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gain += diff if diff > 0 else 0.0
        loss += -diff if diff < 0 else 0.0
    gain /= period
    loss /= period
    out[period] = _value(gain, loss)
    for i in range(period + 1, n):
        diff = values[i] - values[i - 1]
        gain = (gain * (period - 1) + (diff if diff > 0 else 0.0)) / period
        loss = (loss * (period - 1) + (-diff if diff < 0 else 0.0)) / period
        out[i] = _value(gain, loss)
    return out


def highest(values: Sequence[float], end: int, period: int) -> Optional[float]:
    """Max of the `period` values ending just before index `end`."""
    start = end - period
    if start < 0:
        return None
    return max(values[start:end])


def lowest(values: Sequence[float], end: int, period: int) -> Optional[float]:
    """Min of the `period` values ending just before index `end`."""
    start = end - period
    if start < 0:
        return None
    return min(values[start:end])
