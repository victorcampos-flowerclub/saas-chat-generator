"""
Backend principal do SaaS Chat Generator - VERSÃO CORRIGIDA
"""

import os
import sys
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import timedelta
import json

# Adicionar o diretório pai ao path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from auth.auth_service import auth_service
from models.database import user_model, chat_model, message_model

# Inicializar Flask
app = Flask(__name__)
app.config.from_object(Config)

# Configurar CORS
CORS(app, origins=["*"])

# Configurar JWT
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# ================================
# KNOWLEDGE BASE SETUP
# ================================
try:
    from knowledge_base_system import knowledge_service
    KNOWLEDGE_BASE_ENABLED = True
    print("✅ Knowledge Base habilitado")
except ImportError as e:
    KNOWLEDGE_BASE_ENABLED = False
    print(f"⚠️ Knowledge Base não disponível: {e}")

# ================================
# ROUTES DE AUTENTICAÇÃO
# ================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registrar novo usuário"""
    try:
        data = request.get_json()
        
        result = auth_service.register_user(
            email=data.get('email'),
            password=data.get('password'),
            full_name=data.get('full_name'),
            company_name=data.get('company_name'),
            phone=data.get('phone')
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Usuário criado com sucesso',
                'user': result['user'],
                'access_token': result['access_token']
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login do usuário"""
    try:
        data = request.get_json()
        
        result = auth_service.login_user(
            email=data.get('email'),
            password=data.get('password')
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Login realizado com sucesso',
                'user': result['user'],
                'access_token': result['access_token']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Obter dados do usuário atual"""
    try:
        user_id = get_jwt_identity()
        user = user_model.get_user_by_id(user_id)
        
        if user:
            return jsonify({
                'success': True,
                'user': user
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Usuário não encontrado'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

# ================================
# ROUTES DE CHATS
# ================================

@app.route('/api/chats', methods=['GET'])
@jwt_required()
def get_user_chats():
    """Listar chats do usuário"""
    try:
        user_id = get_jwt_identity()
        chats = chat_model.get_user_chats(user_id)
        
        return jsonify({
            'success': True,
            'chats': chats
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/chats', methods=['POST'])
@jwt_required()
def create_chat():
    """Criar novo chat"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validações básicas
        required_fields = ['chat_name', 'chat_type', 'system_prompt']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field}'
                }), 400
        
        # Verificar limites do plano do usuário
        user = user_model.get_user_by_id(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'Usuário não encontrado'
            }), 404
        
        current_chats = chat_model.get_user_chats(user_id)
        plan_limits = Config.PLANS.get(user['plan'], {})
        max_chats = plan_limits.get('max_chats', 0)
        
        if max_chats != -1 and len(current_chats) >= max_chats:
            return jsonify({
                'success': False,
                'error': f'Limite de {max_chats} chats atingido para o plano {user["plan"]}'
            }), 403
        
        # Criar chat
        chat = chat_model.create_chat(
            user_id=user_id,
            chat_name=data['chat_name'],
            chat_type=data['chat_type'],
            system_prompt=data['system_prompt'],
            personality=data.get('personality', 'professional'),
            claude_model=data.get('claude_model', Config.CLAUDE_MODEL),
            max_tokens=data.get('max_tokens', 1500)
        )
        
        if chat:
            return jsonify({
                'success': True,
                'message': 'Chat criado com sucesso',
                'chat': chat
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Erro ao criar chat'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/chats/<chat_id>', methods=['GET'])
@jwt_required()
def get_chat(chat_id):
    """Obter detalhes de um chat"""
    try:
        user_id = get_jwt_identity()
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        
        if chat:
            return jsonify({
                'success': True,
                'chat': chat
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Chat não encontrado'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

# ================================
# KNOWLEDGE BASE ROUTES
# ================================

if KNOWLEDGE_BASE_ENABLED:
    
    @app.route('/manage/<chat_id>')
    def manage_chat_page(chat_id):
        """Página de gerenciamento do chat"""
        return render_template('manage_chat.html', chat_id=chat_id)
    
    @app.route('/api/chats/<chat_id>/documents', methods=['GET'])
    @jwt_required()
    def get_chat_documents(chat_id):
        """Listar documentos do chat"""
        try:
            user_id = get_jwt_identity()
            chat = chat_model.get_chat_by_id(chat_id, user_id)
            if not chat:
                return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
            
            documents = knowledge_service.get_chat_documents(chat_id)
            return jsonify({'success': True, 'documents': documents}), 200
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/chats/<chat_id>/documents', methods=['POST'])
    @jwt_required()
    def upload_document(chat_id):
        """Upload de documento para o chat"""
        try:
            user_id = get_jwt_identity()
            chat = chat_model.get_chat_by_id(chat_id, user_id)
            if not chat:
                return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
            
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'Arquivo vazio'}), 400
            
            file_data = file.read()
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
            
            chat = chat_model.get_chat_by_id(chat_id, user_id)
            if not chat:
                return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
            
            github_url = data.get('github_url')
            if not github_url:
                return jsonify({'success': False, 'error': 'URL do GitHub obrigatória'}), 400
            
            result = knowledge_service.fetch_github_content(chat_id, github_url)
            
            if result['success']:
                return jsonify(result), 201
            else:
                return jsonify(result), 500
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/chats/<chat_id>/documents/<document_id>', methods=['DELETE'])
    @jwt_required()
    def delete_document(chat_id, document_id):
        """Deletar documento"""
        try:
            user_id = get_jwt_identity()
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

else:
    # Fallback routes se Knowledge Base não estiver disponível
    @app.route('/manage/<chat_id>')
    def manage_chat_fallback(chat_id):
        return jsonify({'error': 'Knowledge Base não disponível'}), 503

# ================================
# ROUTES DO SISTEMA
# ================================

@app.route('/')
def index():
    """Página inicial"""
    return jsonify({
        'system': 'SaaS Chat Generator',
        'version': '1.0.0',
        'status': 'operational',
        'knowledge_base': KNOWLEDGE_BASE_ENABLED,
        'endpoints': {
            'auth': '/api/auth/*',
            'chats': '/api/chats/*',
            'management': '/manage/*'
        }
    })

@app.route('/health')
def health():
    """Health check"""
    try:
        # Testar conexão com BigQuery
        test_query = "SELECT 1 as test"
        user_model._execute_query(test_query)
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'knowledge_base': KNOWLEDGE_BASE_ENABLED,
            'timestamp': Config.CLAUDE_MODEL
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

# ================================
# ROUTES DE FRONTEND
# ================================

@app.route('/login')
def login_page():
    """Página de login"""
    return render_template('login.html')

@app.route('/dashboard')
def dashboard_page():
    """Página do dashboard"""
    return render_template('dashboard.html')

# ================================
# ERROR HANDLERS
# ================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint não encontrado'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Erro interno do servidor'
    }), 500

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'success': False,
        'error': 'Token expirado'
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'success': False,
        'error': 'Token inválido'
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        'success': False,
        'error': 'Token de acesso obrigatório'
    }), 401

if __name__ == '__main__':
    print("🚀 Iniciando SaaS Chat Generator Backend...")
    print(f"📊 Projeto: {Config.PROJECT_ID}")
    print(f"🗄️ Dataset: {Config.BIGQUERY_DATASET}")
    print(f"🤖 Modelo Claude: {Config.CLAUDE_MODEL}")
    print(f"🧠 Knowledge Base: {KNOWLEDGE_BASE_ENABLED}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
