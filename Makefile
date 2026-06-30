.PHONY: help verify test miniclaw-test minimal-test walkthrough learn-check readiness real-model

help:
	@echo "MiniClaw learning commands:"
	@echo "  make verify       Run full offline verification"
	@echo "  make test         Alias for verify"
	@echo "  make miniclaw-test Run MiniClaw test suite"
	@echo "  make minimal-test  Run minimal harness test suite"
	@echo "  make walkthrough  Generate MiniClaw walkthrough evidence"
	@echo "  make learn-check  Run short MiniClaw learning acceptance"
	@echo "  make readiness    Check git/model external readiness"
	@echo "  make real-model   Run gated real-model smoke tests"

verify:
	scripts/verify_offline.sh

test: verify

miniclaw-test:
	python3 -m unittest discover -s prototypes/miniclaw_harness/tests -v

minimal-test:
	python3 -m unittest discover -s prototypes/minimal_harness_agent/tests -v

walkthrough:
	scripts/run_miniclaw_walkthrough.sh

learn-check:
	@tmp="$$(mktemp -d)"; \
	workspace="$$tmp/workspace"; \
	mkdir -p "$$workspace/tests"; \
	printf '# Demo\n' > "$$workspace/README.md"; \
	printf 'import unittest\n\nclass SmokeTest(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n' > "$$workspace/tests/test_smoke.py"; \
	python3 prototypes/miniclaw_harness/main.py --db "$$tmp/miniclaw.db" --workspace "$$workspace" learn-check

readiness:
	scripts/check_external_readiness.sh

real-model:
	scripts/verify_real_model.sh
