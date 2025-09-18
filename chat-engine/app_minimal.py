"""
Chat Engine MÍNIMO - Apenas o essencial para funcionar
"""

import os
from flask import Flask
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app, origins=["*"])

# Cache da API key
API_KEY_CACHE = None

def get_claude_api_key():
    """Função SIMPLES para pegar API key"""
    global API_KEY_CACHE
    
    if API_KEY_CACHE:
        return API_KEY_CACHE
    
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = "projects/flower-ai-generator/secrets/claude-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8").strip()
        
        if api_key and len(api_key) > 50:
            API_KEY_CACHE = api_key
            return api_key
        return None
    except Exception as e:
        print(f"Erro API key: {e}")
        return None

@app.route('/')
def index():
    return {
        "service": "Chat Engine MINIMAL", 
        "status": "OK",
        "timestamp": datetime.now().isoformat()
    }

@app.route('/health')
def health():
    api_key = get_claude_api_key()
    return {
        "status": "healthy" if api_key else "no_api_key",
        "api_key_available": bool(api_key)
    }

@app.route('/test')
def test_claude():
    """Teste direto com Claude"""
    api_key = get_claude_api_key()
    if not api_key:
        return {"error": "No API key"}, 500
    
    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "Say hello in Portuguese"}]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message": result['content'][0]['text'],
                "tokens": result.get('usage', {}).get('output_tokens', 0)
            }
        else:
            return {
                "success": False,
                "error": f"Claude API error {response.status_code}",
                "details": response.text[:200]
            }, 500
            
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@app.route('/chat/<chat_id>')
def chat_page(chat_id):
    """Página de chat SIMPLES"""
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Chat Mínimo - {chat_id}</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
        .messages {{ height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; }}
        .input-area {{ display: flex; gap: 10px; }}
        .input {{ flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .btn {{ padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }}
        .message {{ margin-bottom: 15px; }}
        .user {{ text-align: right; }}
        .assistant {{ text-align: left; }}
        .user .content {{ background: #007bff; color: white; display: inline-block; padding: 10px; border-radius: 15px; }}
        .assistant .content {{ background: #e9ecef; display: inline-block; padding: 10px; border-radius: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>💬 Chat Mínimo - ID: {chat_id}</h2>
        <div class="messages" id="messages">
            <div style="text-align: center; color: #666; padding: 20px;">
                👋 Digite uma mensagem para começar
            </div>
        </div>
        <div class="input-area">
            <input type="text" class="input" id="messageInput" placeholder="Digite sua mensagem...">
            <button class="btn" onclick="sendMessage()">Enviar</button>
        </div>
    </div>
    
    <script>
        const chatId = '{chat_id}';
        const messagesDiv = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        
        function addMessage(role, content) {{
            const msg = document.createElement('div');
            msg.className = `message ${{role}}`;
            msg.innerHTML = `<div class="content">${{content}}</div>`;
            messagesDiv.appendChild(msg);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }}
        
        async function sendMessage() {{
            const message = messageInput.value.trim();
            if (!message) return;
            
            addMessage('user', message);
            messageInput.value = '';
            
            addMessage('assistant', '🤔 Pensando...');
            
            try {{
                const response = await fetch(`/api/send/${{chatId}}`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ message }})
                }});
                
                const data = await response.json();
                
                // Remove "pensando"
                messagesDiv.removeChild(messagesDiv.lastChild);
                
                if (data.success) {{
                    addMessage('assistant', data.message);
                }} else {{
                    addMessage('assistant', `❌ Erro: ${{data.error}}`);
                }}
            }} catch (error) {{
                messagesDiv.removeChild(messagesDiv.lastChild);
                addMessage('assistant', '❌ Erro de conexão');
            }}
        }}
        
        messageInput.addEventListener('keypress', e => {{
            if (e.key === 'Enter') sendMessage();
        }});
    </script>
</body>
</html>
    '''

@app.route('/api/send/<chat_id>', methods=['POST'])
def send_message(chat_id):
    """API para enviar mensagem"""
    try:
        from flask import request
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return {"success": False, "error": "Mensagem vazia"}, 400
        
        api_key = get_claude_api_key()
        if not api_key:
            return {"success": False, "error": "API key indisponível"}, 500
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        claude_data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 500,
            "messages": [
                {"role": "user", "content": f"Você é um assistente útil. Responda em português: {message}"}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=claude_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message": result['content'][0]['text'],
                "chat_id": chat_id
            }
        else:
            return {
                "success": False,
                "error": f"Claude error {response.status_code}",
                "details": response.text[:100]
            }, 500
            
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Starting MINIMAL Chat Engine on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
