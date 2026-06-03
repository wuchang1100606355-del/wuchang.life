FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY services/xiaoj_intent_field /app/services/xiaoj_intent_field
ENV PYTHONPATH=/app
EXPOSE 9107
CMD ["uvicorn", "services.xiaoj_intent_field.app:app", "--host", "0.0.0.0", "--port", "9107"]
