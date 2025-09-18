import requests
import sys
from google.cloud import secretmanager

def test_api_key():
    try:
        # Buscar API key
        client = secretmanager.SecretManagerServiceClient()
        name = "projects/flower-ai-generator/secrets/claude-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8")
        
        print(f"API Key raw (primeiros 30): {repr(api_key[:30])}")
        print(f"API Key length: {len(api_key)}")
        
        # Limpar espaços
        api_key_clean = api_key.strip()
        print(f"API Key clean length: {len(api_key_clean)}")
        print(f"API Key clean (primeiros 30): {repr(api_key_clean[:30])}")
        
        # Testar com a API
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key_clean,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "Teste"}]
        }
        
        print("\n📤 Testando com Claude API...")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API KEY FUNCIONANDO!")
            print(f"Resposta: {result['content'][0]['text']}")
            return True
        else:
            print(f"❌ ERRO na API: {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

if __name__ == "__main__":
    test_api_key()
