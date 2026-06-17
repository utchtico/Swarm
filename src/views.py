from flask import Blueprint, render_template, send_from_directory, session

from src.api.auth import roles_required
from src.models.models import db, User
from src.algoritmos.topsis import MATRIZ_FIJA

views_bp = Blueprint('views', __name__)


@views_bp.route('/')
@roles_required('user', 'admin', 'superadmin')
def home():
    usuario = None
    uid = session.get('user_id')
    if uid:
        user = db.session.get(User, uid)
        if user:
            usuario = user.username
    return render_template('index.html', usuario=usuario)


@views_bp.route('/acercade')
def acercade():
    return render_template('acercade.html')


@views_bp.route('/casoexperimental')
@roles_required('user', 'admin', 'superadmin')
def casoexperimental():
    return render_template('casoexperimental.html', matriz=MATRIZ_FIJA)


@views_bp.route('/descargar-parametros')
@roles_required('user', 'admin', 'superadmin')
def descargar_parametros():
    """
    Sirve el archivo de referencia con rangos y valores comunes para cada
    algoritmo (w predefinidos, rangos válidos de alpha/beta/rho/Q/n_ants,
    etc.). Es un archivo estático, no generado dinámicamente — mismo
    comportamiento que la ruta original (send_from_directory contra
    'Experiments/static'), apuntando ahora a static/doc/.
    """
    directorio = 'static/doc'
    filename = 'entradas-Programa.xlsx'
    return send_from_directory(directorio, filename, as_attachment=True)


@views_bp.route('/articulos')
@roles_required('admin', 'superadmin')
def articulos():
    return render_template('articulos.html')


@views_bp.route('/publicaciones')
@roles_required('user', 'admin', 'superadmin')
def publicacion():
    return render_template('publicaciones.html')


@views_bp.route('/admin/usuarios')
@roles_required('admin', 'superadmin')
def admin_usuarios():
    """Rerouta al blueprint de admin para mantener la URL limpia desde la navbar."""
    from flask import redirect, url_for
    return redirect(url_for('admin.panel_usuarios'))