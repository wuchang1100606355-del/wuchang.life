FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY claw_api.py .

EXPOSE 9004

CMD ["python", "-u", "claw_api.py"]
