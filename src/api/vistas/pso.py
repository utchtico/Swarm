from flask import Blueprint, render_template
from src.api.auth import roles_required

pso_bp = Blueprint('pso', __name__)


# ── Vistas HTML ──────────────────────────────────────────────────────────────

@pso_bp.get('/pso')
@roles_required('user', 'admin', 'superadmin')
def vista_pso():
    return render_template('pso/pso.html')


@pso_bp.get('/dapso')
@roles_required('user', 'admin', 'superadmin')
def vista_dapso():
    return render_template('pso/dapso.html')


@pso_bp.get('/moorapso')
@roles_required('user', 'admin', 'superadmin')
def vista_moorapso():
    return render_template('pso/moorapso.html')


@pso_bp.get('/topsispso')
@roles_required('user', 'admin', 'superadmin')
def vista_topsispso():
    return render_template('pso/topsispso.html')


@pso_bp.get('/comparacionPso')
@roles_required('user', 'admin', 'superadmin')
def vista_comparacion_pso():
    return render_template('pso/comparacionPso.html')
