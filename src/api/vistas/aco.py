# src/api/vistas_aco.py
# Rutas de la familia ACO + MCDM puros (TOPSIS, MOORA-V, DA).
# Cálculos se activarán en la Fase 3.

from flask import Blueprint, render_template
from src.api.auth import roles_required

aco_bp = Blueprint('aco', __name__)


@aco_bp.get('/aco')
@roles_required('user', 'admin', 'superadmin')
def vista_aco():
    return render_template('aco/aco.html')


@aco_bp.get('/daaco')
@roles_required('user', 'admin', 'superadmin')
def vista_daaco():
    return render_template('aco/daaco.html')


@aco_bp.get('/mooraaco')
@roles_required('user', 'admin', 'superadmin')
def vista_mooraaco():
    return render_template('aco/mooraaco.html')


@aco_bp.get('/topsisaco')
@roles_required('user', 'admin', 'superadmin')
def vista_topsisaco():
    return render_template('aco/topsisaco.html')


# ── MCDM puros ───────────────────────────────────────────────────────────────

@aco_bp.get('/topsis')
@roles_required('user', 'admin', 'superadmin')
def vista_topsis():
    return render_template('mcdm/topsis.html')


@aco_bp.get('/moorav')
@roles_required('user', 'admin', 'superadmin')
def vista_moorav():
    return render_template('mcdm/moorav.html')


@aco_bp.get('/da')
@roles_required('user', 'admin', 'superadmin')
def vista_da():
    return render_template('mcdm/da.html')