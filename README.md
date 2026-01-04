# Example

``` shell
uv sync --all-groups --all-extras
uv run uvicorn example.main:app --host 0.0.0.0 --port 8082 --reload
```

## Docker

``` shell
docker-compose -f .configs/docker/docker-compose.yml build
    docker-compose -f .configs/docker/docker-compose.yml up
docker-compose -f .configs/docker/docker-compose.yml run --rm backend /bin/bash -c "uv sync --all-groups --all-extras"
docker-compose -f .configs/docker/docker-compose.yml run --rm backend /bin/bash -c "uv run pytest"
```

``` shell
docker exec -it rollyum-backend-1 git config --global --add safe.directory '*'
docker exec -it rollyum-backend-1 uv run pre-commit run --all-files
```

Docs:
`http://0.0.0.0:8082/docs`
`http://0.0.0.0:8082/redoc`
`http://0.0.0.0:8082/scalar`

Tests:
``` shell
uv run pytest
```
