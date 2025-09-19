#!/usr/bin/env python3
"""
Script de Migração - Sistema de Agentes Especializados
Cria novas tabelas e estruturas necessárias
"""

from google.cloud import bigquery
import sys
import json
from datetime import datetime

def create_agent_configurations_table():
    """Criar tabela agent_configurations"""
    
    client = bigquery.Client(project="flower-ai-generator")
    
    table_id = "flower-ai-generator.saas_chat_generator.agent_configurations"
    
    schema = [
        bigquery.SchemaField("config_id", "STRING", mode="REQUIRED", description="ID único da configuração"),
        bigquery.SchemaField("chat_id", "STRING", mode="REQUIRED", description="ID do chat associado"),
        bigquery.SchemaField("user_id", "STRING", mode="REQUIRED", description="ID do usuário proprietário"),
        bigquery.SchemaField("agent_type", "STRING", mode="REQUIRED", description="Tipo do agente especializado"),
        bigquery.SchemaField("configuration", "STRING", mode="REQUIRED", description="Configurações do agente em JSON"),
        bigquery.SchemaField("conversation_types", "STRING", mode="NULLABLE", description="Tipos de conversa esperados em JSON"),
        bigquery.SchemaField("tracking_keywords", "STRING", mode="NULLABLE", description="Palavras-chave para tracking em JSON"),
        bigquery.SchemaField("prompt_variables", "STRING", mode="NULLABLE", description="Variáveis extraídas para o prompt em JSON"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED", description="Status da configuração (active, inactive)"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED", description="Data de criação"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED", description="Data da última atualização"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    
    try:
        table = client.create_table(table)
        print(f"✅ Tabela agent_configurations criada: {table.table_id}")
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            print("⚠️  Tabela agent_configurations já existe")
            return True
        else:
            print(f"❌ Erro ao criar tabela agent_configurations: {e}")
            return False

def create_conversation_analytics_table():
    """Criar tabela para analytics de conversas (preparação futura)"""
    
    client = bigquery.Client(project="flower-ai-generator")
    
    table_id = "flower-ai-generator.saas_chat_generator.conversation_analytics"
    
    schema = [
        bigquery.SchemaField("analytics_id", "STRING", mode="REQUIRED", description="ID único do registro de analytics"),
        bigquery.SchemaField("chat_id", "STRING", mode="REQUIRED", description="ID do chat"),
        bigquery.SchemaField("conversation_id", "STRING", mode="REQUIRED", description="ID da conversa específica"),
        bigquery.SchemaField("user_id", "STRING", mode="REQUIRED", description="ID do usuário"),
        bigquery.SchemaField("conversation_type", "STRING", mode="NULLABLE", description="Tipo classificado da conversa"),
        bigquery.SchemaField("keywords_detected", "STRING", mode="NULLABLE", description="Palavras-chave detectadas em JSON"),
        bigquery.SchemaField("sentiment_score", "FLOAT", mode="NULLABLE", description="Pontuação de sentimento (futuro)"),
        bigquery.SchemaField("resolution_status", "STRING", mode="NULLABLE", description="Status de resolução da conversa"),
        bigquery.SchemaField("total_messages", "INTEGER", mode="REQUIRED", description="Total de mensagens na conversa"),
        bigquery.SchemaField("duration_minutes", "INTEGER", mode="NULLABLE", description="Duração da conversa em minutos"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED", description="Data da análise"),
    ]
    
    table = bigquery.Table(table_id, schema=schema)
    
    try:
        table = client.create_table(table)
        print(f"✅ Tabela conversation_analytics criada: {table.table_id}")
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            print("⚠️  Tabela conversation_analytics já existe")
            return True
        else:
            print(f"❌ Erro ao criar tabela conversation_analytics: {e}")
            return False

def add_agent_type_to_chats_table():
    """Verificar se a coluna agent_type existe na tabela chats"""
    
    client = bigquery.Client(project="flower-ai-generator")
    
    try:
        # Verificar schema atual da tabela chats
        table_ref = client.get_table("flower-ai-generator.saas_chat_generator.chats")
        
        # Verificar se já tem a coluna agent_type (via chat_type)
        existing_fields = [field.name for field in table_ref.schema]
        
        if 'chat_type' in existing_fields:
            print("✅ Coluna chat_type já existe na tabela chats (pode ser usada como agent_type)")
            return True
        else:
            print("⚠️  Coluna chat_type não encontrada, mas sistema funcionará normalmente")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao verificar tabela chats: {e}")
        return False

def test_system_integration():
    """Testar integração básica do sistema"""
    
    client = bigquery.Client(project="flower-ai-generator")
    
    try:
        # Teste 1: Verificar se tabelas existem
        tables_to_check = [
            "flower-ai-generator.saas_chat_generator.users",
            "flower-ai-generator.saas_chat_generator.chats", 
            "flower-ai-generator.saas_chat_generator.messages",
            "flower-ai-generator.saas_chat_generator.chat_documents",
            "flower-ai-generator.saas_chat_generator.agent_configurations"
        ]
        
        for table_id in tables_to_check:
            try:
                client.get_table(table_id)
                print(f"✅ Tabela verificada: {table_id.split('.')[-1]}")
            except Exception as e:
                print(f"❌ Tabela não encontrada: {table_id.split('.')[-1]} - {e}")
                return False
        
        # Teste 2: Query simples na nova tabela
        query = """
        SELECT COUNT(*) as total
        FROM `flower-ai-generator.saas_chat_generator.agent_configurations`
        """
        
        query_job = client.query(query)
        results = list(query_job.result())
        
        print(f"✅ Teste de query na agent_configurations: {results[0]['total']} registros")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de integração: {e}")
        return False

def insert_sample_agent_templates():
    """Inserir dados de exemplo (opcional)"""
    
    # Este método é opcional - os templates são definidos em código
    # Pode ser usado para criar registros de teste
    
    print("📝 Templates de agentes são definidos em código (agent_templates_system.py)")
    print("   • medical_secretary: Secretariado Médico")
    print("   • media_performance_analyst: Analista de Performance de Mídia")
    
    return True

def main():
    """Executar migração completa"""
    print("🚀 Iniciando migração do Sistema de Agentes Especializados")
    print("=" * 60)
    
    steps = [
        ("Criar tabela agent_configurations", create_agent_configurations_table),
        ("Criar tabela conversation_analytics", create_conversation_analytics_table),
        ("Verificar coluna agent_type em chats", add_agent_type_to_chats_table),
        ("Testar integração do sistema", test_system_integration),
        ("Configurar templates de agentes", insert_sample_agent_templates)
    ]
    
    success_count = 0
    
    for step_name, step_function in steps:
        print(f"\n📋 {step_name}...")
        try:
            if step_function():
                success_count += 1
            else:
                print(f"⚠️  Falha em: {step_name}")
        except Exception as e:
            print(f"❌ Erro em {step_name}: {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ Migração concluída: {success_count}/{len(steps)} passos bem-sucedidos")
    
    if success_count == len(steps):
        print("\n🎉 MIGRAÇÃO 100% COMPLETA!")
        print("\nPróximos passos:")
        print("1. Deploy do backend atualizado:")
        print("   cd ~/saas-chat-generator/backend")
        print("   gcloud run deploy saas-chat-backend --source=.")
        print("\n2. Testar endpoints de agentes:")
        print("   GET /api/agent-templates")
        print("   POST /api/chats (com agent_configuration)")
        print("\n3. Configurar primeiro agente especializado no frontend")
        
        return True
    else:
        print(f"\n⚠️  Migração parcial: {len(steps) - success_count} falhas")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
