"""`mt5-agent` command line: backtest the EA's rules on MT5-exported history."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from dataclasses import fields
from typing import Dict, List, Optional

from mt5_agent.backtest import Costs, Market, RiskConfig, run_backtest
from mt5_agent.data import load_csv, parse_time
from mt5_agent.metrics import compute_metrics
from mt5_agent.strategy import STRATEGIES, build_strategy


def _key_values(items: List[str], flag: str) -> Dict[str, str]:
    out = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        if not sep or not key or not value:
            raise SystemExit(f"{flag} expects KEY=VALUE, got {item!r}")
        out[key] = value
    return out


def _strategy_overrides(raw: Dict[str, str]) -> Dict[str, Dict[str, object]]:
    overrides: Dict[str, Dict[str, object]] = {name: {} for name in STRATEGIES}
    for dotted, value in raw.items():
        strategy, _, param = dotted.partition(".")
        if strategy not in STRATEGIES:
            raise SystemExit(f"--param: unknown strategy {strategy!r} in {dotted!r}")
        types = {f.name: f.type for f in fields(STRATEGIES[strategy][1])}
        if param not in types:
            raise SystemExit(f"--param: {strategy} has no parameter {param!r}; choose from {sorted(types)}")
        kind = types[param]
        if kind in (bool, "bool"):
            overrides[strategy][param] = value.lower() in ("1", "true", "yes", "on")
        elif kind in (int, "int"):
            overrides[strategy][param] = int(value)
        else:
            overrides[strategy][param] = float(value)
    return overrides


def cmd_backtest(args: argparse.Namespace) -> int:
    spreads = {k: float(v) for k, v in _key_values(args.spread, "--spread").items()}
    overrides = _strategy_overrides(_key_values(args.param, "--param"))
    start = parse_time(args.start) if args.start else None
    markets = []
    for symbol, strategy, path in args.market:
        bars = load_csv(path)
        if strategy not in STRATEGIES:
            raise SystemExit(f"--market {symbol}: unknown strategy {strategy!r}; choose from {sorted(STRATEGIES)}")
        markets.append(Market(symbol, bars, build_strategy(strategy, bars, **overrides[strategy]),
                              Costs(spreads.get(symbol, 0.0), args.swap)))

    result = run_backtest(markets, RiskConfig(args.risk, args.max_daily_loss, args.max_drawdown, args.max_positions),
                          args.equity)
    if start is not None:
        result.equity_curve = [(t, v) for t, v in result.equity_curve if t >= start]
        result.trades = [t for t in result.trades if t.entry_time >= start]
        if result.equity_curve:
            result.initial_equity = result.equity_curve[0][1]
    m = compute_metrics(result)

    rows = [
        ("Period", f"{m.start:%Y-%m-%d} .. {m.end:%Y-%m-%d} ({m.years:.1f} y)" if m.start else "no data"),
        ("Equity", f"{m.initial_equity:,.2f} -> {m.final_equity:,.2f}"),
        ("Total return", f"{m.total_return_pct:.2f}%"),
        ("CAGR", f"{m.cagr_pct:.2f}%"),
        ("Max drawdown", f"{m.max_drawdown_pct:.2f}%"),
        ("Sharpe (daily)", f"{m.sharpe:.2f}"),
        ("Trades", str(m.trades)),
        ("Win rate", f"{m.win_rate_pct:.1f}%"),
        ("Profit factor", f"{m.profit_factor:.2f}"),
        ("Avg / worst R", f"{m.avg_r:.3f} / {m.worst_r:.2f}"),
        ("Halted (max DD)", f"{result.halted_at:%Y-%m-%d}" if result.halted_at else "no"),
    ]
    width = max(len(k) for k, _ in rows)
    for key, value in rows:
        print(f"{key:<{width}}  {value}")

    if args.trades_csv:
        with open(args.trades_csv, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["symbol", "direction", "entry_time", "entry_price", "exit_time", "exit_price",
                             "units", "pnl", "r_multiple", "bars_held", "reason"])
            for t in result.trades:
                writer.writerow([t.symbol, "long" if t.direction > 0 else "short", f"{t.entry_time:%Y-%m-%d %H:%M}",
                                 t.entry_price, f"{t.exit_time:%Y-%m-%d %H:%M}", t.exit_price, round(t.units, 6),
                                 round(t.pnl, 2), round(t.r_multiple, 3), t.bars_held, t.reason])
        print(f"Trades written to {args.trades_csv}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mt5-agent", description="Backtest the AgencyMT5Agent EA rules on MT5 history.")
    parser.add_argument("--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Run a portfolio backtest on exported bars")
    bt.add_argument("--market", nargs=3, action="append", required=True, metavar=("SYMBOL", "STRATEGY", "CSV"),
                    help=f"one per symbol; STRATEGY is one of {sorted(STRATEGIES)}")
    bt.add_argument("--spread", action="append", metavar="SYMBOL=PRICE",
                    help="full bid/ask spread in price units, e.g. XAUUSD=0.35")
    bt.add_argument("--swap", type=float, default=3.0, help="annual financing cost on notional, %% (default 3)")
    bt.add_argument("--param", action="append", metavar="STRATEGY.NAME=VALUE",
                    help="override a strategy parameter, e.g. breakout.entry_period=55")
    bt.add_argument("--risk", type=float, default=1.0, help="risk per trade, %% of equity (default 1)")
    bt.add_argument("--max-daily-loss", type=float, default=3.0, help="no new entries after this daily loss, %%")
    bt.add_argument("--max-drawdown", type=float, default=20.0, help="close everything and stop at this drawdown, %%")
    bt.add_argument("--max-positions", type=int, default=0, help="cap on simultaneous positions (0 = none)")
    bt.add_argument("--equity", type=float, default=10_000.0)
    bt.add_argument("--start", help="report from this date (indicators still warm up on earlier bars)")
    bt.add_argument("--trades-csv", help="write every trade to this CSV")
    bt.set_defaults(func=cmd_backtest)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
