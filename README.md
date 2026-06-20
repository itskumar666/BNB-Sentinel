# Sentinel 🛡️

**A self-custody autonomous trader that's frugal with two things: your capital, and its own data budget.**

> BNB Hack: AI Trading Agent Edition (CoinMarketCap × Trust Wallet × BNB Chain)
> **Track 2 — Strategy Skills**, plus *Best Use of Agent Hub* and *Best Use of BNB AI Agent SDK*.

Sentinel reads the market with CoinMarketCap data and decides how much of a book should be in
risk-on blue-chips vs. risk-off stables — biased toward **capital preservation**, with a hard
drawdown gate, and a plain-English rationale for every decision. It ships as a portable
**CMC Skill** (the Track 2 deliverable) *and* as a reference autonomous agent with an on-chain
**ERC-8004 identity** and a self-custody **Trust Wallet** execution layer.

---

## Why it's different

Most hackathon trading bots optimize for upside and die in drawdowns. Sentinel inverts that:
**survival first.** It would rather miss the top 10% of a rally than sit through a 30% drawdown
— which is exactly the agent a self-custody user would actually leave running unattended.

The original hook: **a self-managed data budget.** Sentinel runs a cheap heartbeat every tick
and only *pays* for expensive deep data (derivatives funding) when a decision is genuinely at
stake — when sentiment and momentum disagree, or drawdown is rising. It budgets its own
intelligence the way it budgets risk.

---

## What's in here

| Piece | Path | What it is |
|---|---|---|
| **CMC Skill** (Track 2 deliverable) | `skills/sentinel-regime-rotator/` | Portable `SKILL.md` + runnable backtest + methodology |
| Regime engine | `src/sentinel/strategy/regime.py` | Deterministic risk-on/off decision + rationale |
| Allocator | `src/sentinel/strategy/allocator.py` | Target allocation → one rebalancing trade |
| Live CMC data | `src/sentinel/data/cmc.py` | Signals via CMC MCP (F&G, funding, RSI/MACD) |
| x402 data budget | `src/sentinel/data/base.py` | Pay-for-deep-data-only-when-it-matters policy |
| TWAK execution | `src/sentinel/execution/twak.py` | Guarded self-custody swaps (sole execution path) |
| ERC-8004 identity | `src/sentinel/identity/bnb.py` | On-chain agent identity via BNB AI Agent SDK |
| Agent loop + backtest | `src/sentinel/agent.py` | Orchestration; paper backtest = Track 2 engine |
| Guardrails + allowlist | `src/sentinel/config.py` | Drawdown caps, per-trade/daily limits, eligible tokens |

---

## The three-stack integration

- **CoinMarketCap Agent Hub** — live signals over the **CMC MCP**: Fear & Greed
  (`get_global_metrics_latest`), funding rate (`get_global_crypto_derivatives_metrics`), and
  market RSI/MACD (`get_crypto_marketcap_technical_analysis`). The x402 budget decides *when*
  to pay for the expensive derivatives call.
- **Trust Wallet Agent Kit (TWAK)** — the sole execution layer. Non-custodial agent wallet,
  unlock-once **local signing** (keys never leave the device), guardrails enforced *before*
  signing. All 9 universe tokens verified routing on BSC.
- **BNB AI Agent SDK** — Sentinel's **ERC-8004 identity** is live on BSC testnet and
  cryptographically **bound to the TWAK trading wallet** via on-chain metadata, so anyone can
  verify "this published identity is the wallet that trades."

---

## Proof points

- **On-chain identity (live):** ERC-8004 `agentId 1442` on BSC testnet,
  tx `0xc8609aeaeaf914ab7094126e081088daf664135baa97512f25bdf85df6d4d2d4`,
  `tradingWallet` metadata → `0xD8C578fD1F3661e9eC8aE211a2512DE8477a8624`.
- **Backtest (full market cycle):** **+14.9%** vs buy-and-hold **−1.7%**, **max drawdown 6.6%**
  (well under the 30% gate). See `skills/sentinel-regime-rotator/`.
- **Live decision (real CMC data):** at Fear & Greed 20 with momentum turning up, Sentinel
  detected the sentiment/momentum conflict, *paid for deep data to break the tie*, and took a
  measured **21% risk-on** position.

---

## Run it

```bash
# install (Python 3.12, uv)
uv sync

# 1) Track 2 Skill backtest (no key needed)
python skills/sentinel-regime-rotator/scripts/backtest.py

# 2) Regime engine tests + token routing checks
uv run python tests/test_regime.py
uv run python scripts/verify_tokens.py

# 3) Live regime read from real CMC data  (set CMC_API_KEY in .env)
uv run python -m src.sentinel.agent          # paper backtest
# live signals: see src/sentinel/data/cmc.py
```

To use the Skill in any agent, add the CMC MCP and copy the skill folder:

```json
{ "mcpServers": { "cmc-mcp": { "url": "https://mcp.coinmarketcap.com/mcp",
  "headers": { "X-CMC-MCP-API-KEY": "your-key" } } } }
```

---

## Guardrails (the spine)

Drawdown: hard stop **20%** / de-risk **12%** (gate is 30%). Per-trade cap **$50**, daily **$150**,
slippage **80 bps**, min trade **$5**. Token allowlist restricted to CMC-eligible BEP-20 tokens;
anything off-list is rejected *before* signing.

## Honest limitations

The sample backtest is an illustrative market cycle, not a validated historical edge — treat
+14.9% as a behavior demonstration. The reference live-trading loop is built and dry-run tested
but not run with real funds (Track 1 was out of scope for this submission). Spot only, no
leverage — a deliberate choice to bound drawdown.

_License: MIT._
