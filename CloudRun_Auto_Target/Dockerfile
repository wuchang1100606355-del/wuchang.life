FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY . .
EXPOSE 8080
CMD ["uvicorn", "jules_cloud_api:app", "--host", "0.0.0.0", "--port", "8080"]
