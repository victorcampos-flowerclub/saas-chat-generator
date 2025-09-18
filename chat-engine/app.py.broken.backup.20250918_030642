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
