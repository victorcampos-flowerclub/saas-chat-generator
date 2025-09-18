#!/bin/bash

echo "🔧 CORRIGINDO CHAT ENGINE - Erro 504"
echo "====================================="

cd ~/saas-chat-generator/chat-engine


echo ""
echo "🔍 Verificando arquivos do chat-engine..."
ls -la

echo ""
echo "🛠️ Criando Chat Engine corrigido..."

# Criar app.py limpo e funcional
cat > app.py << 'EOF'
"""
Chat Engine - Interface de chat funcionando
"""

import os
import sys
import json
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timezone
import requests

# Adicionar path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import Config
    from models.database import chat_model, message_model, user_model
except ImportError:
    # Fallback caso não encontre
    class Config:
        PROJECT_ID = 'flower-ai-generator'
        BIGQUERY_DATASET = 'saas_chat_generator'
        CLAUDE_MODEL = 'claude-sonnet-4-20250514'

# Inicializar Flask
app = Flask(__name__)
CORS(app, origins=["*"])

# Claude Service simplificado
class ClaudeService:
    def __init__(self):
        self.api_key = self._get_claude_api_key()
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    def _get_claude_api_key(self):
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/flower-ai-generator/secrets/claude-api-key/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"Erro API key: {e}")
            return None
    
    def send_message(self, messages, model="claude-3-haiku-20240307", max_tokens=1500):
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

claude_service = ClaudeService()

@app.route('/')
def index():
    return jsonify({
        'status': 'Chat Engine funcionando',
        'version': '1.0.0',
        'endpoints': ['/health', '/chat/<id>', '/api/chat/<id>/info', '/api/chat/<id>/send']
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'chat-engine',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/chat/<chat_id>')
def chat_interface(chat_id):
    try:
        # Verificar se chat existe
        from models.database import chat_model
        chat = chat_model.get_chat_by_id(chat_id)
        
        if not chat:
            return render_template('chat_not_found.html'), 404
        
        return render_template('chat_interface.html', chat=chat)
    except Exception as e:
        print(f"Erro ao carregar chat: {e}")
        return f"<h1>Erro</h1><p>Chat não encontrado: {str(e)}</p>", 404

@app.route('/api/chat/<chat_id>/info', methods=['GET'])
def get_chat_info(chat_id):
    try:
        from models.database import chat_model, user_model
        
        chat = chat_model.get_chat_by_id(chat_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        user = user_model.get_user_by_id(chat['user_id'])
        
        return jsonify({
            'success': True,
            'chat': chat,
            'user': {
                'full_name': user['full_name'] if user else 'Usuário',
                'plan': user['plan'] if user else 'free'
            }
        })
    except Exception as e:
        print(f"Erro get_chat_info: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat/<chat_id>/send', methods=['POST'])
def send_message(chat_id):
    try:
        from models.database import chat_model, message_model
        
        data = request.get_json()
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        if not user_message:
            return jsonify({'success': False, 'error': 'Mensagem vazia'}), 400
        
        # Buscar chat
        chat = chat_model.get_chat_by_id(chat_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        # Salvar mensagem do usuário
        message_model.save_message(
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
                "content": f"Sistema: {chat['system_prompt']}"
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
        message_model.save_message(
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

@app.route('/api/chat/<chat_id>/history/<conversation_id>', methods=['GET'])
def get_conversation_history(chat_id, conversation_id):
    try:
        from models.database import message_model
        history = message_model.get_conversation_history(chat_id, conversation_id)
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    print("🚀 Chat Engine iniciando...")
    app.run(debug=True, host='0.0.0.0', port=5001)
EOF

echo "✅ App.py criado!"

# Criar config.py
cat > config.py << 'EOF'
import os

class Config:
    PROJECT_ID = 'flower-ai-generator'
    REGION = 'southamerica-east1'
    CLAUDE_MODEL = 'claude-sonnet-4-20250514'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
    BIGQUERY_DATASET = 'saas_chat_generator'
    STORAGE_BUCKET = f'{PROJECT_ID}-saas-chats'
EOF

echo "✅ Config.py criado!"

# Copiar models do backend
echo "📋 Copiando models..."
cp -r ../backend/models/ ./

# Criar requirements.txt
cat > requirements.txt << 'EOF'
Flask==2.3.3
flask-cors==4.0.0
google-cloud-bigquery==3.11.4
google-cloud-secret-manager==2.16.4
requests==2.31.0
bcrypt==4.0.1
gunicorn[gevent]==21.2.0
EOF

echo "✅ Requirements criado!"

# Criar template chat_interface.html
mkdir -p templates

cat > templates/chat_interface.html << 'EOF'
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
        .typing { display: none; align-self: flex-start; gap: 10px; }
        .typing .content { background: white; padding: 15px; }
        .dots { display: flex; gap: 4px; }
        .dot { width: 8px; height: 8px; background: #6b7280; border-radius: 50%; animation: typing 1.4s infinite; }
        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes typing { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
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
        const API_BASE = 'https://saas-chat-engine-zyzjkxq7ca-ue.a.run.app';
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
        
        function showTyping() {
            const typingEl = document.createElement('div');
            typingEl.className = 'typing';
            typingEl.id = 'typing';
            typingEl.innerHTML = `
                <div class="avatar">🤖</div>
                <div class="content">
                    <div class="dots">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                </div>
            `;
            
            messagesContainer.appendChild(typingEl);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        function hideTyping() {
            const typing = document.getElementById('typing');
            if (typing) typing.remove();
        }
        
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;
            
            addMessage('user', message);
            messageInput.value = '';
            showTyping();
            
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
                hideTyping();
                
                if (data.success) {
                    addMessage('assistant', data.message);
                } else {
                    addMessage('assistant', 'Desculpe, ocorreu um erro: ' + data.error);
                }
                
            } catch (error) {
                hideTyping();
                addMessage('assistant', 'Erro de conexão. Tente novamente.');
            }
        }
        
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            sendMessage();
        });
        
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        messageInput.focus();
    </script>
</body>
</html>
EOF

echo "✅ Template criado!"

# Criar template chat_not_found.html
cat > templates/chat_not_found.html << 'EOF'
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
EOF

echo "✅ Template de erro criado!"

# Criar Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --worker-class gevent --timeout 60 app:app
EOF

echo "✅ Dockerfile criado!"

echo ""
echo "🚀 Fazendo deploy do Chat Engine corrigido..."

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

sleep 5

ENGINE_URL="https://saas-chat-engine-zyzjkxq7ca-ue.a.run.app"

echo "🔍 Testando endpoints..."
echo "   Health: $(curl -s -o /dev/null -w "%{http_code}" "$ENGINE_URL/health")"
echo "   Root: $(curl -s -o /dev/null -w "%{http_code}" "$ENGINE_URL/")"

echo ""
echo "✅ CHAT ENGINE CORRIGIDO!"
echo ""
echo "🎯 Agora teste:"
echo "1. Volte ao dashboard"
echo "2. Clique no botão '💬 Chat'"
echo "3. Deve abrir a interface de chat funcionando!"
echo ""
echo "🔗 URL de teste direto:"
echo "   $ENGINE_URL/chat/5ef22072-fc21-4a3e-a8bc-c00286e43832"
