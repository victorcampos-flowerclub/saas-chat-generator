FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# SEM gevent - threads normais
CMD exec gunicorn --bind :$PORT --workers 1 --timeout 60 app:app
