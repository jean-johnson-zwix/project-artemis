.PHONY: setup migrate migrate-dev seed dev-frontend dev-backend \
        docker-up docker-down docker-reset

# ---------------------------------------------------------------------------
# First-time setup
# Creates .env from the example and symlinks it into each service directory
# so local dev works without maintaining multiple env files.
# ---------------------------------------------------------------------------
setup:
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env — fill in your API keys before continuing."; fi
	@ln -sf ../.env data-explorer/.env  && echo "Linked data-explorer/.env -> ../.env"
	@ln -sf ../.env backend/.env        && echo "Linked backend/.env -> ../.env"

# ---------------------------------------------------------------------------
# Database migrations (Prisma is the single migration source of truth)
# ---------------------------------------------------------------------------
migrate:
	cd data-explorer && npx prisma migrate deploy

migrate-dev:
	@read -p "Migration name: " name; cd data-explorer && npx prisma migrate dev --name "$$name"

seed:
	cd data-explorer && npx prisma db seed

# ---------------------------------------------------------------------------
# Local dev servers (run in separate terminals, or use Docker instead)
# Requires: make setup && docker compose up postgres
# ---------------------------------------------------------------------------
dev-frontend:
	cd data-explorer && npm run dev -- --webpack

dev-backend:
	cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000

# ---------------------------------------------------------------------------
# Docker Compose shortcuts
# ---------------------------------------------------------------------------
docker-up:
	docker compose up

docker-down:
	docker compose down

docker-reset:
	docker compose down -v
