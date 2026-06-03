FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY taiji01_metric_identity_gateway.py /app/taiji01_metric_identity_gateway.py
USER 65532:65532
ENTRYPOINT ["python3", "/app/taiji01_metric_identity_gateway.py"]
