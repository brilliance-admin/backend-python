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

## Dependencies

```shell
docker compose -f .configs/docker/docker-compose.yml run --rm backend uv sync --all-groups --all-extras
```
