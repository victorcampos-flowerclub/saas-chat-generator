"""
Modelos de banco de dados para o SaaS
"""

from google.cloud import bigquery
from datetime import datetime, timezone
import uuid
import json
import bcrypt
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, project_id: str = 'flower-ai-generator'):
        self.project_id = project_id
        self.dataset_id = 'saas_chat_generator'
        self.client = bigquery.Client(project=project_id)
    
    def _get_table_ref(self, table_name: str) -> str:
        return f"{self.project_id}.{self.dataset_id}.{table_name}"
    
    def _execute_query(self, query: str, parameters: List = None) -> List[Dict]:
        """Executa query e retorna resultados como lista de dicts"""
        job_config = bigquery.QueryJobConfig()
        if parameters:
            job_config.query_parameters = parameters
        
        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    def _insert_rows(self, table_name: str, rows: List[Dict]) -> bool:
        """Insere linhas na tabela"""
        table_ref = self._get_table_ref(table_name)
        errors = self.client.insert_rows_json(table_ref, rows)
        return len(errors) == 0

class UserModel(Database):
    def create_user(self, email: str, password: str, full_name: str, 
                   company_name: str = None, phone: str = None, 
                   plan: str = 'free') -> Dict[str, Any]:
        """Criar novo usuário"""
        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        now = datetime.now(timezone.utc)
        
        # Calcular data de fim do trial (7 dias)
        trial_days = 7
        trial_ends_at = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
        trial_ends_at = trial_ends_at.replace(day=trial_ends_at.day + trial_days)
        
        user_data = {
            'user_id': user_id,
            'email': email,
            'password_hash': password_hash,
            'full_name': full_name,
            'company_name': company_name,
            'phone': phone,
            'plan': plan,
            'status': 'active',
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'trial_ends_at': trial_ends_at.isoformat()
        }
        
        if self._insert_rows('users', [user_data]):
            user_data.pop('password_hash')  # Não retornar hash da senha
            return user_data
        return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Buscar usuário por email"""
        query = f"""
        SELECT * FROM `{self._get_table_ref('users')}`
        WHERE email = @email
        """
        
        parameters = [bigquery.ScalarQueryParameter("email", "STRING", email)]
        results = self._execute_query(query, parameters)
        
        return results[0] if results else None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Buscar usuário por ID"""
        query = f"""
        SELECT * FROM `{self._get_table_ref('users')}`
        WHERE user_id = @user_id
        """
        
        parameters = [bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        results = self._execute_query(query, parameters)
        
        if results:
            user = results[0]
            user.pop('password_hash', None)  # Remover hash da senha
            return user
        return None
    
    def verify_password(self, email: str, password: str) -> bool:
        """Verificar senha do usuário"""
        user = self.get_user_by_email(email)
        if not user or 'password_hash' not in user:
            return False
        
        return bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8'))
    
    def update_last_login(self, user_id: str):
        """Atualizar último login"""
        query = f"""
        UPDATE `{self._get_table_ref('users')}`
        SET last_login = CURRENT_TIMESTAMP()
        WHERE user_id = @user_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        )
        
        self.client.query(query, job_config=job_config)

class ChatModel(Database):
    def create_chat(self, user_id: str, chat_name: str, chat_type: str,
                   system_prompt: str, personality: str = 'professional',
                   claude_model: str = 'claude-sonnet-4-20250514',
                   max_tokens: int = 1500) -> Dict[str, Any]:
        """Criar novo chat"""
        chat_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        chat_data = {
            'chat_id': chat_id,
            'user_id': user_id,
            'chat_name': chat_name,
            'chat_type': chat_type,
            'personality': personality,
            'system_prompt': system_prompt,
            'claude_model': claude_model,
            'max_tokens': max_tokens,
            'temperature': 0.7,
            'status': 'active',
            'whatsapp_enabled': False,
            'total_messages': 0,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
        
        if self._insert_rows('chats', [chat_data]):
            return chat_data
        return None
    
    def get_user_chats(self, user_id: str) -> List[Dict]:
        """Buscar chats do usuário"""
        query = f"""
        SELECT * FROM `{self._get_table_ref('chats')}`
        WHERE user_id = @user_id AND status != 'deleted'
        ORDER BY created_at DESC
        """
        
        parameters = [bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        return self._execute_query(query, parameters)
    
    def get_chat_by_id(self, chat_id: str, user_id: str = None) -> Optional[Dict]:
        """Buscar chat por ID"""
        query = f"""
        SELECT * FROM `{self._get_table_ref('chats')}`
        WHERE chat_id = @chat_id
        """
        
        parameters = [bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)]
        
        if user_id:
            query += " AND user_id = @user_id"
            parameters.append(bigquery.ScalarQueryParameter("user_id", "STRING", user_id))
        
        results = self._execute_query(query, parameters)
        return results[0] if results else None

class MessageModel(Database):
    def save_message(self, chat_id: str, conversation_id: str, role: str,
                    content: str, source: str = 'web', tokens_used: int = 0,
                    response_time_ms: int = 0, source_phone: str = None) -> bool:
        """Salvar mensagem"""
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        message_data = {
            'message_id': message_id,
            'chat_id': chat_id,
            'conversation_id': conversation_id,
            'role': role,
            'content': content,
            'source': source,
            'source_phone': source_phone,
            'tokens_used': tokens_used,
            'response_time_ms': response_time_ms,
            'timestamp': now.isoformat()
        }
        
        return self._insert_rows('messages', [message_data])
    
    def get_conversation_history(self, chat_id: str, conversation_id: str, 
                               limit: int = 50) -> List[Dict]:
        """Buscar histórico da conversa"""
        query = f"""
        SELECT role, content, timestamp
        FROM `{self._get_table_ref('messages')}`
        WHERE chat_id = @chat_id AND conversation_id = @conversation_id
        ORDER BY timestamp DESC
        LIMIT {limit}
        """
        
        parameters = [
            bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id),
            bigquery.ScalarQueryParameter("conversation_id", "STRING", conversation_id)
        ]
        
        results = self._execute_query(query, parameters)
        return list(reversed(results))  # Reverter para ordem cronológica

# Instâncias globais
user_model = UserModel()
chat_model = ChatModel()
message_model = MessageModel()
