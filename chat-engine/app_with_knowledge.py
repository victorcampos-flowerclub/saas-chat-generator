"""
Chat Engine MÍNIMO + Knowledge Base
"""

import os
from flask import Flask, request
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app, origins=["*"])

# Cache da API key
API_KEY_CACHE = None
BQ_CLIENT_CACHE = None

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

def get_bigquery_client():
    """Cliente BigQuery simples"""
    global BQ_CLIENT_CACHE
    
    if BQ_CLIENT_CACHE:
        return BQ_CLIENT_CACHE
    
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project="flower-ai-generator")
        
        # Teste simples
        query = "SELECT 1 as test"
        list(client.query(query).result())
        
        BQ_CLIENT_CACHE = client
        return client
    except Exception as e:
        print(f"BigQuery error: {e}")
        return None

def get_knowledge_context(chat_id, user_message):
    """Buscar documentos relevantes"""
    try:
        client = get_bigquery_client()
        if not client:
            return ""
        
        from google.cloud import bigquery
        
        # Buscar documentos do chat
        query = """
        SELECT filename, processed_content
        FROM `flower-ai-generator.saas_chat_generator.chat_documents`
        WHERE chat_id = @chat_id
        ORDER BY uploaded_at DESC
        LIMIT 3
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
        )
        
        results = list(client.query(query, job_config=job_config).result())
        
        if not results:
            return ""
        
        context = "=== DOCUMENTOS ===\n"
        for doc in results:
            context += f"📄 {doc['filename']}:\n"
            content = doc['processed_content'][:800] if doc['processed_content'] else ""
            context += f"{content}\n\n"
        
        return context
        
    except Exception as e:
        print(f"Knowledge error: {e}")
        return ""

@app.route('/')
def index():
    return {
        "service": "Chat Engine MINIMAL + Knowledge", 
        "status": "OK",
        "timestamp": datetime.now().isoformat()
    }

@app.route('/health')
def health():
    api_key = get_claude_api_key()
    bq_client = get_bigquery_client()
    return {
        "status": "healthy" if api_key else "no_api_key",
        "api_key_available": bool(api_key),
        "bigquery_available": bool(bq_client)
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
                "error": f"Claude API error {response.status_code}"
            }, 500
            
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@app.route('/chat/<chat_id>')
def chat_page(chat_id):
    """Página de chat com Knowledge Base"""
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Chat + Knowledge Base - {chat_id}</title>
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
        .knowledge-badge {{ background: #28a745; color: white; font-size: 11px; padding: 2px 6px; border-radius: 10px; margin-left: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🧠 Chat + Knowledge Base - ID: {chat_id}</h2>
        <div class="messages" id="messages">
            <div style="text-align: center; color: #666; padding: 20px;">
                👋 Este chat pode usar seus documentos carregados para responder
            </div>
        </div>
        <div class="input-area">
            <input type="text" class="input" id="messageInput" placeholder="Pergunte sobre documentos ou qualquer coisa...">
            <button class="btn" onclick="sendMessage()">Enviar</button>
        </div>
    </div>
    
    <script>
        const chatId = '{chat_id}';
        const messagesDiv = document.getElementById('messages');
        const messageInput = document.getElementById('messageInput');
        
        function addMessage(role, content, hasKnowledge = false) {{
            const msg = document.createElement('div');
            msg.className = `message ${{role}}`;
            const knowledgeBadge = hasKnowledge ? '<span class="knowledge-badge">📚 Docs</span>' : '';
            msg.innerHTML = `<div class="content">${{content}}${{knowledgeBadge}}</div>`;
            messagesDiv.appendChild(msg);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }}
        
        async function sendMessage() {{
            const message = messageInput.value.trim();
            if (!message) return;
            
            addMessage('user', message);
            messageInput.value = '';
            
            addMessage('assistant', '🤔 Analisando documentos...');
            
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
                    addMessage('assistant', data.message, data.used_knowledge || false);
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
    """API para enviar mensagem COM Knowledge Base"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return {"success": False, "error": "Mensagem vazia"}, 400
        
        api_key = get_claude_api_key()
        if not api_key:
            return {"success": False, "error": "API key indisponível"}, 500
        
        # BUSCAR KNOWLEDGE BASE
        knowledge_context = get_knowledge_context(chat_id, message)
        has_knowledge = bool(knowledge_context)
        
        # Montar prompt com contexto
        system_prompt = "Você é um assistente útil que responde em português."
        
        if has_knowledge:
            system_prompt += f"\n\nUSE ESTAS INFORMAÇÕES DOS DOCUMENTOS:\n{knowledge_context}"
            system_prompt += "\nResponda baseado nos documentos quando relevante."
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        claude_data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 500,
            "messages": [
                {"role": "user", "content": f"Sistema: {system_prompt}"},
                {"role": "assistant", "content": "Entendido!"},
                {"role": "user", "content": message}
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
                "chat_id": chat_id,
                "used_knowledge": has_knowledge
            }
        else:
            return {
                "success": False,
                "error": f"Claude error {response.status_code}"
            }, 500
            
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Starting Chat Engine + Knowledge Base on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
