import os

class Config:
    # Google Cloud
    PROJECT_ID = 'flower-ai-generator'
    REGION = 'southamerica-east1'
    
    # Claude API
    CLAUDE_MODEL = 'claude-sonnet-4-20250514'
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # Database
    BIGQUERY_DATASET = 'saas_chat_generator'
    
    # Storage
    STORAGE_BUCKET = f'{PROJECT_ID}-saas-chats'
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hora
    
    # Planos do SaaS
    PLANS = {
        'free': {
            'name': 'Gratuito',
            'max_chats': 1,
            'max_messages_per_month': 100,
            'price': 0
        },
        'basic': {
            'name': 'Básico',
            'max_chats': 3,
            'max_messages_per_month': 1000,
            'price': 29.90
        },
        'premium': {
            'name': 'Premium',
            'max_chats': 10,
            'max_messages_per_month': 5000,
            'price': 99.90
        },
        'enterprise': {
            'name': 'Enterprise',
            'max_chats': -1,  # ilimitado
            'max_messages_per_month': -1,  # ilimitado
            'price': 299.90
        }
    }
