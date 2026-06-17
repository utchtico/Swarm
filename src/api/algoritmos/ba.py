# src/api/algoritmos/ba.py
# API JSON del Bat Algorithm — recibe JSON, responde JSON.
# Endpoint de ejecución: /api/algoritmos/ba
# Endpoints de plantilla: /api/algoritmos/ba/plantilla
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
from src.algoritmos.ba import ejecutar_ba

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
