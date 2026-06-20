"""Real CMC Agent Hub data source — live signals via the CoinMarketCap MCP.

Implements the same `DataSource` interface as the mock, so it drops straight into the agent
loop. Mirrors the x402 data-budget split:
  - heartbeat() = CHEAP: Fear & Greed + market RSI/MACD (get_global_metrics_latest,
    get_crypto_marketcap_technical_analysis)
  - deep()      = PAID:  derivatives funding rate (get_global_crypto_derivatives_metrics),
    fetched only when the budget policy says a decision is at stake.

Uses the CMC MCP endpoint (https://mcp.coinmarketcap.com/mcp) with the X-CMC-MCP-API-KEY
header. Each call costs 1 CMC credit — `DataBudget` keeps the agent frugal with them.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request

from .base import Signals

MCP_URL = "https://mcp.coinmarketcap.com/mcp"


def _num(s) -> float | None:
    """Extract a leading signed float from values like '12.56 B', '-69.89 B', '0.0019'."""
    if s is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(s))
    return float(m.group()) if m else None


class CMCClient:
    def __init__(self, api_key: str | None = None, timeout: int = 30):
        self.api_key = api_key or os.environ["CMC_API_KEY"]
        self.timeout = timeout
        self._id = 0

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        self._id += 1
        body = json.dumps({
            "jsonrpc": "2.0", "id": self._id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }).encode()
        req = urllib.request.Request(MCP_URL, data=body, headers={
            "X-CMC-MCP-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        })
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode())
        content = payload.get("result", {}).get("content", [])
        if not content:
            raise RuntimeError(f"{name}: {json.dumps(payload)[:200]}")
        return json.loads(content[0]["text"])


class CMCDataSource:
    """Live DataSource backed by the CMC MCP. Credit cost per deep fetch ~= 1."""

    def __init__(self, client: CMCClient | None = None, deep_cost: float = 0.02):
        self.client = client or CMCClient()
        self.deep_cost = deep_cost

    def heartbeat(self) -> Signals:
        gm = self.client.call_tool("get_global_metrics_latest")
        fg = int(_num(gm.get("sentiment", {}).get("fear_greed", {})
                       .get("current", {}).get("index")) or 50)

        ta = self.client.call_tool("get_crypto_marketcap_technical_analysis")
        rsi = _num(ta.get("rsi", {}).get("rsi14"))
        macd = ta.get("macd", {})
        macd_hist = _num(macd.get("histogram"))
        macd_line, sig_line = _num(macd.get("macdLine")), _num(macd.get("signalLine"))
        ema = (macd_line > sig_line) if (macd_line is not None and sig_line is not None) else None

        return Signals(fear_greed=fg, rsi=rsi, macd_hist=macd_hist, ema_fast_over_slow=ema)

    def deep(self, base: Signals) -> tuple[Signals, float]:
        dv = self.client.call_tool("get_global_crypto_derivatives_metrics")
        funding = _num(dv.get("fundingRate", {}).get("current"))
        enriched = Signals(
            fear_greed=base.fear_greed, rsi=base.rsi, macd_hist=base.macd_hist,
            ema_fast_over_slow=base.ema_fast_over_slow, funding_rate=funding,
        )
        return enriched, self.deep_cost

    def advance(self) -> None:  # no-op; live source is always "now"
        pass
