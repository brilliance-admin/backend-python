# Development

All commands run via docker compose.

## Run

```shell
docker compose -f .configs/docker/docker-compose.yml up
```

## Tests

```shell
docker compose -f .configs/docker/docker-compose.yml run --rm backend uv run pytest
```

## Linter

```shell
docker compose -f .configs/docker/docker-compose.yml run --rm backend uv run ruff check .
docker compose -f .configs/docker/docker-compose.yml run --rm backend uv run pylint brilliance_admin
```

## Dependencies

```shell
docker compose -f .configs/docker/docker-compose.yml run --rm backend uv sync --all-groups --all-extras
```

## Profiling

```shell
docker compose -f .configs/docker/docker-compose.yml run --rm backend uv run pytest tests/django/test_payment_list_timing.py -s -m benchmark -vvv
```
