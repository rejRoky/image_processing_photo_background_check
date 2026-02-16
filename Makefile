# =============================================================================
# Photo Background Check - Makefile
# Common development and deployment commands
# =============================================================================

.PHONY: help install install-dev run test lint format migrate shell docker-build docker-up docker-down clean

# Default target
help:
	@echo "Photo Background Check - Available Commands"
	@echo "============================================"
	@echo ""
	@echo "Development:"
	@echo "  make install        Install production dependencies"
	@echo "  make install-dev    Install development dependencies"
	@echo "  make run            Run development server"
	@echo "  make shell          Open Django shell"
	@echo "  make migrate        Run database migrations"
	@echo "  make migrations     Create new migrations"
	@echo "  make superuser      Create a superuser"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test           Run tests"
	@echo "  make test-cov       Run tests with coverage"
	@echo "  make lint           Run linters"
	@echo "  make format         Format code"
	@echo "  make check          Run all checks (lint + test)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build Docker images"
	@echo "  make docker-up      Start Docker containers"
	@echo "  make docker-down    Stop Docker containers"
	@echo "  make docker-logs    View Docker logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          Remove generated files"
	@echo "  make collectstatic  Collect static files"

# =============================================================================
# Development
# =============================================================================

install:
	pip install -r requirements/production.txt

install-dev:
	pip install -r requirements/development.txt
	pre-commit install

run:
	python manage.py runserver

shell:
	python manage.py shell_plus

migrate:
	python manage.py migrate

migrations:
	python manage.py makemigrations

superuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput

# =============================================================================
# Testing & Quality
# =============================================================================

test:
	pytest

test-cov:
	pytest --cov=photo_checker --cov-report=html --cov-report=term

lint:
	flake8 photo_checker photo_background_check
	mypy photo_checker

format:
	black photo_checker photo_background_check
	isort photo_checker photo_background_check

check: lint test

# =============================================================================
# Docker
# =============================================================================

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-dev:
	docker-compose -f docker-compose.dev.yml up --build

docker-shell:
	docker-compose exec web python manage.py shell

docker-migrate:
	docker-compose exec web python manage.py migrate

# =============================================================================
# Celery
# =============================================================================

celery-worker:
	celery -A photo_background_check worker -l INFO

celery-beat:
	celery -A photo_background_check beat -l INFO

celery-flower:
	celery -A photo_background_check flower

# =============================================================================
# Maintenance
# =============================================================================

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf .tox/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

logs-dir:
	mkdir -p logs

setup-dev: install-dev migrate logs-dir
	@echo "Development environment ready!"
