from google.cloud import secretmanager
import requests

def test_api_key():
    try:
        print("Conectando ao Secret Manager...")
        client = secretmanager.SecretManagerServiceClient()
        name = "projects/flower-ai-generator/secrets/claude-api-key/versions/latest"
        
        print("Buscando secret...")
        response = client.access_secret_version(request={"name": name})
        api_key_raw = response.payload.data.decode("UTF-8")
        
        print(f"Raw key length: {len(api_key_raw)}")
        print(f"Raw key preview: {repr(api_key_raw[:30])}...")
        
        # Limpar
        api_key = api_key_raw.strip()
        print(f"Clean key length: {len(api_key)}")
        
        if not api_key.startswith('sk-ant-api03-'):
            print(f"❌ ERRO: API key não começa com sk-ant-api03-")
            print(f"Começa com: {repr(api_key[:15])}")
            return False
        
        print("✅ API key format OK")
        
        # TESTE COM CLAUDE
        print("\n🧪 Testando Claude API...")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 20,
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ CLAUDE API FUNCIONANDO!")
            print(f"Resposta: {result['content'][0]['text']}")
            return True
        else:
            print("❌ ERRO Claude API:")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_api_key()
    exit(0 if success else 1)
