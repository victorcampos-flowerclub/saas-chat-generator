#!/usr/bin/env python3
"""
Teste direto da Claude API para verificar se está funcionando
"""

import requests
import json
from google.cloud import secretmanager

def test_claude_api():
    print("🧪 TESTANDO CLAUDE API DIRETAMENTE")
    print("==================================")
    
    try:
        # 1. Buscar API key do Secret Manager
        print("📡 Buscando API key do Secret Manager...")
        client = secretmanager.SecretManagerServiceClient()
        name = "projects/flower-ai-generator/secrets/claude-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8").strip()
        
        print(f"✅ API Key encontrada: {api_key[:20]}...{api_key[-10:]}")
        print(f"📏 Tamanho: {len(api_key)} caracteres")
        
        # 2. Testar API do Claude
        print("\n🔄 Testando API do Claude...")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 50,
            "messages": [
                {
                    "role": "user", 
                    "content": "Responda apenas: 'Claude API funcionando perfeitamente!'"
                }
            ]
        }
        
        print("📤 Enviando requisição para Claude...")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"📥 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            message = result['content'][0]['text']
            print(f"✅ SUCESSO! Claude respondeu: '{message}'")
            print("🎉 A Claude API está funcionando PERFEITAMENTE!")
            return True
        else:
            print(f"❌ ERRO! Status: {response.status_code}")
            print(f"📄 Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERRO na execução: {e}")
        return False

if __name__ == "__main__":
    test_claude_api()
