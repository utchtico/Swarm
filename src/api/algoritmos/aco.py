# src/api/algoritmos/aco.py
# API JSON de Ant Colony Optimization — recibe JSON, responde JSON.
# Endpoint de ejecución: /api/algoritmos/aco
# Endpoints de plantilla: /api/algoritmos/aco/plantilla
#
# El historial de ejecuciones (genérico) vive en src/api/ejecuciones.py.

from flask import Blueprint, jsonify, request, send_file, session

from src.api.auth import roles_required
from src.models.models import db, User
from src.services.ejecuciones_aco import (
    generar_plantilla_excel_aco,
    guardar_ejecucion,
    parsear_plantilla_excel_aco,
    validar_entrada_aco,
)
from src.services.ejecuciones_daaco import (
    generar_plantilla_excel_daaco,
    parsear_plantilla_excel_daaco,
    validar_entrada_daaco,
)
from src.services.ejecuciones_mooraaco import (
    generar_plantilla_excel_mooraaco,
    parsear_plantilla_excel_mooraaco,
    validar_entrada_mooraaco,
)
from src.algoritmos.aco import ejecutar_aco
from src.algoritmos.daaco import ejecutar_daaco
from src.algoritmos.mooraaco import ejecutar_mooraaco

algoritmos_aco_bp = Blueprint('algoritmos_aco_api', __name__, url_prefix='/api')


def _usuario_actual():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None


@algoritmos_aco_bp.post('/algoritmos/aco')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_aco():
    """ACO — alpha, beta, rho, Q y n_ants son definidos por el usuario; sin w."""
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        params  = validar_entrada_aco(payload)
        datos = ejecutar_aco(
            matriz=params['matriz'], alpha=params['alpha'], beta=params['beta'],
            rho=params['rho'], Q=params['Q'], n_ants=params['n_ants'],
            T=params['T'], username=user.username,
        )
        ejecucion = guardar_ejecucion('ACO', user.id, params, datos)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f'[api_calcular_aco] Error: {e}')
        return jsonify({'error': 'Ocurrió un error al ejecutar el algoritmo.'}), 500

    return jsonify({
        'ejecucion_id':             ejecucion.id,
        'mejor_alternativa':        datos['mejor_alternativa'],
        'iteraciones':              datos['iteraciones'],
        'hora_inicio':              datos['hora_inicio'],
        'fecha_inicio':             datos['fecha_inicio'],
        'hora_finalizacion':        datos['hora_finalizacion'],
        'tiempo_ejecucion':         datos['tiempo_ejecucion'],
        'historico_gbf':            datos['historico_gbf'],
        'resultados_por_iteracion': datos['resultados_por_iteracion'],
        'gbf_final':                datos['gbf_final'],
        'mejor_alternativa_final':  datos['mejor_alternativa_final'],
        'n_criterios':              datos['n_criterios'],
        'n_alternativas':           datos['n_alternativas'],
    })


@algoritmos_aco_bp.get('/algoritmos/aco/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_plantilla_aco():
    n = int(request.args.get('criterios',    5))
    a = int(request.args.get('alternativas', 9))
    buffer = generar_plantilla_excel_aco(n, a)
    return send_file(buffer, as_attachment=True,
                     download_name='plantilla_aco.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@algoritmos_aco_bp.post('/algoritmos/aco/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_cargar_plantilla_aco():
    archivo = request.files.get('archivo')
    if archivo is None:
        return jsonify({'error': 'No se recibió archivo.'}), 400
    try:
        payload = parsear_plantilla_excel_aco(archivo)
        return jsonify(payload)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@algoritmos_aco_bp.post('/algoritmos/daaco')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_daaco():
    """DA-ACO — w pondera el índice de similitud DA (calculado una sola vez)."""
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        params  = validar_entrada_daaco(payload)
        datos = ejecutar_daaco(
            matriz=params['matriz'], w=params['w'], alpha=params['alpha'],
            beta=params['beta'], rho=params['rho'], Q=params['Q'],
            n_ants=params['n_ants'], T=params['T'], username=user.username,
        )
        ejecucion = guardar_ejecucion('DAACO', user.id, params, datos)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f'[api_calcular_daaco] Error: {e}')
        return jsonify({'error': 'Ocurrió un error al ejecutar el algoritmo.'}), 500

    return jsonify({
        'ejecucion_id':             ejecucion.id,
        'mejor_alternativa':        datos['mejor_alternativa'],
        'iteraciones':              datos['iteraciones'],
        'hora_inicio':              datos['hora_inicio'],
        'fecha_inicio':             datos['fecha_inicio'],
        'hora_finalizacion':        datos['hora_finalizacion'],
        'tiempo_ejecucion':         datos['tiempo_ejecucion'],
        'historico_gbf':            datos['historico_gbf'],
        'resultados_por_iteracion': datos['resultados_por_iteracion'],
        'gbf_final':                datos['gbf_final'],
        'mejor_alternativa_final':  datos['mejor_alternativa_final'],
        'n_criterios':              datos['n_criterios'],
        'n_alternativas':           datos['n_alternativas'],
    })


@algoritmos_aco_bp.get('/algoritmos/daaco/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_plantilla_daaco():
    n = int(request.args.get('criterios',    5))
    a = int(request.args.get('alternativas', 9))
    buffer = generar_plantilla_excel_daaco(n, a)
    return send_file(buffer, as_attachment=True,
                     download_name='plantilla_daaco.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@algoritmos_aco_bp.post('/algoritmos/daaco/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_cargar_plantilla_daaco():
    archivo = request.files.get('archivo')
    if archivo is None:
        return jsonify({'error': 'No se recibió archivo.'}), 400
    try:
        payload = parsear_plantilla_excel_daaco(archivo)
        return jsonify(payload)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@algoritmos_aco_bp.post('/algoritmos/mooraaco')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_mooraaco():
    """MOORA-ACO — w y EV (por criterio) ponderan el ranking MOORA inicial."""
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        params  = validar_entrada_mooraaco(payload)
        datos = ejecutar_mooraaco(
            matriz=params['matriz'], w=params['w'], EV=params['EV'],
            alpha=params['alpha'], beta=params['beta'], rho=params['rho'],
            Q=params['Q'], n_ants=params['n_ants'], T=params['T'],
            username=user.username,
        )
        ejecucion = guardar_ejecucion('MOORAACO', user.id, params, datos)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f'[api_calcular_mooraaco] Error: {e}')
        return jsonify({'error': 'Ocurrió un error al ejecutar el algoritmo.'}), 500

    return jsonify({
        'ejecucion_id':             ejecucion.id,
        'mejor_alternativa':        datos['mejor_alternativa'],
        'iteraciones':              datos['iteraciones'],
        'hora_inicio':              datos['hora_inicio'],
        'fecha_inicio':             datos['fecha_inicio'],
        'hora_finalizacion':        datos['hora_finalizacion'],
        'tiempo_ejecucion':         datos['tiempo_ejecucion'],
        'historico_gbf':            datos['historico_gbf'],
        'resultados_por_iteracion': datos['resultados_por_iteracion'],
        'gbf_final':                datos['gbf_final'],
        'mejor_alternativa_final':  datos['mejor_alternativa_final'],
        'n_criterios':              datos['n_criterios'],
        'n_alternativas':           datos['n_alternativas'],
    })


@algoritmos_aco_bp.get('/algoritmos/mooraaco/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_plantilla_mooraaco():
    n = int(request.args.get('criterios',    5))
    a = int(request.args.get('alternativas', 9))
    buffer = generar_plantilla_excel_mooraaco(n, a)
    return send_file(buffer, as_attachment=True,
                     download_name='plantilla_mooraaco.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@algoritmos_aco_bp.post('/algoritmos/mooraaco/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_cargar_plantilla_mooraaco():
    archivo = request.files.get('archivo')
    if archivo is None:
        return jsonify({'error': 'No se recibió archivo.'}), 400
    try:
        payload = parsear_plantilla_excel_mooraaco(archivo)
        return jsonify(payload)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
