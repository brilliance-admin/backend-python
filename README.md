# Brilliance Admin Backend

Brilliance Admin Backend is a backend framework for building admin panels with Python and FastAPI.

- Serves a prebuilt SPA frontend as static files
- Generates schemas for frontend sections on the backend
- Provides a backend-driven API for admin interfaces
- Designed for fast data management and data viewing from any sources
- Inspired by Django Admin and Django REST Framework
- Focused on minimal boilerplate and simplified backend-controlled configuration

[Live Demo](https://brilliance-admin.com/)


## Development

``` shell
uv sync --all-groups --all-extras
uv run uvicorn example.main:app --host 0.0.0.0 --port 8082 --reload
```

Docs:
- `http://0.0.0.0:8082/docs`
- `http://0.0.0.0:8082/redoc`
- `http://0.0.0.0:8082/scalar`

Tests:
``` shell
uv run pytest
```

## Docker

``` shell
docker compose -f .configs/docker/docker-compose.yml build
docker compose -f .configs/docker/docker-compose.yml up
docker compose -f .configs/docker/docker-compose.yml run --rm backend /bin/bash -c "uv sync --all-groups --all-extras"
docker compose -f .configs/docker/docker-compose.yml run --rm backend /bin/bash -c "uv run pytest"
```

``` shell
docker exec -it rollyum-backend-1 git config --global --add safe.directory '*'
docker exec -it rollyum-backend-1 uv run pre-commit run --all-files
```
