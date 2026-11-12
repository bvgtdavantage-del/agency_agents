"""Portfolio backtester that executes the strategy rules the same way the EA does on a live MT5 account.

Execution model (bars are mid prices):
- a signal on the close of bar i is filled at the open of bar i+1, buying at the ask and selling at the bid;
- stops are resting orders: a gap through the stop fills at the open, otherwise at the stop price;
- a position opened and stopped within the same bar is counted as a loss (worst case);
- size = risk% of marked-to-market equity / stop distance, so a stop-out loses about risk% plus the spread;
- financing (swap) is charged on notional for every calendar day held.
P&L is computed in account currency per unit of price, so FX-denominated instruments need no conversion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from mt5_agent.data import Bars
from mt5_agent.strategy import LONG, Entry

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Costs:
    spread: float = 0.0
    swap_annual_pct: float = 0.0


@dataclass
class Market:
    symbol: str
    bars: Bars
    strategy: object
    costs: Costs = field(default_factory=Costs)


@dataclass(frozen=True)
class RiskConfig:
    risk_pct: float = 0.5
    max_daily_loss_pct: float = 3.0
    max_drawdown_pct: float = 20.0
    max_positions: int = 0


@dataclass
class Position:
    symbol: str
    direction: int
    entry_index: int
    entry_time: datetime
    entry_price: float
    units: float
    stop: float
    risk_amount: float
    swap_paid: float = 0.0
    swap_until: Optional[datetime] = None
    exit_pending: bool = False


@dataclass(frozen=True)
class Trade:
    symbol: str
    direction: int
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    units: float
    pnl: float
    r_multiple: float
    bars_held: int
    reason: str


@dataclass
class BacktestResult:
    initial_equity: float
    equity_curve: List[Tuple[datetime, float]]
    trades: List[Trade]
    halted_at: Optional[datetime] = None


class _Book:
    def __init__(self, initial_equity: float):
        self.cash = initial_equity
        self.positions: Dict[str, Position] = {}
        self.last_close: Dict[str, Tuple[float, float]] = {}
        self.trades: List[Trade] = []

    def equity(self) -> float:
        total = self.cash
        for sym, pos in self.positions.items():
            close, half = self.last_close.get(sym, (pos.entry_price, 0.0))
            total += (close - pos.direction * half - pos.entry_price) * pos.direction * pos.units
        return total

    def close(self, pos: Position, price: float, when: datetime, index: int, reason: str) -> None:
        gross = (price - pos.entry_price) * pos.direction * pos.units
        self.cash += gross
        net = gross - pos.swap_paid
        self.trades.append(Trade(
            symbol=pos.symbol, direction=pos.direction, entry_time=pos.entry_time,
            entry_price=pos.entry_price, exit_time=when, exit_price=price, units=pos.units,
            pnl=net, r_multiple=net / pos.risk_amount if pos.risk_amount else 0.0,
            bars_held=index - pos.entry_index + 1, reason=reason,
        ))
        del self.positions[pos.symbol]


def run_backtest(markets: List[Market], risk: RiskConfig = RiskConfig(),
                 initial_equity: float = 10_000.0) -> BacktestResult:
    symbols = [m.symbol for m in markets]
    if len(set(symbols)) != len(symbols):
        raise ValueError("each market needs a unique symbol")

    book = _Book(initial_equity)
    lookup = [{t: i for i, t in enumerate(m.bars.time)} for m in markets]
    timeline = sorted({t for m in markets for t in m.bars.time})
    pending: Dict[str, Entry] = {}
    curve: List[Tuple[datetime, float]] = []
    peak = day_start = initial_equity
    day = None
    halted_at: Optional[datetime] = None

    for t in timeline:
        if t.date() != day:
            day = t.date()
            day_start = book.equity()
        for k, m in enumerate(markets):
            i = lookup[k].get(t)
            if i is None:
                continue
            _process_bar(book, m, i, pending, risk, day_start, halted_at is not None)
        equity = book.equity()
        peak = max(peak, equity)
        if halted_at is None and risk.max_drawdown_pct and equity <= peak * (1 - risk.max_drawdown_pct / 100.0):
            halted_at = t
            pending.clear()
            for pos in book.positions.values():
                pos.exit_pending = True
            log.info("drawdown limit hit at %s: equity %.2f, peak %.2f", t, equity, peak)
        curve.append((t, equity))

    for m in markets:
        pos = book.positions.get(m.symbol)
        if pos is not None:
            last = len(m.bars) - 1
            half = m.costs.spread / 2.0
            book.close(pos, m.bars.close[last] - pos.direction * half, m.bars.time[last], last, "end_of_data")
    if curve:
        curve[-1] = (curve[-1][0], book.cash)
    return BacktestResult(initial_equity, curve, book.trades, halted_at)


def _process_bar(book: _Book, m: Market, i: int, pending: Dict[str, Entry], risk: RiskConfig,
                 day_start: float, halted: bool) -> None:
    b, strat = m.bars, m.strategy
    t, half = b.time[i], m.costs.spread / 2.0
    pos = book.positions.get(m.symbol)

    if pos is not None and pos.exit_pending:
        book.close(pos, b.open[i] - pos.direction * half, t, i, "halt" if halted else "signal")
        pos = None

    entry = pending.pop(m.symbol, None)
    if entry is not None and pos is None and not halted:
        price = b.open[i] + entry.direction * half
        risk_amount = book.equity() * risk.risk_pct / 100.0
        pos = Position(
            symbol=m.symbol, direction=entry.direction, entry_index=i, entry_time=t, entry_price=price,
            units=risk_amount / entry.stop_distance, stop=price - entry.direction * entry.stop_distance,
            risk_amount=risk_amount, swap_until=t,
        )
        book.positions[m.symbol] = pos

    if pos is not None:
        if pos.direction == LONG:
            at_open, extreme = b.open[i] - half, b.low[i] - half
            gapped, touched = at_open <= pos.stop, extreme <= pos.stop
        else:
            at_open, extreme = b.open[i] + half, b.high[i] + half
            gapped, touched = at_open >= pos.stop, extreme >= pos.stop
        if gapped or touched:
            book.close(pos, at_open if gapped else pos.stop, t, i, "stop")
            pos = None

    book.last_close[m.symbol] = (b.close[i], half)

    if pos is not None:
        days = (t - pos.swap_until).days
        if days > 0 and m.costs.swap_annual_pct:
            fee = pos.units * b.close[i] * m.costs.swap_annual_pct / 100.0 / 365.0 * days
            book.cash -= fee
            pos.swap_paid += fee
        pos.swap_until = t
        pos.stop = strat.trail_stop(i, pos.direction, pos.stop)
        if strat.exit_signal(i, pos.direction, i - pos.entry_index + 1):
            pos.exit_pending = True
        return

    if halted:
        return
    signal = strat.entry_signal(i)
    if signal is None or signal.stop_distance <= 0:
        return
    if risk.max_daily_loss_pct and book.equity() <= day_start * (1 - risk.max_daily_loss_pct / 100.0):
        return
    if risk.max_positions and len(book.positions) + len(pending) >= risk.max_positions:
        return
    pending[m.symbol] = signal
