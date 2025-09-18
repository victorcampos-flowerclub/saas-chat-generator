"""
Chat Engine OTIMIZADO - Imports lazy para evitar timeout
"""
import os
import sys
import json
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timezone
import requests

# Configuração simples
class Config:
    PROJECT_ID = 'flower-ai-generator'
    BIGQUERY_DATASET = 'saas_chat_generator'
    CLAUDE_MODEL = 'claude-sonnet-4-20250514'

# Flask app
app = Flask(__name__)
CORS(app, origins=["*"])

# LAZY LOADING - só importa quando necessário
_bigquery_client = None
_secret_client = None

def get_bigquery_client():
    """Lazy import do BigQuery"""
    global _bigquery_client
    if _bigquery_client is None:
        try:
            from google.cloud import bigquery
            _bigquery_client = bigquery.Client(project=Config.PROJECT_ID)
        except Exception as e:
            print(f"Erro BigQuery: {e}")
            _bigquery_client = False
    return _bigquery_client if _bigquery_client is not False else None

def get_secret_client():
    """Lazy import do Secret Manager"""
    global _secret_client
    if _secret_client is None:
        try:
            from google.cloud import secretmanager
            _secret_client = secretmanager.SecretManagerServiceClient()
        except Exception as e:
            print(f"Erro Secret Manager: {e}")
            _secret_client = False
    return _secret_client if _secret_client is not False else None

def get_claude_api_key():
    """Buscar API key (lazy)"""
    try:
        client = get_secret_client()
        if not client:
            return None
        name = f"projects/{Config.PROJECT_ID}/secrets/claude-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        print(f"Erro API key: {e}")
        return None

def get_chat_by_id(chat_id):
    """Buscar chat por ID (lazy)"""
    try:
        client = get_bigquery_client()
        if not client:
            return {'chat_id': chat_id, 'chat_name': 'Chat Teste', 'system_prompt': 'Você é um assistente útil.'}
        
        from google.cloud import bigquery
        query = f"""
        SELECT * FROM `{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.chats`
        WHERE chat_id = @chat_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        return dict(results[0]) if results else None
    except Exception as e:
        print(f"Erro ao buscar chat: {e}")
        # Fallback
        return {'chat_id': chat_id, 'chat_name': 'Chat Teste', 'system_prompt': 'Você é um assistente útil.'}

def save_message(chat_id, conversation_id, role, content, source='web', tokens_used=0, response_time_ms=0):
    """Salvar mensagem (lazy)"""
    try:
        client = get_bigquery_client()
        if not client:
            return False
            
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
        errors = client.insert_rows_json(table_ref, [message_data])
        
        return len(errors) == 0
    except Exception as e:
        print(f"Erro ao salvar mensagem: {e}")
        return False

def send_claude_message(messages, model="claude-3-haiku-20240307", max_tokens=1500):
    """Enviar para Claude (lazy)"""
    try:
        api_key = get_claude_api_key()
        if not api_key:
            return {"error": "API key não configurada"}
        
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
        
        response = requests.post("https://api.anthropic.com/v1/messages", 
                               headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Erro Claude API: {str(e)}"}

# ROUTES
@app.route('/')
def index():
    return jsonify({
        'status': 'Chat Engine OTIMIZADO funcionando!',
        'version': '2.1.0-optimized',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'chat-engine-optimized',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/chat/<chat_id>')
def chat_interface(chat_id):
    try:
        chat = get_chat_by_id(chat_id)
        if not chat:
            return render_template('chat_not_found.html'), 404
        return render_template('chat_interface.html', chat=chat)
    except Exception as e:
        print(f"Erro ao carregar chat: {e}")
        return f"<h1>Erro</h1><p>Chat: {str(e)}</p>", 404

@app.route('/api/chat/<chat_id>/info', methods=['GET'])
def get_chat_info(chat_id):
    try:
        chat = get_chat_by_id(chat_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        return jsonify({
            'success': True,
            'chat': chat,
            'user': {'full_name': 'Usuário', 'plan': 'free'}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat/<chat_id>/send', methods=['POST'])
def send_message_route(chat_id):
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        if not user_message:
            return jsonify({'success': False, 'error': 'Mensagem vazia'}), 400
        
        chat = get_chat_by_id(chat_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        # Salvar mensagem do usuário
        save_message(chat_id, conversation_id, 'user', user_message, 'web')
        
        # Claude
        claude_messages = [
            {"role": "user", "content": f"Sistema: {chat.get('system_prompt', 'Você é um assistente útil.')}"},
            {"role": "assistant", "content": "Entendido. Estou pronto para ajudar."},
            {"role": "user", "content": user_message}
        ]
        
        start_time = datetime.now()
        claude_response = send_claude_message(
            messages=claude_messages,
            model=chat.get('claude_model', 'claude-3-haiku-20240307'),
            max_tokens=chat.get('max_tokens', 1500)
        )
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        if 'error' in claude_response:
            return jsonify({'success': False, 'error': claude_response['error']}), 500
        
        assistant_message = claude_response['content'][0]['text']
        tokens_used = claude_response.get('usage', {}).get('output_tokens', 0)
        
        # Salvar resposta
        save_message(chat_id, conversation_id, 'assistant', assistant_message, 
                    'web', tokens_used, response_time)
        
        return jsonify({
            'success': True,
            'message': assistant_message,
            'conversation_id': conversation_id,
            'tokens_used': tokens_used,
            'response_time_ms': response_time
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
