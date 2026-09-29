ARG XIAOJ_BASE_IMAGE=python:3.11-slim
FROM ${XIAOJ_BASE_IMAGE}
ARG XIAOJ_SKIP_DEPENDENCY_INSTALL=0
WORKDIR /app
RUN if [ "$XIAOJ_SKIP_DEPENDENCY_INSTALL" = "1" ]; then \
      python -c "import fastapi, uvicorn"; \
    else \
      pip install --no-cache-dir fastapi uvicorn; \
    fi
COPY services/xiaoj_intent_field /app/services/xiaoj_intent_field
COPY services/w7tp_gt_mesh_v21/w7tp_gt_mesh /app/w7tp_gt_mesh
COPY w7tp_runtime /app/w7tp_runtime
ENV PYTHONPATH=/app
EXPOSE 9107
CMD ["uvicorn", "services.xiaoj_intent_field.app:app", "--host", "0.0.0.0", "--port", "9107"]
