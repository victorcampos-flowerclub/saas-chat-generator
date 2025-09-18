#!/bin/bash

echo "🔄 Atualizando URLs nos templates HTML..."
echo "========================================"

BACKEND_URL="https://saas-chat-backend-zyzjkxq7ca-ue.a.run.app"
ENGINE_URL="https://saas-chat-engine-zyzjkxq7ca-ue.a.run.app"

echo "🔧 URLs detectados:"
echo "   Backend: $BACKEND_URL"
echo "   Engine: $ENGINE_URL"
echo ""

# 1. Atualizar login.html
echo "📝 Atualizando login.html..."
sed -i "s|const API_BASE = 'http://localhost:5002'|const API_BASE = '$BACKEND_URL'|g" backend/templates/login.html
sed -i "s|const API_BASE = 'http://localhost:5000'|const API_BASE = '$BACKEND_URL'|g" backend/templates/login.html

# 2. Atualizar dashboard.html  
echo "📝 Atualizando dashboard.html..."
sed -i "s|const API_BASE = window.location.origin|const API_BASE = '$BACKEND_URL'|g" backend/templates/dashboard.html

# 3. Atualizar manage_chat.html
echo "📝 Atualizando manage_chat.html..."
sed -i "s|const API_BASE = window.location.origin|const API_BASE = '$BACKEND_URL'|g" backend/templates/manage_chat.html

# 4. Atualizar chat_interface.html
echo "📝 Atualizando chat_interface.html..."
sed -i "s|const API_BASE = 'http://localhost:5001'|const API_BASE = '$ENGINE_URL'|g" chat-engine/templates/chat_interface.html

echo ""
echo "✅ URLs atualizados com sucesso!"
echo ""
echo "🌐 Teste sua aplicação:"
echo "   Login: $BACKEND_URL/login"
echo "   Dashboard: $BACKEND_URL/dashboard"
echo ""
echo "🎯 Próximo passo: Teste completo da aplicação!"

# 5. Re-deploy para aplicar mudanças
echo ""
echo "🚀 Re-deployando com URLs atualizados..."

cd backend
gcloud run deploy saas-chat-backend \
  --source=. \
  --region=us-east1 \
  --quiet

cd ../chat-engine  
gcloud run deploy saas-chat-engine \
  --source=. \
  --region=us-east1 \
  --quiet

cd ..

echo ""
echo "🎉 Deploy atualizado concluído!"
echo ""
echo "🔗 ACESSE SUA APLICAÇÃO:"
echo "   👉 $BACKEND_URL/login"
echo ""
echo "📋 Para testar:"
echo "1. Abra o link acima"
echo "2. Crie uma conta"
echo "3. Teste criar um chat"
echo "4. Teste o upload de documentos"
echo "5. Teste a interface de chat"
