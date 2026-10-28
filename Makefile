.PHONY: up down test eval seed lint mcp

up:            ## Поднять всё: БД, Redis, API, воркер, фронтенд
	@test -f .env || cp .env.example .env
	docker compose up --build -d
	@echo "UI: http://localhost:3000   API docs: http://localhost:8000/docs"

down:
	docker compose down

seed:          ## Загрузить демо-вакансию KOZ AI и 8 резюме
	python3 scripts/seed.py

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check .

eval:          ## Оценка качества/стоимости. Пример: make eval P="mock anthropic"
	cd backend && python -m eval.run_eval $(foreach p,$(or $(P),mock),--provider $(p))

mcp:           ## Запустить MCP-сервер (stdio)
	cd backend && python -m app.mcp_server
