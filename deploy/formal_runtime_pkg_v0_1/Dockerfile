FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TAIJI_BIND_HOST=127.0.0.1
ENV TAIJI_PORT=8125
ENV TAIJI_STATE_DIR=/app/state

WORKDIR /app

COPY deploy/formal_runtime_pkg_v0_1/runtime_entry_v0_1.py /app/deploy/formal_runtime_pkg_v0_1/runtime_entry_v0_1.py
COPY runtime_adapters /app/runtime_adapters
COPY services /app/services

RUN mkdir -p /app/state/audit /app/state/deadbox /app/state/replay /app/state/cache

EXPOSE 8125

CMD ["python3", "/app/deploy/formal_runtime_pkg_v0_1/runtime_entry_v0_1.py"]
