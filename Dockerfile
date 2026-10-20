FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system litter && useradd --system --gid litter --create-home litter

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN python -m pip install --upgrade pip \
    && python -m pip install ".[runtime-headless,api,rfdetr]"

RUN mkdir -p /app/models /app/reports/generated \
    && chown -R litter:litter /app

USER litter

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8088/healthz', timeout=3)"

CMD ["litter-serve"]
