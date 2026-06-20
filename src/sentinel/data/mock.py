"""Mock data source — deterministic scenario sequence so the whole agent runs at $0.

Replaced by the real CMC Agent Hub adapter (same `DataSource` interface) once the API key
is wired. The cheap heartbeat omits funding/derivatives; `deep` adds them, simulating an
x402-paid enrichment.
"""

from __future__ import annotations

from .base import Signals

# A scripted week of regimes to exercise the agent: fear -> recovery -> greed -> overheated.
# `ret` is the realized risk-on market return for HOLDING through that period (for the paper
# backtest): fear keeps falling, recovery/greed rise, the overheated top crashes.
_SCENARIOS = [
    dict(fear_greed=18, rsi=33, macd_hist=-1, ema=False, funding=-0.02, ret=-0.05),  # extreme fear
    dict(fear_greed=38, rsi=45, macd_hist=-1, ema=False, funding=-0.01, ret=-0.02),  # fear
    dict(fear_greed=52, rsi=51, macd_hist=1, ema=True, funding=0.005, ret=0.01),     # indecisive
    dict(fear_greed=66, rsi=58, macd_hist=1, ema=True, funding=0.01, ret=0.03),      # constructive
    dict(fear_greed=72, rsi=64, macd_hist=1, ema=True, funding=0.02, ret=0.025),     # greed
    dict(fear_greed=88, rsi=78, macd_hist=1, ema=True, funding=0.07, ret=-0.07),     # overheated top -> crash
    dict(fear_greed=60, rsi=49, macd_hist=-1, ema=False, funding=0.0, ret=-0.015),   # sentiment/momentum clash
]


class MockDataSource:
    def __init__(self) -> None:
        self._i = 0

    def heartbeat(self) -> Signals:
        s = _SCENARIOS[self._i % len(_SCENARIOS)]
        # Cheap signals: F&G + basic trend only. NO funding (that's deep/paid data).
        return Signals(
            fear_greed=s["fear_greed"], rsi=s["rsi"],
            macd_hist=s["macd_hist"], ema_fast_over_slow=s["ema"],
        )

    def deep(self, base: Signals) -> tuple[Signals, float]:
        s = _SCENARIOS[self._i % len(_SCENARIOS)]
        enriched = Signals(
            fear_greed=base.fear_greed, rsi=base.rsi, macd_hist=base.macd_hist,
            ema_fast_over_slow=base.ema_fast_over_slow, funding_rate=s["funding"],
        )
        return enriched, 0.02  # simulated x402 cost per deep fetch

    def realized_return(self) -> float:
        """Risk-on market return realized over the current period (paper backtest only)."""
        return _SCENARIOS[self._i % len(_SCENARIOS)]["ret"]

    def advance(self) -> None:
        self._i += 1
