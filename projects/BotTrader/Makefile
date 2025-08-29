.PHONY: help install test test-coverage run-dev run-prod clean lint format docker-build docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m\033[0m"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install dependencies
	pip install -r requirements.txt
	pip install -e .

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests
	pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests
	pytest tests/e2e/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint: ## Run code linting
	flake8 src/ tests/
	mypy src/

format: ## Format code with black
	black src/ tests/

clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

##@ Running

run-dev: ## Run in development mode
	python -m src.core.bot --env development

run-prod: ## Run in production mode
	python -m src.core.bot --env production

run-backtest: ## Run backtesting
	python -m src.strategies.backtest --config config/config.yaml

##@ Docker

docker-build: ## Build Docker image
	docker-compose build

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

##@ Database

db-migrate: ## Run database migrations
	python scripts/migrate_db.py

db-seed: ## Seed database with test data
	python scripts/seed_db.py

##@ ML Models

train-transformer: ## Train Transformer model
	python -m src.ml.training.trainer --model transformer

train-lstm: ## Train LSTM model
	python -m src.ml.training.trainer --model lstm

train-xgboost: ## Train XGBoost model
	python -m src.ml.training.trainer --model xgboost

train-all: ## Train all models
	python -m src.ml.training.trainer --model all

##@ Monitoring

monitor: ## Start monitoring dashboard
	python -m src.monitoring.dashboard

logs: ## Tail application logs
	tail -f logs/bot.log

##@ Deployment

deploy-railway: ## Deploy to Railway
	railway up

deploy-check: ## Check deployment status
	railway status