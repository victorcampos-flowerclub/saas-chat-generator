#!/bin/bash
echo "🚀 Deploy automático"
git add .
git commit -m "Auto deploy: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main
echo "✅ Deploy concluído!"
