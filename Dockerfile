# S00 CPU/format-stub candidate. Full BTC Docker validation remains pending P13.
FROM ghcr.io/astral-sh/uv:0.13.6 AS uv
FROM python:3.11.18-slim-bookworm
COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/
COPY configs/smoke.yaml configs/smoke.yaml
COPY tests/fixtures/synthetic/ tests/fixtures/synthetic/
COPY predict.sh ./
RUN uv sync --locked --no-dev --no-group cloud \
    && useradd --uid 10001 --create-home datamate \
    && mkdir -p /app/runs /result \
    && chown -R datamate:datamate /app/runs /result
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
ENTRYPOINT ["/bin/sh", "/app/predict.sh"]
