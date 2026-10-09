FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    ENV=production \
    CAUSALBIO_WORKSPACE_ROOT=/app \
    CAUSALBIO_ARTIFACT_DIR=/app/artifacts \
    CAUSALBIO_NO_LLM=true \
    CAUSALBIO_NO_TELEMETRY=true

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY packages/causalbio-core/src ./packages/causalbio-core/src
COPY apps/api/src ./apps/api/src
COPY data/demo ./data/demo
COPY scripts/seed_demo_data.py ./scripts/seed_demo_data.py

RUN python -m pip install --upgrade pip \
    && python -m pip uninstall -y setuptools \
    && python -m pip install . \
    && python scripts/seed_demo_data.py --database /app/data/causalbio.sqlite3 \
    && groupadd --system causalbio \
    && useradd --system --gid causalbio --home-dir /app --shell /usr/sbin/nologin causalbio \
    && mkdir -p /app/artifacts \
    && chown -R causalbio:causalbio /app/artifacts /app/data

USER causalbio

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1

CMD ["python", "-m", "uvicorn", "causalbio_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
