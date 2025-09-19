"""
Backend principal do SaaS Chat Generator - VERSÃO COM AGENTES ESPECIALIZADOS
Versão 2.1.0 - Sistema completo de agentes médicos e de performance de mídia
"""

import os
import sys
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import timedelta, datetime, timezone
import json
import uuid
import requests
from google.cloud import bigquery

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

# Inicializar cliente BigQuery globalmente
bigquery_client = bigquery.Client(project=Config.PROJECT_ID)

# EXTENSÃO: Sistema de Agentes Especializados
try:
    from agent_templates_system import AGENT_TEMPLATES, agent_config_model, advanced_prompt_generator
    AGENT_SYSTEM_ENABLED = True
    print("✅ Sistema de Agentes Especializados habilitado")
except ImportError as e:
    AGENT_SYSTEM_ENABLED = False
    print(f"⚠️ Sistema de Agentes não disponível: {e}")

# ================================
# INTEGRAÇÃO COM SISTEMAS
# ================================

# Knowledge Base
try:
    from knowledge_base_system import knowledge_service
    KNOWLEDGE_BASE_ENABLED = True
    print("✅ Knowledge Base habilitado")
except ImportError as e:
    KNOWLEDGE_BASE_ENABLED = False
    print(f"⚠️ Knowledge Base não disponível: {e}")

# AI Prompt Generator
try:
    from ai_prompt_generator import ai_prompt_generator
    AI_PROMPT_ENABLED = True
    print("✅ AI Prompt Generator habilitado")
except ImportError as e:
    AI_PROMPT_ENABLED = False
    print(f"⚠️ AI Prompt Generator não disponível: {e}")

# Chat Engine URL
CHAT_ENGINE_URL = "https://saas-chat-engine-365442086139.us-east1.run.app"

# ================================
# FUNÇÕES UTILITÁRIAS
# ================================

def get_current_timestamp():
    """Retorna timestamp atual UTC"""
    return datetime.now(timezone.utc)

def initialize_agent_system():
    """Inicializar sistema de agentes (chamar no startup do app.py)"""
    if not AGENT_SYSTEM_ENABLED:
        print("⚠️ Sistema de agentes não habilitado - pulando inicialização")
        return False
    
    try:
        # Criar tabela de configurações se não existir
        agent_config_model.create_agent_configuration_table()
        print("✅ Sistema de agentes especializados inicializado")
        return True
    except Exception as e:
        print(f"❌ Erro ao inicializar sistema de agentes: {e}")
        return False

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
    """Criar novo chat com suporte a agentes especializados"""
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
        
        chat_type = data.get('chat_type')
        
        # Verificar se é um agente especializado
        if AGENT_SYSTEM_ENABLED and chat_type in AGENT_TEMPLATES:
            # Criar chat básico primeiro
            system_prompt = f"Você é um assistente especializado em {AGENT_TEMPLATES[chat_type]['name']}."
        else:
            # Chat padrão
            system_prompt = data.get('system_prompt', '')
            if not system_prompt:
                personality = data.get('personality', 'professional')
                system_prompt = f"Você é um assistente {personality} especializado em {chat_type}."
        
        # Criar chat
        chat = chat_model.create_chat(
            user_id=user_id,
            chat_name=data['chat_name'],
            chat_type=chat_type,
            system_prompt=system_prompt,
            personality=data.get('personality', 'professional'),
            claude_model=data.get('claude_model', Config.CLAUDE_MODEL),
            max_tokens=data.get('max_tokens', 1500)
        )
        
        if not chat:
            return jsonify({
                'success': False,
                'error': 'Erro ao criar chat'
            }), 500
        
        # Se é agente especializado e tem configuração, processar
        agent_configuration = data.get('agent_configuration')
        if AGENT_SYSTEM_ENABLED and chat_type in AGENT_TEMPLATES and agent_configuration:
            
            try:
                # Salvar configuração do agente
                agent_configuration['user_id'] = user_id
                
                success = agent_config_model.save_agent_configuration(
                    chat_id=chat['chat_id'],
                    user_id=user_id,
                    agent_type=chat_type,
                    configuration=agent_configuration,
                    conversation_types=AGENT_TEMPLATES[chat_type]['conversation_types'],
                    tracking_keywords=AGENT_TEMPLATES[chat_type]['tracking_keywords']
                )
                
                if success:
                    # Gerar prompt especializado
                    specialized_prompt = advanced_prompt_generator.generate_specialized_prompt(
                        chat_id=chat['chat_id'],
                        agent_type=chat_type,
                        configuration=agent_configuration,
                        use_ai=data.get('use_ai_prompt', True)
                    )
                    
                    # Atualizar chat com prompt especializado
                    update_query = f"""
                    UPDATE `{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.chats`
                    SET system_prompt = @system_prompt
                    WHERE chat_id = @chat_id
                    """
                    
                    job_config = bigquery.QueryJobConfig(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("chat_id", "STRING", chat['chat_id']),
                            bigquery.ScalarQueryParameter("system_prompt", "STRING", specialized_prompt)
                        ]
                    )
                    
                    bigquery_client.query(update_query, job_config=job_config)
                    chat['system_prompt'] = specialized_prompt[:200] + '...'
                    
            except Exception as e:
                print(f"Erro ao configurar agente especializado: {e}")
                # Chat foi criado, mas configuração do agente falhou
                # Continuar normalmente
        
        return jsonify({
            'success': True,
            'message': 'Chat criado com sucesso',
            'chat': chat,
            'agent_specialized': AGENT_SYSTEM_ENABLED and chat_type in AGENT_TEMPLATES
        }), 201
        
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
# ROUTES DE AGENTES ESPECIALIZADOS
# ================================

@app.route('/api/agent-templates', methods=['GET'])
@jwt_required()
def get_agent_templates():
    """Listar todos os templates de agentes disponíveis"""
    try:
        if not AGENT_SYSTEM_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Sistema de agentes não habilitado'
            }), 503
        
        return jsonify({
            'success': True,
            'templates': AGENT_TEMPLATES
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/agent-templates/<agent_type>', methods=['GET'])
@jwt_required()
def get_agent_template_details(agent_type):
    """Obter detalhes de um template específico"""
    try:
        if not AGENT_SYSTEM_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Sistema de agentes não habilitado'
            }), 503
        
        if agent_type not in AGENT_TEMPLATES:
            return jsonify({
                'success': False,
                'error': 'Template de agente não encontrado'
            }), 404
        
        template = AGENT_TEMPLATES[agent_type]
        return jsonify({
            'success': True,
            'template': template
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chats/<chat_id>/agent-config', methods=['POST'])
@jwt_required()
def create_agent_configuration(chat_id):
    """Criar configuração de agente especializado"""
    try:
        if not AGENT_SYSTEM_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Sistema de agentes não habilitado'
            }), 503
        
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({
                'success': False,
                'error': 'Chat não encontrado'
            }), 404
        
        agent_type = data.get('agent_type')
        configuration = data.get('configuration', {})
        
        if not agent_type or agent_type not in AGENT_TEMPLATES:
            return jsonify({
                'success': False,
                'error': 'Tipo de agente inválido'
            }), 400
        
        # Validar campos obrigatórios
        template = AGENT_TEMPLATES[agent_type]
        for field in template['fields']:
            if field.get('required') and not configuration.get(field['key']):
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field["label"]}'
                }), 400
        
        # Adicionar user_id à configuração
        configuration['user_id'] = user_id
        
        # Salvar configuração
        success = agent_config_model.save_agent_configuration(
            chat_id=chat_id,
            user_id=user_id,
            agent_type=agent_type,
            configuration=configuration,
            conversation_types=template['conversation_types'],
            tracking_keywords=template['tracking_keywords']
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Erro ao salvar configuração do agente'
            }), 500
        
        # Gerar prompt especializado
        specialized_prompt = advanced_prompt_generator.generate_specialized_prompt(
            chat_id=chat_id,
            agent_type=agent_type,
            configuration=configuration,
            use_ai=data.get('use_ai', True)
        )
        
        # Atualizar system_prompt do chat
        update_query = f"""
        UPDATE `{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.chats`
        SET 
            system_prompt = @system_prompt,
            chat_type = @agent_type,
            updated_at = @updated_at
        WHERE chat_id = @chat_id AND user_id = @user_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("system_prompt", "STRING", specialized_prompt),
                bigquery.ScalarQueryParameter("agent_type", "STRING", agent_type),
                bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", get_current_timestamp())
            ]
        )
        
        bigquery_client.query(update_query, job_config=job_config)
        
        return jsonify({
            'success': True,
            'message': 'Configuração do agente salva com sucesso',
            'agent_type': agent_type,
            'specialized_prompt': specialized_prompt[:200] + '...' if len(specialized_prompt) > 200 else specialized_prompt,
            'configuration': configuration
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chats/<chat_id>/agent-config', methods=['GET'])
@jwt_required()
def get_agent_configuration(chat_id):
    """Obter configuração do agente"""
    try:
        if not AGENT_SYSTEM_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Sistema de agentes não habilitado'
            }), 503
        
        user_id = get_jwt_identity()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({
                'success': False,
                'error': 'Chat não encontrado'
            }), 404
        
        # Buscar configuração do agente
        agent_config = agent_config_model.get_agent_configuration(chat_id)
        
        if not agent_config:
            return jsonify({
                'success': False,
                'error': 'Configuração de agente não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'agent_config': agent_config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chats/<chat_id>/agent-config', methods=['PUT'])
@jwt_required()
def update_agent_configuration(chat_id):
    """Atualizar configuração do agente"""
    try:
        if not AGENT_SYSTEM_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Sistema de agentes não habilitado'
            }), 503
        
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({
                'success': False,
                'error': 'Chat não encontrado'
            }), 404
        
        configuration = data.get('configuration', {})
        regenerate_prompt = data.get('regenerate_prompt', True)
        
        # Buscar configuração existente
        existing_config = agent_config_model.get_agent_configuration(chat_id)
        if not existing_config:
            return jsonify({
                'success': False,
                'error': 'Configuração de agente não encontrada'
            }), 404
        
        agent_type = existing_config['agent_type']
        
        # Validar campos obrigatórios
        template = AGENT_TEMPLATES[agent_type]
        for field in template['fields']:
            if field.get('required') and not configuration.get(field['key']):
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field["label"]}'
                }), 400
        
        # Atualizar configuração
        success = agent_config_model.update_agent_configuration(
            chat_id=chat_id,
            configuration=configuration,
            conversation_types=template['conversation_types'],
            tracking_keywords=template['tracking_keywords']
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Erro ao atualizar configuração do agente'
            }), 500
        
        specialized_prompt = None
        
        # Regenerar prompt se solicitado
        if regenerate_prompt:
            configuration['user_id'] = user_id
            specialized_prompt = advanced_prompt_generator.generate_specialized_prompt(
                chat_id=chat_id,
                agent_type=agent_type,
                configuration=configuration,
                use_ai=data.get('use_ai', True)
            )
            
            # Atualizar system_prompt do chat
            update_query = f"""
            UPDATE `{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.chats`
            SET 
                system_prompt = @system_prompt,
                updated_at = @updated_at
            WHERE chat_id = @chat_id AND user_id = @user_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id),
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                    bigquery.ScalarQueryParameter("system_prompt", "STRING", specialized_prompt),
                    bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", get_current_timestamp())
                ]
            )
            
            bigquery_client.query(update_query, job_config=job_config)
        
        return jsonify({
            'success': True,
            'message': 'Configuração do agente atualizada com sucesso',
            'specialized_prompt': specialized_prompt[:200] + '...' if specialized_prompt and len(specialized_prompt) > 200 else specialized_prompt,
            'configuration': configuration
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chats/<chat_id>/regenerate-agent-prompt', methods=['POST'])
@jwt_required()
def regenerate_agent_prompt(chat_id):
    """Regenerar prompt do agente com base na configuração atual + documentos"""
    try:
        if not AGENT_SYSTEM_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Sistema de agentes não habilitado'
            }), 503
        
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({
                'success': False,
                'error': 'Chat não encontrado'
            }), 404
        
        # Buscar configuração do agente
        agent_config = agent_config_model.get_agent_configuration(chat_id)
        if not agent_config:
            return jsonify({
                'success': False,
                'error': 'Configuração de agente não encontrada'
            }), 404
        
        # Buscar documentos do chat para contexto adicional
        documents_context = ""
        if KNOWLEDGE_BASE_ENABLED:
            try:
                documents = knowledge_service.get_chat_documents(chat_id)
                if documents:
                    documents_context = "\n\nCONTEXTO DOS DOCUMENTOS:\n"
                    for doc in documents[:3]:  # Máximo 3 documentos
                        content = doc.get('processed_content', '')[:500]  # Primeiros 500 chars
                        documents_context += f"📄 {doc['filename']}: {content}\n"
            except Exception as e:
                print(f"Erro ao buscar documentos: {e}")
        
        # Gerar prompt especializado
        configuration = agent_config['configuration']
        configuration['user_id'] = user_id
        
        specialized_prompt = advanced_prompt_generator.generate_specialized_prompt(
            chat_id=chat_id,
            agent_type=agent_config['agent_type'],
            configuration=configuration,
            use_ai=data.get('use_ai', True)
        )
        
        # Adicionar contexto dos documentos se houver
        if documents_context:
            specialized_prompt += documents_context
        
        # Atualizar system_prompt do chat
        update_query = f"""
        UPDATE `{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.chats`
        SET 
            system_prompt = @system_prompt,
            updated_at = @updated_at
        WHERE chat_id = @chat_id AND user_id = @user_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("system_prompt", "STRING", specialized_prompt),
                bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", get_current_timestamp())
            ]
        )
        
        bigquery_client.query(update_query, job_config=job_config)
        
        return jsonify({
            'success': True,
            'message': 'Prompt do agente regenerado com sucesso',
            'specialized_prompt': specialized_prompt,
            'agent_type': agent_config['agent_type'],
            'used_documents': len(documents) if KNOWLEDGE_BASE_ENABLED and 'documents' in locals() else 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chats/<chat_id>/conversation-analytics', methods=['GET'])
@jwt_required()
def get_conversation_analytics(chat_id):
    """Obter analytics das conversas (preparação para futuro dashboard)"""
    try:
        if not AGENT_SYSTEM_ENABLED:
            return jsonify({
                'success': False,
                'error': 'Sistema de agentes não habilitado'
            }), 503
        
        user_id = get_jwt_identity()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({
                'success': False,
                'error': 'Chat não encontrado'
            }), 404
        
        # Buscar configuração do agente para palavras-chave
        agent_config = agent_config_model.get_agent_configuration(chat_id)
        tracking_keywords = []
        conversation_types = []
        
        if agent_config:
            tracking_keywords = agent_config.get('tracking_keywords', [])
            conversation_types = agent_config.get('conversation_types', [])
        
        # Buscar mensagens do chat (últimas 100)
        messages_query = f"""
        SELECT content, timestamp, role
        FROM `{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.messages`
        WHERE chat_id = @chat_id
        ORDER BY timestamp DESC
        LIMIT 100
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
        )
        
        query_job = bigquery_client.query(messages_query, job_config=job_config)
        messages = list(query_job.result())
        
        # Análise simples
        total_messages = len(messages)
        user_messages = [msg for msg in messages if msg['role'] == 'user']
        
        # Contar palavras-chave
        keyword_counts = {}
        for keyword in tracking_keywords:
            count = 0
            for msg in user_messages:
                if keyword.lower() in msg['content'].lower():
                    count += 1
            keyword_counts[keyword] = count
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_messages': total_messages,
                'user_messages': len(user_messages),
                'keyword_tracking': keyword_counts,
                'available_conversation_types': conversation_types,
                'last_activity': messages[0]['timestamp'].isoformat() if messages else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ================================
# AI PROMPT GENERATOR - INTEGRAÇÃO SIMPLES
# ================================

@app.route('/api/chats/<chat_id>/generate-prompt', methods=['POST'])
@jwt_required()
def generate_ai_prompt(chat_id):
    """Gerar prompt otimizado com IA - PROXY para chat-engine"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verificar se o chat pertence ao usuário
        chat = chat_model.get_chat_by_id(chat_id, user_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat não encontrado'}), 404
        
        # Fazer proxy para chat-engine
        chat_engine_url = f"{CHAT_ENGINE_URL}/api/generate-master-prompt/{chat_id}"
        
        # Preparar dados para chat-engine
        payload = {
            'chat_name': data.get('chat_name', chat.get('chat_name')),
            'chat_type': data.get('chat_type', chat.get('chat_type')),
            'personality': data.get('personality', chat.get('personality', 'professional')),
            'business_context': data.get('business_context', '')
        }
        
        # Chamar chat-engine
        try:
            response = requests.post(
                chat_engine_url,
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Atualizar system_prompt do chat se solicitado
                if data.get('update_chat', False) and result.get('success'):
                    new_prompt = result.get('master_prompt')
                    if new_prompt:
                        # Atualizar via BigQuery diretamente
                        update_query = f"""
                        UPDATE `{Config.PROJECT_ID}.{Config.BIGQUERY_DATASET}.chats`
                        SET system_prompt = @system_prompt, updated_at = @updated_at
                        WHERE chat_id = @chat_id AND user_id = @user_id
                        """
                        
                        job_config = bigquery.QueryJobConfig(
                            query_parameters=[
                                bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id),
                                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                                bigquery.ScalarQueryParameter("system_prompt", "STRING", new_prompt),
                                bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", get_current_timestamp())
                            ]
                        )
                        
                        bigquery_client.query(update_query, job_config=job_config)
                
                return jsonify(result), 200
            else:
                return jsonify({
                    'success': False,
                    'error': f'Erro no chat-engine: {response.status_code}',
                    'fallback_prompt': f"Você é um assistente {payload['personality']} especializado em {payload['chat_type']}."
                }), 500
                
        except requests.RequestException as e:
            return jsonify({
                'success': False,
                'error': f'Erro de conexão com chat-engine: {str(e)}',
                'fallback_prompt': f"Você é um assistente {payload['personality']} especializado em {payload['chat_type']}."
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

# ================================
# ROUTES DE KNOWLEDGE BASE
# ================================

if KNOWLEDGE_BASE_ENABLED:
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

# ================================
# ROUTES DO SISTEMA
# ================================

@app.route('/')
def index():
    """Página inicial"""
    return jsonify({
        'system': 'SaaS Chat Generator',
        'version': '2.1.0',
        'status': 'operational',
        'ai_prompt_enabled': AI_PROMPT_ENABLED,
        'knowledge_base_enabled': KNOWLEDGE_BASE_ENABLED,
        'agent_system_enabled': AGENT_SYSTEM_ENABLED,
        'chat_engine_url': CHAT_ENGINE_URL,
        'endpoints': {
            'auth': '/api/auth/*',
            'chats': '/api/chats/*',
            'ai_prompts': '/api/chats/{chat_id}/generate-prompt',
            'agent_templates': '/api/agent-templates',
            'agent_configs': '/api/chats/{chat_id}/agent-config'
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
            'ai_prompt': AI_PROMPT_ENABLED,
            'agent_system': AGENT_SYSTEM_ENABLED,
            'chat_engine': CHAT_ENGINE_URL,
            'timestamp': get_current_timestamp().isoformat()
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

# ================================
# INICIALIZAÇÃO DO APLICATIVO
# ================================

if __name__ == '__main__':
    print("🚀 Iniciando SaaS Chat Generator Backend...")
    print(f"📊 Projeto: {Config.PROJECT_ID}")
    print(f"🗄️ Dataset: {Config.BIGQUERY_DATASET}")
    print(f"🤖 Modelo Claude: {Config.CLAUDE_MODEL}")
    print(f"🔗 Chat Engine: {CHAT_ENGINE_URL}")
    
    # INICIALIZAR SISTEMA DE AGENTES (só se estiver habilitado)
    initialize_agent_system()
    
    app.run(debug=True, host='0.0.0.0', port=5000)