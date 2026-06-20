"""Sentinel configuration: guardrails + the competition token allowlist.

This module is intentionally credential-free and fully knowable today. It encodes the
"rules you set" that make Sentinel safe to run unattended — the spine the TWAK special
prize is scored on (autonomous execution + guardrails).

Contract addresses for each symbol are resolved at runtime via the CMC Agent Hub /
TWAK token lookups; we never hardcode a swap target that isn't on the eligible list.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Eligible tokens — the 149 CMC-listed BEP-20 tokens from the competition rules.
# Trades outside this set do not count, so we reject them BEFORE signing.
# (Symbols as published; kept verbatim incl. non-ASCII. Dedup handled by the set.)
# ---------------------------------------------------------------------------
ELIGIBLE_TOKENS: frozenset[str] = frozenset({
    "ETH", "USDT", "USDC", "XRP", "TRX", "DOGE", "ZEC", "ADA", "LINK", "BCH",
    "DAI", "TON", "USD1", "USDe", "M", "LTC", "AVAX", "SHIB", "XAUt", "WLFI",
    "H", "DOT", "UNI", "ASTER", "DEXE", "USDD", "ETC", "AAVE", "ATOM", "U",
    "STABLE", "FIL", "INJ", "币安人生", "NIGHT", "FET", "TUSD", "BONK", "PENGU", "CAKE",
    "SIREN", "LUNC", "ZRO", "KITE", "FDUSD", "BEAT", "PIEVERSE", "BTT", "NFT", "EDGE",
    "FLOKI", "LDO", "B", "FF", "PENDLE", "NEX", "STG", "AXS", "TWT", "HOME",
    "RAY", "COMP", "GWEI", "XCN", "GENIUS", "XPL", "BAT", "SKYAI", "APE", "IP",
    "SFP", "TAG", "NXPC", "AB", "SAHARA", "1INCH", "CHEEMS", "BANANAS31", "RIVER", "MYX",
    "RAVE", "SNX", "FORM", "LAB", "HTX", "USDf", "CTM", "BDX", "SLX", "UB",
    "DUCKY", "FRAX", "BILL", "WFI", "KOGE", "ALE", "FRXUSD", "USDF", "GOMINING", "VCNT",
    "GUA", "DUSD", "SMILEK", "0G", "BEAM", "MY", "SOON", "REAL", "Q", "AIOZ",
    "ZIG", "YFI", "TAC", "lisUSD", "CYS", "ZAMA", "TRIA", "HUMA", "PLUME", "ZIL",
    "XPR", "ZETA", "BabyDoge", "NILA", "ROSE", "VELO", "UAI", "BRETT", "OPEN", "BSB",
    "TOSHI", "BAS", "ACH", "AXL", "LUR", "ELF", "KAVA", "APR", "IRYS", "EURI",
    "XUSD", "BARD", "DUSK", "SUSHI", "PEAQ", "COAI", "BDCA", "XAUM",
})

# ---------------------------------------------------------------------------
# Trading universe — Sentinel only TOUCHES a curated, liquid subset of the
# eligible list. The full list above is the validation gate; these are the
# baskets the strategy actually rotates between.
# ---------------------------------------------------------------------------

# Risk-off: deep, liquid stables on BSC. Capital parks here when fear is high.
# (USD1 dropped: its BSC contract was ambiguous in TWAK search; revisit via CMC lookup.)
RISK_OFF_BASKET: tuple[str, ...] = ("USDT", "USDC", "FDUSD", "DAI")

# Risk-on: liquid blue-chips on PancakeSwap that are also CMC-eligible.
RISK_ON_BASKET: tuple[str, ...] = ("ETH", "CAKE", "LINK", "UNI", "DOT")

# The single asset we hold as the "home base" / quote for sizing.
BASE_STABLE: str = "USDT"


@dataclass(frozen=True)
class Guardrails:
    """Hard rules that make Sentinel safe to run unattended.

    Drawdown math uses a margin below the competition gate so a noisy BSC hour can
    never push us across the disqualification line.
    """

    # Competition disqualification gate (the rules say "for example 30%").
    competition_drawdown_gate: float = 0.30

    # Our HARD internal stop — flatten to BASE_STABLE and halt new risk if breached.
    hard_drawdown_stop: float = 0.20

    # Softer DE-RISK trigger — rotate the whole book to stables but keep running.
    derisk_drawdown: float = 0.12

    # Per-trade and per-day notional caps (USD). Bound the blast radius.
    per_trade_usd_cap: float = 50.0
    daily_usd_cap: float = 150.0

    # Don't bother trading deltas smaller than this (avoid dust churn + gas waste).
    min_trade_usd: float = 5.0

    # Max acceptable slippage per swap, in basis points (100 bps = 1%).
    max_slippage_bps: int = 80

    # Stay qualified: the rules require >= 1 eligible trade per day.
    min_trades_per_day: int = 1

    # Minimum portfolio value (USD) below which we stop trading (dust protection;
    # the rules score any hour starting <= $1 as 0%).
    min_portfolio_usd: float = 5.0

    # Decision cadence in seconds (hourly matches the hourly scoring window).
    decision_interval_sec: int = 3600

    # Tokens Sentinel is allowed to actually hold/trade (must be a subset of eligible).
    allowed: frozenset[str] = field(
        default_factory=lambda: frozenset(RISK_OFF_BASKET) | frozenset(RISK_ON_BASKET)
    )

    def is_eligible(self, symbol: str) -> bool:
        """A symbol must be both competition-eligible and in our allowed basket."""
        return symbol in ELIGIBLE_TOKENS and symbol in self.allowed


# Sanity: every token we plan to trade must be on the competition eligible list.
_universe = set(RISK_OFF_BASKET) | set(RISK_ON_BASKET) | {BASE_STABLE}
_off_list = _universe - ELIGIBLE_TOKENS
assert not _off_list, f"Trading universe contains non-eligible tokens: {sorted(_off_list)}"


DEFAULT_GUARDRAILS = Guardrails()
