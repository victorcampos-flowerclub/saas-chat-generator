FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# Configuração otimizada do gunicorn
CMD exec gunicorn --bind :$PORT \
    --workers 1 \
    --worker-class gevent \
    --timeout 120 \
    --preload \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    app:app
