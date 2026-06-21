#!/bin/bash
# Screen-record this for real terminal footage to drop into Google Flow.
# It types each command, runs it live, and pauses so the output is readable.
# Run from the project root:  bash demo_run.sh
set -e
cd "$(dirname "$0")"

# colors
B=$'\033[1m'; DIM=$'\033[2m'; GRN=$'\033[32m'; YEL=$'\033[33m'; BLU=$'\033[34m'; CYN=$'\033[36m'; RST=$'\033[0m'
PROMPT="${GRN}➜${RST} ${BLU}sentinel${RST} "

pause() { sleep "${1:-2.2}"; }

# type a command out like a human, then newline
type_cmd() {
  printf "%s" "$PROMPT"
  local s="$1"
  for ((i=0; i<${#s}; i++)); do printf "%s" "${s:$i:1}"; sleep 0.025; done
  printf "\n"; sleep 0.5
}

header() { printf "\n${DIM}── %s ──${RST}\n\n" "$1"; }

clear
printf "${B}${YEL}  Sentinel — live demo${RST}\n"
printf "${DIM}  capital-preservation regime rotator · real CoinMarketCap data${RST}\n\n"
pause 2

# 1) live decision
header "1 / 3  ·  the live decision (real CMC data + self-managed x402 budget)"
type_cmd "uv run python live_read.py"
uv run python live_read.py
pause 4.5

# 2) backtest
header "2 / 3  ·  backtest over a full market cycle"
type_cmd "uv run python skills/sentinel-regime-rotator/scripts/backtest.py"
uv run python skills/sentinel-regime-rotator/scripts/backtest.py | tail -12
pause 5

# 3) engine tests
header "3 / 3  ·  the deterministic engine, unit-tested"
type_cmd "uv run python tests/test_regime.py"
uv run python tests/test_regime.py | grep -iE "\[OK|scenarios passed"
pause 3.5

# on-chain identity (text)
header "on-chain proof  ·  ERC-8004 identity bound to the trading wallet"
printf "  ${DIM}Standard    ${RST} ${GRN}ERC-8004 on-chain agent identity${RST}\n"
printf "  ${DIM}agentId     ${RST} ${GRN}1442  (BSC testnet)${RST}\n"
printf "  ${DIM}tx          ${RST} ${GRN}0xc8609aea…d6d4d2d4${RST}\n"
printf "  ${DIM}bound wallet${RST} ${GRN}0xD8C5…8624  (the TWAK trading wallet)${RST}\n"
pause 4

printf "\n${B}${YEL}  Capital-preserving. Explainable. Self-custody. That's Sentinel.${RST}\n\n"
