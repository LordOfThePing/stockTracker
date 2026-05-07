## Tracker — local-only personal portfolio tracker.
## Targets group into: docker stack, native dev, tests, tools.

ROOT := $(abspath $(CURDIR))

ifeq ($(OS),Windows_NT)
	VENV_PY  := $(ROOT)/backend/.venv/Scripts/python.exe
	VENV_PIP := $(ROOT)/backend/.venv/Scripts/pip.exe
	RM_RF    := powershell -NoProfile -Command "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
else
	VENV_PY  := $(ROOT)/backend/.venv/bin/python
	VENV_PIP := $(ROOT)/backend/.venv/bin/pip
	RM_RF    := rm -rf
endif

COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: help \
        dev deploy stop down restart logs ps build \
        setup venv front-install \
        backend-dev frontend-dev migrate \
        test test-watch \
        refresh refresh-binance refresh-manual keys-check \
        clean clean-data

help: ## Show this help
	@echo Tracker - make targets:
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ============================================================================
# Docker stack — primary path; binds services to 127.0.0.1 only.
# ============================================================================

dev: ## docker compose up --build (foreground, follows logs)
	$(COMPOSE) up --build

deploy: ## docker compose build + up -d (background; still localhost-only)
	$(COMPOSE) build
	$(COMPOSE) up -d
	@echo Tracker running. UI http://127.0.0.1:3000  --  API http://127.0.0.1:8000/docs

build: ## (re)build images without starting
	$(COMPOSE) build

stop: ## docker compose stop (keep containers)
	$(COMPOSE) stop

down: ## docker compose down (stop + remove containers)
	$(COMPOSE) down

restart: ## restart both services
	$(COMPOSE) restart

logs: ## tail logs from both services
	$(COMPOSE) logs -f --tail=100

ps: ## show service status
	$(COMPOSE) ps

redeploy: down deploy logs

# ============================================================================
# Native dev (alternate path; runs uvicorn + next dev outside Docker).
# ============================================================================

setup: venv front-install migrate ## one-shot: venv + npm install + first migration

venv: ## create backend/.venv and install Python deps
	python -m venv backend/.venv
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r backend/requirements.txt

front-install: ## npm install in frontend/
	cd frontend && npm install

backend-dev: ## run backend natively (uvicorn --reload, host 127.0.0.1)
	cd backend && $(VENV_PY) -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

frontend-dev: ## run frontend natively (next dev, port 3000)
	cd frontend && npm run dev

migrate: ## alembic upgrade head (against ./data/tracker.db)
	cd backend && $(VENV_PY) -m alembic upgrade head

# ============================================================================
# Tests
# ============================================================================

test: ## run pytest in the backend venv
	cd backend && $(VENV_PY) -m pytest -v

test-watch: ## re-run pytest on change (requires pytest-watch)
	cd backend && $(VENV_PY) -m pytest_watch

# ============================================================================
# Operational helpers
# ============================================================================

refresh: ## POST /api/refresh/all on the running backend
	curl -fsS -X POST http://127.0.0.1:8000/api/refresh/all && echo

refresh-binance: ## POST /api/refresh/binance
	curl -fsS -X POST http://127.0.0.1:8000/api/refresh/binance && echo

refresh-manual: ## POST /api/refresh/manual
	curl -fsS -X POST http://127.0.0.1:8000/api/refresh/manual && echo

keys-check: ## report whether Binance keys are configured (NEVER prints values)
	@cd backend && $(VENV_PY) -c "from app.config import get_settings; print('binance_enabled:', get_settings().binance_enabled)"

purge-mock: ## delete all mock-sourced positions/accounts/sync_runs from the DB
	curl -fsS -X DELETE http://127.0.0.1:8000/api/admin/venue/mock && echo

purge-venue: ## delete all rows for VENUE=<name> (e.g. make purge-venue VENUE=mock)
	@if [ -z "$(VENUE)" ]; then echo "usage: make purge-venue VENUE=<name>"; exit 1; fi
	curl -fsS -X DELETE http://127.0.0.1:8000/api/admin/venue/$(VENUE) && echo

# ============================================================================
# Cleanup
# ============================================================================

clean: ## remove venv, node_modules, build artifacts (keeps data/)
	-$(RM_RF) "backend/.venv"
	-$(RM_RF) "backend/.pytest_cache"
	-$(RM_RF) "backend/__pycache__"
	-$(RM_RF) "frontend/node_modules"
	-$(RM_RF) "frontend/.next"

clean-data: ## DESTRUCTIVE: also delete data/ (SQLite DB + history)
	-$(RM_RF) "data"
