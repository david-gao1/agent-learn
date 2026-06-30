#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"

cd "$ROOT_DIR"

echo "== MiniClaw tests =="
if [[ "${MINICLAW_VERIFY_NESTED:-0}" == "1" ]]; then
  python3 -m unittest \
    prototypes.miniclaw_harness.tests.test_miniclaw_harness.MiniClawHarnessTest.test_walkthrough_script_exports_learning_evidence \
    -v
else
  python3 -m unittest discover -s prototypes/miniclaw_harness/tests -v
fi

echo "== minimal harness tests =="
python3 -m unittest discover -s prototypes/minimal_harness_agent/tests -v

echo "== walkthrough evidence =="
"$ROOT_DIR/scripts/run_miniclaw_walkthrough.sh" --output "$TMP_DIR/walkthrough-output"

echo "== whitespace check =="
git diff --check

echo "Offline verification complete"
