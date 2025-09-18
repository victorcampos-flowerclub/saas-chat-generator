"""
Sistema de Knowledge Base - Upload de documentos e integração GitHub
"""

import os
import uuid
import requests
import PyPDF2
import markdown
from io import BytesIO
from flask import Flask, request, jsonify, render_template
from google.cloud import storage
from google.cloud import bigquery
from datetime import datetime, timezone
import base64
import mimetypes

class KnowledgeBaseService:
    def __init__(self, project_id='flower-ai-generator'):
        self.project_id = project_id
        self.bucket_name = f'{project_id}-chat-knowledge'
        self.storage_client = storage.Client(project=project_id)
        self.bigquery_client = bigquery.Client(project=project_id)
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Criar bucket se não existir"""
        try:
            self.storage_client.get_bucket(self.bucket_name)
        except Exception:
            bucket = self.storage_client.bucket(self.bucket_name)
            bucket.storage_class = "STANDARD"
            bucket = self.storage_client.create_bucket(bucket, location="US")
            print(f"Bucket {self.bucket_name} criado")
    
    def upload_document(self, chat_id, file_data, filename, content_type, user_id=None):
        """Upload de documento para o storage"""
        try:
            # Gerar ID único para o documento
            doc_id = str(uuid.uuid4())
            
            # Path no storage
            storage_path = f"chats/{chat_id}/documents/{doc_id}-{filename}"
            
            # Upload para Cloud Storage
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(storage_path)
            blob.upload_from_string(file_data, content_type=content_type)
            
            # Processar conteúdo do documento
            processed_content = self._process_document(file_data, content_type, filename)
            
            # Salvar metadados no BigQuery
            document_data = {
                'document_id': doc_id,
            'user_id': user_id,
                'chat_id': chat_id,
                'filename': filename,
                'original_filename': filename,
                'file_type': content_type,
                'file_size': len(file_data),
                'storage_path': storage_path,
                'processed_content': processed_content,
                'content_summary': self._summarize_content(processed_content),
                'processing_status': 'completed',
                'uploaded_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Inserir no BigQuery
            table_ref = f"{self.project_id}.saas_chat_generator.chat_documents"
            errors = self.bigquery_client.insert_rows_json(table_ref, [document_data])
            
            if not errors:
                return {
                    'success': True,
                    'document_id': doc_id,
            'user_id': user_id,
                    'storage_path': storage_path,
                    'processed_content': processed_content[:500] + '...' if len(processed_content) > 500 else processed_content
                }
            else:
                return {'success': False, 'error': f'Erro no BigQuery: {errors}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _process_document(self, file_data, content_type, filename):
        """Processar conteúdo do documento"""
        try:
            if content_type == 'application/pdf':
                return self._extract_pdf_text(file_data)
            elif content_type.startswith('text/'):
                return file_data.decode('utf-8')
            elif content_type == 'application/json':
                return file_data.decode('utf-8')
            elif 'markdown' in content_type or filename.endswith('.md'):
                return file_data.decode('utf-8')
            else:
                return f"Documento {content_type} - processamento não implementado"
        except Exception as e:
            return f"Erro ao processar documento: {str(e)}"
    
    def _extract_pdf_text(self, pdf_data):
        """Extrair texto de PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_data))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            return f"Erro ao extrair texto do PDF: {str(e)}"
    
    def _summarize_content(self, content):
        """Criar resumo do conteúdo"""
        if len(content) <= 200:
            return content
        
        # Resumo simples (primeiras 200 chars)
        summary = content[:200] + "..."
        
        # Tentar extrair primeira linha que pareça título
        lines = content.split('\n')
        for line in lines:
            if line.strip() and len(line.strip()) < 100:
                if any(char in line for char in ['#', '=', '-', '*']):
                    summary = line.strip() + " - " + summary
                    break
        
        return summary
    
    def fetch_github_content(self, chat_id, github_url):
        """Buscar conteúdo do GitHub"""
        try:
            # Converter URL do GitHub para API
            api_url = self._convert_github_url_to_api(github_url)
            
            response = requests.get(api_url, timeout=30)
            if response.status_code != 200:
                return {'success': False, 'error': f'Erro ao acessar GitHub: {response.status_code}'}
            
            data = response.json()
            
            # Se for arquivo único
            if 'content' in data:
                content = base64.b64decode(data['content']).decode('utf-8')
                filename = data['name']
                
                # Salvar como documento
                return self.upload_document(
                    chat_id=chat_id,
                    file_data=content.encode('utf-8'),
                    filename=f"github_{filename}",
                    content_type='text/plain'
                )
            
            # Se for diretório, buscar arquivos importantes
            elif isinstance(data, list):
                results = []
                important_files = ['README.md', 'README.txt', 'CHANGELOG.md']
                
                for item in data:
                    if any(imp in item['name'] for imp in important_files):
                        if item['type'] == 'file':
                            file_result = self.fetch_github_content(chat_id, item['download_url'])
                            results.append(file_result)
                
                return {'success': True, 'files_processed': len(results), 'results': results}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _convert_github_url_to_api(self, github_url):
        """Converter URL do GitHub para API"""
        if 'github.com' in github_url:
            # https://github.com/user/repo/blob/main/file.py -> API
            url_parts = github_url.replace('https://github.com/', '').split('/')
            
            if len(url_parts) >= 2:
                user, repo = url_parts[0], url_parts[1]
                
                if len(url_parts) > 4:  # Arquivo específico
                    branch = url_parts[3]
                    file_path = '/'.join(url_parts[4:])
                    return f"https://api.github.com/repos/{user}/{repo}/contents/{file_path}?ref={branch}"
                else:  # Repositório raiz
                    return f"https://api.github.com/repos/{user}/{repo}/contents"
        
        return github_url
    
    def get_chat_documents(self, chat_id):
        """Buscar documentos de um chat"""
        query = f"""
        SELECT * FROM `{self.project_id}.saas_chat_generator.chat_documents`
        WHERE chat_id = @chat_id
        ORDER BY uploaded_at DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
        )
        
        query_job = self.bigquery_client.query(query, job_config=job_config)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    def delete_document(self, document_id, chat_id):
        """Deletar documento"""
        try:
            # Buscar documento
            query = f"""
            SELECT storage_path FROM `{self.project_id}.saas_chat_generator.chat_documents`
            WHERE document_id = @document_id AND chat_id = @chat_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("document_id", "STRING", document_id),
                    bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)
                ]
            )
            
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            if not results:
                return {'success': False, 'error': 'Documento não encontrado'}
            
            storage_path = results[0]['storage_path']
            
            # Deletar do Storage
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(storage_path)
            blob.delete()
            
            # Deletar do BigQuery
            delete_query = f"""
            DELETE FROM `{self.project_id}.saas_chat_generator.chat_documents`
            WHERE document_id = @document_id AND chat_id = @chat_id
            """
            
            delete_job = self.bigquery_client.query(delete_query, job_config=job_config)
            delete_job.result()
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_chat_knowledge_context(self, chat_id, query_text="", max_docs=3):
        """Buscar contexto relevante para uma query"""
        documents = self.get_chat_documents(chat_id)
        
        if not documents:
            return ""
        
        # Busca simples por palavras-chave
        relevant_docs = []
        query_words = query_text.lower().split()
        
        for doc in documents:
            content = doc.get('processed_content', '').lower()
            relevance_score = sum(1 for word in query_words if word in content)
            
            if relevance_score > 0 or not query_text:
                relevant_docs.append((doc, relevance_score))
        
        # Ordenar por relevância
        relevant_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Montar contexto
        context = "=== DOCUMENTOS DO CHAT ===\n\n"
        
        for doc, score in relevant_docs[:max_docs]:
            context += f"📄 {doc['filename']}:\n"
            context += f"{doc['processed_content'][:1000]}...\n\n"
        
        return context

# Instância global
knowledge_service = KnowledgeBaseService()
