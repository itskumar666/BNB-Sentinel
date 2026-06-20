# Sentinel — working notes for Claude

**Project:** `/Users/ashutoshkumar/Desktop/bnb-sentinel`
**Hackathon:** BNB Hack: AI Trading Agent Edition (CMC × Trust Wallet × BNB Chain).
**Track:** Track 1 (Autonomous Trading Agents) + targeting **Best Use of TWAK** special prize.
**Owner:** solo builder, experienced (Foundry, ERC-8004, EIP-712 signing — see prior Mantle Agent Arena project). Skip the basics.
**Stake:** small real ($50–200) on BSC mainnet.

## What we're building
**Sentinel** — a self-custody autonomous **capital-preservation regime rotator**. Rotates
risk-on (liquid blue-chips) ↔ risk-off (stables) on CMC signals (Fear&Greed, funding, RSI/MACD).
Structurally can't breach the ~30% drawdown gate → can't be disqualified. Explains every trade
in plain English. **Original hook: self-managed x402 data budget** — only pays CMC for expensive
deep data when volatility makes a decision worth informing. Full spec in `PRD.md`.

## Stack roles (don't confuse them)
- **TWAK** = sole execution layer (agent-wallet mode, unlock-once local signing, x402, `twak compete register`). The star.
- **CMC Agent Hub** = data brains via MCP, deep data paid per-request via x402.
- **bnbagent-sdk** = ⚠️ NOT a trading SDK. Use for ERC-8004 identity + hardened x402 signing policy only. Swaps go through TWAK + PancakeSwap.

## Plan: HYBRID (chosen) — build full agent now at $0, fund ~$10 mainnet before June 22 if possible.
Dry-runs (`--quote-only`) + off-chain signing cost nothing. Also ship a Track 2 CMC Skill from
the same strategy as a guaranteed $0 submission. TWAK is MAINNET-ONLY (no BSC testnet), so the
live TWAK loop + tx hash needs ~$10 real BNB; without it we still target Track 2 + Agent Hub +
BNB SDK specials (ERC-8004 identity is gas-free on testnet).

## Status
- [x] Env: uv + Python 3.12, `bnbagent` + `web3` installed.
- [x] TWAK CLI installed + authed. Agent wallet: `0xD8C578fD1F3661e9eC8aE211a2512DE8477a8624` (key in keychain).
- [x] Competition status checked: open, on-chain deadline 2026-06-25.
- [x] `config.py` — guardrails + 148-token allowlist. Baskets: risk-off USDT/USDC/FDUSD/DAI, risk-on ETH/CAKE/LINK/UNI/DOT.
- [x] `tokens.py` — canonical BSC addresses, all 9 verified routing via TWAK quote-only.
- [x] `execution/twak.py` — guarded swap wrapper, dry-run tested, guardrails reject pre-sign. ✅
- [x] `strategy/regime.py` — regime engine + plain-English rationale, 8/8 scenario tests pass. ✅
- [x] bnbagent ERC-8004 identity LIVE on testnet: agentId 1442, tx 0xc8609aea…d2d4, bound to TWAK wallet via `tradingWallet` metadata. ✅
- [x] Data interface + mock + x402 data-budget logic (`data/base.py`, `data/mock.py`). ✅
- [x] Allocator (`strategy/allocator.py`) + agent loop (`agent.py`): paper backtest beats buy&hold (-2% vs -17%, maxDD 6%), live driver dry-run tested. ✅
- [x] CMC REAL adapter (`data/cmc.py`) via CMC MCP — live, x402 budget split verified. ✅
- [x] Track 2 CMC Skill (`skills/sentinel-regime-rotator/`) — SKILL.md + backtest (+14.9% vs -1.7%, 6.6% maxDD). ✅
- [ ] README + DoraHacks submission + demo video (free-tier final stage).

## CMC live facts
- Key works on REST (`X-CMC_PRO_API_KEY`) and MCP (`https://mcp.coinmarketcap.com/mcp`, `X-CMC-MCP-API-KEY`). 15k credits/mo, 50/min.
- F&G: `get_global_metrics_latest` -> sentiment.fear_greed.current.index. Funding: `get_global_crypto_derivatives_metrics` -> fundingRate.current. RSI/MACD: `get_crypto_marketcap_technical_analysis` -> rsi.rsi14 / macd.histogram.

## How to run
- Backtest: `uv run python -m src.sentinel.agent`
- Regime tests: `uv run python tests/test_regime.py`  | Token routing: `uv run python scripts/verify_tokens.py`
- Live tick (dry-run today; flip TwakExecutor(dry_run=False) once funded): see `live_tick` in agent.py

## Verified TWAK facts (don't re-derive)
- Chain key `bsc` (mainnet only). Stables + ETH resolve by symbol; others need contract address.
- Swap forms: `twak swap <amt> <from> <to>` OR `twak swap <from> <to> --usd <amt>` (we use --usd).
- `twak compete register` / `twak compete status`. `twak wallet portfolio --json`. Password via keychain (don't pass --password on CLI).
- `twak serve --watch` = background automation watcher (autonomous-mode surface for the demo).

## Hard facts
- Competition contract: `0x212c61b9b72c95d95bf29cf032f5e5635629aed5` (BSC).
- Drawdown gate ~30% = DQ. Our hard stop 20%, de-risk at 12%.
- Min 1 eligible trade/day. Hold non-zero eligible assets at start. Hour starting ≤$1 scored 0%.
- Build ends June 21; register before June 22; live trade June 22–28.

## Note
`bnbagent-sdk`, TWAK, and CMC docs are partly behind portal auth — verify real tool/command
names against the live CLI/MCP once credentials exist before writing integration code. Don't
guess interfaces.
