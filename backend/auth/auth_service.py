"""
Serviço de autenticação JWT
"""

from flask_jwt_extended import create_access_token, decode_token
from datetime import timedelta
import re
from typing import Dict, Optional, Tuple

from models.database import user_model

class AuthService:
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validar formato do email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """Validar força da senha"""
        if len(password) < 8:
            return False, "Senha deve ter pelo menos 8 caracteres"
        
        if not re.search(r'[A-Z]', password):
            return False, "Senha deve ter pelo menos uma letra maiúscula"
        
        if not re.search(r'[a-z]', password):
            return False, "Senha deve ter pelo menos uma letra minúscula"
        
        if not re.search(r'\d', password):
            return False, "Senha deve ter pelo menos um número"
        
        return True, "Senha válida"
    
    @staticmethod
    def register_user(email: str, password: str, full_name: str,
                     company_name: str = None, phone: str = None) -> Dict:
        """Registrar novo usuário"""
        # Validações
        if not AuthService.validate_email(email):
            return {'success': False, 'error': 'Email inválido'}
        
        password_valid, password_msg = AuthService.validate_password(password)
        if not password_valid:
            return {'success': False, 'error': password_msg}
        
        if not full_name or len(full_name.strip()) < 2:
            return {'success': False, 'error': 'Nome completo obrigatório'}
        
        # Verificar se email já existe
        existing_user = user_model.get_user_by_email(email)
        if existing_user:
            return {'success': False, 'error': 'Email já cadastrado'}
        
        # Criar usuário
        user = user_model.create_user(
            email=email.lower().strip(),
            password=password,
            full_name=full_name.strip(),
            company_name=company_name.strip() if company_name else None,
            phone=phone.strip() if phone else None
        )
        
        if user:
            # Criar token de acesso
            access_token = create_access_token(
                identity=user['user_id'],
                expires_delta=timedelta(hours=24)
            )
            
            return {
                'success': True,
                'user': user,
                'access_token': access_token
            }
        else:
            return {'success': False, 'error': 'Erro ao criar usuário'}
    
    @staticmethod
    def login_user(email: str, password: str) -> Dict:
        """Fazer login do usuário"""
        if not email or not password:
            return {'success': False, 'error': 'Email e senha obrigatórios'}
        
        # Verificar credenciais
        if not user_model.verify_password(email.lower().strip(), password):
            return {'success': False, 'error': 'Email ou senha incorretos'}
        
        # Buscar usuário
        user = user_model.get_user_by_email(email.lower().strip())
        if not user:
            return {'success': False, 'error': 'Usuário não encontrado'}
        
        # Verificar se usuário está ativo
        if user['status'] != 'active':
            return {'success': False, 'error': 'Conta suspensa ou inativa'}
        
        # Atualizar último login
        user_model.update_last_login(user['user_id'])
        
        # Criar token de acesso
        access_token = create_access_token(
            identity=user['user_id'],
            expires_delta=timedelta(hours=24)
        )
        
        return {
            'success': True,
            'user': user,
            'access_token': access_token
        }
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[Dict]:
        """Obter usuário a partir do token"""
        try:
            decoded = decode_token(token)
            user_id = decoded['sub']
            return user_model.get_user_by_id(user_id)
        except Exception:
            return None

auth_service = AuthService()
