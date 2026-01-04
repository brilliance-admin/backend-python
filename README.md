# Brilliance Admin Backend

[![PyPI](https://img.shields.io/pypi/v/brilliance-admin)](https://pypi.org/project/brilliance-admin/)
[![License](https://img.shields.io/pypi/l/brilliance-admin)](https://github.com/brilliance-admin/backend-python/blob/main/LICENSE)
[![CI](https://github.com/brilliance-admin/backend-python/actions/workflows/deploy.yml/badge.svg)](https://github.com/brilliance-admin/backend-python/actions)


Brilliance Admin Backend is a backend framework for building admin panels with Python and FastAPI.

- Serves a prebuilt SPA frontend as static files
- Generates schemas for frontend sections on the backend
- Provides a backend-driven API for admin interfaces
- Designed for fast data management and data viewing from any sources
- Inspired by Django Admin and Django REST Framework
- Focused on minimal boilerplate and simplified backend-controlled configuration

## [Live Demo](https://brilliance-admin.com/)

Features:

* Tables with full CRUD support, including filtering, sorting, and pagination.
* Ability to define custom table actions with forms, response messages, and file uploads.
* SQLAlchemy integration with automatic field generation from models.
* Authorization via any account provider.
* Localization support with language selection in the interface.


## Development

``` shell
uv sync --all-groups --all-extras
uv run uvicorn example.main:app --host 0.0.0.0 --port 8082 --reload
```

Tests:
``` shell
uv run pytest
```

Docs:
- `http://0.0.0.0:8082/docs`
- `http://0.0.0.0:8082/redoc`
- `http://0.0.0.0:8082/scalar`

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
