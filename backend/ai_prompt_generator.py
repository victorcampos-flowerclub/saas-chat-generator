"""
Sistema de Geração de Prompts com IA - VERSÃO SEM DEADLOCK
Carrega a API key ANTES do gunicorn worker inicializar
"""

import json
import re
import os
from typing import Dict, List, Optional, Any
import requests
from google.cloud import bigquery
import logging

# CARREGAR API KEY GLOBALMENTE NA INICIALIZAÇÃO (antes do gunicorn)
CLAUDE_API_KEY = None

def initialize_api_key():
    """Inicializar API key ANTES do gunicorn worker"""
    global CLAUDE_API_KEY
    
    if CLAUDE_API_KEY:
        return CLAUDE_API_KEY
    
    try:
        # Tentar Secret Manager UMA VEZ na inicialização
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = "projects/flower-ai-generator/secrets/claude-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8").strip()
        
        if api_key and api_key.startswith('sk-ant-api03-'):
            CLAUDE_API_KEY = api_key
            print(f"✅ Claude API key carregada: {api_key[:20]}...")
            return api_key
        else:
            raise ValueError("API key inválida")
            
    except Exception as e:
        print(f"❌ Erro ao carregar Claude API key: {e}")
        # Fallback: tentar variável de ambiente
        env_key = os.getenv('CLAUDE_API_KEY')
        if env_key:
            CLAUDE_API_KEY = env_key
            return env_key
        return None

class AIPromptGenerator:
    def __init__(self, project_id: str = "flower-ai-generator"):
        self.project_id = project_id
        self.bigquery_client = bigquery.Client(project=project_id)
        
        # Garantir que API key está carregada
        if not CLAUDE_API_KEY:
            initialize_api_key()
        
    def analyze_documents(self, chat_id: str) -> Dict[str, Any]:
        """Analisa documentos do chat - SEM chamadas ao Secret Manager"""
        try:
            query = """
            SELECT filename, processed_content, file_type
            FROM `flower-ai-generator.saas_chat_generator.chat_documents`
            WHERE chat_id = @chat_id
            ORDER BY uploaded_at DESC
            LIMIT 3
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
            )
            
            results = list(self.bigquery_client.query(query, job_config=job_config).result())
            
            if not results:
                return self._default_analysis()
            
            # Combinar conteúdo (limitado)
            all_content = ""
            for doc in results[:2]:  # Máximo 2 documentos
                if doc['processed_content']:
                    content_chunk = doc['processed_content'][:800]  # 800 chars max
                    all_content += f"\n{content_chunk}"
            
            if all_content and CLAUDE_API_KEY:
                return self._analyze_content_with_ai(all_content)
            else:
                return self._default_analysis()
                
        except Exception as e:
            logging.error(f"Erro ao analisar documentos: {e}")
            return self._default_analysis()

    def _analyze_content_with_ai(self, content: str) -> Dict[str, Any]:
        """Análise com Claude - SEM acesso ao Secret Manager"""
        
        if not CLAUDE_API_KEY:
            return self._default_analysis()
        
        try:
            # Prompt SUPER conciso para evitar timeout
            analysis_prompt = f"""
            Analise este conteúdo em JSON:
            {content[:1500]}
            
            JSON:
            {{"company_info": {{"name": "Nome da empresa"}}, "services": ["serviço1"], "tone": "friendly"}}
            """

            headers = {
                "Content-Type": "application/json",
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 200,  # MUITO pequeno
                "messages": [{"role": "user", "content": analysis_prompt}]
            }
            
            # Timeout agressivo
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content_response = result['content'][0]['text']
                
                # Extrair JSON básico
                json_match = re.search(r'\{[^}]*\}', content_response)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except:
                        pass
                        
            return self._default_analysis()
                
        except Exception as e:
            logging.error(f"Erro na análise: {e}")
            return self._default_analysis()

    def generate_optimized_prompt(self, chat_config: Dict, documents_analysis: Dict) -> str:
        """Gera prompt - SEM Secret Manager"""
        
        if not CLAUDE_API_KEY:
            return self._fallback_prompt(chat_config, documents_analysis)
        
        try:
            company = documents_analysis.get('company_info', {}).get('name', 'não identificado')
            services = documents_analysis.get('services', [])
            
            # Prompt MUITO simples
            generation_prompt = f"""
            Crie um prompt de sistema para:
            - Nome: {chat_config['chat_name']}
            - Tipo: {chat_config['chat_type']} 
            - Personalidade: {chat_config['personality']}
            - Empresa: {company}
            
            Prompt deve ser natural, não mencionar arquivos, e ser {chat_config['personality']}.
            """

            headers = {
                "Content-Type": "application/json",
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": generation_prompt}]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                prompt = result['content'][0]['text'].strip()
                return prompt if len(prompt) > 20 else self._fallback_prompt(chat_config, documents_analysis)
            else:
                return self._fallback_prompt(chat_config, documents_analysis)
                
        except Exception as e:
            logging.error(f"Erro na geração: {e}")
            return self._fallback_prompt(chat_config, documents_analysis)

    def _default_analysis(self) -> Dict[str, Any]:
        return {
            'company_info': {'name': 'não identificado'},
            'services': [],
            'tone': 'professional'
        }

    def _fallback_prompt(self, chat_config: Dict, documents_analysis: Dict) -> str:
        company = documents_analysis.get('company_info', {}).get('name', '')
        personality = chat_config.get('personality', 'professional')
        
        if company and company != 'não identificado':
            return f"Você é um assistente {personality} da {company}. Responda de forma {personality} e útil, direcionando para agendamentos quando apropriado."
        else:
            return f"Você é um assistente {personality}. Seja {personality} e sempre tente ajudar os usuários."

# Inicializar API key IMEDIATAMENTE
initialize_api_key()

# Instância global
ai_prompt_generator = AIPromptGenerator()
