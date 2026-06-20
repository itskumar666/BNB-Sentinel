"""Sentinel regime engine + allocator (standalone, no dependencies).

This is the exact, deterministic logic the SKILL.md describes. Kept self-contained so the
skill folder is portable (copy it anywhere). Mirrors the reference agent in the parent repo.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# --- guardrails / universe (the "rules you set") ---------------------------
COMPETITION_DRAWDOWN_GATE = 0.30
HARD_DRAWDOWN_STOP = 0.20
DERISK_DRAWDOWN = 0.12
PER_TRADE_USD_CAP = 50.0
MIN_TRADE_USD = 5.0
MIN_PORTFOLIO_USD = 5.0
RISK_ON_BASKET = ("ETH", "CAKE", "LINK", "UNI", "DOT")
BASE_STABLE = "USDT"


class Regime(str, Enum):
    HALT = "HALT"
    RISK_OFF = "RISK_OFF"
    NEUTRAL = "NEUTRAL"
    RISK_ON = "RISK_ON"


@dataclass
class Signals:
    fear_greed: int
    funding_rate: float | None = None
    rsi: float | None = None
    macd_hist: float | None = None
    ema_fast_over_slow: bool | None = None


@dataclass
class RegimeDecision:
    regime: Regime
    target_risk_on: float
    rationale: str


def _trend_score(s: Signals) -> tuple[float, list[str]]:
    parts, used = [], []
    if s.rsi is not None:
        parts.append(max(-1.0, min(1.0, (s.rsi - 50) / 20)))
        used.append(f"RSI {s.rsi:.0f}")
    if s.macd_hist is not None:
        parts.append(1.0 if s.macd_hist > 0 else -1.0)
        used.append(f"MACD {'+' if s.macd_hist > 0 else '-'}")
    if s.ema_fast_over_slow is not None:
        parts.append(1.0 if s.ema_fast_over_slow else -1.0)
        used.append("EMA up" if s.ema_fast_over_slow else "EMA down")
    return (sum(parts) / len(parts) if parts else 0.0), used


def decide(signals: Signals, drawdown: float) -> RegimeDecision:
    if drawdown >= HARD_DRAWDOWN_STOP:
        return RegimeDecision(Regime.HALT, 0.0,
            f"Drawdown {drawdown:.0%} hit the hard stop ({HARD_DRAWDOWN_STOP:.0%}). Flatten to "
            f"stables; stay clear of the {COMPETITION_DRAWDOWN_GATE:.0%} gate.")
    if drawdown >= DERISK_DRAWDOWN:
        return RegimeDecision(Regime.RISK_OFF, 0.0,
            f"Drawdown {drawdown:.0%} crossed the de-risk line ({DERISK_DRAWDOWN:.0%}). "
            f"Rotate fully to stables; preservation outranks any signal.")

    fg = signals.fear_greed
    if fg <= 24:
        base, posture = 0.0, "extreme fear — defensive in stables"
    elif fg <= 45:
        base, posture = 0.25, "fear — small cautious tilt"
    elif fg <= 74:
        base, posture = 0.6, "constructive — deploying into blue-chips"
    else:
        base, posture = 0.35, "extreme greed — trimming, mean-reversion risk"

    trend, trend_used = _trend_score(signals)
    target = max(0.0, min(1.0, base + 0.25 * trend))

    note = ""
    if signals.funding_rate is not None and abs(signals.funding_rate) >= 0.05:
        target *= 0.5
        note = f" Funding stretched ({signals.funding_rate:+.2%}) → halving risk."

    regime = (Regime.RISK_ON if target >= 0.55
              else Regime.NEUTRAL if target >= 0.2 else Regime.RISK_OFF)
    rationale = (f"Fear & Greed {fg} → {posture}. Trend {trend:+.2f} "
                 f"({', '.join(trend_used) or 'no trend data'}). Target {target:.0%} risk-on.{note}")
    return RegimeDecision(regime, round(target, 2), rationale)


@dataclass
class TradePlan:
    from_sym: str
    to_sym: str
    usd: float


def allocate(portfolio: dict[str, float], target_risk_on: float) -> TradePlan | None:
    """One rebalancing step toward target. None if within tolerance."""
    total = sum(portfolio.values())
    if total <= MIN_PORTFOLIO_USD:
        return None
    risk_on_now = sum(portfolio.get(t, 0.0) for t in RISK_ON_BASKET)
    delta = total * target_risk_on - risk_on_now
    if abs(delta) < MIN_TRADE_USD:
        return None
    trade = min(abs(delta), PER_TRADE_USD_CAP)
    if delta > 0:
        per = (total * target_risk_on) / len(RISK_ON_BASKET)
        to = min(RISK_ON_BASKET, key=lambda t: portfolio.get(t, 0.0) - per)
        trade = min(trade, portfolio.get(BASE_STABLE, 0.0))
        return TradePlan(BASE_STABLE, to, round(trade, 2)) if trade >= MIN_TRADE_USD else None
    held = {t: portfolio.get(t, 0.0) for t in RISK_ON_BASKET if portfolio.get(t, 0.0) > 0}
    if not held:
        return None
    frm = max(held, key=held.get)
    trade = min(trade, held[frm])
    return TradePlan(frm, BASE_STABLE, round(trade, 2)) if trade >= MIN_TRADE_USD else None
