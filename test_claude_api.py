#!/usr/bin/env python3
"""
Teste da Claude API Key - Verificar se está funcionando
"""

import requests
import json
from google.cloud import secretmanager

def get_claude_api_key():
    """Buscar API key do Claude no Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = "flower-ai-generator"
        name = f"projects/{project_id}/secrets/claude-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8")
        
        print(f"✅ API Key encontrada: {api_key[:20]}...")
        return api_key
        
    except Exception as e:
        print(f"❌ Erro ao buscar API key: {e}")
        return None

def test_claude_api(api_key):
    """Testar chamada real para Claude API"""
    url = "https://api.anthropic.com/v1/messages"
    
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
                "content": "Responda apenas: 'API funcionando perfeitamente!'"
            }
        ]
    }
    
    try:
        print("🔄 Testando chamada para Claude API...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            message = result['content'][0]['text']
            tokens = result.get('usage', {}).get('output_tokens', 0)
            
            print("🎉 SUCESSO! Claude API está funcionando!")
            print(f"📝 Resposta: {message}")
            print(f"🔢 Tokens usados: {tokens}")
            return True
        else:
            print(f"❌ Erro na API: {response.status_code}")
            print(f"📄 Resposta: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏱️ Timeout - API demorou muito para responder")
        return False
    except requests.exceptions.RequestException as e:
        print(f"🌐 Erro de conexão: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def main():
    print("🤖 Testando Claude API Key")
    print("=" * 40)
    
    # 1. Buscar API key
    api_key = get_claude_api_key()
    
    if not api_key:
        print("\n❌ Não foi possível obter a API key")
        print("💡 Configure com:")
        print("echo 'sua_api_key_aqui' | gcloud secrets versions add claude-api-key --project=flower-ai-generator --data-file=-")
        return False
    
    # 2. Verificar se não é placeholder
    if api_key == "ANTHROPIC_API_KEY_PLACEHOLDER":
        print("\n⚠️ API key ainda é um placeholder!")
        print("💡 Configure sua API key real:")
        print("echo 'sk-ant-api03-...' | gcloud secrets versions add claude-api-key --project=flower-ai-generator --data-file=-")
        return False
    
    # 3. Testar chamada real
    success = test_claude_api(api_key)
    
    print("\n" + "=" * 40)
    
    if success:
        print("✅ RESULTADO: Claude API está 100% funcional!")
        print("🚀 Pode executar o chat engine sem problemas!")
    else:
        print("❌ RESULTADO: Claude API não está funcionando")
        print("🔧 Verifique sua API key em: https://console.anthropic.com/")
    
    return success

if __name__ == "__main__":
    main()
