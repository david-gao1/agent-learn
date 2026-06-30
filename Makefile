.PHONY: help verify test miniclaw-test minimal-test walkthrough readiness real-model

help:
	@echo "MiniClaw learning commands:"
	@echo "  make verify       Run full offline verification"
	@echo "  make test         Alias for verify"
	@echo "  make miniclaw-test Run MiniClaw test suite"
	@echo "  make minimal-test  Run minimal harness test suite"
	@echo "  make walkthrough  Generate MiniClaw walkthrough evidence"
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

readiness:
	scripts/check_external_readiness.sh

real-model:
	scripts/verify_real_model.sh
