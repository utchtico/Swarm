# src/api/ejecucion/pso.py
# Lógica de ejecución de la familia PSO.
# Puentes legacy (form-data) para los templates actuales.
# Los endpoints JSON nuevos viven en src/api/algoritmos.py

from flask import jsonify, request, session

from src.api.auth import roles_required
from src.api.vistas.pso import pso_bp
from src.algoritmos.pso import ejecutar_pso
from src.algoritmos.dapso import ejecutar_dapso
from src.algoritmos.moorapso import ejecutar_moorapso
from src.algoritmos.topsispso import ejecutar_topsispso
from src.models.models import db, User
from src.services.ejecuciones import MATRIZ_DEFAULT, guardar_ejecucion, validar_entrada_pso


def _user():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None


def _legacy(nombre_algo, ejecutar_fn, tiene_r1r2=True):
    """Factory de rutas legacy para evitar duplicación."""
    user = _user()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401
    try:
        w_input = [request.form.get(f'w{i}', None) for i in range(1, 6)]
        if any(v is None or str(v).strip() == '' for v in w_input):
            return jsonify({'error': 'Faltan valores en w1..w5'}), 400
        base = {
            'matriz': MATRIZ_DEFAULT,
            'w':   [float(v) for v in w_input],
            'wwi': float(request.form['wwi']),
            'c1':  float(request.form['c1']),
            'c2':  float(request.form['c2']),
            'T':   int(request.form['T']),
            'r1':  [float(x.strip()) for x in request.form['r1'].split(',')] if tiene_r1r2 else [0]*5,
            'r2':  [float(x.strip()) for x in request.form['r2'].split(',')] if tiene_r1r2 else [0]*5,
        }
        params = validar_entrada_pso(base)
 
        # Construir kwargs según si el algoritmo acepta r1/r2
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
        return jsonify({
            'ejecucion_id':      ejecucion.id,
            'mejor_alternativa': datos['mejor_alternativa'],
            'iteraciones':       datos['iteraciones'],
            'hora_inicio':       datos['hora_inicio'],
            'fecha_inicio':      datos['fecha_inicio'],
            'hora_finalizacion': datos['hora_finalizacion'],
            'tiempo_ejecucion':  datos['tiempo_ejecucion'],
            'historico_gbf':     datos['historico_gbf'],
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@pso_bp.post('/pso')
@roles_required('user', 'admin', 'superadmin')
def calcular_pso():
    return _legacy('PSO', ejecutar_pso, tiene_r1r2=True)


@pso_bp.post('/dapso')
@roles_required('user', 'admin', 'superadmin')
def calcular_dapso():
    return _legacy('DAPSO', ejecutar_dapso, tiene_r1r2=False)


@pso_bp.post('/moorapso')
@roles_required('user', 'admin', 'superadmin')
def calcular_moorapso():
    return _legacy('MOORAPSO', ejecutar_moorapso, tiene_r1r2=False)

@pso_bp.post('/topsispso')
@roles_required('user', 'admin', 'superadmin')
def calcular_topsispso():
    return _legacy('TOPSISPSO', ejecutar_topsispso, tiene_r1r2=False)
 