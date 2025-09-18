import os

class Config:
    PROJECT_ID = 'flower-ai-generator'
    REGION = 'southamerica-east1'
    CLAUDE_MODEL = 'claude-sonnet-4-20250514'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
    BIGQUERY_DATASET = 'saas_chat_generator'
    STORAGE_BUCKET = f'{PROJECT_ID}-saas-chats'
