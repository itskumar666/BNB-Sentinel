"""TWAK execution layer — the SOLE path from a decision to an on-chain trade.

Every trade goes through `twak swap`, signed locally by the agent wallet (key in the OS
keychain, never leaves the device). Guardrails are enforced HERE, before any signing:
allowlist, per-trade cap, daily cap, slippage. Nothing reaches the signer unless it passes.

`dry_run=True` uses `--quote-only` (no funds, no signature) so the whole loop is testable
at $0. Flip to `dry_run=False` once the wallet is funded on mainnet.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

from ..config import DEFAULT_GUARDRAILS, Guardrails
from ..tokens import resolve


class GuardrailViolation(Exception):
    """Raised when a proposed trade breaks a rule. Never reaches the signer."""


@dataclass
class TradeResult:
    ok: bool
    from_sym: str
    to_sym: str
    usd: float
    rationale: str
    dry_run: bool
    output: str | None = None      # human-readable amount out / quote
    tx_hash: str | None = None     # on-chain proof when executed
    provider: str | None = None
    error: str | None = None


@dataclass
class TwakExecutor:
    guardrails: Guardrails = field(default_factory=lambda: DEFAULT_GUARDRAILS)
    chain: str = "bsc"
    dry_run: bool = True
    _spent_today_usd: float = 0.0
    _trades_today: int = 0

    # -- low-level CLI --------------------------------------------------------
    def _twak(self, args: list[str]) -> dict:
        cmd = ["twak", *args, "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        raw = proc.stdout.strip() or proc.stderr.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": raw[:200] or f"twak exited {proc.returncode}"}

    def _token_arg(self, symbol: str) -> str:
        """Stables/ETH resolve by symbol in TWAK; everything else needs an address."""
        symbol_native = {"USDT", "USDC", "ETH"}
        return symbol if symbol in symbol_native else resolve(symbol)

    # -- reads ----------------------------------------------------------------
    def portfolio_usd(self) -> dict[str, float]:
        """Return {symbol: usdValue} for non-zero holdings on this chain."""
        data = self._twak(["wallet", "portfolio"])
        out: dict[str, float] = {}
        rows = data if isinstance(data, list) else data.get("portfolio", [])
        for row in rows:
            if row.get("chain") != self.chain:
                continue
            usd = float(row.get("usdValue") or 0)
            if usd > 0:
                out[row.get("symbol", "?")] = out.get(row.get("symbol", "?"), 0) + usd
        return out

    def quote(self, from_sym: str, to_sym: str, usd: float) -> dict:
        # --usd form: `swap <from> <to> --usd <amount>` (size in USD, any source token).
        return self._twak([
            "swap", self._token_arg(from_sym), self._token_arg(to_sym),
            "--usd", str(usd), "--chain", self.chain, "--quote-only",
        ])

    # -- the guarded trade ----------------------------------------------------
    def _check_guardrails(self, from_sym: str, to_sym: str, usd: float) -> None:
        g = self.guardrails
        if not g.is_eligible(to_sym):
            raise GuardrailViolation(f"{to_sym} not in allowed eligible basket")
        if from_sym != "USDT" and not g.is_eligible(from_sym):
            raise GuardrailViolation(f"{from_sym} not in allowed eligible basket")
        if usd > g.per_trade_usd_cap:
            raise GuardrailViolation(
                f"${usd:.2f} exceeds per-trade cap ${g.per_trade_usd_cap:.2f}")
        if self._spent_today_usd + usd > g.daily_usd_cap:
            raise GuardrailViolation(
                f"would exceed daily cap ${g.daily_usd_cap:.2f} "
                f"(spent ${self._spent_today_usd:.2f})")

    def swap(self, from_sym: str, to_sym: str, usd: float, rationale: str) -> TradeResult:
        """Guarded swap. Dry-run quotes; live mode signs locally and returns a tx hash."""
        try:
            self._check_guardrails(from_sym, to_sym, usd)
        except GuardrailViolation as e:
            return TradeResult(False, from_sym, to_sym, usd, rationale,
                               self.dry_run, error=f"GUARDRAIL: {e}")

        slippage_pct = self.guardrails.max_slippage_bps / 100.0
        args = ["swap", self._token_arg(from_sym), self._token_arg(to_sym),
                "--usd", str(usd), "--chain", self.chain,
                "--slippage", str(slippage_pct)]
        if self.dry_run:
            args.append("--quote-only")
        # NOTE: no --password on CLI (leaks to shell history); TWAK falls back to
        # the OS keychain for local signing. That IS the self-custody loop.

        data = self._twak(args)
        if data.get("error"):
            return TradeResult(False, from_sym, to_sym, usd, rationale,
                               self.dry_run, error=data["error"])

        if not self.dry_run:
            self._spent_today_usd += usd
            self._trades_today += 1
        return TradeResult(
            ok=True, from_sym=from_sym, to_sym=to_sym, usd=usd, rationale=rationale,
            dry_run=self.dry_run, output=data.get("output"),
            tx_hash=data.get("txHash") or data.get("hash"),
            provider=data.get("provider"),
        )

    @property
    def trades_today(self) -> int:
        return self._trades_today
