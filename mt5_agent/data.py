"""OHLC bar container and CSV loading for MT5 history exports and generic OHLC files."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Union

_TIME_FORMATS = (
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y.%m.%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
)


@dataclass
class Bars:
    time: List[datetime] = field(default_factory=list)
    open: List[float] = field(default_factory=list)
    high: List[float] = field(default_factory=list)
    low: List[float] = field(default_factory=list)
    close: List[float] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.close)

    def append(self, t: datetime, o: float, h: float, l: float, c: float) -> None:
        self.time.append(t)
        self.open.append(o)
        self.high.append(h)
        self.low.append(l)
        self.close.append(c)

    def since(self, start: datetime) -> "Bars":
        out = Bars()
        for i, t in enumerate(self.time):
            if t >= start:
                out.append(t, self.open[i], self.high[i], self.low[i], self.close[i])
        return out


def parse_time(text: str) -> datetime:
    text = text.strip()
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {text!r}")


def _normalise(name: str) -> str:
    return name.strip().strip("<>").lower()


def load_csv(path: Union[str, Path]) -> Bars:
    """Load bars from an MT5 'Export bars' file (tab-separated, <DATE>/<TIME> columns) or a CSV with time/open/high/low/close."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as fh:
        sample = fh.readline()
        fh.seek(0)
        delimiter = "\t" if "\t" in sample else ("," if "," in sample else ";")
        reader = csv.reader(fh, delimiter=delimiter)
        header = [_normalise(h) for h in next(reader)]
        col = {name: idx for idx, name in enumerate(header)}
        missing = [c for c in ("open", "high", "low", "close") if c not in col]
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")
        time_col = col.get("time", col.get("datetime", col.get("date")))
        if time_col is None:
            raise ValueError(f"{path}: no time/date column")
        split_date_time = "date" in col and "time" in col
        rows = []
        for row in reader:
            if not row or not row[0].strip():
                continue
            stamp = f"{row[col['date']]} {row[col['time']]}" if split_date_time else row[time_col]
            rows.append((parse_time(stamp), float(row[col["open"]]), float(row[col["high"]]),
                         float(row[col["low"]]), float(row[col["close"]])))
    rows.sort(key=lambda r: r[0])
    bars = Bars()
    for r in rows:
        bars.append(*r)
    return bars
