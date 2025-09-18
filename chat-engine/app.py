"""
Chat Engine ULTRA-OTIMIZADO - Inicialização instantânea
"""
import os
import json
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import requests

# Flask app minimalista
app = Flask(__name__)
CORS(app)

# Cache global da API key
API_KEY_CACHE = None

def get_api_key():
    """Função ultra-rápida para API key"""
    global API_KEY_CACHE
    
    if API_KEY_CACHE:
        return API_KEY_CACHE
    
    try:
        # Import lazy para evitar timeout
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        
        name = "projects/flower-ai-generator/secrets/claude-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8").strip()
        
        API_KEY_CACHE = api_key
        return api_key
    except:
        return None

@app.route('/')
def index():
    return {"status": "ULTRA-FAST Chat Engine", "version": "4.0.0"}

@app.route('/health')
def health():
    try:
        api_key = get_api_key()
        return {
            "status": "healthy",
            "claude_api": "OK" if api_key else "ERROR",
            "timestamp": datetime.now().isoformat()
        }
    except:
        return {"status": "error"}, 500

@app.route('/chat/<chat_id>')
def chat_interface(chat_id):
    # Template inline para evitar problemas de arquivo
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Chat {chat_id}</title>
    <style>
        body {{ font-family: system-ui; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .messages {{ height: 400px; overflow-y: auto; background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .input-area {{ display: flex; gap: 10px; }}
        .input {{ flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 4px; }}
        .btn {{ padding: 12px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        .message {{ margin: 10px 0; padding: 10px; border-radius: 8px; }}
        .user {{ background: #007bff; color: white; margin-left: 50px; }}
        .assistant {{ background: #e9ecef; margin-right: 50px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>💬 Chat {chat_id}</h1>
        <div id="messages" class="messages">
            <div class="message assistant">👋 Olá! Como posso ajudar?</div>
        </div>
        <div class="input-area">
            <input type="text" id="messageInput" class="input" placeholder="Digite sua mensagem...">
            <button onclick="sendMessage()" class="btn">Enviar</button>
        </div>
    </div>
    
    <script>
        async function sendMessage() {{
            const input = document.getElementById('messageInput');
            const messages = document.getElementById('messages');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Adicionar mensagem do usuário
            messages.innerHTML += `<div class="message user">${{message}}</div>`;
            input.value = '';
            
            // Mostrar typing
            messages.innerHTML += `<div class="message assistant" id="typing">🤖 Digitando...</div>`;
            messages.scrollTop = messages.scrollHeight;
            
            try {{
                const response = await fetch(`/api/chat/{chat_id}/send`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{message, conversation_id: 'web-chat'}})
                }});
                
                const data = await response.json();
                
                // Remover typing
                document.getElementById('typing').remove();
                
                if (data.success) {{
                    messages.innerHTML += `<div class="message assistant">${{data.message}}</div>`;
                }} else {{
                    messages.innerHTML += `<div class="message assistant" style="color: red;">❌ Erro: ${{data.error}}</div>`;
                }}
                
                messages.scrollTop = messages.scrollHeight;
            }} catch (error) {{
                document.getElementById('typing').remove();
                messages.innerHTML += `<div class="message assistant" style="color: red;">❌ Erro de conexão</div>`;
            }}
        }}
        
        document.getElementById('messageInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') sendMessage();
        }});
    </script>
</body>
</html>
    """

@app.route('/api/chat/<chat_id>/send', methods=['POST'])
def send_message(chat_id):
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return {"success": False, "error": "Mensagem vazia"}, 400
        
        # Buscar API key
        api_key = get_api_key()
        if not api_key:
            return {"success": False, "error": "Claude API key não disponível"}, 500
        
        # Enviar para Claude
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        claude_data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=claude_data,
            timeout=25
        )
        
        if response.status_code == 200:
            result = response.json()
            assistant_message = result['content'][0]['text']
            
            return {
                "success": True,
                "message": assistant_message,
                "conversation_id": data.get('conversation_id', 'web-chat')
            }
        else:
            return {
                "success": False, 
                "error": f"Claude API error: {response.status_code}"
            }, 500
            
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
