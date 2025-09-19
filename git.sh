#!/bin/bash

# Git Deploy Script - SaaS Chat Generator
# Exclui automaticamente node_modules e arquivos desnecessários

echo "🚀 DEPLOY GITHUB - SaaS CHAT GENERATOR"
echo "====================================="

# Verificar se token está definido
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ ERRO: Defina GITHUB_TOKEN primeiro"
    echo "Execute: export GITHUB_TOKEN='sua_key_aqui'"
    exit 1
fi

GITHUB_USER="victorcampos-flowerclub"
REPO_NAME="saas-chat-generator"

# Função de log
log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

log "Verificando diretório..."
if [ ! -f "README.md" ]; then
    echo "❌ Execute a partir da raiz do projeto!"
    exit 1
fi

# Configurar Git
git config user.name "Victor Campos" 2>/dev/null
git config user.email "victor@flowerclub.com.br" 2>/dev/null

# Criar/atualizar .gitignore ANTES de adicionar arquivos
log "Criando .gitignore seguro..."
cat > .gitignore << 'GITIGNORE_EOF'
# Dependencies
node_modules/
npm-debug.log*
package-lock.json

# Environment
.env
.env.local
.env.production

# Cache e logs
logs/
*.log
.npm
.cache/

# OS e IDE
.DS_Store
Thumbs.db
.vscode/
.idea/

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# WhatsApp session data
.wwebjs_auth/
.wwebjs_cache/

# Backups
*.backup
*.bak
GITIGNORE_EOF

log "Removendo node_modules do tracking..."
git rm -r --cached whatsapp-service/node_modules/ 2>/dev/null || true
git rm --cached whatsapp-service/package-lock.json 2>/dev/null || true

log "Limpando arquivos temporários..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.backup*" -delete 2>/dev/null || true

log "Adicionando arquivos essenciais..."
git add .gitignore
git add README.md 
git add git.sh
git add backend/
git add chat-engine/
git add docs/
git add whatsapp-service/app.js
git add whatsapp-service/package.json
git add whatsapp-service/Dockerfile
git add whatsapp-service/.dockerignore
git add whatsapp-service/.env

# Verificar o que será commitado
STAGED_FILES=$(git diff --cached --name-only | wc -l)
log "Arquivos para commit: $STAGED_FILES"

if [ $STAGED_FILES -eq 0 ]; then
    log "Nenhuma mudança para commitar"
    exit 0
fi

# Verificar se não há node_modules sendo commitado
if git diff --cached --name-only | grep -q "node_modules"; then
    echo "❌ ERRO: node_modules detectado no commit!"
    echo "Cancelando deploy para evitar problemas..."
    exit 1
fi

# Commit
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
COMMIT_MSG="Deploy SaaS Chat Generator - $TIMESTAMP

✅ Sistema completo v2.2.0:
- Backend Principal (Flask + Agentes)
- Chat Engine (Claude API)  
- WhatsApp Service (Node.js)
- Documentação técnica completa
- Infraestrutura: 3 serviços Cloud Run

🧹 Deploy limpo sem node_modules
📱 WhatsApp integration funcionando"

log "Fazendo commit..."
git commit -m "$COMMIT_MSG"

# Configurar remote
git remote set-url origin "https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git" 2>/dev/null

# Push
log "Enviando para GitHub..."
if git push origin main; then
    log "✅ Deploy realizado com sucesso!"
    echo ""
    echo "📁 Repositório: https://github.com/${GITHUB_USER}/${REPO_NAME}"
    echo "🌐 Branch: main"
    echo "⏰ Horário: $TIMESTAMP"
    echo ""
    echo "🚀 Serviços em produção:"
    echo "   Backend: https://saas-chat-backend-365442086139.us-east1.run.app"
    echo "   Chat-Engine: https://saas-chat-engine-365442086139.us-east1.run.app"
    echo "   WhatsApp: https://saas-chat-whatsapp-service-365442086139.us-east1.run.app"
else
    log "❌ Erro no push. Tentando force push..."
    if git push --force origin main; then
        log "✅ Force push realizado!"
    else
        log "❌ Falha total no deploy"
        exit 1
    fi
fi

log "✨ Deploy finalizado!"
