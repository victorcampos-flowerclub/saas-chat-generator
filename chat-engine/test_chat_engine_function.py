import sys
import os

# Simular exatamente o que o chat engine faz
def test_chat_engine_api_key():
    try:
        print("🔧 Testando função get_claude_api_key do Chat Engine...")
        
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/flower-ai-generator/secrets/claude-api-key/versions/latest"
        
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8").strip()
        
        print(f"✅ API Key obtida: {api_key[:20]}...{api_key[-10:]}")
        print(f"📏 Length: {len(api_key)}")
        
        # Verificações que o Chat Engine faz
        if not api_key:
            print("❌ API key vazia")
            return None
            
        if not api_key.startswith('sk-ant-api03-'):
            print(f"❌ API key formato inválido: {api_key[:20]}...")
            return None
            
        if len(api_key) < 50:
            print(f"❌ API key muito curta: {len(api_key)} caracteres")
            return None
        
        print("✅ Todas as validações passaram!")
        return api_key
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return None

if __name__ == "__main__":
    api_key = test_chat_engine_api_key()
    if api_key:
        print("🎉 Chat Engine deveria conseguir obter a API key!")
    else:
        print("⚠️ Chat Engine não conseguiria obter a API key")
