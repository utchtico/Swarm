from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from src.models.models import db, User
from functools import wraps
import os
from datetime import date


auth_bp = Blueprint('auth', __name__)
user_root = 'Experiments'

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username or 'Invitado'
            
            today_str = date.today().isoformat()  # 'YYYY-MM-DD'
            path = os.path.join(user_root, username, today_str)
            os.makedirs(path, exist_ok=True) 
            return redirect(url_for('home'))
        else:
            msg = 'Credenciales incorrectas'
    return render_template('login.html', msg=msg)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*allowed):
    def wrap(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            role = session.get('role')
            if role is None:
                # No autenticado → a login
                return redirect(url_for('auth.login'))
            if allowed and role not in allowed:
                # Autenticado pero sin permiso → 403 (NO limpiar sesión)
                return render_template('403.html'), 403
            return f(*args, **kwargs)
        return decorated
    return wrap
