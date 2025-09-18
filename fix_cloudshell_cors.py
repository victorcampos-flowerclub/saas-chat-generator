#!/usr/bin/env python3
"""
Proxy completo para CloudShell - Serve páginas e APIs
"""

import os
import sys
from flask import Flask, request, jsonify, make_response, render_template
import requests

app = Flask(__name__, template_folder='backend/templates')

# Servir páginas HTML
@app.route('/')
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Proxy para APIs
@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_api(path):
    """Proxy para APIs locais"""
    target_url = f"http://localhost:5002/api/{path}"
    
    data = request.get_json() if request.is_json else None
    headers = dict(request.headers)
    
    # Remover headers problemáticos
    headers.pop('Host', None)
    headers.pop('Origin', None)
    
    try:
        response = requests.request(
            method=request.method,
            url=target_url,
            json=data,
            headers=headers,
            timeout=30
        )
        
        resp = make_response(response.text, response.status_code)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Content-Type'] = 'application/json'
        
        return resp
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/<path:path>', methods=['OPTIONS'])
def proxy_options(path):
    """CORS preflight"""
    resp = make_response('', 200)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp

if __name__ == '__main__':
    print("🔧 Proxy completo rodando na porta 5003...")
    app.run(debug=True, host='0.0.0.0', port=5003)
