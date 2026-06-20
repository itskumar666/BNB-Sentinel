"""ERC-8004 on-chain identity for Sentinel, via the BNB AI Agent SDK (bnbagent-sdk).

This is the "who is this agent" layer (Best Use of BNB AI Agent SDK). We mint an ERC-8004
identity NFT on BSC testnet (gas-free via the SDK's paymaster), then **bind it on-chain to
the TWAK trading wallet** with a `tradingWallet` metadata entry. That linkage — discoverable
identity ↔ self-custody execution wallet ↔ competition registration — is the inventive part:
anyone can verify that this published identity is the wallet actually trading.

Run: uv run python -m src.sentinel.identity.bnb
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from bnbagent import AgentEndpoint, ERC8004Agent, EVMWalletProvider

WALLETS_DIR = Path(".wallets")
NETWORK = "bsc-testnet"


def register_identity() -> dict:
    load_dotenv()
    password = os.environ["IDENTITY_WALLET_PASSWORD"]
    trading_wallet = os.environ.get("TWAK_AGENT_WALLET_ADDRESS", "")

    # Persisted Keystore V3 — the identity key is generated locally and stays local.
    wallet = EVMWalletProvider(
        password=password, persist=True, wallets_dir=str(WALLETS_DIR)
    )
    info = wallet.get_wallet_info()
    print(f"Identity wallet: {info.get('address')}")

    agent = ERC8004Agent(wallet, network=NETWORK, debug=True)

    endpoints = [
        AgentEndpoint(
            name="strategy",
            endpoint="https://github.com/ashutosh/bnb-sentinel",
            capabilities=["spot-rotation", "self-custody", "capital-preservation"],
        ),
    ]
    agent_uri = agent.generate_agent_uri(
        name="Sentinel",
        description=(
            "Capital-preservation autonomous trader on BNB Chain. Rotates risk-on/"
            "risk-off on CMC signals via self-custody TWAK local signing, inside hard "
            "guardrails. Explains every trade in plain English."
        ),
        endpoints=endpoints,
    )

    metadata = []
    if trading_wallet:
        metadata.append({"key": "tradingWallet", "value": trading_wallet})
    metadata.append({"key": "executionLayer", "value": "TrustWalletAgentKit"})

    result = agent.register_agent(agent_uri, metadata=metadata or None)
    print(f"Registered ERC-8004 agentId={result.get('agentId')} "
          f"tx={result.get('transactionHash')}")
    return result


if __name__ == "__main__":
    res = register_identity()
    agent_id = res.get("agentId")
    if agent_id is not None:
        # write the agentId back to .env
        env = Path(".env")
        lines = env.read_text().splitlines()
        out, seen = [], False
        for ln in lines:
            if ln.startswith("AGENT_ID="):
                out.append(f"AGENT_ID={agent_id}")
                seen = True
            else:
                out.append(ln)
        if not seen:
            out.append(f"AGENT_ID={agent_id}")
        env.write_text("\n".join(out) + "\n")
        print(f"Wrote AGENT_ID={agent_id} to .env")
