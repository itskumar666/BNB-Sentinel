# Sentinel — DoraHacks Submission

**Track 2 (Strategy Skills)** · also targeting *Best Use of Agent Hub* and *Best Use of BNB AI Agent SDK*.

## One-liner
A capital-preservation crypto regime Skill that turns CoinMarketCap data into a risk-on/risk-off
allocation with explicit rules and a plain-English rationale — and budgets its own data spend.

## The strategy (what the Skill does)
Sentinel blends three CMC signals into one allocation decision:
- **Fear & Greed** sets the base posture (defensive in fear, constructive in neutral, *trims* in
  extreme greed because tops mean-revert).
- **Market RSI/MACD** modulate it by trend.
- **Derivatives funding** dampens risk when positioning is crowded (extremes unwind violently).
- A **drawdown gate** overrides everything — ≥12% de-risks, ≥20% halts — keeping clear of the
  30% disqualification line by design.

It outputs a regime, a target allocation across a liquid blue-chip basket vs. stables, concrete
entry/exit rules, and a one-paragraph rationale citing the actual numbers.

## Backtest (the deliverable is a *backtestable* spec)
On a full fear→rally→overheated-top→crash→recovery cycle (`scripts/backtest.py`):

| | Sentinel | Buy & hold |
|---|---|---|
| Return | **+14.9%** | −1.7% |
| Max drawdown | **6.6%** | (deep) |
| Trades | 15 | — |

It rode the rally, trimmed at the overheated top, sat out the crash in stables, and re-entered
on recovery. We judge on **drawdown first** — the strategy optimizes risk-adjusted survival.

## Why it maps to the judging criteria
- **Technical execution** — deterministic engine with unit tests (8/8), a runnable backtest, a
  live CMC-MCP adapter, and a real on-chain artifact (not cosmetic).
- **Originality** — capital-preservation-first regime rotation + a self-managed x402-style data
  budget (pay for deep data only when a decision is at stake). On live data it detected a
  sentiment/momentum conflict and paid to break the tie.
- **Real-world relevance** — explicitly the agent a self-custody holder would leave running:
  bounded downside, every decision explained, hard drawdown backstop.
- **Demo** — see `DEMO_SCRIPT.md`; backed by on-chain proof.

## Best Use of Agent Hub
Live signals over the CMC MCP — `get_global_metrics_latest` (Fear & Greed),
`get_global_crypto_derivatives_metrics` (funding), `get_crypto_marketcap_technical_analysis`
(RSI/MACD) — with an intelligent budget that decides *when* the expensive derivatives call is
worth its credit.

## Best Use of BNB AI Agent SDK
ERC-8004 identity minted via `bnbagent-sdk` (gas-free on testnet), **bound on-chain to the
self-custody TWAK trading wallet** via `tradingWallet` metadata. Identity ↔ execution wallet is
verifiable by anyone.
- agentId: **1442** (BSC testnet)
- tx: `0xc8609aeaeaf914ab7094126e081088daf664135baa97512f25bdf85df6d4d2d4`
- bound wallet: `0xD8C578fD1F3661e9eC8aE211a2512DE8477a8624`

## Repo
Public repo with reproducible setup (`README.md`). The Skill is portable: copy
`skills/sentinel-regime-rotator/` into any agent's skills directory and add the CMC MCP.

## Honest scope
Track 1 live trading (June 22–28) was out of scope (no live capital). The reference execution
loop is built and dry-run verified on BSC mainnet routing; the submission centers on the Track 2
Skill + the two cross-track specials, all reproducible today.
