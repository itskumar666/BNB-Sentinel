"""Canonical BSC (BNB Smart Chain) token registry for Sentinel's trading universe.

TWAK resolves a few tokens by symbol (USDT, USDC, ETH) but most need an explicit
contract address — and its `search` is noisy (searching "UNI" returns unrelated tokens,
"ETH" surfaces a look-alike before the canonical Binance-Peg token). So we PIN canonical
addresses here and verify each one actually routes via `twak swap --quote-only`
(see `scripts/verify_tokens.py`).

Eligibility note: the competition counts trades in the 149 CMC-eligible tokens. These
Binance-Peg / official BSC contracts are what CMC tracks on BSC; cross-check against the
CMC Agent Hub token lookup once wired before going live.
"""

from __future__ import annotations

# symbol -> canonical BSC (BEP-20) contract address
BSC_ADDRESSES: dict[str, str] = {
    # --- stables (risk-off) ---
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
    "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
    "FDUSD": "0xc5f0f7b66764F6ec8C8Dff7BA683102295E16409",
    "DAI": "0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3",
    # --- blue-chips (risk-on) ---
    "ETH": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",   # Binance-Peg ETH
    "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",  # PancakeSwap
    "LINK": "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",  # Binance-Peg LINK
    "UNI": "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1",   # Binance-Peg UNI
    "DOT": "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402",   # Binance-Peg DOT
}

# Decimals for sizing/normalization. Pegged BSC tokens are 18 decimals (unlike
# native USDT/USDC on Ethereum which are 6) — important when computing amounts.
BSC_DECIMALS: dict[str, str] = {s: 18 for s in BSC_ADDRESSES}


def resolve(symbol: str) -> str:
    """Return the canonical BSC contract address for a symbol, or raise."""
    try:
        return BSC_ADDRESSES[symbol]
    except KeyError:
        raise ValueError(f"No pinned BSC address for {symbol!r}; refusing to guess.")
