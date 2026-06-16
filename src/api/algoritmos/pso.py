# src/api/algoritmos_pso.py
# API JSON de la familia PSO — recibe JSON, responde JSON.
# Endpoints de ejecución: /api/algoritmos/{pso,dapso,moorapso,topsispso}
# Endpoints de plantilla: /api/algoritmos/pso/plantilla
#
# El historial de ejecuciones (genérico, no específico de PSO) vive en
# src/api/ejecuciones.py — ese módulo no sabe nada de wwi/c1/c2/r1/r2.

from flask import Blueprint, jsonify, request, send_file, session

from src.api.auth import roles_required
from src.models.models import db, User
from src.services.ejecuciones_pso import (
    exportar_ejecucion_excel,
    generar_plantilla_excel,
    guardar_ejecucion,
    parsear_plantilla_excel,
    validar_entrada_pso,
)
from src.algoritmos.pso import ejecutar_pso
from src.algoritmos.dapso import ejecutar_dapso
from src.algoritmos.moorapso import ejecutar_moorapso
from src.algoritmos.topsispso import ejecutar_topsispso

algoritmos_bp = Blueprint('algoritmos_api', __name__, url_prefix='/api')


def _usuario_actual():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None


def _ejecutar_familia_pso(nombre_algo, ejecutar_fn, tiene_r1r2=True):
    """Helper compartido para endpoints de la familia PSO."""
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        payload = request.get_json(silent=True) or {}
        n_col   = len(payload.get('matriz', [[]])[0]) if payload.get('matriz') else 5
        params  = validar_entrada_pso({
            **payload,
            'r1': payload.get('r1', [0]*n_col),
            'r2': payload.get('r2', [0]*n_col),
        })
        kwargs = dict(matriz=params['matriz'], w=params['w'],
                      wwi=params['wwi'], c1=params['c1'],
                      c2=params['c2'], T=params['T'],
                      username=user.username)
        if tiene_r1r2:
            kwargs['r1'] = params['r1']
            kwargs['r2'] = params['r2']

        datos = ejecutar_fn(**kwargs)
        omitir = () if tiene_r1r2 else ('r1', 'r2')
        ejecucion = guardar_ejecucion(nombre_algo, user.id,
                                      {k: v for k, v in params.items()
                                       if k not in omitir}, datos)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f'[api_{nombre_algo.lower()}] Error: {e}')
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


# ── Familia PSO ──────────────────────────────────────────────────────────────

@algoritmos_bp.post('/algoritmos/pso')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_pso():
    """PSO — r1 y r2 son definidos por el usuario."""
    return _ejecutar_familia_pso('PSO', ejecutar_pso, tiene_r1r2=True)


@algoritmos_bp.post('/algoritmos/dapso')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_dapso():
    """DA-PSO — r1 y r2 se derivan del ranking DA."""
    return _ejecutar_familia_pso('DAPSO', ejecutar_dapso, tiene_r1r2=False)


@algoritmos_bp.post('/algoritmos/moorapso')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_moorapso():
    """MOORA-PSO — r1 y r2 se derivan del ranking MOORA."""
    return _ejecutar_familia_pso('MOORAPSO', ejecutar_moorapso, tiene_r1r2=False)


@algoritmos_bp.post('/algoritmos/topsispso')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_topsispso():
    """TOPSIS-PSO — r1 y r2 se derivan del ranking TOPSIS."""
    return _ejecutar_familia_pso('TOPSISPSO', ejecutar_topsispso, tiene_r1r2=False)


# ── Plantilla Excel ──────────────────────────────────────────────────────────
# La ruta incluye el algoritmo para que la plantilla generada y la validación
# de carga sean conscientes de la variante (PSO sí usa R1/R2; las demás no).

ALGORITMOS_VALIDOS_PLANTILLA = {'pso', 'dapso', 'moorapso', 'topsispso'}


@algoritmos_bp.get('/algoritmos/<algoritmo>/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_plantilla(algoritmo):
    algoritmo = algoritmo.lower()
    if algoritmo not in ALGORITMOS_VALIDOS_PLANTILLA:
        return jsonify({'error': f"Algoritmo '{algoritmo}' no reconocido."}), 404

    n = int(request.args.get('criterios',    5))
    a = int(request.args.get('alternativas', 9))
    buffer = generar_plantilla_excel(n, a, algoritmo=algoritmo.upper())
    return send_file(buffer, as_attachment=True,
                     download_name=f'plantilla_{algoritmo}.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@algoritmos_bp.post('/algoritmos/<algoritmo>/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_cargar_plantilla(algoritmo):
    algoritmo = algoritmo.lower()
    if algoritmo not in ALGORITMOS_VALIDOS_PLANTILLA:
        return jsonify({'error': f"Algoritmo '{algoritmo}' no reconocido."}), 404

    archivo = request.files.get('archivo')
    if archivo is None:
        return jsonify({'error': 'No se recibió archivo.'}), 400
    try:
        payload = parsear_plantilla_excel(archivo, algoritmo_esperado=algoritmo.upper())
        return jsonify(payload)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400