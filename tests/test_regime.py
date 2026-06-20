"""Scenario tests for the regime engine. Run: uv run python tests/test_regime.py"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
from src.sentinel.config import DEFAULT_GUARDRAILS as G  # noqa: E402
from src.sentinel.strategy.regime import Regime, Signals, decide  # noqa: E402

CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case("hard drawdown stop -> HALT, flatten")
def _():
    d = decide(Signals(fear_greed=80, rsi=70, macd_hist=1, ema_fast_over_slow=True), drawdown=0.21)
    assert d.regime is Regime.HALT and d.target_risk_on == 0.0, d


@case("de-risk drawdown -> RISK_OFF even if bullish")
def _():
    d = decide(Signals(fear_greed=70, rsi=65, macd_hist=1, ema_fast_over_slow=True), drawdown=0.13)
    assert d.regime is Regime.RISK_OFF and d.target_risk_on == 0.0, d


@case("extreme fear -> defensive")
def _():
    d = decide(Signals(fear_greed=10, rsi=35, macd_hist=-1, ema_fast_over_slow=False), drawdown=0.0)
    assert d.regime is Regime.RISK_OFF and d.target_risk_on <= 0.1, d


@case("healthy greed + uptrend -> RISK_ON")
def _():
    d = decide(Signals(fear_greed=65, rsi=60, macd_hist=1, ema_fast_over_slow=True), drawdown=0.02)
    assert d.regime is Regime.RISK_ON and d.target_risk_on >= 0.6, d


@case("extreme greed -> trimmed, not max risk")
def _():
    d = decide(Signals(fear_greed=92, rsi=75, macd_hist=1, ema_fast_over_slow=True), drawdown=0.0)
    assert d.target_risk_on < 0.7, d


@case("stretched funding halves risk")
def _():
    base = decide(Signals(fear_greed=65, rsi=60, macd_hist=1, ema_fast_over_slow=True), drawdown=0.0)
    hot = decide(Signals(fear_greed=65, rsi=60, macd_hist=1, ema_fast_over_slow=True,
                         funding_rate=0.08), drawdown=0.0)
    assert hot.target_risk_on <= base.target_risk_on / 2 + 0.01, (base, hot)


@case("bullish sentiment but downtrend -> reduced")
def _():
    up = decide(Signals(fear_greed=65, rsi=60, macd_hist=1, ema_fast_over_slow=True), drawdown=0.0)
    down = decide(Signals(fear_greed=65, rsi=40, macd_hist=-1, ema_fast_over_slow=False), drawdown=0.0)
    assert down.target_risk_on < up.target_risk_on, (up, down)


@case("graceful with only F&G (no deep data)")
def _():
    d = decide(Signals(fear_greed=65), drawdown=0.0)
    assert 0.0 <= d.target_risk_on <= 1.0 and "no trend data" in d.rationale, d


def main() -> int:
    fails = 0
    for name, fn in CASES:
        try:
            fn()
            print(f"  [OK ] {name}")
        except AssertionError as e:
            fails += 1
            print(f"  [FAIL] {name}\n         {e}")
    print(f"\n{len(CASES) - fails}/{len(CASES)} scenarios passed.")
    # Show a sample rationale so we can eyeball the plain-English output.
    sample = decide(Signals(fear_greed=22, rsi=38, macd_hist=-1, ema_fast_over_slow=False,
                            funding_rate=-0.06), drawdown=0.05)
    print(f"\nSample rationale ({sample.regime.value}, {sample.target_risk_on:.0%} risk-on):\n  {sample.rationale}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
