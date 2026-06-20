"""Data-source interface + the x402 self-managed data budget.

The original hook: Sentinel doesn't blindly buy every signal. It runs a CHEAP heartbeat
(Fear & Greed + price/RSI) every tick, and only PAYS — via x402 — for expensive deep data
(funding rates, derivatives positioning, social/KOL heat) when a decision is actually at
stake. `DataBudget` tracks that spend; `should_buy_deep` is the policy.

Concrete sources implement `DataSource`. The real one (CMC Agent Hub) drops in behind this
interface; `MockDataSource` lets the whole agent run end-to-end at $0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..strategy.regime import Signals


@dataclass
class DataBudget:
    """Tracks x402 micro-payments for data this session. The agent is frugal on purpose."""

    daily_cap_usd: float = 1.00
    spent_usd: float = 0.0
    purchases: int = 0

    def can_spend(self, usd: float) -> bool:
        return self.spent_usd + usd <= self.daily_cap_usd

    def record(self, usd: float) -> None:
        self.spent_usd += usd
        self.purchases += 1


class DataSource(Protocol):
    """A source of market signals for the regime engine."""

    def heartbeat(self) -> Signals:
        """Cheap/free signals fetched every tick (Fear & Greed + basic trend)."""
        ...

    def deep(self, base: Signals) -> tuple[Signals, float]:
        """Enrich `base` with expensive data (funding, derivatives, social).

        Returns (enriched_signals, usd_cost). The caller pays via x402 and only calls
        this when `should_buy_deep` says it's worth it.
        """
        ...


def should_buy_deep(cheap: Signals, drawdown: float, budget: DataBudget,
                    price_usd: float = 0.02) -> tuple[bool, str]:
    """Decide whether to pay for deep data. Frugal-by-default policy.

    Buy deep data only when the cheap signal is AMBIGUOUS or conditions are RISKY —
    i.e. when better information could actually change the decision and protect capital.
    """
    if not budget.can_spend(price_usd):
        return False, "x402 daily data budget exhausted — deciding on free signals"

    fg = cheap.fear_greed
    # Near a regime boundary (F&G in the indecisive 40-60 band) → pay to disambiguate.
    if 40 <= fg <= 60:
        return True, f"F&G {fg} is in the indecisive band — buying deep data to confirm"
    # Elevated drawdown → pay to make sure we're not about to step into a trap.
    if drawdown >= 0.08:
        return True, f"drawdown {drawdown:.0%} elevated — buying deep data before any risk"
    # Trend conflicts with sentiment → pay to break the tie.
    if cheap.macd_hist is not None and (
        (fg >= 60 and cheap.macd_hist < 0) or (fg <= 40 and cheap.macd_hist > 0)
    ):
        return True, "sentiment and momentum disagree — buying deep data to break the tie"
    return False, f"clear regime (F&G {fg}) — free signals suffice, saving the x402 spend"
