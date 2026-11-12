"""Performance statistics for a BacktestResult."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from mt5_agent.backtest import BacktestResult


@dataclass(frozen=True)
class Metrics:
    start: Optional[datetime]
    end: Optional[datetime]
    years: float
    initial_equity: float
    final_equity: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe: float
    trades: int
    win_rate_pct: float
    profit_factor: float
    avg_r: float
    worst_r: float


def max_drawdown_pct(equity: Sequence[float]) -> float:
    peak, worst = -math.inf, 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst * 100.0


def _daily_returns(curve: Sequence[Tuple[datetime, float]]) -> List[float]:
    closes = {}
    for t, value in curve:
        closes[t.date()] = value
    values = [closes[d] for d in sorted(closes)]
    return [values[k] / values[k - 1] - 1.0 for k in range(1, len(values)) if values[k - 1] > 0]


def sharpe_ratio(curve: Sequence[Tuple[datetime, float]], periods_per_year: int = 252) -> float:
    rets = _daily_returns(curve)
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return 0.0 if var <= 0 else mean / math.sqrt(var) * math.sqrt(periods_per_year)


def compute_metrics(result: BacktestResult) -> Metrics:
    curve = result.equity_curve
    start = curve[0][0] if curve else None
    end = curve[-1][0] if curve else None
    final = curve[-1][1] if curve else result.initial_equity
    years = (end - start).days / 365.25 if curve else 0.0
    growth = final / result.initial_equity
    cagr = (growth ** (1.0 / years) - 1.0) * 100.0 if years > 0 and growth > 0 else 0.0

    pnls = [t.pnl for t in result.trades]
    wins = [p for p in pnls if p > 0]
    gross_win = sum(wins)
    gross_loss = -sum(p for p in pnls if p < 0)
    rs = [t.r_multiple for t in result.trades]
    return Metrics(
        start=start, end=end, years=years,
        initial_equity=result.initial_equity, final_equity=final,
        total_return_pct=(growth - 1.0) * 100.0, cagr_pct=cagr,
        max_drawdown_pct=max_drawdown_pct([v for _, v in curve]),
        sharpe=sharpe_ratio(curve),
        trades=len(pnls),
        win_rate_pct=100.0 * len(wins) / len(pnls) if pnls else 0.0,
        profit_factor=gross_win / gross_loss if gross_loss > 0 else (math.inf if gross_win > 0 else 0.0),
        avg_r=sum(rs) / len(rs) if rs else 0.0,
        worst_r=min(rs) if rs else 0.0,
    )
