FROM python:3.14.2-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential gettext libpq-dev git ssh openssh-client \
    && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

COPY . .

RUN uv sync --frozen
