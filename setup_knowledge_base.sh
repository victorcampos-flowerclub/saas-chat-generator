#!/bin/bash

echo "🧠 Configurando Knowledge Base System..."
echo "========================================"

cd ~/saas-chat-generator

# 1. Instalar dependências adicionais
echo "📦 Instalando dependências..."

cat >> backend/requirements.txt << 'EOF'
PyPDF2==3.0.1
python-magic==0.4.27
google-cloud-storage==2.10.0
requests==2.31.0
markdown==3.5.1
EOF

cat >> chat-engine/requirements.txt << 'EOF'
PyPDF2==3.0.1
python-magic==0.4.27
google-cloud-storage==2.10.0
EOF

# 2. Criar sistema de Knowledge Base
cp knowledge_base_system.py backend/
cp knowledge_base_system.py chat-engine/

# 3. Adicionar APIs ao backend
echo "🔧 Atualizando backend com APIs de Knowledge Base..."

cat >> backend/app.py << 'EOF'

# ================================
# IMPORTS PARA KNOWLEDGE BASE
# ================================
from knowledge_base_system import knowledge_service
import base64
from datetime import datetime, timezone
from google.cloud import bigquery

# ================================
# ROUTES DE KNOWLEDGE BASE
# ================================

@app.route('/api/chats/<chat_id>/documents', methods=['POST'])
@jwt_required()
def upload_document(chat_id):
    """Upload de documento para o chat"""
    try:
        user_id = get_jwt_identity()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        # Verificar se há arquivo
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Arquivo vazio'}), 400
        
        # Validar tipo de arquivo
        allowed_types = [
            'application/pdf',
            'text/plain',
            'text/markdown',
            'application/json',
            'text/csv'
        ]
        
        if file.content_type not in allowed_types:
            return jsonify({
                'success': False, 
                'error': f'Tipo de arquivo não suportado: {file.content_type}'
            }), 400
        
        # Validar tamanho (máximo 10MB)
        file_data = file.read()
        if len(file_data) > 10 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'Arquivo muito grande (máximo 10MB)'}), 400
        
        # Upload do documento
        result = knowledge_service.upload_document(
            chat_id=chat_id,
            file_data=file_data,
            filename=file.filename,
            content_type=file.content_type
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chats/<chat_id>/documents/github', methods=['POST'])
@jwt_required()
def import_github_content(chat_id):
    """Importar conteúdo do GitHub"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        github_url = data.get('github_url')
        if not github_url:
            return jsonify({'success': False, 'error': 'URL do GitHub obrigatória'}), 400
        
        # Importar conteúdo
        result = knowledge_service.fetch_github_content(chat_id, github_url)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chats/<chat_id>/documents', methods=['GET'])
@jwt_required()
def get_chat_documents(chat_id):
    """Listar documentos do chat"""
    try:
        user_id = get_jwt_identity()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        documents = knowledge_service.get_chat_documents(chat_id)
        
        return jsonify({
            'success': True,
            'documents': documents
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chats/<chat_id>/documents/<document_id>', methods=['DELETE'])
@jwt_required()
def delete_document(chat_id, document_id):
    """Deletar documento"""
    try:
        user_id = get_jwt_identity()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        result = knowledge_service.delete_document(document_id, chat_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chats/<chat_id>', methods=['PUT'])
@jwt_required()
def update_chat(chat_id):
    """Atualizar configurações do chat"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        # Campos que podem ser atualizados
        updatable_fields = [
            'chat_name', 'chat_description', 'system_prompt', 
            'personality', 'claude_model', 'max_tokens', 
            'temperature', 'status'
        ]
        
        update_data = {}
        for field in updatable_fields:
            if field in data:
                update_data[field] = data[field]
        
        if not update_data:
            return jsonify({'success': False, 'error': 'Nenhum campo para atualizar'}), 400
        
        # Atualizar no BigQuery
        update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        set_clause = ', '.join([f"{field} = @{field}" for field in update_data.keys()])
        query = f"""
        UPDATE `{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.chats`
        SET {set_clause}
        WHERE chat_id = @chat_id AND user_id = @user_id
        """
        
        query_parameters = [
            bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id),
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
        ]
        
        for field, value in update_data.items():
            param_type = "STRING"
            if field in ['max_tokens']:
                param_type = "INTEGER"
            elif field in ['temperature']:
                param_type = "FLOAT"
            
            query_parameters.append(
                bigquery.ScalarQueryParameter(field, param_type, value)
            )
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
        query_job = chat_model.client.query(query, job_config=job_config)
        
        return jsonify({
            'success': True,
            'message': 'Chat atualizado com sucesso',
            'updated_fields': list(update_data.keys())
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/manage/<chat_id>')
def manage_chat_page(chat_id):
    """Página de gerenciamento do chat"""
    return render_template('manage_chat.html', chat_id=chat_id)
EOF

# 4. Atualizar chat engine
echo "🤖 Atualizando chat engine..."

cp chat-engine/app.py chat-engine/app.py.backup
cat > chat-engine/app.py << 'EOF'
"""
Chat Engine - Interface individual de chat em tempo real (COM KNOWLEDGE BASE)
"""

import os
import sys
import json
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timezone
import requests

# Adicionar path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.models.database import chat_model, message_model, user_model
from google.cloud import secretmanager
from knowledge_base_system import knowledge_service

# Inicializar Flask
app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=["*"])

class ClaudeService:
    def __init__(self):
        self.api_key = self._get_claude_api_key()
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    def _get_claude_api_key(self):
        """Buscar API key do Claude no Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{Config.PROJECT_ID}/secrets/claude-api-key/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"Erro ao buscar API key: {e}")
            return None
    
    def send_message(self, messages, model="claude-3-haiku-20240307", max_tokens=1500):
        """Enviar mensagem para Claude (SÍNCRONO)"""
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
            return {"error": f"Erro na API do Claude: {str(e)}"}

claude_service = ClaudeService()

@app.route('/')
def index():
    """Página inicial do chat engine"""
    return render_template('chat_selection.html')

@app.route('/chat/<chat_id>')
def chat_interface(chat_id):
    """Interface principal do chat"""
    # Verificar se chat existe
    chat = chat_model.get_chat_by_id(chat_id)
    if not chat:
        return render_template('chat_not_found.html'), 404
    
    return render_template('chat_interface.html', chat=chat)

@app.route('/api/chat/<chat_id>/info', methods=['GET'])
def get_chat_info(chat_id):
    """Obter informações do chat"""
    try:
        chat = chat_model.get_chat_by_id(chat_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        # Buscar informações do usuário
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
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat/<chat_id>/send', methods=['POST'])
def send_message(chat_id):
    """Enviar mensagem para o chat com contexto de documentos"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        if not user_message:
            return jsonify({'success': False, 'error': 'Mensagem vazia'}), 400
        
        # Buscar configurações do chat
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
        
        # Buscar histórico da conversa
        history = message_model.get_conversation_history(chat_id, conversation_id, limit=10)
        
        # NOVO: Buscar contexto relevante dos documentos
        knowledge_context = knowledge_service.get_chat_knowledge_context(
            chat_id=chat_id, 
            query_text=user_message,
            max_docs=3
        )
        
        # Preparar mensagens para Claude
        claude_messages = []
        
        # System prompt melhorado com contexto
        enhanced_system_prompt = chat['system_prompt']
        
        if knowledge_context:
            enhanced_system_prompt += f"\n\n{knowledge_context}\n\n"
            enhanced_system_prompt += """
INSTRUÇÕES PARA USO DOS DOCUMENTOS:
- Use as informações dos documentos fornecidos quando relevantes para a pergunta
- Cite os documentos quando usar informações específicas deles
- Se a informação não estiver nos documentos, use seu conhecimento geral
- Seja preciso e factual ao referenciar os documentos
"""
        
        claude_messages.append({
            "role": "user",
            "content": f"Sistema: {enhanced_system_prompt}"
        })
        claude_messages.append({
            "role": "assistant", 
            "content": "Entendido. Estou pronto para ajudar seguindo essas instruções e usando os documentos fornecidos quando relevantes."
        })
        
        # Adicionar histórico
        for msg in history:
            if msg['role'] in ['user', 'assistant']:
                claude_messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
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
        
        # Extrair resposta do Claude
        assistant_message = claude_response['content'][0]['text']
        tokens_used = claude_response.get('usage', {}).get('output_tokens', 0)
        
        # Metadados sobre o contexto usado
        context_metadata = {
            'documents_used': len(knowledge_context.split('📄')) - 1 if knowledge_context else 0,
            'has_knowledge_context': bool(knowledge_context)
        }
        
        # Salvar resposta do Claude
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
            'response_time_ms': response_time,
            'context_metadata': context_metadata
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/chat/<chat_id>/history/<conversation_id>', methods=['GET'])
def get_conversation_history(chat_id, conversation_id):
    """Buscar histórico da conversa"""
    try:
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

@app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'service': 'chat-engine'})

if __name__ == '__main__':
    print("🤖 Iniciando Chat Engine...")
    print(f"🔗 Acesse: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
EOF

# 5. Adicionar template de management
cp manage_chat.html backend/templates/

# 6. Atualizar dashboard para incluir links de management
echo "📊 Atualizando dashboard..."

# Adicionar botão de gerenciar no dashboard
sed -i 's|<button class="btn btn-small" onclick="testChat.*|<button class="btn btn-small" onclick="manageChat('\''${chat.chat_id}'\'')">Gerenciar</button>|g' backend/templates/dashboard.html

# Adicionar função JavaScript
cat >> backend/templates/dashboard.html << 'EOF'

<script>
function manageChat(chatId) {
    window.open(`/manage/${chatId}`, '_blank');
}
</script>
EOF

# 7. Criar bucket no Google Cloud Storage
echo "🗄️ Criando bucket para documentos..."

gsutil mb gs://flower-ai-generator-chat-knowledge 2>/dev/null || echo "Bucket já existe"

# 8. Atualizar schema do BigQuery
echo "📊 Atualizando BigQuery schema..."

python3 -c "
from create_database_schema import create_saas_database_schema
print('Verificando/criando tabelas do BigQuery...')
create_saas_database_schema()
"

echo ""
echo "✅ Knowledge Base System configurado com sucesso!"
echo ""
echo "🎯 Funcionalidades implementadas:"
echo "   📄 Upload de documentos (PDF, TXT, MD, JSON, CSV)"
echo "   🐙 Integração com GitHub"
echo "   🗄️ Storage no Google Cloud Storage"
echo "   🧠 RAG (Retrieval Augmented Generation)"
echo "   ⚙️ Interface de management completa"
echo ""
echo "🚀 Para testar:"
echo "1. Execute os serviços normalmente"
echo "2. Crie um chat no dashboard"
echo "3. Clique em 'Gerenciar' para adicionar documentos"
echo "4. Teste o chat - ele vai usar o contexto dos documentos!"
echo ""
echo "🔗 URLs importantes:"
echo "   Dashboard: http://localhost:5002/dashboard"
echo "   Management: http://localhost:5002/manage/[CHAT_ID]"
echo "   Chat Engine: http://localhost:5001/chat/[CHAT_ID]"
