"""
Backend principal do SaaS Chat Generator
"""

import os
import sys
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import timedelta
import json

# Adicionar o diretório pai ao path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.auth.auth_service import auth_service
from backend.models.database import user_model, chat_model, message_model

# Inicializar Flask
app = Flask(__name__)
app.config.from_object(Config)

# Configurar CORS
CORS(app, origins=["*"])

# Configurar JWT
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)


# ================================
# ROUTES DE FRONTEND
# ================================

@app.route('/login')
def login_page():
    """Página de login"""
    return render_template('login.html')

@app.route('/dashboard')
def dashboard_page():
    """Página do dashboard"""
    return render_template('dashboard.html')

if __name__ == '__main__':
    print("🚀 Iniciando SaaS Chat Generator Backend...")
    print(f"📊 Projeto: {Config.PROJECT_ID}")
    print(f"🗄️ Dataset: {Config.BIGQUERY_DATASET}")
    print(f"🤖 Modelo Claude: {Config.CLAUDE_MODEL}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
