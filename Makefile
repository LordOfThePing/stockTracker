## Tracker — personal portfolio tracker.
## Targets group into: full stack, backend-only, frontend-only, native dev, tests, tools.

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
        dev deploy stop down restart logs ps build redeploy \
        prod prod-down prod-logs prod-redeploy \
        backend-build backend-up backend-stop backend-down \
        backend-restart backend-logs backend-redeploy \
        frontend-build frontend-up frontend-stop frontend-down \
        frontend-restart frontend-logs frontend-redeploy \
        setup venv front-install \
        backend-dev frontend-dev migrate \
        test test-watch \
        refresh refresh-binance refresh-manual keys-check \
        purge-mock purge-venue \
        clean clean-data

help: ## Show this help
	@echo Tracker - make targets:
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ============================================================================
# Full stack (backend + frontend)
# ============================================================================

dev: ## up --build foreground (both services)
	$(COMPOSE) up --build

deploy: ## build + up -d (both services, background)
	$(COMPOSE) build
	$(COMPOSE) up -d
	@echo Tracker running. UI http://127.0.0.1:3000  --  API http://127.0.0.1:8000/docs

build: ## (re)build both images without starting
	$(COMPOSE) build

stop: ## stop both services (keep containers)
	$(COMPOSE) stop

down: ## stop + remove both containers
	$(COMPOSE) down

restart: ## restart both services
	$(COMPOSE) restart

logs: ## tail logs from both services
	$(COMPOSE) logs -f --tail=100

ps: ## show service status
	$(COMPOSE) ps

redeploy: down deploy logs ## down → build → up -d → logs (both)

# ============================================================================
# Production (backend + tunnel, no frontend — frontend is on Cloudflare Pages)
# ============================================================================

prod: ## build + up -d backend and cloudflared
	$(COMPOSE) build backend
	$(COMPOSE) up -d backend cloudflared
	@echo API running. Tunnel active.

prod-down: ## stop + remove backend and cloudflared
	$(COMPOSE) down backend cloudflared

prod-logs: ## tail logs from backend and cloudflared
	$(COMPOSE) logs -f --tail=100 backend cloudflared

prod-redeploy: prod-down prod prod-logs ## down → build → up → logs (prod only)

# ============================================================================
# Backend only
# ============================================================================

backend-build: ## (re)build backend image without starting
	$(COMPOSE) build backend

backend-up: ## start backend container (build if needed)
	$(COMPOSE) up -d --build backend
	@echo API http://127.0.0.1:8000/docs

backend-stop: ## stop backend container (keep it)
	$(COMPOSE) stop backend

backend-down: ## stop + remove backend container
	$(COMPOSE) down backend

backend-restart: ## restart backend container
	$(COMPOSE) restart backend

backend-logs: ## tail backend logs
	$(COMPOSE) logs -f --tail=100 backend

backend-redeploy: backend-down backend-up backend-logs ## down → build → up → logs (backend only)

# ============================================================================
# Frontend only
# ============================================================================

frontend-build: ## (re)build frontend image without starting
	$(COMPOSE) build frontend

frontend-up: ## start frontend container (build if needed)
	$(COMPOSE) up -d --build frontend
	@echo UI http://127.0.0.1:3000

frontend-stop: ## stop frontend container (keep it)
	$(COMPOSE) stop frontend

frontend-down: ## stop + remove frontend container
	$(COMPOSE) down frontend

frontend-restart: ## restart frontend container
	$(COMPOSE) restart frontend

frontend-logs: ## tail frontend logs
	$(COMPOSE) logs -f --tail=100 frontend

frontend-redeploy: frontend-down frontend-up frontend-logs ## down → build → up → logs (frontend only)

# ============================================================================
# Native dev (runs uvicorn + next dev outside Docker)
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

purge-mock: ## delete all mock-sourced positions from the DB
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
	-$(RM_RF) "frontend/out"

clean-data: ## DESTRUCTIVE: also delete data/ (SQLite DB + history)
	-$(RM_RF) "data"
