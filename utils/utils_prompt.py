from google.cloud import bigquery

def aplicar_prompt_seguro(chat_id, prompt_text, project_id='flower-ai-generator'):
    try:
        client = bigquery.Client(project=project_id)
        
        query = """
        UPDATE `flower-ai-generator.saas_chat_generator.chats`
        SET system_prompt = @prompt_content
        WHERE chat_id = @chat_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("prompt_content", "STRING", prompt_text),
                bigquery.ScalarQueryParameter("chat_id", "STRING", chat_id)
            ]
        )
        
        job = client.query(query, job_config=job_config)
        job.result()
        
        print(f"✅ Prompt aplicado com sucesso ao chat {chat_id}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar prompt: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    chat_id = sys.argv[1]
    arquivo_prompt = sys.argv[2]
    
    with open(arquivo_prompt, 'r', encoding='utf-8') as f:
        prompt_content = f.read().strip()
    
    aplicar_prompt_seguro(chat_id, prompt_content)
