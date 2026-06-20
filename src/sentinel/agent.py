"""Sentinel's orchestration loop.

`decide_tick` is the pure decision: portfolio + drawdown + data source -> regime decision +
(maybe) a trade, with the x402 data-budget logic deciding whether to pay for deep data. It's
driver-agnostic — the same decision runs against a live TWAK wallet or a paper book.

`run_paper` drives it over the mock scenario week as a mini-backtest (also the Track 2 engine).
`run_live` (added when funded) drives it against the real wallet via TWAK.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import BASE_STABLE, DEFAULT_GUARDRAILS, RISK_ON_BASKET, Guardrails
from .data.base import DataBudget, DataSource, should_buy_deep
from .data.mock import MockDataSource
from .strategy.allocator import TradePlan, allocate
from .strategy.regime import Regime, decide


@dataclass
class TickDecision:
    regime: Regime
    target_risk_on: float
    rationale: str
    data_reason: str        # why we did/didn't pay for deep data
    paid_usd: float         # x402 spend this tick
    plan: TradePlan | None  # the rebalancing trade, if any


def decide_tick(
    portfolio: dict[str, float],
    drawdown: float,
    source: DataSource,
    budget: DataBudget,
    guardrails: Guardrails = DEFAULT_GUARDRAILS,
) -> TickDecision:
    cheap = source.heartbeat()
    buy_deep, why = should_buy_deep(cheap, drawdown, budget)
    signals, paid = cheap, 0.0
    if buy_deep:
        enriched, cost = source.deep(cheap)
        if budget.can_spend(cost):
            budget.record(cost)
            signals, paid = enriched, cost
    decision = decide(signals, drawdown, guardrails)
    plan = allocate(portfolio, decision.target_risk_on, guardrails)
    return TickDecision(decision.regime, decision.target_risk_on,
                        decision.rationale, why, paid, plan)


# --------------------------------------------------------------------------
# Paper driver = backtest. Holdings tracked in USD notional per token.
# --------------------------------------------------------------------------
class PaperBook:
    def __init__(self, holdings: dict[str, float]):
        self.holdings = dict(holdings)

    def total(self) -> float:
        return sum(self.holdings.values())

    def risk_on_frac(self) -> float:
        t = self.total()
        return sum(self.holdings.get(s, 0.0) for s in RISK_ON_BASKET) / t if t else 0.0

    def apply_trade(self, plan: TradePlan, cost_bps: float) -> None:
        out = plan.usd * (1 - cost_bps / 10_000)  # simulated swap + gas friction
        self.holdings[plan.from_sym] = self.holdings.get(plan.from_sym, 0.0) - plan.usd
        self.holdings[plan.to_sym] = self.holdings.get(plan.to_sym, 0.0) + out

    def mark(self, risk_on_return: float) -> None:
        for s in RISK_ON_BASKET:
            if self.holdings.get(s):
                self.holdings[s] *= 1 + risk_on_return


@dataclass
class BacktestResult:
    final_usd: float
    total_return: float
    max_drawdown: float
    trades: int
    data_spent_usd: float
    buy_hold_return: float


def run_paper(
    ticks: int = 14,
    starting_usd: float = 100.0,
    guardrails: Guardrails = DEFAULT_GUARDRAILS,
    verbose: bool = True,
) -> BacktestResult:
    source = MockDataSource()
    budget = DataBudget()
    book = PaperBook({BASE_STABLE: starting_usd})
    bh = starting_usd  # buy-and-hold benchmark (100% risk-on the whole time)

    peak, max_dd, trades = book.total(), 0.0, 0
    for t in range(ticks):
        total = book.total()
        peak = max(peak, total)
        dd = (peak - total) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

        td = decide_tick(book.holdings, dd, source, budget, guardrails)
        if td.plan:
            book.apply_trade(td.plan, cost_bps=30)
            trades += 1

        r = source.realized_return()
        book.mark(r)
        bh *= 1 + r
        source.advance()

        if verbose:
            trade = (f"{td.plan.from_sym}->{td.plan.to_sym} ${td.plan.usd:.0f}"
                     if td.plan else "hold")
            paid = f" | x402 ${td.paid_usd:.2f}" if td.paid_usd else ""
            print(f"  t{t:02d} {td.regime.value:8s} on={book.risk_on_frac():.0%} "
                  f"dd={dd:.0%} {trade:18s} eq=${book.total():.2f}{paid}")
            print(f"        ↳ {td.rationale}")

    final = book.total()
    return BacktestResult(
        final_usd=round(final, 2),
        total_return=round(final / starting_usd - 1, 4),
        max_drawdown=round(max_dd, 4),
        trades=trades,
        data_spent_usd=round(budget.spent_usd, 2),
        buy_hold_return=round(bh / starting_usd - 1, 4),
    )


# --------------------------------------------------------------------------
# Live driver — same decision, real TWAK execution. One tick per call so it's
# restart-safe under a scheduler (twak serve --watch / cron). Peak persists for
# an accurate drawdown gate across restarts.
# --------------------------------------------------------------------------
import json
from pathlib import Path

_STATE = Path(".sentinel_state.json")


def _load_peak() -> float:
    if _STATE.exists():
        try:
            return float(json.loads(_STATE.read_text()).get("peak_usd", 0.0))
        except Exception:  # noqa: BLE001
            return 0.0
    return 0.0


def _save_peak(peak: float) -> None:
    _STATE.write_text(json.dumps({"peak_usd": peak}))


def live_tick(executor, source: DataSource, budget: DataBudget,
              guardrails: Guardrails = DEFAULT_GUARDRAILS) -> TickDecision:
    """One live decision+execution tick against the real TWAK wallet."""
    portfolio = executor.portfolio_usd()
    total = sum(portfolio.values())
    peak = max(_load_peak(), total)
    _save_peak(peak)
    dd = (peak - total) / peak if peak > 0 else 0.0

    td = decide_tick(portfolio, dd, source, budget, guardrails)
    print(f"[{td.regime.value}] dd={dd:.0%} target_on={td.target_risk_on:.0%} | {td.rationale}")
    print(f"  data: {td.data_reason}{' (paid $%.2f)' % td.paid_usd if td.paid_usd else ''}")
    if td.plan:
        res = executor.swap(td.plan.from_sym, td.plan.to_sym, td.plan.usd, td.rationale)
        if res.ok:
            print(f"  TRADE {td.plan.from_sym}->{td.plan.to_sym} ${td.plan.usd:.2f} "
                  f"-> {res.output or 'quoted'} tx={res.tx_hash or '(dry-run)'}")
        else:
            print(f"  TRADE BLOCKED: {res.error}")
    else:
        print("  no rebalance needed this tick")
    return td


if __name__ == "__main__":
    print("Sentinel paper backtest (mock scenario week x2):\n")
    res = run_paper(ticks=14)
    print(f"\n  Final ${res.final_usd}  |  return {res.total_return:+.1%}  "
          f"(buy&hold {res.buy_hold_return:+.1%})")
    print(f"  Max drawdown {res.max_drawdown:.1%}  |  trades {res.trades}  "
          f"|  x402 data spend ${res.data_spent_usd}")
    gate = DEFAULT_GUARDRAILS.competition_drawdown_gate
    print(f"  Drawdown gate {gate:.0%}: {'PASS' if res.max_drawdown < gate else 'BREACH'}")
