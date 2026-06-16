from flask import Blueprint, render_template
from src.api.auth import roles_required

ba_bp = Blueprint('ba', __name__)


@ba_bp.get('/ba')
@roles_required('user', 'admin', 'superadmin')
def vista_ba():
    return render_template('ba/ba.html')


@ba_bp.get('/daba')
@roles_required('user', 'admin', 'superadmin')
def vista_daba():
    return render_template('ba/daba.html')


@ba_bp.get('/mooraba')
@roles_required('user', 'admin', 'superadmin')
def vista_mooraba():
    return render_template('ba/mooraba.html')


@ba_bp.get('/topsisba')
@roles_required('user', 'admin', 'superadmin')
def vista_topsisba():
    return render_template('ba/topsisba.html')