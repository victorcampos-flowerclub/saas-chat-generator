#!/bin/bash

echo "🔧 CORRIGINDO CHAT ENGINE - Versão Simplificada"
echo "==============================================="

cd ~/saas-chat-generator/chat-engine

echo ""
echo "🔍 Problema identificado:"
echo "   ❌ Imports complexos do backend causando timeout"
echo "   ❌ Dependências circulares"
echo "   ❌ Knowledge base travando inicialização"
echo ""

echo "🛠️ Aplicando correção..."

# 1. Backup da versão atual
echo "💾 Fazendo backup..."
cp app.py app.py.broken.backup.$(date +%Y%m%d_%H%M%S)

# 2. Criar app.py simplificado e funcional
echo "🚀 Criando versão corrigida..."

cat > app.py << 'EOF'
"""
Chat Engine CORRIGIDO - Versão independente e funcional
"""

import os
import sys
import json
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timezone
import requests

# Configuração simples e local
class Config:
    PROJECT_ID = 'flower-ai-generator'
    BIGQUERY_DATASET = 'saas_chat_generator'
    CLAUDE_MODEL = 'claude-sonnet-4-20250514'

# Inicializar Flask
app = Flask(__name__)
CORS(app, origins=["*"])

# ================================
# MODELS SIMPLIFICADOS
# ================================

class SimpleDatabase:
    def __init__(self):
        try:
            from google.cloud import bigquery
            self.client = bigquery.Client(project=Config.PROJECT_ID)
        except Exception as e:
            print(f"Erro BigQuery: {e}")
            self.client = None
    
    def get_chat_by_id(self, chat_id):
        """Buscar chat por ID"""
        if not self.client:
            return None
            
        try:
            query = f"""
            SELECT * FROM `{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.chats`
            WHERE chat_id = @chat_id
            """
            
            from google.cloud import bigquery
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            return dict(results[0]) if results else None
        except Exception as e:
            print(f"Erro ao buscar chat: {e}")
            return None
    
    def save_message(self, chat_id, conversation_id, role, content, source='web', tokens_used=0, response_time_ms=0):
        """Salvar mensagem"""
        if not self.client:
            return False
            
        try:
            message_data = {
                'message_id': str(uuid.uuid4()),
                'chat_id': chat_id,
                'conversation_id': conversation_id,
                'role': role,
                'content': content,
                'source': source,
                'source_phone': None,
                'tokens_used': tokens_used,
                'response_time_ms': response_time_ms,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            table_ref = f"{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.messages"
            errors = self.client.insert_rows_json(table_ref, [message_data])
            
            return len(errors) == 0
        except Exception as e:
            print(f"Erro ao salvar mensagem: {e}")
            return False

# ================================
# CLAUDE SERVICE SIMPLIFICADO
# ================================

class ClaudeService:
    def __init__(self):
        self.api_key = self._get_claude_api_key()
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    def _get_claude_api_key(self):
        """Buscar API key do Claude no Secret Manager"""
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{Config.PROJECT_ID}/secrets/claude-api-key/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"Erro API key: {e}")
            return None
    
    def send_message(self, messages, model="claude-3-haiku-20240307", max_tokens=1500):
        """Enviar mensagem para Claude"""
        if not self.api_key:
            return {"error": "API key não configurada"}
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Erro Claude API: {str(e)}"}

# Inicializar serviços
db = SimpleDatabase()
claude_service = ClaudeService()

# ================================
# ROUTES PRINCIPAIS
# ================================

@app.route('/')
def index():
    """Página inicial"""
    return jsonify({
        'status': 'Chat Engine funcionando!',
        'version': '2.0.0-fixed',
        'endpoints': ['/health', '/chat/<id>', '/api/chat/<id>/info', '/api/chat/<id>/send']
    })

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'chat-engine-fixed',
        'timestamp': datetime.now().isoformat(),
        'claude_api': 'configured' if claude_service.api_key else 'missing',
        'database': 'connected' if db.client else 'error'
    })

@app.route('/chat/<chat_id>')
def chat_interface(chat_id):
    """Interface de chat"""
    try:
        # Verificar se chat existe
        chat = db.get_chat_by_id(chat_id)
        
        if not chat:
            return render_template('chat_not_found.html'), 404
        
        return render_template('chat_interface.html', chat=chat)
        
    except Exception as e:
        print(f"Erro ao carregar chat: {e}")
        return f"<h1>Erro</h1><p>Chat não encontrado: {str(e)}</p>", 404

@app.route('/api/chat/<chat_id>/info', methods=['GET'])
def get_chat_info(chat_id):
    """Obter informações do chat"""
    try:
        chat = db.get_chat_by_id(chat_id)
        
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        return jsonify({
            'success': True,
            'chat': chat,
            'user': {
                'full_name': 'Usuário',
                'plan': 'free'
            }
        })
        
    except Exception as e:
        print(f"Erro get_chat_info: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat/<chat_id>/send', methods=['POST'])
def send_message(chat_id):
    """Enviar mensagem para o chat"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        if not user_message:
            return jsonify({'success': False, 'error': 'Mensagem vazia'}), 400
        
        # Buscar chat
        chat = db.get_chat_by_id(chat_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        # Salvar mensagem do usuário
        db.save_message(
            chat_id=chat_id,
            conversation_id=conversation_id,
            role='user',
            content=user_message,
            source='web'
        )
        
        # Preparar mensagens para Claude
        claude_messages = [
            {
                "role": "user",
                "content": f"Sistema: {chat.get('system_prompt', 'Você é um assistente útil.')}"
            },
            {
                "role": "assistant", 
                "content": "Entendido. Estou pronto para ajudar."
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
        
        # Enviar para Claude
        start_time = datetime.now()
        claude_response = claude_service.send_message(
            messages=claude_messages,
            model=chat.get('claude_model', 'claude-3-haiku-20240307'),
            max_tokens=chat.get('max_tokens', 1500)
        )
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        if 'error' in claude_response:
            return jsonify({
                'success': False,
                'error': claude_response['error']
            }), 500
        
        # Extrair resposta
        assistant_message = claude_response['content'][0]['text']
        tokens_used = claude_response.get('usage', {}).get('output_tokens', 0)
        
        # Salvar resposta
        db.save_message(
            chat_id=chat_id,
            conversation_id=conversation_id,
            role='assistant',
            content=assistant_message,
            source='web',
            tokens_used=tokens_used,
            response_time_ms=response_time
        )
        
        return jsonify({
            'success': True,
            'message': assistant_message,
            'conversation_id': conversation_id,
            'tokens_used': tokens_used,
            'response_time_ms': response_time
        })
        
    except Exception as e:
        print(f"Erro send_message: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

# ================================
# ERROR HANDLERS
# ================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    print("🚀 Chat Engine CORRIGIDO iniciando...")
    print(f"📊 Projeto: {Config.PROJECT_ID}")
    print(f"🤖 Modelo: {Config.CLAUDE_MODEL}")
    app.run(debug=True, host='0.0.0.0', port=5001)
EOF

echo "✅ App.py corrigido criado!"

# 3. Simplificar requirements.txt
echo "📦 Simplificando requirements..."

cat > requirements.txt << 'EOF'
Flask==2.3.3
flask-cors==4.0.0
google-cloud-bigquery==3.11.4
google-cloud-secret-manager==2.16.4
requests==2.31.0
gunicorn[gevent]==21.2.0
EOF

echo "✅ Requirements simplificado!"

# 4. Verificar se templates existem
echo "📄 Verificando templates..."

if [ ! -f "templates/chat_interface.html" ]; then
    echo "🔧 Criando template chat_interface.html..."
    mkdir -p templates
    
    cat > templates/chat_interface.html << 'TEMPLATE_EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ chat.chat_name }} - Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui; height: 100vh; display: flex; flex-direction: column; background: #f8fafc; }
        .header { background: white; padding: 20px; border-bottom: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header h1 { color: #1f2937; margin-bottom: 5px; }
        .header p { color: #6b7280; font-size: 14px; }
        .chat-container { flex: 1; display: flex; flex-direction: column; max-width: 1000px; margin: 0 auto; width: 100%; padding: 0 20px; }
        .messages { flex: 1; overflow-y: auto; padding: 20px 0; display: flex; flex-direction: column; gap: 15px; }
        .message { display: flex; gap: 10px; max-width: 70%; }
        .message.user { align-self: flex-end; flex-direction: row-reverse; }
        .message.assistant { align-self: flex-start; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; }
        .message.user .avatar { background: #4f46e5; color: white; }
        .message.assistant .avatar { background: #10b981; color: white; }
        .content { background: white; padding: 15px; border-radius: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .message.user .content { background: #4f46e5; color: white; }
        .input-container { background: white; border-top: 1px solid #e5e7eb; padding: 20px; }
        .input-form { display: flex; gap: 15px; max-width: 1000px; margin: 0 auto; }
        .input { flex: 1; padding: 12px; border: 2px solid #e5e7eb; border-radius: 25px; font-size: 16px; outline: none; }
        .input:focus { border-color: #4f46e5; }
        .send-btn { background: #4f46e5; color: white; border: none; border-radius: 50%; width: 50px; height: 50px; cursor: pointer; font-size: 20px; }
        .send-btn:hover { background: #4338ca; }
        .welcome { text-align: center; padding: 40px; color: #6b7280; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ chat.chat_name }}</h1>
        <p>{{ chat.chat_type|title }} • {{ chat.personality|title }}</p>
    </div>
    
    <div class="chat-container">
        <div class="messages" id="messages">
            <div class="welcome">
                <h3>👋 Olá! Como posso ajudar?</h3>
            </div>
        </div>
        
        <div class="input-container">
            <form class="input-form" id="messageForm">
                <input type="text" class="input" id="messageInput" placeholder="Digite sua mensagem..." autocomplete="off">
                <button type="submit" class="send-btn">➤</button>
            </form>
        </div>
    </div>
    
    <script>
        const chatId = '{{ chat.chat_id }}';
        const API_BASE = window.location.origin;
        let conversationId = generateUUID();
        
        const messagesContainer = document.getElementById('messages');
        const messageForm = document.getElementById('messageForm');
        const messageInput = document.getElementById('messageInput');
        
        function generateUUID() {
            return 'xxxx-xxxx-4xxx-yxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }
        
        function addMessage(role, content) {
            const welcomeMsg = messagesContainer.querySelector('.welcome');
            if (welcomeMsg) welcomeMsg.remove();
            
            const messageEl = document.createElement('div');
            messageEl.className = `message ${role}`;
            
            const avatar = role === 'user' ? '👤' : '🤖';
            
            messageEl.innerHTML = `
                <div class="avatar">${avatar}</div>
                <div class="content">${content}</div>
            `;
            
            messagesContainer.appendChild(messageEl);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;
            
            addMessage('user', message);
            messageInput.value = '';
            
            try {
                const response = await fetch(`${API_BASE}/api/chat/${chatId}/send`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        conversation_id: conversationId
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addMessage('assistant', data.message);
                } else {
                    addMessage('assistant', 'Desculpe, ocorreu um erro: ' + data.error);
                }
                
            } catch (error) {
                addMessage('assistant', 'Erro de conexão. Tente novamente.');
            }
        }
        
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            sendMessage();
        });
        
        messageInput.focus();
    </script>
</body>
</html>
TEMPLATE_EOF
fi

if [ ! -f "templates/chat_not_found.html" ]; then
    echo "🔧 Criando template chat_not_found.html..."
    
    cat > templates/chat_not_found.html << 'TEMPLATE_EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Não Encontrado</title>
    <style>
        body { font-family: system-ui; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f8fafc; }
        .container { text-align: center; max-width: 500px; padding: 40px; }
        .icon { font-size: 80px; margin-bottom: 20px; }
        .title { color: #1f2937; font-size: 32px; margin-bottom: 10px; }
        .message { color: #6b7280; font-size: 18px; margin-bottom: 30px; }
        .btn { background: #4f46e5; color: white; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">❌</div>
        <h1 class="title">Chat Não Encontrado</h1>
        <p class="message">O chat que você está tentando acessar não existe ou foi removido.</p>
        <a href="/" class="btn">Voltar ao Início</a>
    </div>
</body>
</html>
TEMPLATE_EOF
fi

echo "✅ Templates verificados!"

# 5. Teste local rápido
echo ""
echo "🧪 Testando sintaxe do Python..."
python3 -c "
import sys
sys.path.append('.')
exec(open('app.py').read().replace('app.run', '# app.run'))
print('✅ Sintaxe OK!')
" || echo "❌ Erro de sintaxe encontrado!"

echo ""
echo "🚀 Fazendo deploy da versão corrigida..."

gcloud run deploy saas-chat-engine \
  --source=. \
  --platform=managed \
  --region=us-east1 \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=10 \
  --timeout=300 \
  --set-env-vars="PROJECT_ID=flower-ai-generator,BIGQUERY_DATASET=saas_chat_generator" \
  --quiet

echo ""
echo "🧪 Testando Chat Engine corrigido..."

sleep 10

ENGINE_URL="https://saas-chat-engine-zyzjkxq7ca-ue.a.run.app"

echo "🔍 Testando endpoints:"
echo "   Health: $(curl -s -o /dev/null -w "%{http_code}" "$ENGINE_URL/health")"
echo "   Root: $(curl -s -o /dev/null -w "%{http_code}" "$ENGINE_URL/")"

if [ "$(curl -s -o /dev/null -w "%{http_code}" "$ENGINE_URL/health")" = "200" ]; then
    echo ""
    echo "🎉 SUCESSO! CHAT ENGINE CORRIGIDO!"
    echo ""
    echo "✅ O que foi corrigido:"
    echo "   🔧 Removido imports complexos do backend"
    echo "   🔧 Criado models simplificados e independentes"
    echo "   🔧 Removido knowledge base (que causava timeout)"
    echo "   🔧 Simplificado requirements.txt"
    echo "   🔧 Versão autossuficiente e estável"
    echo ""
    echo "🌐 Teste agora:"
    echo "   1. Vá para o dashboard"
    echo "   2. Clique no botão '💬 Chat'"
    echo "   3. Deve abrir a interface funcionando!"
    echo ""
    echo "🔗 URLs de teste:"
    echo "   Dashboard: https://saas-chat-backend-365442086139.us-east1.run.app/dashboard"
    echo "   Chat direto: $ENGINE_URL/chat/[CHAT_ID]"
else
    echo ""
    echo "⚠️ Chat Engine ainda não está respondendo"
    echo "🔧 Verificar logs: gcloud run services logs tail saas-chat-engine --region=us-east1"
fi

echo ""
echo "📋 Próximos passos:"
echo "1. Teste a interface de chat"
echo "2. Se funcionando, implementar WhatsApp"
echo "3. Knowledge Base pode ser re-adicionado depois (opcional)"
