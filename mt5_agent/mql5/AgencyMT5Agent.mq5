//+------------------------------------------------------------------+
//|                                               AgencyMT5Agent.mq5 |
//| Rules-based trading agent. Mirrors mt5_agent/strategy.py and the |
//| execution model in mt5_agent/backtest.py.                         |
//+------------------------------------------------------------------+
#property copyright   "Agency Agents"
#property version     "1.00"
#property description "Breakout (trend) and RSI(2) mean-reversion agent with risk-based sizing, daily loss limit and account drawdown kill switch."

#include <Trade\Trade.mqh>

enum ENUM_AGENT_STRATEGY
  {
   STRATEGY_BREAKOUT = 0, // Breakout: trend following (gold, oil)
   STRATEGY_MEANREV  = 1  // Mean reversion: RSI(2) dips in an uptrend (US500, NAS100)
  };

enum ENUM_AGENT_DIRECTION
  {
   DIRECTION_AUTO  = 0, // Auto: breakout both ways, mean reversion long only
   DIRECTION_LONG  = 1, // Long only
   DIRECTION_SHORT = 2, // Short only
   DIRECTION_BOTH  = 3  // Long and short
  };

input group "Strategy"
input ENUM_AGENT_STRATEGY  InpStrategy  = STRATEGY_MEANREV; // Strategy
input ENUM_TIMEFRAMES      InpTimeframe = PERIOD_D1;        // Signal timeframe (independent of the chart)
input ENUM_AGENT_DIRECTION InpDirection = DIRECTION_AUTO;   // Allowed direction

input group "Breakout"
input int    InpBoEntryPeriod = 55;  // Entry channel: close beyond the prior N-bar high/low
input int    InpBoExitPeriod  = 20;  // Trailing channel: stop follows the M-bar low/high
input int    InpBoTrendPeriod = 200; // Trend filter EMA period
input int    InpBoAtrPeriod   = 20;  // ATR period
input double InpBoStopAtr     = 2.0; // Initial stop, ATR multiples

input group "Mean reversion"
input int    InpMrRsiPeriod   = 2;    // RSI period
input double InpMrRsiEntry    = 10.0; // Buy when RSI is below this (short: above 100 - this)
input int    InpMrTrendPeriod = 200;  // Trend filter SMA period
input int    InpMrExitPeriod  = 5;    // Exit on the first close beyond this SMA
input int    InpMrAtrPeriod   = 20;   // ATR period
input double InpMrStopAtr     = 3.0;  // Protective stop, ATR multiples
input int    InpMrMaxHoldBars = 10;   // Time stop, bars

input group "Risk"
input double InpRiskPercent      = 1.0;   // Risk per trade, % of equity
input double InpMaxDailyLossPct  = 3.0;   // No new entries after losing this % today (0 = off)
input double InpMaxDrawdownPct   = 20.0;  // Close all and stop at this % below peak equity (0 = off)
input double InpMaxSpreadAtr     = 0.10;  // Wait while spread exceeds this fraction of ATR (0 = off)
input int    InpEntryWindowMin   = 240;   // Give up on a signal not filled within this many minutes
input int    InpExitWaitMin      = 60;    // Exit regardless of spread after this many minutes
input int    InpSlippagePoints   = 30;    // Max deviation, points
input bool   InpResetHalt        = false; // Clear a drawdown halt and restart the peak from current equity

input group "Identification"
input long   InpMagic   = 550055;           // Magic number (unique per strategy instance)
input string InpComment = "AgencyMT5Agent"; // Order comment

CTrade   g_trade;
int      g_hTrend = INVALID_HANDLE;
int      g_hExit  = INVALID_HANDLE;
int      g_hAtr   = INVALID_HANDLE;
int      g_hRsi   = INVALID_HANDLE;
datetime g_lastBar     = 0;
bool     g_entryArmed  = false;
int      g_armedDir    = 0;
double   g_armedStop   = 0.0;
int      g_entryTries  = 0;
bool     g_exitPending = false;
double   g_atr         = 0.0;

//+------------------------------------------------------------------+
//| Account-wide guard state, shared by every instance on the account |
//+------------------------------------------------------------------+
string GvName(const string key)
  {
   return StringFormat("AgencyMT5Agent.%I64d.%s", AccountInfoInteger(ACCOUNT_LOGIN), key);
  }

bool IsHalted()
  {
   return GlobalVariableCheck(GvName("halt")) && GlobalVariableGet(GvName("halt")) > 0.0;
  }

void UpdateAccountGuards()
  {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   string peakKey = GvName("peak");
   double peak = GlobalVariableCheck(peakKey) ? GlobalVariableGet(peakKey) : 0.0;
   if(equity > peak)
     {
      peak = equity;
      GlobalVariableSet(peakKey, peak);
     }

   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   double dayKey = now.year * 10000.0 + now.mon * 100.0 + now.day;
   if(!GlobalVariableCheck(GvName("day")) || GlobalVariableGet(GvName("day")) != dayKey)
     {
      GlobalVariableSet(GvName("day"), dayKey);
      GlobalVariableSet(GvName("day_start"), equity);
     }

   if(InpMaxDrawdownPct > 0.0 && !IsHalted() && equity <= peak * (1.0 - InpMaxDrawdownPct / 100.0))
     {
      GlobalVariableSet(GvName("halt"), 1.0);
      PrintFormat("HALT: equity %.2f is %.1f%% below peak %.2f. All agent instances stop; set InpResetHalt=true to resume.",
                  equity, 100.0 * (1.0 - equity / peak), peak);
     }
  }

bool DailyLossBlocked()
  {
   if(InpMaxDailyLossPct <= 0.0 || !GlobalVariableCheck(GvName("day_start")))
      return false;
   double start = GlobalVariableGet(GvName("day_start"));
   return AccountInfoDouble(ACCOUNT_EQUITY) <= start * (1.0 - InpMaxDailyLossPct / 100.0);
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
bool AllowLong()
  {
   return InpDirection == DIRECTION_LONG || InpDirection == DIRECTION_BOTH || InpDirection == DIRECTION_AUTO;
  }

bool AllowShort()
  {
   if(InpDirection == DIRECTION_AUTO)
      return InpStrategy == STRATEGY_BREAKOUT;
   return InpDirection == DIRECTION_SHORT || InpDirection == DIRECTION_BOTH;
  }

int Warmup()
  {
   if(InpStrategy == STRATEGY_BREAKOUT)
      return (int)MathMax(MathMax(InpBoTrendPeriod, InpBoEntryPeriod + 1), MathMax(InpBoAtrPeriod + 1, InpBoExitPeriod));
   return (int)MathMax(MathMax(InpMrTrendPeriod, InpMrExitPeriod), MathMax(InpMrRsiPeriod + 1, InpMrAtrPeriod + 1));
  }

bool ReadBuffer(const int handle, const int shift, double &value)
  {
   double buf[1];
   if(handle == INVALID_HANDLE || CopyBuffer(handle, 0, shift, 1, buf) != 1)
      return false;
   value = buf[0];
   return value != EMPTY_VALUE;
  }

bool SelectOwnPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return true;
     }
   return false;
  }

bool SpreadOK()
  {
   if(InpMaxSpreadAtr <= 0.0 || g_atr <= 0.0)
      return true;
   double spread = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
   return spread <= InpMaxSpreadAtr * g_atr;
  }

int VolumeDigits(const double step)
  {
   int digits = 0;
   double s = step;
   while(digits < 8 && MathAbs(s - MathRound(s)) > 1e-9)
     {
      s *= 10.0;
      digits++;
     }
   return digits;
  }

double LotsForRisk(const int dir, const double price, const double stopDist)
  {
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tickValue <= 0.0)
      tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(tickSize <= 0.0 || tickValue <= 0.0 || step <= 0.0 || stopDist <= 0.0)
      return 0.0;

   double riskMoney  = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPercent / 100.0;
   double lossPerLot = stopDist / tickSize * tickValue;
   double lots = MathFloor(riskMoney / lossPerLot / step) * step;
   lots = MathMin(lots, maxLot);

   double margin = 0.0;
   ENUM_ORDER_TYPE type = dir > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.9;
   if(lots >= minLot && OrderCalcMargin(type, _Symbol, lots, price, margin) && margin > freeMargin && margin > 0.0)
      lots = MathFloor(lots * freeMargin / margin / step) * step;

   // Never round up to the minimum lot: that would risk more than InpRiskPercent.
   if(lots < minLot)
      return 0.0;
   return NormalizeDouble(lots, VolumeDigits(step));
  }

//+------------------------------------------------------------------+
//| Signals (bar 1 = the bar that just closed)                        |
//+------------------------------------------------------------------+
bool EntrySignal(int &dir, double &stopDist)
  {
   double close1 = iClose(_Symbol, InpTimeframe, 1);
   double trend, atr;
   if(close1 <= 0.0 || !ReadBuffer(g_hTrend, 1, trend) || !ReadBuffer(g_hAtr, 1, atr) || atr <= 0.0)
      return false;
   g_atr = atr;

   if(InpStrategy == STRATEGY_BREAKOUT)
     {
      int hi = iHighest(_Symbol, InpTimeframe, MODE_HIGH, InpBoEntryPeriod, 2);
      int lo = iLowest(_Symbol, InpTimeframe, MODE_LOW, InpBoEntryPeriod, 2);
      if(hi < 0 || lo < 0)
         return false;
      if(AllowLong() && close1 > trend && close1 > iHigh(_Symbol, InpTimeframe, hi))
        {
         dir = 1;
         stopDist = InpBoStopAtr * atr;
         return true;
        }
      if(AllowShort() && close1 < trend && close1 < iLow(_Symbol, InpTimeframe, lo))
        {
         dir = -1;
         stopDist = InpBoStopAtr * atr;
         return true;
        }
      return false;
     }

   double rsi;
   if(!ReadBuffer(g_hRsi, 1, rsi))
      return false;
   if(AllowLong() && close1 > trend && rsi < InpMrRsiEntry)
     {
      dir = 1;
      stopDist = InpMrStopAtr * atr;
      return true;
     }
   if(AllowShort() && close1 < trend && rsi > 100.0 - InpMrRsiEntry)
     {
      dir = -1;
      stopDist = InpMrStopAtr * atr;
      return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Position management at the open of each new bar                   |
//+------------------------------------------------------------------+
void ManageOpenPosition()
  {
   ulong  ticket = (ulong)PositionGetInteger(POSITION_TICKET);
   long   type   = PositionGetInteger(POSITION_TYPE);
   double sl     = PositionGetDouble(POSITION_SL);
   double tp     = PositionGetDouble(POSITION_TP);
   int    dir    = type == POSITION_TYPE_BUY ? 1 : -1;

   if(InpStrategy == STRATEGY_MEANREV)
     {
      double close1 = iClose(_Symbol, InpTimeframe, 1);
      double exitMa;
      int held = iBarShift(_Symbol, InpTimeframe, (datetime)PositionGetInteger(POSITION_TIME), false);
      if(!ReadBuffer(g_hExit, 1, exitMa))
         return;
      bool exitNow = held >= InpMrMaxHoldBars || (dir > 0 ? close1 > exitMa : close1 < exitMa);
      if(exitNow)
        {
         g_exitPending = true;
         PrintFormat("%s exit signal: held %d bars, close %.5f vs SMA %.5f", _Symbol, held, close1, exitMa);
        }
      return;
     }

   int idx = dir > 0 ? iLowest(_Symbol, InpTimeframe, MODE_LOW, InpBoExitPeriod, 1)
                     : iHighest(_Symbol, InpTimeframe, MODE_HIGH, InpBoExitPeriod, 1);
   if(idx < 0)
      return;
   double level = dir > 0 ? iLow(_Symbol, InpTimeframe, idx) : iHigh(_Symbol, InpTimeframe, idx);
   level = NormalizeDouble(level, _Digits);
   bool tighter = dir > 0 ? (sl <= 0.0 || level > sl) : (sl <= 0.0 || level < sl);
   if(!tighter)
      return;

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double minGap = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 1) * _Point;
   bool crossed = dir > 0 ? level >= bid : level <= ask;
   if(crossed)
     {
      // Price already gapped through the new channel level: same as a stop filled at the open.
      if(!g_trade.PositionClose(ticket, InpSlippagePoints))
         PrintFormat("%s trailing close failed: %u %s", _Symbol, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
      return;
     }
   bool farEnough = dir > 0 ? bid - level >= minGap : level - ask >= minGap;
   if(farEnough && !g_trade.PositionModify(ticket, level, tp))
      PrintFormat("%s trailing stop to %.5f failed: %u %s", _Symbol, level, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
  }

bool OnNewBar()
  {
   if(Bars(_Symbol, InpTimeframe) < Warmup() + 2)
      return false;
   double atr;
   if(!ReadBuffer(g_hAtr, 1, atr))
      return false;
   g_atr = atr;

   g_entryArmed  = false;
   g_exitPending = false;
   g_entryTries  = 0;

   if(SelectOwnPosition())
     {
      ManageOpenPosition();
      return true;
     }
   if(IsHalted() || DailyLossBlocked())
      return true;

   int dir = 0;
   double stopDist = 0.0;
   if(EntrySignal(dir, stopDist) && stopDist > 0.0)
     {
      g_entryArmed = true;
      g_armedDir   = dir;
      g_armedStop  = stopDist;
      PrintFormat("%s %s signal, stop distance %.5f (%.1f ATR)", _Symbol, dir > 0 ? "BUY" : "SELL", stopDist, stopDist / atr);
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Execution                                                        |
//+------------------------------------------------------------------+
void TryExit()
  {
   if(!SelectOwnPosition())
     {
      g_exitPending = false;
      return;
     }
   if(!SpreadOK() && TimeCurrent() < g_lastBar + InpExitWaitMin * 60)
      return;
   ulong ticket = (ulong)PositionGetInteger(POSITION_TICKET);
   if(g_trade.PositionClose(ticket, InpSlippagePoints))
      g_exitPending = false;
   else
      PrintFormat("%s exit failed: %u %s", _Symbol, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
  }

void TryEntry()
  {
   if(TimeCurrent() >= g_lastBar + InpEntryWindowMin * 60)
     {
      PrintFormat("%s signal expired: spread stayed above %.2f ATR", _Symbol, InpMaxSpreadAtr);
      g_entryArmed = false;
      return;
     }
   if(!SpreadOK() || IsHalted() || DailyLossBlocked() || SelectOwnPosition())
      return;

   double price = g_armedDir > 0 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = NormalizeDouble(price - g_armedDir * g_armedStop, _Digits);
   double minGap = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 1) * _Point;
   if(g_armedStop < minGap)
     {
      PrintFormat("%s skipped: stop %.5f is inside the broker stops level", _Symbol, g_armedStop);
      g_entryArmed = false;
      return;
     }
   double lots = LotsForRisk(g_armedDir, price, g_armedStop);
   if(lots <= 0.0)
     {
      PrintFormat("%s skipped: %.2f%% risk is below the minimum lot for a %.5f stop (or not enough margin)",
                  _Symbol, InpRiskPercent, g_armedStop);
      g_entryArmed = false;
      return;
     }

   bool sent = g_armedDir > 0 ? g_trade.Buy(lots, _Symbol, 0.0, sl, 0.0, InpComment)
                              : g_trade.Sell(lots, _Symbol, 0.0, sl, 0.0, InpComment);
   uint code = g_trade.ResultRetcode();
   if(sent && (code == TRADE_RETCODE_DONE || code == TRADE_RETCODE_DONE_PARTIAL || code == TRADE_RETCODE_PLACED))
     {
      PrintFormat("%s %s %.2f lots at %.5f, SL %.5f", _Symbol, g_armedDir > 0 ? "BUY" : "SELL", lots, g_trade.ResultPrice(), sl);
      g_entryArmed = false;
      return;
     }
   PrintFormat("%s order failed: %u %s", _Symbol, code, g_trade.ResultRetcodeDescription());
   if(++g_entryTries >= 3)
      g_entryArmed = false;
  }

void CloseOwnPositions(const string reason)
  {
   while(SelectOwnPosition())
     {
      ulong ticket = (ulong)PositionGetInteger(POSITION_TICKET);
      if(!g_trade.PositionClose(ticket, InpSlippagePoints))
        {
         PrintFormat("%s close (%s) failed: %u %s", _Symbol, reason, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
         return;
        }
     }
  }

void ShowStatus()
  {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double peak = GlobalVariableCheck(GvName("peak")) ? GlobalVariableGet(GvName("peak")) : equity;
   Comment(StringFormat("AgencyMT5Agent | %s %s | risk %.2f%%\nEquity %.2f | peak %.2f | drawdown %.1f%%\n%s%s",
                        InpStrategy == STRATEGY_BREAKOUT ? "Breakout" : "Mean reversion", EnumToString(InpTimeframe),
                        InpRiskPercent, equity, peak, peak > 0.0 ? 100.0 * (1.0 - equity / peak) : 0.0,
                        IsHalted() ? "HALTED (max drawdown)" : (DailyLossBlocked() ? "Paused for today (daily loss limit)" : "Active"),
                        g_entryArmed ? " | entry pending" : ""));
  }

//+------------------------------------------------------------------+
//| Event handlers                                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpRiskPercent <= 0.0 || InpRiskPercent > 10.0)
     {
      Print("InpRiskPercent must be in (0, 10]");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpBoEntryPeriod < 1 || InpBoExitPeriod < 1 || InpBoTrendPeriod < 1 || InpBoAtrPeriod < 1 || InpBoStopAtr <= 0.0 ||
      InpMrRsiPeriod < 1 || InpMrTrendPeriod < 1 || InpMrExitPeriod < 1 || InpMrAtrPeriod < 1 || InpMrStopAtr <= 0.0 ||
      InpMrMaxHoldBars < 1)
     {
      Print("Strategy periods must be >= 1 and ATR multiples > 0");
      return INIT_PARAMETERS_INCORRECT;
     }

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpSlippagePoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   if(InpStrategy == STRATEGY_BREAKOUT)
     {
      g_hTrend = iMA(_Symbol, InpTimeframe, InpBoTrendPeriod, 0, MODE_EMA, PRICE_CLOSE);
      g_hAtr   = iATR(_Symbol, InpTimeframe, InpBoAtrPeriod);
     }
   else
     {
      g_hTrend = iMA(_Symbol, InpTimeframe, InpMrTrendPeriod, 0, MODE_SMA, PRICE_CLOSE);
      g_hExit  = iMA(_Symbol, InpTimeframe, InpMrExitPeriod, 0, MODE_SMA, PRICE_CLOSE);
      g_hRsi   = iRSI(_Symbol, InpTimeframe, InpMrRsiPeriod, PRICE_CLOSE);
      g_hAtr   = iATR(_Symbol, InpTimeframe, InpMrAtrPeriod);
      if(g_hExit == INVALID_HANDLE || g_hRsi == INVALID_HANDLE)
        {
         Print("Failed to create mean-reversion indicators");
         return INIT_FAILED;
        }
     }
   if(g_hTrend == INVALID_HANDLE || g_hAtr == INVALID_HANDLE)
     {
      Print("Failed to create indicators");
      return INIT_FAILED;
     }

   if(InpResetHalt)
     {
      GlobalVariableDel(GvName("halt"));
      GlobalVariableSet(GvName("peak"), AccountInfoDouble(ACCOUNT_EQUITY));
      Print("Drawdown halt cleared; peak equity restarted. Set InpResetHalt back to false.");
     }
   UpdateAccountGuards();
   ShowStatus();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_hTrend != INVALID_HANDLE)
      IndicatorRelease(g_hTrend);
   if(g_hExit != INVALID_HANDLE)
      IndicatorRelease(g_hExit);
   if(g_hAtr != INVALID_HANDLE)
      IndicatorRelease(g_hAtr);
   if(g_hRsi != INVALID_HANDLE)
      IndicatorRelease(g_hRsi);
   Comment("");
  }

void OnTick()
  {
   UpdateAccountGuards();
   if(IsHalted())
     {
      g_entryArmed = false;
      CloseOwnPositions("drawdown halt");
      return;
     }

   datetime bar = iTime(_Symbol, InpTimeframe, 0);
   if(bar == 0)
      return;
   if(bar != g_lastBar)
     {
      if(!OnNewBar())
         return;
      g_lastBar = bar;
      ShowStatus();
     }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
      return;
   if(g_exitPending)
      TryExit();
   if(g_entryArmed)
      TryEntry();
  }

double OnTester()
  {
   if(TesterStatistics(STAT_TRADES) < 20)
      return 0.0;
   return TesterStatistics(STAT_RECOVERY_FACTOR);
  }
//+------------------------------------------------------------------+
