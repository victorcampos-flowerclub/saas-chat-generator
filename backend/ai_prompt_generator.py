"""
Sistema de Geração de Prompts com IA - VERSÃO SIMPLIFICADA
Baseado na abordagem funcional do chat-engine
"""

import json
import re
from typing import Dict, List, Optional, Any
import requests
from google.cloud import bigquery
import logging

# Cache global da API key
API_KEY_CACHE = None

def get_claude_api_key():
    """Função SIMPLES para pegar API key - baseada no chat-engine"""
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

class AIPromptGenerator:
    def __init__(self, project_id: str = "flower-ai-generator"):
        self.project_id = project_id
        self.bigquery_client = bigquery.Client(project=project_id)
        
    def analyze_documents(self, chat_id: str) -> Dict[str, Any]:
        """Analisa documentos do chat para extrair informações relevantes"""
        try:
            # Query simples como no chat-engine
            query = """
            SELECT filename, processed_content, file_type
            FROM `flower-ai-generator.saas_chat_generator.chat_documents`
            WHERE chat_id = @chat_id
            ORDER BY uploaded_at DESC
            LIMIT 5
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
            )
            
            results = list(self.bigquery_client.query(query, job_config=job_config).result())
            
            if not results:
                return self._default_analysis()
            
            # Combinar conteúdo
            all_content = ""
            document_types = []
            
            for doc in results:
                if doc['processed_content']:
                    # Apenas primeiros 1000 chars
                    content_chunk = doc['processed_content'][:1000]
                    all_content += f"\n{content_chunk}"
                document_types.append(doc.get('file_type', 'unknown'))
            
            if all_content:
                return self._analyze_content_with_ai(all_content, document_types)
            else:
                return self._default_analysis()
                
        except Exception as e:
            logging.error(f"Erro ao analisar documentos: {e}")
            return self._default_analysis()

    def _analyze_content_with_ai(self, content: str, document_types: List[str]) -> Dict[str, Any]:
        """Usa Claude para analisar - VERSÃO SIMPLES"""
        
        api_key = get_claude_api_key()
        if not api_key:
            return self._default_analysis()
        
        try:
            # Prompt muito simples
            analysis_prompt = f"""
            Analise este conteúdo e extraia informações para criar um chatbot:

            CONTEÚDO: {content[:2000]}

            Retorne um JSON com:
            - company_info: nome da empresa/pessoa
            - services: lista de serviços
            - tone: tom recomendado (friendly/professional)
            - key_concepts: conceitos importantes

            Apenas JSON, sem explicações.
            """

            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": analysis_prompt}]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                content_response = result['content'][0]['text']
                
                # Extrair JSON
                json_match = re.search(r'\{.*\}', content_response, re.DOTALL)
                
                if json_match:
                    try:
                        analysis = json.loads(json_match.group())
                        analysis['document_types'] = document_types
                        return analysis
                    except json.JSONDecodeError:
                        return self._default_analysis()
                else:
                    return self._default_analysis()
                    
            else:
                return self._default_analysis()
                
        except Exception as e:
            logging.error(f"Erro na análise com IA: {e}")
            return self._default_analysis()

    def _default_analysis(self) -> Dict[str, Any]:
        """Análise padrão"""
        return {
            'company_info': {'name': 'não identificado', 'industry': 'não identificado'},
            'services': [],
            'tone': 'professional',
            'key_concepts': [],
            'target_audience': 'não identificado',
            'document_types': []
        }

    def generate_optimized_prompt(self, chat_config: Dict, documents_analysis: Dict) -> str:
        """Gera prompt otimizado - VERSÃO SIMPLES"""
        
        api_key = get_claude_api_key()
        if not api_key:
            return self._fallback_prompt(chat_config, documents_analysis)
        
        try:
            company = documents_analysis.get('company_info', {}).get('name', 'não identificado')
            services = documents_analysis.get('services', [])
            tone = documents_analysis.get('tone', 'professional')
            
            generation_prompt = f"""
            Crie um prompt de sistema para um chatbot com estas informações:

            - Nome: {chat_config['chat_name']}
            - Tipo: {chat_config['chat_type']}
            - Personalidade: {chat_config['personality']}
            - Empresa: {company}
            - Serviços: {', '.join(services[:3]) if services else 'vários'}
            - Tom: {tone}

            O prompt deve:
            1. NÃO mencionar arquivos ou documentos
            2. Ser natural e conversacional
            3. Usar tom {chat_config['personality']}
            4. Se for "support", ajudar com agendamento e informações

            Retorne APENAS o prompt, sem explicações.
            """

            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": generation_prompt}]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                prompt = result['content'][0]['text'].strip()
                
                # Limpar se tiver aspas extras
                if prompt.startswith('"') and prompt.endswith('"'):
                    prompt = prompt[1:-1]
                
                return prompt if len(prompt) > 20 else self._fallback_prompt(chat_config, documents_analysis)
            else:
                return self._fallback_prompt(chat_config, documents_analysis)
                
        except Exception as e:
            logging.error(f"Erro na geração de prompt: {e}")
            return self._fallback_prompt(chat_config, documents_analysis)

    def _fallback_prompt(self, chat_config: Dict, documents_analysis: Dict) -> str:
        """Prompt de fallback"""
        company = documents_analysis.get('company_info', {}).get('name', '')
        personality = chat_config.get('personality', 'professional')
        chat_type = chat_config.get('chat_type', 'assistant')
        
        if company and company != 'não identificado':
            return f"Você é um assistente {personality} da {company}. Ajude os usuários com informações e, quando apropriado, direcione para agendamentos ou próximos passos. Seja {personality} e útil."
        else:
            return f"Você é um assistente {personality} especializado em {chat_type}. Responda de forma {personality} e sempre busque ser útil aos usuários."

# Instância global
ai_prompt_generator = AIPromptGenerator()
