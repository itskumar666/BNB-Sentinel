"""Allocator — turn a target risk-on fraction into ONE concrete rebalancing trade.

Sentinel trades at most once per tick (keeps it legible, bounds gas, respects caps). Over
successive ticks the book converges to target. Each tick we move the single most off-target
token. Risk-on is held as an equal-weight basket; risk-off parks in the base stable.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import BASE_STABLE, RISK_ON_BASKET, Guardrails


@dataclass
class TradePlan:
    from_sym: str
    to_sym: str
    usd: float
    reason: str


def allocate(
    portfolio: dict[str, float],
    target_risk_on: float,
    guardrails: Guardrails,
) -> TradePlan | None:
    """Return the next rebalancing trade, or None if already within tolerance."""
    total = sum(portfolio.values())
    if total <= guardrails.min_portfolio_usd:
        return None  # dust — don't trade (rules score sub-$1 hours as 0% anyway)

    risk_on_now = sum(portfolio.get(t, 0.0) for t in RISK_ON_BASKET)
    target_usd = total * target_risk_on
    delta = target_usd - risk_on_now  # >0 → buy risk-on, <0 → sell risk-on

    if abs(delta) < guardrails.min_trade_usd:
        return None

    trade_usd = min(abs(delta), guardrails.per_trade_usd_cap)

    if delta > 0:
        # BUY risk-on: fund from base stable, into the most-underweight basket token.
        per_token_target = target_usd / len(RISK_ON_BASKET)
        to_sym = min(RISK_ON_BASKET, key=lambda t: portfolio.get(t, 0.0) - per_token_target)
        available = portfolio.get(BASE_STABLE, 0.0)
        trade_usd = min(trade_usd, available)
        if trade_usd < guardrails.min_trade_usd:
            return None
        return TradePlan(BASE_STABLE, to_sym, round(trade_usd, 2),
                         f"raise risk-on toward {target_risk_on:.0%}")

    # SELL risk-on: from the most-overweight held basket token, back to base stable.
    held = {t: portfolio.get(t, 0.0) for t in RISK_ON_BASKET if portfolio.get(t, 0.0) > 0}
    if not held:
        return None
    from_sym = max(held, key=held.get)
    trade_usd = min(trade_usd, held[from_sym])
    if trade_usd < guardrails.min_trade_usd:
        return None
    return TradePlan(from_sym, BASE_STABLE, round(trade_usd, 2),
                     f"cut risk-on toward {target_risk_on:.0%}")
