.PHONY: install test run up down
install:
	pip install -r requirements.txt

test:
	pytest -q

run:
	uvicorn app.main:app --reload

up:
	docker compose up --build

down:
	docker compose down
