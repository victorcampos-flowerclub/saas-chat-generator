from ai_prompt_improved import improved_ai_generator
"""
Backend principal do SaaS Chat Generator
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
import uuid

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
# KNOWLEDGE BASE IMPORTS
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
    """Criar novo chat com processamento automático de documentos"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validações básicas
        required_fields = ['chat_name', 'chat_type']
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
        
        # Determinar o system_prompt
        system_prompt = data.get('system_prompt', '')
        
        # Se não tem prompt ou é muito simples, gerar com IA (se disponível)
        if (not system_prompt or len(system_prompt.strip()) < 50) and AI_PROMPT_ENABLED:
            print("🤖 Gerando prompt automático com IA...")
            try:
                # Criar chat temporário para análise
                temp_chat_id = str(uuid.uuid4())
                
                # Se há documentos, analisar
                chat_config = {
                    'chat_name': data['chat_name'],
                    'chat_type': data['chat_type'],
                    'personality': data.get('personality', 'professional'),
                    'chat_description': data.get('chat_description', '')
                }
                
                # Buscar documentos se foi fornecido um temp_chat_id
                temp_chat_from_frontend = data.get('temp_chat_id')
                if temp_chat_from_frontend and KNOWLEDGE_BASE_ENABLED:
                    documents_analysis = ai_prompt_generator.analyze_documents(temp_chat_from_frontend)
                else:
                    documents_analysis = ai_prompt_generator._default_analysis()
                
                # Gerar prompt otimizado
                generated_prompt = ai_prompt_generator.generate_optimized_prompt(
                    chat_config=chat_config,
                    documents_analysis=documents_analysis
                )
                
                if generated_prompt and len(generated_prompt.strip()) > 20:
                    system_prompt = generated_prompt
                    print("✅ Prompt gerado automaticamente com IA")
                else:
                    system_prompt = f"Você é um assistente {data.get('personality', 'professional')} especializado em {data['chat_type']}."
                    
            except Exception as e:
                print(f"⚠️ Erro ao gerar prompt com IA: {e}")
                system_prompt = f"Você é um assistente {data.get('personality', 'professional')} especializado em {data['chat_type']}."
        
        # Se ainda não tem prompt, usar padrão
        if not system_prompt:
            system_prompt = f"Você é um assistente {data.get('personality', 'professional')} especializado em {data['chat_type']}."
        
        # Criar chat
        chat = chat_model.create_chat(
            user_id=user_id,
            chat_name=data['chat_name'],
            chat_type=data['chat_type'],
            system_prompt=system_prompt,
            personality=data.get('personality', 'professional'),
            claude_model=data.get('claude_model', Config.CLAUDE_MODEL),
            max_tokens=data.get('max_tokens', 1500)
        )
        
        if chat:
            # Se havia documentos em chat temporário, transferir
            temp_chat_from_frontend = data.get('temp_chat_id')
            if temp_chat_from_frontend and KNOWLEDGE_BASE_ENABLED:
                try:
                    # Transferir documentos do chat temporário para o chat real
                    transfer_result = transfer_temp_documents(temp_chat_from_frontend, chat['chat_id'], user_id)
                    if transfer_result.get('transferred', 0) > 0:
                        print(f"✅ {transfer_result['transferred']} documentos transferidos")
                except Exception as e:
                    print(f"⚠️ Erro ao transferir documentos: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Chat criado com sucesso',
                'chat': chat,
                'prompt_generated_by_ai': len(data.get('system_prompt', '').strip()) < 50
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

def transfer_temp_documents(temp_chat_id, real_chat_id, user_id):
    """Transferir documentos de chat temporário para chat real"""
    try:
        if not KNOWLEDGE_BASE_ENABLED:
            return {'transferred': 0}
            
        # Buscar documentos do chat temporário
        temp_docs = knowledge_service.get_chat_documents(temp_chat_id)
        
        if not temp_docs:
            return {'transferred': 0}
        
        # Atualizar chat_id dos documentos
        from google.cloud import bigquery
        
        update_query = """
        UPDATE `flower-ai-generator.saas_chat_generator.chat_documents`
        SET chat_id = @real_chat_id, user_id = @user_id
        WHERE chat_id = @temp_chat_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("real_chat_id", "STRING", real_chat_id),
                bigquery.ScalarQueryParameter("temp_chat_id", "STRING", temp_chat_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )
        
        job = knowledge_service.bigquery_client.query(update_query, job_config=job_config)
        job.result()
        
        return {'transferred': len(temp_docs)}
        
    except Exception as e:
        print(f"Erro ao transferir documentos: {e}")
        return {'transferred': 0}

import uuid

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
# ROUTES DE KNOWLEDGE BASE
# ================================

if KNOWLEDGE_BASE_ENABLED:
    @app.route('/manage/<chat_id>')
    def manage_chat_page(chat_id):
        """Página de gerenciamento do chat"""
        return render_template('manage_chat.html', chat_id=chat_id)
        
    @app.route('/api/chats/<chat_id>/documents', methods=['GET'])
    @jwt_required()
    def list_chat_documents(chat_id):
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
                content_type=file.content_type,
                user_id=user_id
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
        'endpoints': {
            'auth': '/api/auth/*',
            'chats': '/api/chats/*',
            'admin': '/api/admin/*'
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
    
    app.run(debug=True, host='0.0.0.0', port=5000)
@app.route('/api/test/chat/<chat_id>', methods=['POST'])
@jwt_required()
def test_chat_with_documents(chat_id):
    """Teste simples de chat com documentos"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'success': False, 'error': 'Mensagem vazia'}), 400
        
        # Buscar contexto dos documentos
        if KNOWLEDGE_BASE_ENABLED:
            context = knowledge_service.get_chat_knowledge_context(
                chat_id=chat_id, 
                query_text=user_message,
                max_docs=3
            )
            
            return jsonify({
                'success': True,
                'message': user_message,
                'context_found': bool(context),
                'context_preview': context[:500] + '...' if len(context) > 500 else context,
                'documents_count': len(context.split('📄')) - 1 if context else 0
            })
        else:
            return jsonify({'success': False, 'error': 'Knowledge Base não habilitado'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================================
# AI PROMPT GENERATOR
# ================================

try:
    from ai_prompt_generator import ai_prompt_generator
    AI_PROMPT_ENABLED = True
    print("✅ AI Prompt Generator habilitado")
except ImportError as e:
    AI_PROMPT_ENABLED = False
    print(f"⚠️ AI Prompt Generator não disponível: {e}")

@app.route('/api/chats/<chat_id>/generate-prompt', methods=['POST'])
@jwt_required()
def generate_ai_prompt(chat_id):
    """Gerar prompt otimizado com IA baseado nos documentos"""
    try:
        if not AI_PROMPT_ENABLED:
            return jsonify({
                'success': False,
                'error': 'AI Prompt Generator não disponível'
            }), 500
            
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        # Configuração do chat
        chat_config = {
            'chat_name': data.get('chat_name', chat.get('chat_name')),
            'chat_type': data.get('chat_type', chat.get('chat_type')),
            'personality': data.get('personality', chat.get('personality')),
            'chat_description': data.get('chat_description', '')
        }
        
        # Analisar documentos
        documents_analysis = ai_prompt_generator.analyze_documents(chat_id)
        
        # Gerar prompt otimizado
        optimized_prompt = ai_prompt_generator.generate_optimized_prompt(
            chat_config=chat_config,
            documents_analysis=documents_analysis
        )
        
        return jsonify({
            'success': True,
            'optimized_prompt': optimized_prompt,
            'analysis': documents_analysis,
            'message': 'Prompt gerado com sucesso!'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/chats/<chat_id>/analyze-documents', methods=['GET'])
@jwt_required()
def analyze_chat_documents(chat_id):
    """Analisar documentos do chat"""
    try:
        if not AI_PROMPT_ENABLED:
            return jsonify({
                'success': False,
                'error': 'AI Prompt Generator não disponível'
            }), 500
            
        user_id = get_jwt_identity()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        # Analisar documentos
        analysis = ai_prompt_generator.analyze_documents(chat_id)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/chats/temp', methods=['POST'])
@jwt_required()
def create_temp_chat():
    """Criar chat temporário para upload de documentos"""
    try:
        user_id = get_jwt_identity()
        
        # Criar chat temporário
        temp_chat_id = str(uuid.uuid4())
        temp_chat = chat_model.create_chat(
            user_id=user_id,
            chat_name=f"temp_{temp_chat_id[:8]}",
            chat_type="temp",
            system_prompt="Chat temporário para upload",
            personality="professional",
            claude_model=Config.CLAUDE_MODEL,
            max_tokens=1500
        )
        
        if temp_chat:
            return jsonify({
                'success': True,
                'temp_chat_id': temp_chat['chat_id'],
                'message': 'Chat temporário criado'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Erro ao criar chat temporário'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/chats/temp/<temp_chat_id>', methods=['DELETE'])
@jwt_required()
def cleanup_temp_chat(temp_chat_id):
    """Limpar chat temporário não usado"""
    try:
        user_id = get_jwt_identity()
        
        # Verificar se é do usuário
        chat = chat_model.get_chat_by_id(temp_chat_id, user_id)
        if not chat or chat.get('chat_type') != 'temp':
            return jsonify({'success': False, 'error': 'Chat temporário não encontrado'}), 404
        
        # Deletar documentos do chat temporário
        if KNOWLEDGE_BASE_ENABLED:
            try:
                temp_docs = knowledge_service.get_chat_documents(temp_chat_id)
                for doc in temp_docs:
                    knowledge_service.delete_document(doc['document_id'], temp_chat_id)
            except Exception as e:
                print(f"Erro ao limpar documentos temporários: {e}")
        
        # Deletar chat temporário do BigQuery
        try:
            from google.cloud import bigquery
            delete_query = """
            UPDATE `flower-ai-generator.saas_chat_generator.chats`
            SET status = 'deleted'
            WHERE chat_id = @chat_id AND user_id = @user_id AND chat_type = 'temp'
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("chat_id", "STRING", temp_chat_id),
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
                ]
            )
            
            job = chat_model.bigquery_client.query(delete_query, job_config=job_config)
            job.result()
            
        except Exception as e:
            print(f"Erro ao deletar chat temporário: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Chat temporário limpo'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

