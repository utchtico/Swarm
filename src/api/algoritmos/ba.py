# src/api/algoritmos/ba.py
# API JSON de la familia BA — recibe JSON, responde JSON.
# Endpoints de ejecución: /api/algoritmos/{ba,daba}
# Endpoints de plantilla: /api/algoritmos/{ba,daba}/plantilla
#
# El historial de ejecuciones (genérico) vive en src/api/ejecuciones.py.

from flask import Blueprint, jsonify, request, send_file, session

from src.api.auth import roles_required
from src.models.models import db, User
from src.services.ejecuciones_ba import (
    generar_plantilla_excel_ba,
    guardar_ejecucion,
    parsear_plantilla_excel_ba,
    validar_entrada_ba,
)
from src.services.ejecuciones_daba import (
    generar_plantilla_excel_daba,
    parsear_plantilla_excel_daba,
    validar_entrada_daba,
)
from src.services.ejecuciones_mooraba import (
    generar_plantilla_excel_mooraba,
    parsear_plantilla_excel_mooraba,
    validar_entrada_mooraba,
)
from src.services.ejecuciones_topsisba import (
    generar_plantilla_excel_topsisba,
    parsear_plantilla_excel_topsisba,
    validar_entrada_topsisba,
)
from src.algoritmos.ba import ejecutar_ba
from src.algoritmos.daba import ejecutar_daba
from src.algoritmos.mooraba import ejecutar_mooraba
from src.algoritmos.topsisba import ejecutar_topsisba

algoritmos_ba_bp = Blueprint('algoritmos_ba_api', __name__, url_prefix='/api')


def _usuario_actual():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None


@algoritmos_ba_bp.post('/algoritmos/ba')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_ba():
    """BA — alpha y gamma son definidos por el usuario; sin w, r1, r2."""
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        params  = validar_entrada_ba(payload)
        datos = ejecutar_ba(
            matriz=params['matriz'], alpha=params['alpha'],
            gamma=params['gamma'], T=params['T'], username=user.username,
        )
        ejecucion = guardar_ejecucion('BA', user.id, params, datos)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f'[api_calcular_ba] Error: {e}')
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


@algoritmos_ba_bp.get('/algoritmos/ba/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_plantilla_ba():
    n = int(request.args.get('criterios',    5))
    a = int(request.args.get('alternativas', 9))
    buffer = generar_plantilla_excel_ba(n, a)
    return send_file(buffer, as_attachment=True,
                     download_name='plantilla_ba.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@algoritmos_ba_bp.post('/algoritmos/ba/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_cargar_plantilla_ba():
    archivo = request.files.get('archivo')
    if archivo is None:
        return jsonify({'error': 'No se recibió archivo.'}), 400
    try:
        payload = parsear_plantilla_excel_ba(archivo)
        return jsonify(payload)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@algoritmos_ba_bp.post('/algoritmos/daba')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_daba():
    """DA-BA — w pondera el índice de similitud DA; alpha/gamma controlan BA."""
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        params  = validar_entrada_daba(payload)
        datos = ejecutar_daba(
            matriz=params['matriz'], w=params['w'], alpha=params['alpha'],
            gamma=params['gamma'], T=params['T'], username=user.username,
        )
        ejecucion = guardar_ejecucion('DABA', user.id, params, datos)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f'[api_calcular_daba] Error: {e}')
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


@algoritmos_ba_bp.get('/algoritmos/daba/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_plantilla_daba():
    n = int(request.args.get('criterios',    5))
    a = int(request.args.get('alternativas', 9))
    buffer = generar_plantilla_excel_daba(n, a)
    return send_file(buffer, as_attachment=True,
                     download_name='plantilla_daba.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@algoritmos_ba_bp.post('/algoritmos/daba/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_cargar_plantilla_daba():
    archivo = request.files.get('archivo')
    if archivo is None:
        return jsonify({'error': 'No se recibió archivo.'}), 400
    try:
        payload = parsear_plantilla_excel_daba(archivo)
        return jsonify(payload)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@algoritmos_ba_bp.post('/algoritmos/mooraba')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_mooraba():
    """MOORA-BA — w pondera la puntuación MOORA; alpha/gamma controlan BA."""
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        params  = validar_entrada_mooraba(payload)
        datos = ejecutar_mooraba(
            matriz=params['matriz'], w=params['w'], alpha=params['alpha'],
            gamma=params['gamma'], T=params['T'], username=user.username,
        )
        ejecucion = guardar_ejecucion('MOORABA', user.id, params, datos)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f'[api_calcular_mooraba] Error: {e}')
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


@algoritmos_ba_bp.get('/algoritmos/mooraba/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_plantilla_mooraba():
    n = int(request.args.get('criterios',    5))
    a = int(request.args.get('alternativas', 9))
    buffer = generar_plantilla_excel_mooraba(n, a)
    return send_file(buffer, as_attachment=True,
                     download_name='plantilla_mooraba.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@algoritmos_ba_bp.post('/algoritmos/mooraba/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_cargar_plantilla_mooraba():
    archivo = request.files.get('archivo')
    if archivo is None:
        return jsonify({'error': 'No se recibió archivo.'}), 400
    try:
        payload = parsear_plantilla_excel_mooraba(archivo)
        return jsonify(payload)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@algoritmos_ba_bp.post('/algoritmos/topsisba')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_topsisba():
    """TOPSIS-BA — w pondera la puntuación TOPSIS; alpha/gamma controlan BA."""
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        params  = validar_entrada_topsisba(payload)
        datos = ejecutar_topsisba(
            matriz=params['matriz'], w=params['w'], alpha=params['alpha'],
            gamma=params['gamma'], T=params['T'], username=user.username,
        )
        ejecucion = guardar_ejecucion('TOPSISBA', user.id, params, datos)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f'[api_calcular_topsisba] Error: {e}')
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


@algoritmos_ba_bp.get('/algoritmos/topsisba/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_plantilla_topsisba():
    n = int(request.args.get('criterios',    5))
    a = int(request.args.get('alternativas', 9))
    buffer = generar_plantilla_excel_topsisba(n, a)
    return send_file(buffer, as_attachment=True,
                     download_name='plantilla_topsisba.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@algoritmos_ba_bp.post('/algoritmos/topsisba/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_cargar_plantilla_topsisba():
    archivo = request.files.get('archivo')
    if archivo is None:
        return jsonify({'error': 'No se recibió archivo.'}), 400
    try:
        payload = parsear_plantilla_excel_topsisba(archivo)
        return jsonify(payload)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
