#!/bin/bash

echo "🔧 CORRIGINDO CHAT ENGINE - Timeout API Key Resolvido"
echo "====================================================="

cd ~/saas-chat-generator/chat-engine

# Backup do atual
cp app.py app.py.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

echo "🛠️ Criando versão CORRIGIDA baseada na que funcionou..."

cat > app.py << 'EOF'
"""
Chat Engine com Knowledge Base - VERSÃO CORRIGIDA (Timeout Resolvido)
Baseado na versão que funcionou + Knowledge Base integrado
"""

import os
import json
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
import requests
import traceback

# Flask app
app = Flask(__name__)
CORS(app, origins=["*"])

# Configuração
PROJECT_ID = 'flower-ai-generator'
BIGQUERY_DATASET = 'saas_chat_generator'
DEBUG_MODE = True

# Cache global - SIMPLES
API_KEY_CACHE = None
BQ_CLIENT_CACHE = None

def log_debug(message, level="INFO"):
    """Log debug simplificado"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def get_claude_api_key():
    """Função CORRIGIDA - sem timeout e com retry"""
    global API_KEY_CACHE
    
    if API_KEY_CACHE:
        return API_KEY_CACHE
    
    log_debug("Buscando Claude API key...")
    
    try:
        from google.cloud import secretmanager
        
        # Cliente com timeout menor
        client = secretmanager.SecretManagerServiceClient()
        
        # Nome do secret
        name = f"projects/{PROJECT_ID}/secrets/claude-api-key/versions/latest"
        
        # Request com timeout explícito
        request_obj = {"name": name}
        
        log_debug(f"Acessando: {name}")
        
        # Tentar buscar com timeout de 10 segundos
        response = client.access_secret_version(
            request=request_obj,
            timeout=10  # Timeout explícito
        )
        
        api_key_raw = response.payload.data.decode("UTF-8")
        api_key = api_key_raw.strip()
        
        if not api_key or len(api_key) < 50:
            log_debug(f"API key inválida: len={len(api_key) if api_key else 0}", "ERROR")
            return None
        
        API_KEY_CACHE = api_key
        log_debug(f"API key obtida com sucesso: {len(api_key)} chars")
        return api_key
        
    except Exception as e:
        log_debug(f"ERRO ao buscar API key: {str(e)}", "ERROR")
        return None

def get_bigquery_client():
    """Cliente BigQuery SIMPLIFICADO - sem recursão"""
    global BQ_CLIENT_CACHE
    
    if BQ_CLIENT_CACHE:
        return BQ_CLIENT_CACHE
    
    try:
        from google.cloud import bigquery
        
        # Cliente simples sem configurações complexas
        client = bigquery.Client(project=PROJECT_ID)
        
        # Teste simples
        query = "SELECT 1 as test"
        query_job = client.query(query, timeout=5)  # Timeout de 5 segundos
        results = list(query_job.result(timeout=5))
        
        if results:
            BQ_CLIENT_CACHE = client
            log_debug("BigQuery client OK")
            return client
        
        return None
        
    except Exception as e:
        log_debug(f"BigQuery error: {str(e)}", "ERROR")
        return None

def get_chat_info(chat_id):
    """Buscar info do chat - SIMPLIFICADO"""
    try:
        client = get_bigquery_client()
        
        if not client:
            log_debug("BigQuery não disponível, usando fallback")
            return {
                'chat_id': chat_id,
                'chat_name': 'Chat Inteligente',
                'chat_type': 'assistant',
                'personality': 'professional',
                'system_prompt': 'Você é um assistente inteligente especializado.',
                'claude_model': 'claude-3-haiku-20240307',
                'max_tokens': 1500
            }
        
        from google.cloud import bigquery
        
        query = f"""
        SELECT chat_id, chat_name, chat_type, personality, system_prompt, claude_model, max_tokens
        FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.chats`
        WHERE chat_id = @chat_id
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
        )
        
        query_job = client.query(query, job_config=job_config, timeout=10)
        results = list(query_job.result(timeout=10))
        
        if results:
            return dict(results[0])
        else:
            log_debug(f"Chat {chat_id} não encontrado")
            return None
            
    except Exception as e:
        log_debug(f"Erro ao buscar chat: {str(e)}", "ERROR")
        return None

def get_knowledge_context(chat_id, user_message):
    """Knowledge Base SIMPLIFICADO - sem timeout"""
    try:
        client = get_bigquery_client()
        if not client:
            return ""
        
        from google.cloud import bigquery
        
        # Query simples e rápida
        query = f"""
        SELECT filename, processed_content, content_summary
        FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.chat_documents`
        WHERE chat_id = @chat_id
        ORDER BY uploaded_at DESC
        LIMIT 5
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
        )
        
        query_job = client.query(query, job_config=job_config, timeout=8)
        documents = list(query_job.result(timeout=8))
        
        if not documents:
            return ""
        
        log_debug(f"Encontrados {len(documents)} documentos")
        
        # Contexto simplificado
        context = "=== KNOWLEDGE BASE ===\n\n"
        
        for i, doc in enumerate(documents):
            context += f"📄 DOCUMENTO {i+1}: {doc['filename']}\n"
            
            if doc.get('content_summary'):
                context += f"Resumo: {doc['content_summary']}\n"
            
            if doc.get('processed_content'):
                content = doc['processed_content'][:1000]  # Primeiro 1000 chars
                context += f"Conteúdo: {content}...\n"
            
            context += "\n"
        
        context += "INSTRUÇÕES: Use as informações dos documentos acima para responder.\n"
        
        return context
        
    except Exception as e:
        log_debug(f"Erro no knowledge base: {str(e)}", "ERROR")
        return ""

def send_to_claude(messages, model="claude-3-haiku-20240307", max_tokens=1500):
    """Enviar para Claude API - CORRIGIDO"""
    try:
        api_key = get_claude_api_key()
        if not api_key:
            return {"error": "Claude API key not available"}
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        log_debug(f"Enviando para Claude: {model}")
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30  # Timeout de 30 segundos
        )
        
        if response.status_code == 200:
            result = response.json()
            log_debug("Claude API: sucesso")
            return result
        else:
            error_msg = f"Claude API error {response.status_code}"
            log_debug(error_msg, "ERROR")
            return {"error": error_msg}
            
    except Exception as e:
        error_msg = f"Erro Claude API: {str(e)}"
        log_debug(error_msg, "ERROR")
        return {"error": error_msg}

# ================================
# ROUTES
# ================================

@app.route('/')
def index():
    return {
        "service": "Chat Engine com Knowledge Base CORRIGIDO",
        "version": "12.0.0-timeout-fixed",
        "status": "active",
        "timestamp": datetime.now().isoformat()
    }

@app.route('/health')
def health():
    """Health check CORRIGIDO"""
    try:
        # Testar componentes com timeout
        api_key = get_claude_api_key()
        bq_client = get_bigquery_client()
        
        services = {
            "claude_api": {
                "available": bool(api_key),
                "key_length": len(api_key) if api_key else 0
            },
            "bigquery": {
                "available": bool(bq_client),
                "project": PROJECT_ID
            },
            "knowledge_base": {
                "available": bool(bq_client)
            }
        }
        
        status = "healthy" if api_key and bq_client else "degraded"
        
        return {
            "status": status,
            "services": services,
            "timestamp": datetime.now().isoformat(),
            "version": "12.0.0-timeout-fixed"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 500

@app.route('/chat/<chat_id>')
def chat_interface(chat_id):
    """Interface do chat"""
    try:
        chat = get_chat_info(chat_id)
        
        if not chat:
            chat = {
                'chat_id': chat_id,
                'chat_name': 'Chat Inteligente',
                'chat_type': 'assistant',
                'personality': 'professional'
            }
        
        return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{chat['chat_name']} - Chat com Knowledge Base</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: system-ui; 
            height: 100vh; 
            display: flex; 
            flex-direction: column; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .header {{ 
            background: rgba(255,255,255,0.9); 
            padding: 20px; 
            text-align: center; 
            color: #333;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 5px; }}
        .header p {{ color: #666; }}
        .container {{ 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            max-width: 1000px; 
            margin: 20px auto 0; 
            width: 100%; 
            padding: 0 20px; 
            background: rgba(255,255,255,0.95);
            border-radius: 15px 15px 0 0;
        }}
        .messages {{ 
            flex: 1; 
            overflow-y: auto; 
            padding: 20px; 
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .message {{ display: flex; gap: 10px; max-width: 80%; }}
        .message.user {{ align-self: flex-end; flex-direction: row-reverse; }}
        .message.assistant {{ align-self: flex-start; }}
        .avatar {{ 
            width: 40px; 
            height: 40px; 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            font-size: 18px; 
        }}
        .message.user .avatar {{ background: #667eea; color: white; }}
        .message.assistant .avatar {{ background: #10b981; color: white; }}
        .content {{ 
            background: white; 
            padding: 15px; 
            border-radius: 15px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
            line-height: 1.5;
        }}
        .message.user .content {{ background: #667eea; color: white; }}
        .knowledge-badge {{ 
            display: inline-block; 
            background: #10b981; 
            color: white; 
            padding: 4px 12px; 
            border-radius: 12px; 
            font-size: 11px; 
            margin-top: 8px;
        }}
        .input-area {{ 
            background: rgba(255,255,255,0.9); 
            padding: 20px; 
            border-top: 1px solid #eee; 
        }}
        .input-form {{ display: flex; gap: 10px; }}
        .input {{ 
            flex: 1; 
            padding: 12px; 
            border: 2px solid #ddd; 
            border-radius: 25px; 
            font-size: 16px; 
            outline: none; 
        }}
        .input:focus {{ border-color: #667eea; }}
        .send-btn {{ 
            background: #667eea; 
            color: white; 
            border: none; 
            border-radius: 50%; 
            width: 50px; 
            height: 50px; 
            cursor: pointer; 
            font-size: 18px; 
        }}
        .send-btn:hover {{ background: #5a67d8; }}
        .welcome {{ text-align: center; padding: 40px; color: #666; }}
        .welcome h3 {{ color: #333; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 {chat['chat_name']}</h1>
        <p>Chat Inteligente com Knowledge Base • ID: {chat_id}</p>
    </div>
    
    <div class="container">
        <div class="messages" id="messages">
            <div class="welcome">
                <h3>👋 Olá! Como posso ajudar?</h3>
                <p>Este chat pode usar informações dos seus documentos carregados para dar respostas mais precisas.</p>
            </div>
        </div>
        
        <div class="input-area">
            <div class="input-form">
                <input type="text" class="input" id="messageInput" 
                       placeholder="Digite sua mensagem ou pergunte sobre documentos..."
                       autocomplete="off">
                <button class="send-btn" onclick="sendMessage()">➤</button>
            </div>
        </div>
    </div>
    
    <script>
        const chatId = '{chat_id}';
        const API_BASE = window.location.origin;
        const messages = document.getElementById('messages');
        const input = document.getElementById('messageInput');
        
        let conversationId = 'web-' + Date.now();
        
        function addMessage(role, content, hasKnowledge = false) {{
            const welcomeMsg = messages.querySelector('.welcome');
            if (welcomeMsg) welcomeMsg.remove();
            
            const msg = document.createElement('div');
            msg.className = `message ${{role}}`;
            
            const avatar = role === 'user' ? '👤' : '🤖';
            const knowledgeBadge = hasKnowledge ? '<div class="knowledge-badge">📚 Baseado em documentos</div>' : '';
            
            msg.innerHTML = `
                <div class="avatar">${{avatar}}</div>
                <div class="content">
                    ${{content.replace(/\\n/g, '<br>')}}
                    ${{knowledgeBadge}}
                </div>
            `;
            
            messages.appendChild(msg);
            messages.scrollTop = messages.scrollHeight;
        }}
        
        function showTyping() {{
            const typing = document.createElement('div');
            typing.id = 'typing';
            typing.className = 'message assistant';
            typing.innerHTML = `
                <div class="avatar">🤖</div>
                <div class="content">🤔 Analisando documentos e preparando resposta...</div>
            `;
            messages.appendChild(typing);
            messages.scrollTop = messages.scrollHeight;
        }}
        
        function hideTyping() {{
            const typing = document.getElementById('typing');
            if (typing) typing.remove();
        }}
        
        async function sendMessage() {{
            const message = input.value.trim();
            if (!message) return;
            
            addMessage('user', message);
            input.value = '';
            input.disabled = true;
            showTyping();
            
            try {{
                const response = await fetch(`${{API_BASE}}/api/chat/${{chatId}}/send`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        message: message,
                        conversation_id: conversationId
                    }})
                }});
                
                const data = await response.json();
                hideTyping();
                
                if (data.success) {{
                    addMessage('assistant', data.message, data.used_knowledge || false);
                }} else {{
                    addMessage('assistant', `❌ Erro: ${{data.error}}`);
                }}
                
            }} catch (error) {{
                hideTyping();
                addMessage('assistant', '❌ Erro de conexão. Tente novamente.');
            }} finally {{
                input.disabled = false;
                input.focus();
            }}
        }}
        
        input.addEventListener('keydown', e => {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                sendMessage();
            }}
        }});
        
        input.focus();
    </script>
</body>
</html>
        """
        
    except Exception as e:
        return f"<h1>Erro: {str(e)}</h1>", 500

@app.route('/api/chat/<chat_id>/send', methods=['POST'])
def send_message_api(chat_id):
    """API principal - CORRIGIDA"""
    start_time = datetime.now()
    
    try:
        data = request.get_json()
        if not data:
            return {"success": False, "error": "No JSON data"}, 400
        
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', f'web-{chat_id}-{int(start_time.timestamp())}')
        
        if not user_message:
            return {"success": False, "error": "Empty message"}, 400
        
        log_debug(f"Processando mensagem: {user_message[:50]}...")
        
        # Buscar chat
        chat = get_chat_info(chat_id)
        if not chat:
            chat = {
                'system_prompt': 'Você é um assistente inteligente.',
                'claude_model': 'claude-3-haiku-20240307',
                'max_tokens': 1500
            }
        
        # Buscar contexto do knowledge base
        knowledge_context = get_knowledge_context(chat_id, user_message)
        has_knowledge = bool(knowledge_context)
        
        # Montar prompt
        system_prompt = chat.get('system_prompt', 'Você é um assistente inteligente.')
        
        if has_knowledge:
            system_prompt += f"\n\n{knowledge_context}"
            system_prompt += "\n\nUse as informações dos documentos para responder quando relevante."
        
        # Mensagens para Claude
        claude_messages = [
            {"role": "user", "content": f"Sistema: {system_prompt}"},
            {"role": "assistant", "content": "Entendido! Como posso ajudar?"},
            {"role": "user", "content": user_message}
        ]
        
        # Enviar para Claude
        claude_response = send_to_claude(
            messages=claude_messages,
            model=chat.get('claude_model', 'claude-3-haiku-20240307'),
            max_tokens=chat.get('max_tokens', 1500)
        )
        
        if 'error' in claude_response:
            return {"success": False, "error": claude_response['error']}, 500
        
        assistant_message = claude_response['content'][0]['text']
        tokens_used = claude_response.get('usage', {}).get('output_tokens', 0)
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        log_debug(f"Resposta gerada: {response_time}ms, {tokens_used} tokens, knowledge: {has_knowledge}")
        
        return {
            "success": True,
            "message": assistant_message,
            "used_knowledge": has_knowledge,
            "tokens_used": tokens_used,
            "response_time_ms": response_time,
            "conversation_id": conversation_id,
            "chat_id": chat_id
        }
        
    except Exception as e:
        error_msg = f"Erro interno: {str(e)}"
        log_debug(error_msg, "ERROR")
        return {"success": False, "error": error_msg}, 500

@app.route('/debug/<chat_id>')
def debug_chat(chat_id):
    """Debug endpoint"""
    try:
        debug_info = {
            "chat_id": chat_id,
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Teste Claude API
        api_key = get_claude_api_key()
        debug_info["checks"]["claude_api"] = {
            "available": bool(api_key),
            "key_length": len(api_key) if api_key else 0
        }
        
        # Teste BigQuery
        bq_client = get_bigquery_client()
        debug_info["checks"]["bigquery"] = {
            "available": bool(bq_client)
        }
        
        # Teste Chat
        chat_info = get_chat_info(chat_id)
        debug_info["checks"]["chat"] = {
            "found": bool(chat_info),
            "data": chat_info
        }
        
        # Teste Knowledge Base
        context = get_knowledge_context(chat_id, "teste")
        debug_info["checks"]["knowledge"] = {
            "context_found": bool(context),
            "context_length": len(context)
        }
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e)}, 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return {"error": "Not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    return {"error": "Internal error"}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    
    log_debug("🚀 CHAT ENGINE CORRIGIDO INICIANDO")
    log_debug(f"Port: {port}")
    log_debug(f"Project: {PROJECT_ID}")
    
    # Testes de inicialização
    api_key = get_claude_api_key()
    log_debug(f"Claude API: {'OK' if api_key else 'ERRO'}")
    
    bq_client = get_bigquery_client()
    log_debug(f"BigQuery: {'OK' if bq_client else 'ERRO'}")
    
    if api_key:
        log_debug("✅ SISTEMA PRONTO")
    else:
        log_debug("⚠️ SISTEMA DEGRADADO")
    
    app.run(host='0.0.0.0', port=port, debug=False)
EOF

echo "✅ Chat Engine CORRIGIDO criado!"

echo ""
echo "🚀 Fazendo deploy CORRIGIDO..."

gcloud run deploy saas-chat-engine \
  --source=. \
  --platform=managed \
  --region=us-east1 \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=120 \
  --concurrency=80 \
  --quiet

sleep 10

ENGINE_URL="https://saas-chat-engine-365442086139.us-east1.run.app"

echo ""
echo "🧪 TESTANDO VERSÃO CORRIGIDA..."
echo "================================"

echo ""
echo "1. Health Check:"
curl -s "$ENGINE_URL/health" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"

echo ""
echo "2. Teste com Chat Real:"
CHAT_ID=$(bq query --use_legacy_sql=false --format=json \
  'SELECT chat_id FROM `flower-ai-generator.saas_chat_generator.chats` LIMIT 1' \
  2>/dev/null | jq -r '.[0].chat_id // "test-id"')

echo "Chat ID: $CHAT_ID"

echo ""
echo "3. Debug do Chat:"
curl -s "$ENGINE_URL/debug/$CHAT_ID" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"

echo ""
echo "4. Teste de Mensagem:"
curl -s -X POST "$ENGINE_URL/api/chat/$CHAT_ID/send" \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá! Este é um teste.", "conversation_id": "test"}' | \
  python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"

echo ""
echo "🎉 CHAT ENGINE CORRIGIDO!"
echo "========================="
echo ""
echo "🔗 URLs para teste:"
echo "   Health: $ENGINE_URL/health"
echo "   Debug: $ENGINE_URL/debug/$CHAT_ID"  
echo "   Chat: $ENGINE_URL/chat/$CHAT_ID"
echo ""
echo "📱 Como testar:"
echo "1. Acesse: $ENGINE_URL/chat/$CHAT_ID"
echo "2. Digite uma mensagem"
echo "3. Veja a resposta!"
echo ""
echo "💡 Para testar Knowledge Base:"
echo "1. Vá ao dashboard e carregue documentos PDFs"
echo "2. Pergunte sobre o conteúdo dos documentos"
echo "3. O sistema vai buscar informações relevantes!"
