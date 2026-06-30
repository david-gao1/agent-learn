#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is required for real model verification." >&2
  echo "Usage: OPENAI_API_KEY=... scripts/verify_real_model.sh" >&2
  exit 2
fi

export RUN_REAL_MODEL_TESTS=1

cd "$ROOT_DIR"

echo "== MiniClaw real model runtime smoke =="
python3 -m unittest \
  prototypes.miniclaw_harness.tests.test_miniclaw_harness.MiniClawHarnessTest.test_miniclaw_real_model_smoke \
  -v

echo "== MiniClaw real model planner smoke =="
python3 -m unittest \
  prototypes.miniclaw_harness.tests.test_miniclaw_harness.MiniClawHarnessTest.test_miniclaw_real_model_planner_smoke \
  -v

echo "== MiniClaw real model CodeAct smoke =="
python3 -m unittest \
  prototypes.miniclaw_harness.tests.test_miniclaw_harness.MiniClawHarnessTest.test_miniclaw_real_model_codeact_smoke \
  -v

echo "== minimal harness real model Plan-Act smoke =="
python3 -m unittest \
  prototypes.minimal_harness_agent.tests.test_minimal_harness_agent.MinimalHarnessAgentTest.test_real_model_plan_act_smoke \
  -v

echo "Real model verification complete"
