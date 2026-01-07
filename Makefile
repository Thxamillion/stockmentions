# Makefile for Stock Mentions

.PHONY: help test test-v test-cov install-dev clean

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install-dev:  ## Install development dependencies
	pip3 install --break-system-packages -r requirements-dev.txt

test:  ## Run all tests
	python3 -m pytest tests/

test-v:  ## Run tests with verbose output
	python3 -m pytest tests/ -v

test-cov:  ## Run tests with coverage report
	python3 -m pytest tests/ --cov=worker --cov-report=term-missing

test-ticker:  ## Run only ticker extraction tests
	python3 -m pytest tests/test_ticker_extraction.py -v

clean:  ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov .coverage
