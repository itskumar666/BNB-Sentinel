"""Live regime read from real CoinMarketCap data.

Run from the project root (needs CMC_API_KEY in .env):
    uv run python live_read.py

Prints the live signals, the x402 data-budget decision, and Sentinel's
plain-English allocation rationale.
"""
from dotenv import load_dotenv

load_dotenv()

from src.sentinel.data.cmc import CMCDataSource
from src.sentinel.data.base import DataBudget, should_buy_deep
from src.sentinel.strategy.regime import decide


def main() -> None:
    src, budget = CMCDataSource(), DataBudget()

    # cheap heartbeat: Fear & Greed + RSI/MACD
    c = src.heartbeat()
    buy, why = should_buy_deep(c, 0.0, budget)  # (signals, drawdown, budget)
    print(f"Fear&Greed {c.fear_greed} | RSI {c.rsi} | MACD {c.macd_hist}")
    print("x402:", why)

    # only pay for deep derivatives data when the decision is on the line
    signals = c
    if buy:
        signals, _ = src.deep(c)

    print(decide(signals, 0.0).rationale)  # (signals, drawdown)


if __name__ == "__main__":
    main()
