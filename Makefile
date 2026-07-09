.PHONY: check test test-unit test-tariff lint sqlcheck tmdl-lint fmt clean help

help:
	@echo "targets: check | test | test-unit | test-tariff | lint | sqlcheck | tmdl-lint | fmt | clean"

check: lint sqlcheck tmdl-lint test-unit  ## Backpressure stack (pre-commit)

lint:
	ruff check scripts/ tests/

sqlcheck:
	sqlfluff lint scripts/ --dialect tsql

tmdl-lint:
	python scripts/tmdl_lint.py semantic_model/itrade_tariff_model.SemanticModel/definition

test: test-unit test-tariff

test-unit:
	pytest tests/unit/ -v --timeout=60

test-tariff:
	pytest tests/tariff/ -v --timeout=60

fmt:
	ruff format scripts/ tests/
	ruff check --fix scripts/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
