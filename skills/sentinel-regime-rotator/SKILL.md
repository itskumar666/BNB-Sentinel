---
name: sentinel-regime-rotator
description: |
  Capital-preservation-first crypto regime strategy. Turns CoinMarketCap market data
  (Fear & Greed, derivatives funding, market RSI/MACD) into a risk-on / risk-off allocation
  with explicit entry/exit rules and a plain-English rationale — engineered to sidestep
  large drawdowns, not to chase tops. Includes a runnable, backtestable spec.
  Use when a user asks whether to be risk-on or risk-off, how to position a crypto portfolio,
  for a market regime read, a rotation signal, or a backtestable allocation strategy.
  Trigger: "risk on or risk off", "should I buy or sell crypto", "market regime",
  "rotation signal", "how should I position", "sentinel", "/sentinel"
license: MIT
compatibility: ">=1.0.0"
user-invocable: true
allowed-tools:
  - mcp__cmc-mcp__get_global_metrics_latest
  - mcp__cmc-mcp__get_global_crypto_derivatives_metrics
  - mcp__cmc-mcp__get_crypto_marketcap_technical_analysis
  - mcp__cmc-mcp__get_crypto_technical_analysis
  - mcp__cmc-mcp__trending_crypto_narratives
  - mcp__cmc-mcp__search_cryptos
  - mcp__cmc-mcp__get_crypto_quotes_latest
---

# Sentinel — Regime Rotator Skill

Sentinel reads the market with CoinMarketCap data and returns a single, defensible answer:
**how much of the book should be in risk-on blue-chips vs. risk-off stables right now, and
why.** Its bias is capital preservation — it would rather miss the top 10% of a rally than
sit through a 30% drawdown. Every call ends with a plain-English rationale a human can audit.

## Prerequisites

Verify the CMC MCP tools are available. If they error, ask the user to add the connection:

```json
{
  "mcpServers": {
    "cmc-mcp": {
      "url": "https://mcp.coinmarketcap.com/mcp",
      "headers": { "X-CMC-MCP-API-KEY": "your-api-key" }
    }
  }
}
```

Get an API key from https://pro.coinmarketcap.com/login

## Core principle

Survival first. The strategy is gated by drawdown and dampened by crowded positioning, so a
single bad regime can't blow up the book. When signals conflict, default to *less* risk.

## Step 1 — Gather signals

Pull the three core inputs (skip gracefully if one fails; the engine degrades to what it has):

1. **Sentiment** → `get_global_metrics_latest`
   Read the **Fear & Greed Index** (0–100). Note BTC dominance / altseason index as context.
2. **Positioning** → `get_global_crypto_derivatives_metrics`
   Read the aggregate **funding rate** (positive = longs pay shorts = crowded longs) and
   open-interest change. Extreme funding either way is a risk-off flag.
3. **Trend** → `get_crypto_marketcap_technical_analysis`
   Read total-market-cap **RSI** and **MACD** signal. Optionally call
   `get_crypto_technical_analysis` for BTC (id 1) / ETH (id 1027) to confirm.

Optionally enrich with `trending_crypto_narratives` to name *what* is leading in risk-on regimes.

## Step 2 — Compute the regime

Apply this scoring (deterministic — the bundled `scripts/regime.py` computes it exactly; use
it when you can run code, otherwise reason through it):

**A. Drawdown gates override everything.** If the user provides current drawdown from peak:
- `≥ 20%` → **HALT**: target 0% risk-on. Flatten to stables. (Stay clear of the 30% gate.)
- `≥ 12%` → **RISK_OFF**: target 0% risk-on until the book stabilizes.

**B. Fear & Greed sets the base posture:**
| F&G | Posture | Base risk-on |
|---|---|---|
| ≤ 24 (extreme fear) | defensive | 0% |
| 25–45 (fear) | cautious | 25% |
| 46–74 (neutral→greed) | constructive | 60% |
| ≥ 75 (extreme greed) | trim, mean-reversion risk | 35% |

**C. Trend modulates it.** Trend score = average of: RSI mapped `(rsi−50)/20` clamped to
[−1,1]; MACD `+1/−1`; EMA fast>slow `+1/−1`. Then `target = clamp(base + 0.25 × trend, 0, 1)`.

**D. Crowded funding dampens.** If `|funding| ≥ 5%`, multiply target by 0.5 — stretched perp
positioning unwinds violently.

**E. Classify:** target ≥ 0.55 → **RISK_ON**; ≥ 0.20 → **NEUTRAL**; else → **RISK_OFF**.

## Step 3 — Output

Always produce, in this order:

```
## Sentinel Regime Read — <UTC timestamp>
Regime: RISK_ON | NEUTRAL | RISK_OFF | HALT
Target allocation: XX% risk-on (blue-chip basket) / XX% stables

## Signals
- Fear & Greed: XX (label)
- Funding: ±X.XX%   | Open interest 24h: ±X%
- Market RSI: XX (label)   | MACD: bullish/bearish

## Entry / exit rules (next moves)
- If currently below target: rotate stables -> [most underweight basket token], one step at a time
- If above target: rotate the most overweight risk-on token -> stables
- No move if the gap is < the min-trade threshold (avoid churn)

## Rationale
<one paragraph in plain English explaining the decision and the dominant signal>
```

Keep the rationale concrete: cite the numbers ("Fear & Greed 22 + negative funding → staying
in stables"). Never output a position without the reason.

## Guardrails (always state them)

- Risk-on universe is a small, liquid blue-chip basket; risk-off is major stables.
- Drawdown gate at 30% is a hard line; Sentinel's internal stop (20%) keeps margin.
- One rebalancing step per evaluation — converge over time, don't lurch.

## Backtest (this is a *backtestable* spec)

The strategy is fully specified and runnable:

- `scripts/regime.py` — the exact regime engine (no dependencies).
- `scripts/backtest.py` — event-driven backtest over a CSV of historical signals
  (`assets/sample_signals.csv` included). Run: `python scripts/backtest.py`.
- To backtest on real history, export CMC historical Fear & Greed, derivatives funding, and
  market RSI/MACD into the same CSV columns and re-run. See `references/methodology.md`.

Report final return, **max drawdown** (the key risk metric), trade count, and a buy-and-hold
benchmark. Sentinel optimizes for risk-adjusted survival, so judge it on drawdown first.
