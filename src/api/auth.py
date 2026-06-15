import time
from collections import defaultdict
from functools import wraps

from flask import (Blueprint, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from src.models.models import db, User

auth_bp = Blueprint('auth', __name__)

# ── Throttling de login (en memoria por proceso) ─────────────────────────────
MAX_INTENTOS  = 5
VENTANA_SEG   = 15 * 60
_intentos: dict = defaultdict(list)
_HASH_SENUELO = generate_password_hash('senuelo-no-valido-swarm-2025')


def _clave(username: str) -> str:
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '?')
    return f'{username.lower()}|{ip.split(",")[0].strip()}'


def _bloqueado(clave: str) -> bool:
    ahora = time.time()
    _intentos[clave] = [t for t in _intentos[clave] if ahora - t < VENTANA_SEG]
    return len(_intentos[clave]) >= MAX_INTENTOS


def _fallo(clave: str):
    _intentos[clave].append(time.time())


def _limpiar(clave: str):
    _intentos.pop(clave, None)


# ── Login / Logout ────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya está autenticado, redirigir
    if 'user_id' in session:
        return redirect(url_for('views.home'))

    msg = ''
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password =  request.form.get('password') or ''

        if not username or not password:
            msg = 'Usuario y contraseña son obligatorios.'
            return render_template('login.html', msg=msg)

        clave = _clave(username)
        if _bloqueado(clave):
            msg = 'Demasiados intentos fallidos. Espere unos minutos e intente de nuevo.'
            return render_template('login.html', msg=msg), 429

        user = User.query.filter_by(username=username).first()
        hash_a_validar = user.password_hash if user else _HASH_SENUELO
        ok = check_password_hash(hash_a_validar, password)

        if user and ok:
            if not user.activo:
                msg = 'Tu cuenta ha sido desactivada. Contacta al administrador.'
                return render_template('login.html', msg=msg)

            _limpiar(clave)
            session.clear()
            session.permanent = True
            session['user_id']  = user.id
            session['role']     = user.role
            session['username'] = user.username

            # Registrar último acceso
            from datetime import datetime, timezone
            user.ultimo_acceso = datetime.now(timezone.utc)
            db.session.commit()

            if user.debe_cambiar_password:
                return redirect(url_for('auth.cambiar_password'))
            return redirect(url_for('views.home'))

        _fallo(clave)
        msg = 'Credenciales incorrectas.'

    return render_template('login.html', msg=msg)


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# ── Cambio de contraseña obligatorio ─────────────────────────────────────────

@auth_bp.route('/cambiar-password', methods=['GET', 'POST'])
def cambiar_password():
    """Ruta a la que se redirige si debe_cambiar_password=True."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    msg = ''
    error = False

    if request.method == 'POST':
        nueva    = request.form.get('nueva_password', '')
        confirma = request.form.get('confirmar_password', '')

        if len(nueva) < 8:
            msg, error = 'La contraseña debe tener al menos 8 caracteres.', True
        elif nueva != confirma:
            msg, error = 'Las contraseñas no coinciden.', True
        else:
            user = db.session.get(User, session['user_id'])
            if user:
                user.password_hash        = generate_password_hash(nueva)
                user.debe_cambiar_password = False
                db.session.commit()
                return redirect(url_for('views.home'))
            msg, error = 'Usuario no encontrado.', True

    return render_template('cambiar_password.html', msg=msg, error=error)


# ── Decoradores de acceso ─────────────────────────────────────────────────────

def _es_api() -> bool:
    return request.path.startswith('/api/')


def _no_autenticado():
    if _es_api():
        return jsonify({'error': 'No autenticado.'}), 401
    return redirect(url_for('auth.login'))


def _sin_permiso():
    if _es_api():
        return jsonify({'error': 'No tiene permiso para esta operación.'}), 403
    return render_template('403.html'), 403


def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            return _no_autenticado()
        return f(*args, **kwargs)
    return inner


def roles_required(*allowed):
    def wrap(f):
        @wraps(f)
        def inner(*args, **kwargs):
            if 'user_id' not in session:
                return _no_autenticado()
            if allowed and session.get('role') not in allowed:
                return _sin_permiso()
            return f(*args, **kwargs)
        return inner
    return wrap


def es_admin() -> bool:
    return session.get('role') in ('admin', 'superadmin')


def es_superadmin() -> bool:
    return session.get('role') == 'superadmin'