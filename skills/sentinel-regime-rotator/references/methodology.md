# Sentinel Regime Rotator — Methodology

## Thesis

Most crypto strategies optimize for upside and die in drawdowns. Sentinel inverts that: it
optimizes for **survival first**. The single most important number is **max drawdown**, not
headline return. A strategy that returns +15% with a 7% max drawdown is far more useful to a
real self-custody holder than one that returns +40% with a 60% drawdown they could never
actually hold through.

## Signals and their CMC sources

| Signal | Meaning | CMC MCP tool | Field |
|---|---|---|---|
| Fear & Greed (0–100) | Crowd sentiment; sets base posture | `get_global_metrics_latest` | fear & greed index |
| Funding rate | Perp positioning; extremes = unwind risk | `get_global_crypto_derivatives_metrics` | aggregate funding |
| Open interest Δ | Leverage build-up | `get_global_crypto_derivatives_metrics` | OI 24h change |
| Market RSI | Trend strength / over-extension | `get_crypto_marketcap_technical_analysis` | total mcap RSI |
| Market MACD | Momentum direction | `get_crypto_marketcap_technical_analysis` | MACD signal |
| Per-coin technicals | Confirm BTC/ETH trend | `get_crypto_technical_analysis` | RSI/MACD (id 1, 1027) |

## The algorithm (deterministic)

1. **Drawdown gates** (override all): ≥20% → HALT (0% risk-on); ≥12% → RISK_OFF (0%).
2. **Base posture from Fear & Greed**: ≤24 → 0%; 25–45 → 25%; 46–74 → 60%; ≥75 → 35%
   (extreme greed is trimmed, not chased — tops mean-revert).
3. **Trend modulation**: trend = mean(RSI mapped to [−1,1], MACD ±1, EMA ±1);
   `target = clamp(base + 0.25·trend, 0, 1)`.
4. **Crowded-funding damping**: if |funding| ≥ 5%, halve the target.
5. **Classify**: ≥0.55 RISK_ON; ≥0.20 NEUTRAL; else RISK_OFF.
6. **Allocate**: one rebalancing step per period toward the target (converge, don't lurch),
   bounded by per-trade and min-trade thresholds.

Full implementation: `scripts/regime.py`.

## Backtest design

`scripts/backtest.py` is event-driven: for each period it (a) marks drawdown from running
peak, (b) computes the regime decision on that period's signals, (c) executes at most one
rebalancing step with a 30 bps swap+gas friction, then (d) realizes that period's risk-on
return on held risk-on assets. It reports return, **max drawdown**, trade count, and a
100%-risk-on buy-and-hold benchmark.

### Sample-data result (`assets/sample_signals.csv`, 24 periods, full cycle)

```
Return: +14.9%   (buy & hold -1.7%)
Max drawdown: 6.6%   (PASS vs 30% gate)   |   15 trades
```

## Running on real CMC history (recommended for validation)

The sample CSV is a hand-built market cycle to illustrate behavior. To validate on real data,
export CMC historical series into the same columns and re-run:

- **Fear & Greed history** — CMC Market API fear-and-greed historical endpoint.
- **Derivatives funding history** — CMC derivatives metrics (or per-exchange funding).
- **Market RSI/MACD** — derive from CMC global market-cap OHLCV history, or use CMC's
  technical-analysis outputs sampled over time.
- **risk_on_return** — next-period return of an equal-weight basket of the risk-on tokens
  (ETH/CAKE/LINK/UNI/DOT) from CMC OHLCV.

## Honest limitations

- The sample backtest is illustrative, not a validated historical edge; treat the +14.9% as a
  behavior demonstration, not a performance claim. Real-history results will differ.
- Single rebalancing step per period is deliberate (legibility, gas) but slows convergence in
  fast moves.
- Signals are coincident-to-lagging; the strategy trades robustness for timing precision by
  design. The drawdown gate is the backstop when timing is wrong.
- No leverage, spot only — a conscious choice to keep drawdown bounded.

## Why this is a good fit for a self-custody user

It is the rare strategy you could actually leave running on your own keys: bounded downside,
every decision explained in plain English, and a hard drawdown gate that prioritizes not
blowing up over squeezing out the last few percent.
