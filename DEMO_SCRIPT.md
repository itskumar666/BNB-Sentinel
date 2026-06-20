# Demo Video Script (~2.5 min)

Goal: show a working, original, self-custody-minded Skill backed by real CMC data + on-chain
proof. Keep terminal font large. Record at 1080p.

## 0:00 — Hook (15s)
> "This is Sentinel — a crypto strategy Skill that's frugal with two things: your capital, and
> its own data budget. It's built to *not blow up*, and it explains every decision."

Show `README.md` top.

## 0:15 — The live decision (45s)  ← the centerpiece
Run the live regime read (real CMC data):
```bash
uv run python - <<'PY'
from dotenv import load_dotenv; load_dotenv()
from src.sentinel.data.cmc import CMCDataSource
from src.sentinel.data.base import DataBudget, should_buy_deep
from src.sentinel.strategy.regime import decide
src, b = CMCDataSource(), DataBudget()
c = src.heartbeat(); buy, why = should_buy_deep(c, 0.0, b)
print("Fear&Greed", c.fear_greed, "| RSI", c.rsi, "| MACD", c.macd_hist)
print("x402:", why)
s = c
if buy: s,_ = src.deep(c)
print(decide(s, 0.0).rationale)
PY
```
Narrate: "It pulls Fear & Greed, RSI and MACD live from the CoinMarketCap MCP. Here sentiment is
fearful but momentum's turning up — they disagree — so Sentinel **pays for deep derivatives data
only because the call is close**. Then it takes a measured position, and tells you why."

## 1:00 — The backtest (40s)
```bash
python skills/sentinel-regime-rotator/scripts/backtest.py
```
Point at the final lines: "+14.9% versus buy-and-hold −1.7%, max drawdown 6.6%. It trimmed at the
top, sat out the crash, re-entered on recovery. We optimize drawdown, not bragging rights."

## 1:40 — The Skill itself (25s)
Open `skills/sentinel-regime-rotator/SKILL.md`. Show the frontmatter `allowed-tools` (real CMC
MCP tools) and the regime rules. "It's a portable Agent Skill — drop the folder into any agent,
add the CMC MCP, done."

## 2:05 — On-chain identity (20s)
Open BscScan testnet to the tx, or run:
```bash
uv run python -c "from dotenv import load_dotenv; load_dotenv(); import os; from bnbagent import ERC8004Agent, EVMWalletProvider; w=EVMWalletProvider(password=os.environ['IDENTITY_WALLET_PASSWORD'],persist=True,wallets_dir='.wallets'); a=ERC8004Agent(w,network='bsc-testnet'); print('tradingWallet:', a.get_metadata(1442,'tradingWallet'))"
```
Narrate: "Sentinel has a real ERC-8004 on-chain identity via the BNB AI Agent SDK, bound to its
self-custody Trust Wallet trading address — so the identity that publishes the strategy *is* the
wallet that would trade it."

## 2:25 — Close (10s)
> "Capital preservation, explainable, self-custody, and frugal by design. That's Sentinel."

## Recording checklist
- [ ] `.env` has CMC_API_KEY (don't show the key on screen)
- [ ] Run each command once beforehand to warm caches
- [ ] Have BscScan testnet tab open to the tx hash
- [ ] Keep total under 3 minutes
