"""
User authentication and authorization
"""

import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from backend.database import find_user_by_email, add_user, find_user_by_id

SECRET_KEY = 'tasktraq-jwt-secret-change-in-production'

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def generate_token(user_id):
    """Generate a JWT token for a user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def decode_token(token):
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def register_user(email, password):
    """Register a new user"""
    # Validate email
    if not email or '@' not in email:
        return None, 'Invalid email address'
    
    # Validate password
    if not password or len(password) < 6:
        return None, 'Password must be at least 6 characters'
    
    # Check if user exists
    if find_user_by_email(email):
        return None, 'Email already registered'
    
    # Create user
    user = {
        'id': str(uuid.uuid4()),
        'email': email,
        'password_hash': hash_password(password),
        'created_at': datetime.utcnow().isoformat()
    }
    
    add_user(user)
    return user, None

def login_user(email, password):
    """Authenticate a user"""
    user = find_user_by_email(email)
    
    if not user:
        return None, 'Invalid email or password'
    
    if not verify_password(password, user['password_hash']):
        return None, 'Invalid email or password'
    
    token = generate_token(user['id'])
    return {'user_id': user['id'], 'email': user['email'], 'token': token}, None

def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_id = decode_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        user = find_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Pass user to the route
        return f(user, *args, **kwargs)
    
    return decorated