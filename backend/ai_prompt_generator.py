"""
Sistema de Geração de Prompts com IA
Analisa configuração do chat + documentos para criar prompts otimizados
"""

import json
import re
from typing import Dict, List, Optional, Any
import requests
from google.cloud import secretmanager
from google.cloud import bigquery
import logging

class AIPromptGenerator:
    def __init__(self, project_id: str = "flower-ai-generator"):
        self.project_id = project_id
        self.bigquery_client = bigquery.Client(project=project_id)
        
    def _get_claude_api_key(self) -> str:
        """Recupera a chave da API Claude do Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.project_id}/secrets/claude-api-key/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logging.error(f"Erro ao recuperar Claude API key: {e}")
            raise

    def analyze_documents(self, chat_id: str) -> Dict[str, Any]:
        """Analisa documentos do chat para extrair informações relevantes"""
        try:
            # Buscar documentos do chat
            query = """
            SELECT filename, processed_content, file_type
            FROM `flower-ai-generator.saas_chat_generator.chat_documents`
            WHERE chat_id = @chat_id
            ORDER BY uploaded_at DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
            )
            
            results = list(self.bigquery_client.query(query, job_config=job_config).result())
            
            if not results:
                return self._default_analysis()
            
            # Combinar todo o conteúdo
            all_content = ""
            document_types = []
            
            for doc in results:
                if doc['processed_content']:
                    all_content += f"\n{doc['processed_content'][:2000]}"  # Limitar para evitar tokens excessivos
                document_types.append(doc.get('file_type', 'unknown'))
            
            if all_content:
                return self._analyze_content_with_ai(all_content, document_types)
            else:
                return self._default_analysis()
                
        except Exception as e:
            logging.error(f"Erro ao analisar documentos: {e}")
            return self._default_analysis()

    def _analyze_content_with_ai(self, content: str, document_types: List[str]) -> Dict[str, Any]:
        """Usa Claude para analisar o conteúdo dos documentos"""
        api_key = self._get_claude_api_key()
        
        analysis_prompt = f"""
        Analise o seguinte conteúdo de documentos e extraia informações para criar um chatbot personalizado.

        CONTEÚDO DOS DOCUMENTOS:
        {content[:6000]}

        Retorne um JSON com esta estrutura exata:
        {{
            "company_info": {{
                "name": "nome da empresa ou produto identificado",
                "industry": "setor/indústria identificado",
                "description": "breve descrição do negócio em 1 frase"
            }},
            "services": ["lista de produtos/serviços mencionados"],
            "tone": "professional/friendly/formal/casual baseado no conteúdo",
            "expertise_areas": ["áreas de conhecimento identificadas"],
            "key_concepts": ["conceitos importantes para o chatbot saber"],
            "content_summary": "resumo em 2 frases do que o chatbot precisa saber",
            "target_audience": "quem parece ser o público-alvo",
            "main_topics": ["tópicos principais que o chat deve dominar"]
        }}

        Seja específico e útil. Se algo não estiver claro, use "não identificado".
        """

        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": analysis_prompt}]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content_response = result['content'][0]['text']
                
                # Extrair JSON da resposta
                json_match = re.search(r'\{.*\}', content_response, re.DOTALL)
                
                if json_match:
                    analysis = json.loads(json_match.group())
                    analysis['document_types'] = document_types
                    return analysis
                else:
                    return self._default_analysis()
                    
            else:
                return self._default_analysis()
                
        except Exception as e:
            logging.error(f"Erro na análise com IA: {e}")
            return self._default_analysis()

    def _default_analysis(self) -> Dict[str, Any]:
        """Retorna análise padrão em caso de erro"""
        return {
            'company_info': {'name': 'não identificado', 'industry': 'não identificado', 'description': 'não identificado'},
            'services': [],
            'tone': 'professional',
            'expertise_areas': [],
            'key_concepts': [],
            'content_summary': 'Documentos carregados para consulta',
            'target_audience': 'não identificado',
            'main_topics': [],
            'document_types': []
        }

    def generate_optimized_prompt(self, 
                                 chat_config: Dict,
                                 documents_analysis: Dict) -> str:
        """Gera prompt otimizado baseado na configuração e análise dos documentos"""
        
        # Criar contexto para o gerador de prompt
        context = {
            "chat_name": chat_config.get('chat_name', 'Assistente'),
            "chat_type": chat_config.get('chat_type', 'assistant'),
            "personality": chat_config.get('personality', 'professional'),
            "description": chat_config.get('chat_description', ''),
            "company": documents_analysis.get('company_info', {}).get('name', 'não identificado'),
            "industry": documents_analysis.get('company_info', {}).get('industry', 'não identificado'),
            "services": documents_analysis.get('services', []),
            "expertise": documents_analysis.get('expertise_areas', []),
            "tone": documents_analysis.get('tone', 'professional'),
            "audience": documents_analysis.get('target_audience', 'não identificado'),
            "summary": documents_analysis.get('content_summary', ''),
            "topics": documents_analysis.get('main_topics', [])
        }
        
        return self._generate_prompt_with_ai(context)

    def _generate_prompt_with_ai(self, context: Dict) -> str:
        """Usa Claude para gerar o prompt otimizado"""
        api_key = self._get_claude_api_key()
        
        generation_prompt = f"""
        Crie um prompt de sistema PERFEITO para um chatbot com estas informações:

        CONFIGURAÇÃO DO CHAT:
        - Nome: {context['chat_name']}
        - Tipo: {context['chat_type']}
        - Personalidade: {context['personality']}
        - Descrição: {context['description']}

        ANÁLISE DOS DOCUMENTOS:
        - Empresa/Produto: {context['company']}
        - Setor: {context['industry']}
        - Serviços: {', '.join(context['services']) if context['services'] else 'não identificado'}
        - Expertise: {', '.join(context['expertise']) if context['expertise'] else 'não identificado'}
        - Público-alvo: {context['audience']}
        - Resumo: {context['summary']}
        - Tópicos principais: {', '.join(context['topics']) if context['topics'] else 'não identificado'}

        CRIE UM PROMPT PROFISSIONAL QUE:
        1. NÃO mencione nomes de arquivos ou PDFs
        2. Seja natural e conversacional
        3. Use as informações dos documentos como conhecimento interno
        4. Tenha a personalidade {context['personality']}
        5. Foque no tipo {context['chat_type']}
        6. Seja específico e útil

        Retorne APENAS o prompt do sistema, sem explicações adicionais.
        """

        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 800,
                "messages": [{"role": "user", "content": generation_prompt}]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text'].strip()
            else:
                return self._fallback_prompt(context)
                
        except Exception as e:
            logging.error(f"Erro na geração de prompt: {e}")
            return self._fallback_prompt(context)

    def _fallback_prompt(self, context: Dict) -> str:
        """Prompt de fallback caso a IA falhe"""
        company = context['company'] if context['company'] != 'não identificado' else ''
        services = ', '.join(context['services'][:3]) if context['services'] else ''
        
        base_prompt = f"Você é um assistente {context['personality']} especializado em {context['chat_type']}."
        
        if company:
            base_prompt += f" Você tem conhecimento sobre {company}"
            
        if services:
            base_prompt += f" e seus serviços: {services}."
        else:
            base_prompt += "."
            
        base_prompt += f" Responda sempre de forma {context['personality']} e útil, usando seu conhecimento para ajudar os usuários."
        
        return base_prompt

# Instância global
ai_prompt_generator = AIPromptGenerator()
