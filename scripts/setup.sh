#!/usr/bin/env bash
# Run from any directory. --recreate clears only this checkout's .venv.
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"
if [[ -L .venv ]]; then
    echo "Refusing to modify a symlinked .venv." >&2
    exit 1
fi
case "${1:-}" in
    "") python3 -m venv .venv ;;
    --recreate) python3 -m venv --clear .venv ;;
    *) echo "Usage: bash scripts/setup.sh [--recreate]" >&2; exit 2 ;;
esac
.venv/bin/python -m pip install -e .
echo "Ready. Run: source .venv/bin/activate && pesc-i"
