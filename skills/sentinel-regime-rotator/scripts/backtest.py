"""Event-driven backtest for the Sentinel regime rotator.

Reads a CSV of historical signals + the realized next-period risk-on return, runs the exact
regime engine + allocator, and reports return, MAX DRAWDOWN (the metric that matters), trade
count, and a buy-and-hold benchmark.

Run:  python scripts/backtest.py [path/to/signals.csv]
CSV columns: date,fear_greed,funding_rate,rsi,macd_hist,ema_fast_over_slow,risk_on_return
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from regime import BASE_STABLE, RISK_ON_BASKET, Signals, allocate, decide  # noqa: E402

DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "..", "assets", "sample_signals.csv")
SWAP_COST_BPS = 30.0  # simulated swap + gas friction per trade


def _b(v: str) -> bool | None:
    return None if v == "" else v.strip().lower() in ("1", "true", "yes")


def _f(v: str) -> float | None:
    return None if v == "" else float(v)


def run(csv_path: str, starting_usd: float = 100.0, verbose: bool = True) -> dict:
    holdings = {BASE_STABLE: starting_usd}
    bh = starting_usd
    peak = starting_usd
    max_dd = 0.0
    trades = 0

    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))

    for row in rows:
        total = sum(holdings.values())
        peak = max(peak, total)
        dd = (peak - total) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

        sig = Signals(
            fear_greed=int(float(row["fear_greed"])),
            funding_rate=_f(row.get("funding_rate", "")),
            rsi=_f(row.get("rsi", "")),
            macd_hist=_f(row.get("macd_hist", "")),
            ema_fast_over_slow=_b(row.get("ema_fast_over_slow", "")),
        )
        d = decide(sig, dd)
        plan = allocate(holdings, d.target_risk_on)
        if plan:
            out = plan.usd * (1 - SWAP_COST_BPS / 10_000)
            holdings[plan.from_sym] = holdings.get(plan.from_sym, 0.0) - plan.usd
            holdings[plan.to_sym] = holdings.get(plan.to_sym, 0.0) + out
            trades += 1

        r = _f(row.get("risk_on_return", "")) or 0.0
        for s in RISK_ON_BASKET:
            if holdings.get(s):
                holdings[s] *= 1 + r
        bh *= 1 + r

        if verbose:
            on = sum(holdings.get(s, 0.0) for s in RISK_ON_BASKET) / max(sum(holdings.values()), 1e-9)
            mv = f"{plan.from_sym}->{plan.to_sym} ${plan.usd:.0f}" if plan else "hold"
            print(f"  {row['date']}  {d.regime.value:8s} on={on:5.0%} dd={dd:4.0%} "
                  f"{mv:16s} eq=${sum(holdings.values()):.2f}")

    final = sum(holdings.values())
    return {
        "final_usd": round(final, 2),
        "total_return": round(final / starting_usd - 1, 4),
        "max_drawdown": round(max_dd, 4),
        "trades": trades,
        "buy_hold_return": round(bh / starting_usd - 1, 4),
        "periods": len(rows),
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    print(f"Sentinel backtest on {os.path.basename(path)}:\n")
    res = run(path)
    print(f"\n  Periods: {res['periods']}  |  Trades: {res['trades']}")
    print(f"  Return:  {res['total_return']:+.1%}   (buy & hold {res['buy_hold_return']:+.1%})")
    print(f"  Max drawdown: {res['max_drawdown']:.1%}   "
          f"({'PASS' if res['max_drawdown'] < 0.30 else 'BREACH'} vs 30% gate)")
