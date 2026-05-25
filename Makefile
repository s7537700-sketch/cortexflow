.PHONY: install dev build docker test clean

install:
	pip install -r requirements.txt

dev:
	uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

build:
	docker compose build

docker:
	docker compose up

test:
	pytest tests/ -v

clean:
	rm -rf __pycache__ */__pycache__ *.db *.sqlite3

cli:
	python core/engine.py

mcp:
	python mcp/server.py

web:
	python -m http.server 3000 --directory web/
