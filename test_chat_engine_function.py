#!/usr/bin/env python3
"""
Teste específico da função get_claude_api_key do Chat Engine
"""

import sys
import os

# Simular o ambiente do Chat Engine
sys.path.append('/app')  # Path do Chat Engine

def test_chat_engine_function():
    print("🔧 TESTANDO FUNÇÃO DO CHAT ENGINE")
    print("=================================")
    
    try:
        # Importar e testar a função como o Chat Engine faz
        from google.cloud import secretmanager
        
        print("📡 Testando get_secret_client()...")
        client = secretmanager.SecretManagerServiceClient()
        print("✅ Secret client criado com sucesso")
        
        print("📡 Testando get_claude_api_key()...")
        name = f"projects/flower-ai-generator/secrets/claude-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8").strip()
        
        print(f"✅ API Key obtida: {api_key[:20]}...{api_key[-10:]}")
        
        # Testar se não é None
        if api_key and len(api_key) > 50:
            print("✅ API key válida!")
            return api_key
        else:
            print("❌ API key inválida ou vazia")
            return None
            
    except Exception as e:
        print(f"❌ ERRO na função: {e}")
        return None

def test_send_claude_message():
    print("\n🤖 TESTANDO SEND_CLAUDE_MESSAGE")
    print("===============================")
    
    try:
        import requests
        
        # Buscar API key
        api_key = test_chat_engine_function()
        if not api_key:
            print("❌ Não foi possível obter API key")
            return False
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "Teste do Chat Engine"}]
        }
        
        print("📤 Enviando requisição...")
        response = requests.post("https://api.anthropic.com/v1/messages", 
                               headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            message = result['content'][0]['text']
            print(f"✅ SUCESSO! Resposta: {message}")
            return True
        else:
            print(f"❌ ERRO! Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

if __name__ == "__main__":
    success = test_send_claude_message()
    if success:
        print("\n🎉 Chat Engine deveria estar funcionando!")
        print("💡 O problema pode estar no código de erro handling")
    else:
        print("\n⚠️ Problema identificado na função do Chat Engine")
