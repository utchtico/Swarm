from flask import Blueprint, render_template
from src.api.auth import roles_required

compara_bp = Blueprint('compara', __name__)


@compara_bp.get('/comparacionGeneral')
@roles_required('user', 'admin', 'superadmin')
def vista_comparacion_general():
    return render_template('comparacionGeneral.html')


@compara_bp.get('/comparacionBa')
@roles_required('user', 'admin', 'superadmin')
def vista_comparacion_ba():
    return render_template('ba/comparacionBa.html')


@compara_bp.get('/comparacionAco')
@roles_required('user', 'admin', 'superadmin')
def vista_comparacion_aco():
    return render_template('aco/comparacionAco.html')


@compara_bp.get('/comparacion')
@roles_required('user', 'admin', 'superadmin')
def vista_comparacion():
    return render_template('comparacion.html')