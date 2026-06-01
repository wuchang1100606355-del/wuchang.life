FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TAIJI_BIND_HOST=127.0.0.1
ENV TAIJI_PORT=8126
ENV TAIJI_STATE_DIR=/app/state

WORKDIR /app

COPY deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry.py /app/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry.py
COPY runtime_adapters /app/runtime_adapters
COPY services /app/services

RUN mkdir -p /app/state/audit /app/state/deadbox /app/state/replay /app/state/cache

EXPOSE 8126

CMD ["python3", "/app/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry.py"]
