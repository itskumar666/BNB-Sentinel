"""Verify every pinned BSC token actually routes via TWAK (quote-only, no funds).

Run: uv run python scripts/verify_tokens.py
"""

from __future__ import annotations

import json
import subprocess
import sys

sys.path.insert(0, ".")
from src.sentinel.tokens import BSC_ADDRESSES, resolve  # noqa: E402

QUOTE_FROM = "USDT"
QUOTE_USD = "10"


def quote(symbol: str) -> tuple[bool, str]:
    """Quote QUOTE_USD of USDT -> symbol (by address). Returns (ok, detail)."""
    if symbol == QUOTE_FROM:
        return True, "base stable"
    addr = resolve(symbol)
    cmd = ["twak", "swap", QUOTE_USD, QUOTE_FROM, addr,
           "--chain", "bsc", "--quote-only", "--json"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
        data = json.loads(out)
    except Exception as e:  # noqa: BLE001
        return False, f"call failed: {str(e)[:80]}"
    if data.get("error"):
        return False, data["error"][:80]
    return True, f"{QUOTE_USD} USDT -> {data.get('output', '?')} (via {data.get('provider', '?')})"


def main() -> int:
    failures = 0
    for symbol in BSC_ADDRESSES:
        ok, detail = quote(symbol)
        mark = "OK " if ok else "FAIL"
        print(f"  [{mark}] {symbol:6s} {detail}")
        failures += not ok
    print(f"\n{len(BSC_ADDRESSES) - failures}/{len(BSC_ADDRESSES)} tokens route cleanly.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
