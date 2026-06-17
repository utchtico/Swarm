# src/api/algoritmos/moorav.py
# API JSON de MOORA puro (MCDM, sin metaheurística) — recibe JSON,
# responde JSON. Endpoint de ejecución: /api/algoritmos/moorav
#
# Específico de MOORA. Archivo propio, no comparte código con
# src/api/algoritmos/topsis.py — mismo criterio de responsabilidad
# separada ya aplicado en PSO/BA/ACO.
#
# El historial de ejecuciones (genérico) vive en src/api/ejecuciones.py.
# A diferencia de PSO/BA/ACO, MOORA puro no tiene matriz editable ni
# parámetros de iteración — la matriz es fija y el único input es w.

from flask import Blueprint, jsonify, request, session

from src.api.auth import roles_required
from src.models.models import db, User
from src.services.ejecuciones_moorav import guardar_ejecucion_moorav, validar_entrada_moorav
from src.algoritmos.moorav import MATRIZ_FIJA, ejecutar_moorav

algoritmos_moorav_bp = Blueprint('algoritmos_moorav_api', __name__, url_prefix='/api')


def _usuario_actual():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None


@algoritmos_moorav_bp.get('/algoritmos/moorav/matriz')
@roles_required('user', 'admin', 'superadmin')
def api_obtener_matriz_moorav():
    """
    Expone la matriz fija y sus criterios para que el frontend la pinte
    de solo lectura, sin ejecutar el algoritmo ni persistir nada. Mismo
    patrón que /api/algoritmos/topsis/matriz.
    """
    return jsonify({
        'matriz': MATRIZ_FIJA,
        'criterios': [f'C{i+1}' for i in range(len(MATRIZ_FIJA[0]))],
        'n_criterios': len(MATRIZ_FIJA[0]),
        'n_alternativas': len(MATRIZ_FIJA),
    })


@algoritmos_moorav_bp.post('/algoritmos/moorav')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_moorav():
    """MOORA puro — solo w es definido por el usuario; matriz y EV fijos."""
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        params  = validar_entrada_moorav(payload)
        datos = ejecutar_moorav(w=params['w'], username=user.username)
        ejecucion = guardar_ejecucion_moorav(user.id, params, datos)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f'[api_calcular_moorav] Error: {e}')
        return jsonify({'error': 'Ocurrió un error al ejecutar el algoritmo.'}), 500

    return jsonify({
        'ejecucion_id':             ejecucion.id,
        'mejor_alternativa':        datos['mejor_alternativa'],
        'puntuaciones':             datos['puntuaciones'],
        'mejor_alternativa_final':  datos['mejor_alternativa_final'],
        'hora_inicio':              datos['hora_inicio'],
        'fecha_inicio':             datos['fecha_inicio'],
        'hora_finalizacion':        datos['hora_finalizacion'],
        'tiempo_ejecucion':         datos['tiempo_ejecucion'],
        'n_criterios':              datos['n_criterios'],
        'n_alternativas':           datos['n_alternativas'],
        'matriz':                   datos['matriz'],
    })
