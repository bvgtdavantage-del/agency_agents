"""Indicator values must match MetaTrader 5's built-ins, computed by hand from their published formulas."""

import pytest

from mt5_agent import indicators as ind


def test_sma_warms_up_then_averages_window():
    assert ind.sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_ema_seeds_with_first_price_like_ima():
    assert ind.ema([1, 2, 3, 4], 3) == [None, None, 2.25, 3.125]


def test_ema_of_empty_series():
    assert ind.ema([], 5) == []


def test_true_range_uses_previous_close_for_gaps():
    tr = ind.true_range([10, 11, 12, 11], [9, 10, 10, 9], [9.5, 10.5, 11, 10])
    assert tr == [1, 1.5, 2, 2]


def test_atr_is_simple_average_of_true_range_not_wilder():
    out = ind.atr([10, 11, 12, 11], [9, 10, 10, 9], [9.5, 10.5, 11, 10], 2)
    assert out[:2] == [None, None]
    assert out[2] == pytest.approx(1.75)
    assert out[3] == pytest.approx(2.0)


def test_rsi_follows_mt5_seed_and_wilder_recursion():
    out = ind.rsi([1, 2, 3, 2, 4], 2)
    assert out[:2] == [None, None]
    assert out[2] == pytest.approx(100.0)
    assert out[3] == pytest.approx(50.0)
    assert out[4] == pytest.approx(100.0 - 100.0 / 6.0)


def test_rsi_flat_series_is_fifty():
    assert ind.rsi([5, 5, 5, 5], 2)[2:] == [50.0, 50.0]


def test_rsi_too_short_is_all_none():
    assert ind.rsi([1, 2], 2) == [None, None]


def test_highest_and_lowest_exclude_the_end_index():
    values = [3, 9, 1, 7, 5]
    assert ind.highest(values, 4, 3) == 9
    assert ind.lowest(values, 4, 3) == 1
    assert ind.highest(values, 5, 2) == 7
    assert ind.highest(values, 2, 3) is None
    assert ind.lowest(values, 2, 3) is None
