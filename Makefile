# Liquidation Risk Makefile

.PHONY: help setup install-deps clean format lint type-check test

REPO := $(shell pwd)

# Default target
help:
	@echo 'Liquidation Risk'
	@echo ''
	@echo 'Available targets:'
	@echo '  install         - Install Python dependencies'
	@echo '  clean           - Clean up build artifacts'
	@echo '  format          - Format code with black and ruff'
	@echo '  lint            - Run linting checks'
	@echo '  type-check      - Run type checking with mypy' 
	@echo '  test            - Run all tests'
	@echo '  check           - Run all checks (format, lint, type-check)'
	@echo ''

install:
	@echo '📦 Installing dependencies with uv...'
	uv sync

# Code quality
format:
	@echo '🎨 Formatting code...'
	uv run --all-extras ruff format evc_batch_decoder/ tests/ && uv run --all-extras ruff check evc_batch_decoder/ tests/ --fix

lint:
	@echo '🔍 Running linting checks...'
	uv run --all-extras ruff check evc_batch_decoder/ && uv run --all-extras pylint evc_batch_decoder/

type-check:
	@echo '🔍 Running type checks...'
	uv run --all-extras mypy evc_batch_decoder/ --explicit-package-bases

# Combined check
check: type-check format lint
	@echo '✅ All checks passed'

# Testing
test:
	@echo '🧪 Running all tests...'
	uv run --all-extras pytest tests/ -v --cov=evc_batch_decoder --cov-report=term-missing

# Clean up
clean:
	@echo '🧹 Cleaning up build artifacts...'
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

# Version management
bump-version:
	@current=$$(grep '__version__' shared/__init__.py | cut -d''' -f2); \
	major=$$(echo $$current | cut -d. -f1); \
	minor=$$(echo $$current | cut -d. -f2); \
	patch=$$(echo $$current | cut -d. -f3); \
	new_patch=$$((patch + 1)); \
	new_version='$$major.$$minor.$$new_patch'; \
	sed -i '' 's/__version__ = \'$$current\'/__version__ = \'$$new_version\'/' shared/__init__.py; \
	echo 'Version bumped from $$current to $$new_version'

bump-minor:
	@current=$$(grep '__version__' shared/__init__.py | cut -d''' -f2); \
	major=$$(echo $$current | cut -d. -f1); \
	minor=$$(echo $$current | cut -d. -f2); \
	new_minor=$$((minor + 1)); \
	new_version='$$major.$$new_minor.0'; \
	sed -i '' 's/__version__ = \'$$current\'/__version__ = \'$$new_version\'/' shared/__init__.py; \
	echo 'Version bumped from $$current to $$new_version'

# Information
info:
	@echo 'Liquidation Risk'
	@echo 'Version: $$(grep '__version__' shared/__init__.py | cut -d'\'' -f2 2>/dev/null || echo '2.0.0')'
	@echo 'Python: $$(uv run python --version 2>/dev/null || echo 'Python not available')'
	@echo 'Dependencies: $$(uv pip list 2>/dev/null | grep -E '(web3|pydantic)' | wc -l) key packages installed'


