#!/usr/bin/env python3
"""
PASSO 2: Criar esquema completo do banco de dados BigQuery para o SaaS
"""

from google.cloud import bigquery
from datetime import datetime
import os

def create_saas_database_schema():
    """Criar todas as tabelas necessárias para o SaaS"""
    
    project_id = 'flower-ai-generator'
    dataset_id = 'saas_chat_generator'
    
    client = bigquery.Client(project=project_id)
    
    print("🗄️ Criando esquema do banco de dados do SaaS...")
    
    # 1. Criar dataset principal
    dataset_ref = f"{project_id}.{dataset_id}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"
    dataset.description = "SaaS Chat Generator - Database Principal"
    
    try:
        dataset = client.create_dataset(dataset, exists_ok=True)
        print(f"✅ Dataset criado: {dataset_id}")
    except Exception as e:
        print(f"❌ Erro ao criar dataset: {e}")
        return False
    
    # 2. Definir schemas das tabelas
    tables_schema = {
        # Usuários do SaaS
        'users': [
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("email", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("password_hash", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("full_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("company_name", "STRING"),
            bigquery.SchemaField("phone", "STRING"),
            bigquery.SchemaField("plan", "STRING", mode="REQUIRED"),  # free, basic, premium, enterprise
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),  # active, inactive, suspended
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("last_login", "TIMESTAMP"),
            bigquery.SchemaField("trial_ends_at", "TIMESTAMP"),
            bigquery.SchemaField("subscription_id", "STRING"),
        ],
        
        # Chats criados pelos usuários
        'chats': [
            bigquery.SchemaField("chat_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chat_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chat_description", "STRING"),
            bigquery.SchemaField("chat_type", "STRING", mode="REQUIRED"),  # assistant, support, sales, custom
            bigquery.SchemaField("personality", "STRING"),  # formal, casual, friendly, professional
            bigquery.SchemaField("system_prompt", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("claude_model", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("max_tokens", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("temperature", "FLOAT"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),  # active, inactive, archived
            bigquery.SchemaField("whatsapp_enabled", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("whatsapp_phone", "STRING"),
            bigquery.SchemaField("whatsapp_token", "STRING"),
            bigquery.SchemaField("public_url", "STRING"),
            bigquery.SchemaField("total_messages", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("last_message_at", "TIMESTAMP"),
        ],
        
        # Mensagens dos chats
        'messages': [
            bigquery.SchemaField("message_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chat_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("conversation_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("role", "STRING", mode="REQUIRED"),  # user, assistant, system
            bigquery.SchemaField("content", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("source", "STRING", mode="REQUIRED"),  # web, whatsapp, api
            bigquery.SchemaField("source_phone", "STRING"),  # para WhatsApp
            bigquery.SchemaField("tokens_used", "INTEGER"),
            bigquery.SchemaField("response_time_ms", "INTEGER"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("metadata", "STRING"),  # JSON com dados extras
        ],
        
        # Documentos dos chats
        'chat_documents': [
            bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chat_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("original_filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("file_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("file_size", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("storage_path", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("processed_content", "STRING"),
            bigquery.SchemaField("content_summary", "STRING"),
            bigquery.SchemaField("processing_status", "STRING", mode="REQUIRED"),  # processing, completed, failed
            bigquery.SchemaField("uploaded_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("processed_at", "TIMESTAMP"),
        ],
        
        # Logs administrativos
        'admin_logs': [
            bigquery.SchemaField("log_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("admin_user", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("action_type", "STRING", mode="REQUIRED"),  # create_user, delete_chat, suspend_user, etc
            bigquery.SchemaField("target_type", "STRING", mode="REQUIRED"),  # user, chat, system
            bigquery.SchemaField("target_id", "STRING"),
            bigquery.SchemaField("description", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("metadata", "STRING"),  # JSON com detalhes
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("ip_address", "STRING"),
        ],
        
        # Métricas de uso
        'usage_metrics': [
            bigquery.SchemaField("metric_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chat_id", "STRING"),
            bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("messages_sent", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("tokens_used", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("api_calls", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("whatsapp_messages", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("documents_processed", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("total_cost", "FLOAT"),
        ],
        
        # Integrações WhatsApp
        'whatsapp_integrations': [
            bigquery.SchemaField("integration_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("chat_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("phone_number", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("access_token", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("webhook_url", "STRING"),
            bigquery.SchemaField("verify_token", "STRING"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),  # active, inactive, error
            bigquery.SchemaField("last_webhook_at", "TIMESTAMP"),
            bigquery.SchemaField("total_messages_received", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("total_messages_sent", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
        ],
        
        # Configurações do sistema
        'system_config': [
            bigquery.SchemaField("config_key", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("config_value", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("updated_by", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
        ]
    }
    
    # 3. Criar todas as tabelas
    for table_name, schema in tables_schema.items():
        table_ref = f"{dataset_ref}.{table_name}"
        table = bigquery.Table(table_ref, schema=schema)
        
        try:
            table = client.create_table(table, exists_ok=True)
            print(f"  ✅ Tabela criada: {table_name}")
        except Exception as e:
            print(f"  ❌ Erro ao criar tabela {table_name}: {e}")
    
    # 4. Inserir configurações iniciais do sistema
    config_data = [
        {
            "config_key": "claude_api_enabled",
            "config_value": "true",
            "description": "Claude API habilitada globalmente",
            "updated_by": "system",
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "config_key": "max_message_length",
            "config_value": "4000",
            "description": "Tamanho máximo de mensagem em caracteres",
            "updated_by": "system",
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "config_key": "whatsapp_enabled",
            "config_value": "true",
            "description": "Integração WhatsApp habilitada",
            "updated_by": "system",
            "updated_at": datetime.utcnow().isoformat()
        },
        {
            "config_key": "free_trial_days",
            "config_value": "7",
            "description": "Dias de trial gratuito",
            "updated_by": "system",
            "updated_at": datetime.utcnow().isoformat()
        }
    ]
    
    try:
        table_ref = f"{dataset_ref}.system_config"
        errors = client.insert_rows_json(table_ref, config_data)
        if not errors:
            print("  ✅ Configurações iniciais inseridas")
        else:
            print(f"  ⚠️ Erros ao inserir configurações: {errors}")
    except Exception as e:
        print(f"  ⚠️ Erro ao inserir configurações: {e}")
    
    print("\n🎉 Esquema do banco de dados criado com sucesso!")
    print("\n📊 Tabelas criadas:")
    for table_name in tables_schema.keys():
        print(f"  - {table_name}")
    
    return True

if __name__ == "__main__":
    create_saas_database_schema()
