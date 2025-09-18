#!/bin/bash

echo "🚀 Deploy SaaS Chat Generator no Cloud Run"
echo "=========================================="

PROJECT_ID="flower-ai-generator"
REGION="us-east1"

# 1. Preparar arquivos de deploy
echo "📁 Preparando arquivos..."

# Backend Dockerfile
cat > backend/Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --worker-class gevent --timeout 60 app:app
EOF

# Chat Engine Dockerfile  
cat > chat-engine/Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --worker-class gevent --timeout 60 app:app
EOF

# 2. Atualizar requirements com gunicorn
echo "📦 Atualizando dependências..."

echo "gunicorn[gevent]==21.2.0" >> backend/requirements.txt
echo "gunicorn[gevent]==21.2.0" >> chat-engine/requirements.txt

# 3. Deploy Backend
echo "🔧 Deploy Backend..."

cd backend
gcloud run deploy saas-chat-backend \
  --source=. \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=10 \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET=saas_chat_generator" \
  --project=$PROJECT_ID

cd ..

# 4. Deploy Chat Engine
echo "🤖 Deploy Chat Engine..."

cd chat-engine
gcloud run deploy saas-chat-engine \
  --source=. \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=10 \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET=saas_chat_generator" \
  --project=$PROJECT_ID

cd ..

# 5. Obter URLs dos serviços
echo "📋 Obtendo URLs dos serviços..."

BACKEND_URL=$(gcloud run services describe saas-chat-backend --region=$REGION --format='value(status.url)')
CHAT_ENGINE_URL=$(gcloud run services describe saas-chat-engine --region=$REGION --format='value(status.url)')

echo ""
echo "✅ Deploy concluído com sucesso!"
echo ""
echo "🔗 URLs dos serviços:"
echo "   Backend: $BACKEND_URL"
echo "   Chat Engine: $CHAT_ENGINE_URL"
echo ""
echo "🎯 Próximos passos:"
echo "1. Atualize os URLs no frontend (dashboard.html, login.html)"
echo "2. Teste a interface web - CORS deve estar resolvido!"
echo "3. Configure domínio customizado (opcional)"
echo ""
echo "💡 Para atualizações futuras:"
echo "   gcloud run deploy saas-chat-backend --source=./backend --region=$REGION"
echo "   gcloud run deploy saas-chat-engine --source=./chat-engine --region=$REGION"
