#!/bin/bash
echo "🚀 Deploy automático - SaaS Chat Generator"

# Verificar status atual
echo "📋 Verificando arquivos..."
git status --porcelain

# Adicionar todos os arquivos
echo "📁 Adicionando arquivos..."
git add .

# Mostrar o que será commitado
echo "📝 Arquivos para commit:"
git diff --cached --name-only

# Fazer commit
echo "💾 Fazendo commit..."
git commit -m "Auto deploy: $(date '+%Y-%m-%d %H:%M:%S')"

# Push para GitHub
echo "🌐 Enviando para GitHub..."
git push origin main

echo "✅ Deploy concluído!"
echo "🔗 Verificar em: https://github.com/victorcampos-flowerclub/saas-chat-generator"
