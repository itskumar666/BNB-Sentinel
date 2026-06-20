# Sentinel — Product Requirements

> **A self-custody autonomous trader that's frugal with two things: your capital, and its own data budget.**
>
> BNB Hack: AI Trading Agent Edition (CoinMarketCap × Trust Wallet × BNB Chain).
> Track 1 (Autonomous Trading Agents) + targeting the **Best Use of TWAK** special prize.

---

## 1. The thesis

The decisive rule in Track 1 is the **max-drawdown gate**: breach ~30% drawdown and you are
**disqualified regardless of PnL**. Combined with "≥1 trade/day" and "hold non-zero in-scope
assets all week," this means **survival beats heroics**. Most teams ship a degen momentum bot,
over-extend, hit the gate in one bad BSC hour, and get zeroed.

That same insight is exactly what the **Best Use of TWAK** prize rewards: *"an agent a
self-custody user would actually let run unattended."* Nobody hands their real keys to a degen
bot. **Product and prize criteria point at the same agent.**

## 2. The user

A self-custody crypto holder who wants automated, on-chain trading **without** (a) giving up
their keys, or (b) babysitting a bot that might blow up. They want an agent they can fund, set
rules for, and walk away from.

## 3. What Sentinel does

A **regime rotator** over a small basket of CMC-eligible BEP-20 tokens on BSC:

- **Risk-on** → rotate into a curated basket of liquid blue-chips when Fear & Greed, funding
  rates, and trend (RSI/MACD/EMA) align bullish.
- **Risk-off** → rotate into stables (USDT/USDC/USD1/FDUSD/DAI) when fear spikes, funding goes
  extreme, or trend breaks.
- **Capital-preservation first** → hard internal drawdown stop set *well under* the competition
  gate, so it structurally cannot get disqualified.
- **Explains every trade in plain English** → e.g. *"Fear&Greed 22 + funding negative →
  rotating 40% to stables."* Builds trust; carries the demo.

## 4. The original hook: a self-managed x402 data budget

Most teams' x402 usage will be one throwaway paid call. Sentinel makes x402 **load-bearing
logic**: it runs cheap heartbeat checks normally and **only pays CMC for expensive deep data**
(derivatives positioning, social heat, KOL flow) **when volatility rises and a decision is
actually at stake.** The agent budgets its own intelligence the way it budgets risk. This
directly targets the x402 scoring line *and* the x402 tie-breaker ("most substantive usage").

## 5. How the three stacks are the heart (not plumbing)

| Stack | Role | Maps to scoring |
|---|---|---|
| **TWAK** (the star) | Sole execution layer. Agent-wallet mode, unlock-once **local signing**, `twak compete register`, **x402** payments. Guardrails = the spine. | TWAK depth (30), self-custody (25), autonomy+guardrails (20), x402 (10) |
| **CMC Agent Hub** | Regime signals: Fear & Greed, funding, RSI/MACD/EMA, social/KOL. Bought per-request via **x402**. | Best Use of Agent Hub special |
| **bnbagent-sdk** | ERC-8004 on-chain **identity** (auditable agent) + hardened **x402 signing policy** (EIP-3009 only, Permit denylist). | Best Use of BNB AI Agent SDK special |

**One build → 4 prize shots:** Track 1 placement + 3 special prizes.

## 6. Guardrails (the product spine — see `src/sentinel/config.py`)

- **Token allowlist** — only the 149 CMC-eligible BEP-20 tokens; everything else rejected pre-sign.
- **Hard drawdown stop** — internal cap (20%) below the competition gate (~30%) for margin.
- **De-risk trigger** — softer threshold (12%) flips the whole book to stables.
- **Per-trade USD cap** + **daily USD cap** — bounds blast radius.
- **Slippage protection** — max bps per swap.
- **Min 1 trade/day** — enforced to stay qualified.

## 7. Non-goals

- No leverage / perps in v1 (drawdown risk). Spot rotation only.
- No token launch, no fundraising (rules forbid during event).
- Not a high-frequency bot. Decisions on a slow cadence (e.g. hourly), matching the hourly
  scoring window.

## 8. Deliverables (DoraHacks + on-chain)

1. Public repo + README with reproducible setup.
2. Demo video showing the **self-custody autonomous signing loop end-to-end** + a real **BSC tx hash**.
3. Agent wallet registered on the competition contract (`twak compete register`).
4. Strategy write-up.

## 9. Timeline

- **Build window ends June 21.** Register agent on-chain **before June 22** (trading opens).
- **Live trading June 22–28.** Judging June 29–July 5.
