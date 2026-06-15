import os
from datetime import datetime, timedelta, timezone

from flask import jsonify, redirect, request, session, url_for


def init_security(app):
    idle_minutes = int(os.environ.get('SESSION_IDLE_MINUTES', '480'))

    # ── Cookies de sesión ────────────────────────────────────────────────────
    app.config['SESSION_COOKIE_HTTPONLY']    = True
    app.config['SESSION_COOKIE_SAMESITE']   = 'Lax'
    app.config['SESSION_COOKIE_NAME']       = 'swarm_session'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=idle_minutes)
    app.config['SESSION_COOKIE_SECURE'] = (
        os.environ.get('SESSION_COOKIE_SECURE', '0') == '1')

    # SECRET_KEY sin fallback en producción
    secret = app.config.get('SECRET_KEY', '')
    if not secret or secret == 'dev-insecure-key':
        app.logger.warning(
            '[SEGURIDAD] SECRET_KEY no está definida o usa el valor inseguro. '
            'Define SECRET_KEY en el .env antes de exponer el servidor.')

    # ── Flask-Mail ────────────────────────────────────────────────────────────
    app.config['MAIL_SERVER']   = 'smtp.gmail.com'
    app.config['MAIL_PORT']     = 587
    app.config['MAIL_USE_TLS']  = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'utch.tico@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_APP_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = (
        'Swarm — UACJ', os.environ.get('MAIL_USERNAME', 'utch.tico@gmail.com'))

    # ── Timeout de inactividad (verificación en servidor) ────────────────────
    @app.before_request
    def verificar_inactividad():
        if 'user_id' not in session:
            return None
        ahora  = datetime.now(timezone.utc).timestamp()
        ultimo = session.get('_ultimo_acceso')
        if ultimo is not None and (ahora - ultimo) > idle_minutes * 60:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Sesión expirada por inactividad.'}), 401
            return redirect(url_for('auth.login'))
        session['_ultimo_acceso'] = ahora
        return None

    # ── Headers de seguridad en todas las respuestas ─────────────────────────
    @app.after_request
    def headers_seguridad(resp):
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if request.path.startswith('/api/'):
            resp.headers.setdefault('Cache-Control', 'no-store')
        return resp