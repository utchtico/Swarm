from flask import (Blueprint, jsonify, render_template,
                   request, session, url_for)
from werkzeug.security import generate_password_hash

from src.api.auth import es_superadmin, roles_required
from src.models.models import db, User
from src.services.email import enviar_invitacion, enviar_reset_password, generar_password_temporal

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ROLES_PERMITIDOS = ('user', 'admin', 'superadmin')


def _usuario_actual() -> User | None:
    return db.session.get(User, session.get('user_id'))


# ── Vista del panel ──────────────────────────────────────────────────────────

@admin_bp.get('/usuarios')
@roles_required('admin', 'superadmin')
def panel_usuarios():
    return render_template('admin/usuarios.html')


# ── API JSON del panel ────────────────────────────────────────────────────────

@admin_bp.get('/api/usuarios')
@roles_required('admin', 'superadmin')
def listar_usuarios():
    """Lista todos los usuarios. Superadmin ve todo; admin no ve superadmins."""
    q = User.query.order_by(User.creado_en.desc())
    if not es_superadmin():
        q = q.filter(User.role != 'superadmin')
    return jsonify([u.to_dict() for u in q.all()])


@admin_bp.post('/api/usuarios')
@roles_required('admin', 'superadmin')
def crear_usuario():
    """
    Crea un usuario e intenta enviar el correo de invitación.
    Body JSON: { username, email, role }
    """
    data     = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email    = (data.get('email')    or '').strip()
    role     = (data.get('role')     or 'user').strip()

    # Validaciones
    if not username:
        return jsonify({'error': 'El nombre de usuario es obligatorio.'}), 400
    if not email or '@' not in email:
        return jsonify({'error': 'Se requiere un email válido para enviar la invitación.'}), 400
    if role not in ROLES_PERMITIDOS:
        return jsonify({'error': f'Rol no válido. Opciones: {ROLES_PERMITIDOS}'}), 400
    if role in ('admin', 'superadmin') and not es_superadmin():
        return jsonify({'error': 'Solo superadmin puede asignar roles de administrador.'}), 403
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'El nombre de usuario ya existe.'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'El email ya está registrado.'}), 409

    password_temp = generar_password_temporal()
    creador = _usuario_actual()

    nuevo = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password_temp),
        role=role,
        activo=True,
        debe_cambiar_password=True,
        creado_por_id=creador.id if creador else None,
    )
    db.session.add(nuevo)
    db.session.commit()

    # Intentar enviar correo
    url_login = url_for('auth.login', _external=True)
    correo_ok = enviar_invitacion(email, username, password_temp, url_login)

    return jsonify({
        'ok': True,
        'usuario': nuevo.to_dict(),
        'correo_enviado': correo_ok,
        'aviso': (None if correo_ok else
                  'Usuario creado pero no se pudo enviar el correo. '
                  'Comprueba MAIL_APP_PASSWORD en el .env.'),
    }), 201


@admin_bp.patch('/api/usuarios/<int:uid>')
@roles_required('admin', 'superadmin')
def actualizar_usuario(uid: int):
    """
    Modifica rol o estado activo de un usuario.
    Body JSON (campos opcionales): { role, activo }
    """
    objetivo = db.session.get(User, uid)
    if objetivo is None:
        return jsonify({'error': 'Usuario no encontrado.'}), 404

    # Protecciones
    if objetivo.role in ('admin', 'superadmin') and not es_superadmin():
        return jsonify({'error': 'No puedes modificar administradores.'}), 403
    if objetivo.id == session.get('user_id'):
        return jsonify({'error': 'No puedes modificarte a ti mismo.'}), 400

    data = request.get_json(silent=True) or {}

    if 'role' in data:
        nuevo_rol = data['role']
        if nuevo_rol not in ROLES_PERMITIDOS:
            return jsonify({'error': 'Rol no válido.'}), 400
        if nuevo_rol in ('admin', 'superadmin') and not es_superadmin():
            return jsonify({'error': 'Solo superadmin puede asignar roles de administrador.'}), 403
        objetivo.role = nuevo_rol

    if 'activo' in data:
        if not isinstance(data['activo'], bool):
            return jsonify({'error': "'activo' debe ser true o false."}), 400
        objetivo.activo = data['activo']

    db.session.commit()
    return jsonify({'ok': True, 'usuario': objetivo.to_dict()})


@admin_bp.post('/api/usuarios/<int:uid>/reset-password')
@roles_required('admin', 'superadmin')
def reset_password(uid: int):
    """Genera nueva contraseña temporal y reenvía el correo."""
    objetivo = db.session.get(User, uid)
    if objetivo is None:
        return jsonify({'error': 'Usuario no encontrado.'}), 404
    if objetivo.role in ('admin', 'superadmin') and not es_superadmin():
        return jsonify({'error': 'No puedes resetear contraseñas de administradores.'}), 403
    if not objetivo.email:
        return jsonify({'error': 'El usuario no tiene email registrado.'}), 400

    password_temp = generar_password_temporal()
    objetivo.password_hash        = generate_password_hash(password_temp)
    objetivo.debe_cambiar_password = True
    db.session.commit()

    url_login = url_for('auth.login', _external=True)
    correo_ok = enviar_reset_password(objetivo.email, objetivo.username,
                                      password_temp, url_login)
    return jsonify({
        'ok': True,
        'correo_enviado': correo_ok,
        'aviso': (None if correo_ok else
                  'Contraseña reseteada pero no se pudo enviar el correo.'),
    })