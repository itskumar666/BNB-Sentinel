"""Sentinel's regime engine — capital-preservation-first allocation.

Turns CMC market signals into a single decision: what fraction of the book should be in
risk-on blue-chips vs risk-off stables, plus a plain-English rationale for *why*. Every
output is explainable — the rationale is a product feature (trust), not a log line.

Design priority order: (1) don't get disqualified (drawdown gate), (2) preserve capital in
fear/overheated regimes, (3) participate in healthy uptrends. Heroics are explicitly last.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..config import DEFAULT_GUARDRAILS, Guardrails


class Regime(str, Enum):
    HALT = "HALT"          # drawdown hard stop hit — flatten to base stable, stop trading
    RISK_OFF = "RISK_OFF"  # fear / overheated / downtrend — sit in stables
    NEUTRAL = "NEUTRAL"    # mixed signals — small risk-on tilt
    RISK_ON = "RISK_ON"    # fear normalizing + healthy uptrend — deploy into blue-chips


@dataclass
class Signals:
    """Market signals from the CMC Agent Hub. All optional except fear_greed so the
    engine degrades gracefully when a (paid, x402) deep-data field wasn't fetched."""

    fear_greed: int                      # 0 (extreme fear) .. 100 (extreme greed)
    funding_rate: float | None = None    # perp funding, e.g. 0.01 = +1% (overheated longs)
    rsi: float | None = None             # 0..100
    macd_hist: float | None = None       # MACD histogram (>0 bullish momentum)
    ema_fast_over_slow: bool | None = None  # fast EMA above slow EMA = uptrend


@dataclass
class RegimeDecision:
    regime: Regime
    target_risk_on: float   # 0.0 .. 1.0 fraction of book in risk-on basket
    rationale: str          # human-readable "why"
    signals_used: list[str]


def _trend_score(s: Signals) -> tuple[float, list[str]]:
    """Blend RSI + MACD + EMA into a -1..+1 trend score. Missing inputs are skipped."""
    parts: list[float] = []
    used: list[str] = []
    if s.rsi is not None:
        # 50 neutral; >70 overbought (fade), <30 oversold. Scale around 50, clamp.
        parts.append(max(-1.0, min(1.0, (s.rsi - 50) / 20)))
        used.append(f"RSI {s.rsi:.0f}")
    if s.macd_hist is not None:
        parts.append(1.0 if s.macd_hist > 0 else -1.0)
        used.append(f"MACD {'+' if s.macd_hist > 0 else '-'}")
    if s.ema_fast_over_slow is not None:
        parts.append(1.0 if s.ema_fast_over_slow else -1.0)
        used.append("EMA up" if s.ema_fast_over_slow else "EMA down")
    score = sum(parts) / len(parts) if parts else 0.0
    return score, used


def decide(
    signals: Signals,
    drawdown: float,
    guardrails: Guardrails = DEFAULT_GUARDRAILS,
) -> RegimeDecision:
    """Map signals + current drawdown to a target allocation and a reason.

    `drawdown` is a positive fraction (0.15 == down 15% from peak).
    """
    used: list[str] = [f"F&G {signals.fear_greed}"]

    # --- 1. Drawdown gates ALWAYS win, regardless of how bullish signals look. ---
    if drawdown >= guardrails.hard_drawdown_stop:
        return RegimeDecision(
            Regime.HALT, 0.0,
            f"Drawdown {drawdown:.0%} hit the hard stop ({guardrails.hard_drawdown_stop:.0%}). "
            f"Flattening to stables and halting new risk to protect capital and stay well "
            f"clear of the {guardrails.competition_drawdown_gate:.0%} disqualification gate.",
            used,
        )
    if drawdown >= guardrails.derisk_drawdown:
        return RegimeDecision(
            Regime.RISK_OFF, 0.0,
            f"Drawdown {drawdown:.0%} crossed the de-risk line "
            f"({guardrails.derisk_drawdown:.0%}). Rotating fully to stables until the book "
            f"stabilizes; capital preservation outranks any signal here.",
            used,
        )

    # --- 2. Fear & Greed sets the base posture. ---
    fg = signals.fear_greed
    if fg <= 24:           # extreme fear: flight risk, sit out
        base, posture = 0.0, "extreme fear — staying defensive in stables"
    elif fg <= 45:         # fear: cautious
        base, posture = 0.25, "fear — small, cautious risk-on tilt"
    elif fg <= 74:         # neutral/greed: healthy
        base, posture = 0.6, "constructive sentiment — deploying into blue-chips"
    else:                  # extreme greed: take chips off the table
        base, posture = 0.35, "extreme greed — trimming risk, overheated markets mean-revert"

    # --- 3. Trend modulates the base posture. ---
    trend, trend_used = _trend_score(signals)
    used += trend_used
    target = max(0.0, min(1.0, base + 0.25 * trend))

    # --- 4. Funding extremes pull risk OFF (overheated or stressed perps). ---
    funding_note = ""
    if signals.funding_rate is not None:
        used.append(f"funding {signals.funding_rate:+.3%}")
        if abs(signals.funding_rate) >= 0.05:  # very stretched either way
            target *= 0.5
            funding_note = (
                f" Funding is stretched ({signals.funding_rate:+.2%}), so halving risk — "
                f"crowded perp positioning tends to unwind violently."
            )

    # --- 5. Classify + explain. ---
    if target >= 0.55:
        regime = Regime.RISK_ON
    elif target >= 0.2:
        regime = Regime.NEUTRAL
    else:
        regime = Regime.RISK_OFF

    rationale = (
        f"Fear & Greed {fg} → {posture}. "
        f"Trend score {trend:+.2f} ({', '.join(trend_used) or 'no trend data'}). "
        f"Target {target:.0%} risk-on.{funding_note}"
    )
    return RegimeDecision(regime, round(target, 2), rationale, used)
