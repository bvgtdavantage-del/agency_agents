# mt5_agent — rules-based MetaTrader 5 trading agent

Two parts that implement the same rules:

| Part | File | Runs where | Purpose |
|---|---|---|---|
| Expert Advisor | `mql5/AgencyMT5Agent.mq5` | MetaTrader 5 terminal (Windows, or a VPS) | Live/demo trading |
| Backtester + CLI | `mt5_agent/*.py`, `mt5-agent` | Any OS, Python ≥ 3.9, stdlib only | Verify the rules on history exported from MT5 |

The EA compiles with MetaEditor build 6257 with 0 errors and 0 warnings.

## Strategies

Both act once per closed bar of the signal timeframe (default D1). Entries go in at the next bar's open.

**Breakout** (trend following, for gold and oil)
- Long when the close is above the prior 55-bar high **and** above EMA(200). Short is the mirror image.
- Initial stop is 2 × ATR(20). It then trails the 20-bar low (high for shorts) and only ever tightens.
- This is the classic Turtle "System 2" with a trend filter. The parameters were not optimised.

**Mean reversion** (for US500 and NAS100, long only)
- Buy when RSI(2) < 10 **and** the close is above SMA(200).
- Exit at the next open after the first close above SMA(5), or after 10 bars.
- A protective stop sits at 3 × ATR(20).
- These are Connors' published RSI(2) rules, unchanged.

**Risk controls** (EA and backtester)
- **Position size:** risk % of equity ÷ stop distance. Volume is rounded **down** to the lot step. If even the minimum lot would risk more than the setting, the trade is skipped rather than oversized.
- **Daily loss limit:** after a 3 % loss on the day, no new entries until the next server day.
- **Drawdown kill switch:** at 20 % below peak equity, every instance on the account closes its positions and stops. Instances share the state through terminal global variables. Resume with `InpResetHalt = true`.
- **Spread filter:** an entry waits while the spread is above 0.10 × ATR. This avoids rollover spreads at the daily open. A signal that isn't filled within 240 minutes is dropped.
- **Banned:** no martingale, no grid, no averaging down, and no adding to positions.

## Validation on real data

- **Data:** OANDA M1 mid prices, 2005-01 to 2020-05, resampled to D1 on New York 17:00 server time.
- **Costs:** spreads of US500 0.6, NAS100 1.5, XAUUSD 0.35, USOIL 0.04, plus 3 %/yr financing on notional for every day held, long or short.
- **Fills:** a stop that gaps fills at the open. Entry and stop in the same bar counts as a loss.

The portfolio is mean reversion on US500 and NAS100 plus breakout on XAUUSD and USOIL:

| Risk/trade | Period | CAGR | Max DD | Sharpe | Trades | Win % | PF |
|---|---|---|---|---|---|---|---|
| 1 % | 2005–2014 | 5.8 % | 7.5 % | 0.80 | 223 | 61 | 2.03 |
| 1 % | 2015–2020 | 4.4 % | 8.9 % | 0.63 | 142 | 60 | 1.57 |
| 2 % | 2005–2014 | 11.1 % | 14.0 % | 0.81 | 223 | 61 | 1.99 |
| 2 % | 2015–2020 | 8.9 % | 16.2 % | 0.68 | 141 | 60 | 1.62 |

At 1 % risk, 2 of 16 calendar years lost money: 2016 −0.5 % and 2017 −0.9 %.

What this shows, and what it doesn't:
- **Parameter robustness:** the mean-reversion edge holds on both US indices across every variant tried (RSI threshold 5/10/15, exit SMA 5/10, stop 2/3/4 ATR), in both periods.
- **Breakout:** it is positive on gold and oil in both periods, but that is only two markets and about 50 trades each.
- **Breakout markets that failed:** the same breakout **lost money on FX majors and on equity indices from 2015 to 2020**. That is why the defaults pair each strategy with its market class.
- **Selection bias:** the market-to-strategy pairing was chosen after seeing these results. Treat 2015–2020 as a sanity check, not a clean out-of-sample test.
- **Untested period:** 2020-05 to today. Run the Strategy Tester on your broker's data, as described below, before committing money.
- **Returns scale with capital:** about 5–10 %/yr means 500–1,000 a year on 10,000.

## Installing the EA

1. **Copy the file.** In MetaTrader 5, open File → Open Data Folder and copy `AgencyMT5Agent.mq5` to `MQL5/Experts/`.
2. **Compile it.** Open it in MetaEditor (F4) and press Compile (F7). Expect `0 errors, 0 warnings`.
3. **Allow trading.** In Tools → Options → Expert Advisors, tick "Allow algorithmic trading", then turn on the **Algo Trading** button in the toolbar.
4. **Attach one instance per symbol.** Any chart timeframe works, because the EA reads `InpTimeframe`. Give each instance a **different `InpMagic`**:

| Chart symbol | InpStrategy | InpMagic |
|---|---|---|
| US500 / US500.cash / SPX500 | Mean reversion | 550001 |
| NAS100 / USTEC / US100 | Mean reversion | 550002 |
| XAUUSD | Breakout | 550003 |
| USOIL / XTIUSD / WTI | Breakout | 550004 |

5. **Set the risk.** Use `InpRiskPercent` 0.5–1 % on a new account; the table above shows what 2 % implies. Leave the daily-loss and drawdown limits on.
6. **Run it continuously.** It needs a terminal running 24/5; a VPS near the broker is best. Prefer a broker on **New York close** server time (GMT+2/+3), which gives five D1 bars a week. A GMT+0 server produces Sunday bars that change the daily indicators.

## Verifying on your broker's data (do this first)

**Strategy Tester (Ctrl+R)**
1. Choose AgencyMT5Agent, the symbol, and "Every tick based on real ticks" (or "1 minute OHLC").
2. Set the period to the last 3–5 years and the deposit to your planned size.
3. Use the same inputs as above. The **OnTester** criterion reports the recovery factor and needs at least 20 trades.
4. Run it for each symbol separately; Strategy Tester runs one symbol per test.

**Python backtester on MT5 history**
1. Export the history: open the Symbols window (Ctrl+U), go to the Bars tab, pick D1, then Request and Export.
2. Run:

```bash
pip install -e .
mt5-agent backtest \
  --market US500 meanrev US500_D1.csv \
  --market NAS100 meanrev NAS100_D1.csv \
  --market XAUUSD breakout XAUUSD_D1.csv \
  --market USOIL breakout USOIL_D1.csv \
  --spread US500=0.6 --spread NAS100=1.5 --spread XAUUSD=0.35 --spread USOIL=0.04 \
  --risk 1 --trades-csv trades.csv
```

- `--param breakout.entry_period=40` overrides one parameter. `--start 2021-01-01` reports only a recent window, while indicators still warm up on the earlier bars.
- The Python indicators reproduce MT5's built-ins: EMA is seeded with the first price, ATR is a **simple** average of true range (not Wilder), and RSI uses Wilder smoothing with MT5's seeding. That way the backtest and the EA see the same values.

## Known differences between the backtest and the EA

- **Fill timing:** the backtest fills at the bar open. The EA fills at the first tick after the open where the spread is acceptable, which is usually seconds to minutes later.
- **Halt timing:** the backtest checks drawdown and daily loss on bar closes. The EA checks them on every tick, so it halts sooner.
- **Lot sizes:** the backtest uses fractional size. The EA rounds down to the broker's lot step, so small accounts risk a little less than the setting, or skip the trade.
