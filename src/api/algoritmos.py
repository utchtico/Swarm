# src/api/algoritmos.py
# Blueprint de la API JSON de algoritmos.
#
# Contrato: recibe JSON, responde JSON. Cero render_template.
# Este es el contrato que un futuro frontend en React consumiría sin
# cambiar una línea del backend. Las rutas viejas de main.py siguen
# intactas hasta validar el piloto.

from flask import Blueprint, jsonify, request, send_file, session

from src.algoritmos.pso import ejecutar_pso
from src.api.auth import roles_required
from src.models.models import db, Ejecucion, User
from src.services.ejecuciones import (
    exportar_ejecucion_excel,
    generar_plantilla_excel,
    guardar_ejecucion,
    parsear_plantilla_excel,
    validar_entrada_pso,
)

algoritmos_bp = Blueprint('algoritmos_api', __name__, url_prefix='/api')


def _usuario_actual():
    uid = session.get('user_id')
    if not uid:
        return None
    return db.session.get(User, uid)


@algoritmos_bp.post('/algoritmos/pso')
@roles_required('user', 'admin', 'superadmin')
def api_calcular_pso():
    """
    Ejecuta PSO con matriz de decisión dinámica.

    Body JSON:
    {
      "matriz": [[0.048, 0.047, ...], ...],   # a>=9 filas, n>=5 columnas
      "w":  [0.4, 0.2, 0.03, 0.07, 0.3],       # longitud n
      "wwi": 0.7, "c1": 2.5, "c2": 2.5, "T": 10,
      "r1": [...], "r2": [...]                  # longitud n
    }
    """
    user = _usuario_actual()
    if user is None:
        return jsonify({'error': 'Sesión inválida.'}), 401

    try:
        params = validar_entrada_pso(request.get_json(silent=True))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        datos = ejecutar_pso(
            matriz=params['matriz'], w=params['w'],
            wwi=params['wwi'], c1=params['c1'], c2=params['c2'],
            T=params['T'], r1=params['r1'], r2=params['r2'],
            username=user.username,
        )
        ejecucion = guardar_ejecucion('PSO', user.id, params, datos)
    except Exception as e:
        db.session.rollback()
        print(f'[api_calcular_pso] Error: {e}')
        return jsonify({'error': 'Ocurrió un error al ejecutar el algoritmo.'}), 500

    return jsonify({
        'ejecucion_id': ejecucion.id,
        # Compatibilidad con el frontend actual:
        'mejor_alternativa': datos['mejor_alternativa'],
        'iteraciones': datos['iteraciones'],
        'hora_inicio': datos['hora_inicio'],
        'fecha_inicio': datos['fecha_inicio'],
        'hora_finalizacion': datos['hora_finalizacion'],
        'tiempo_ejecucion': datos['tiempo_ejecucion'],
        # Para las gráficas post-ejecución:
        'historico_gbf': datos['historico_gbf'],
        'resultados_por_iteracion': datos['resultados_por_iteracion'],
        'gbf_final': datos['gbf_final'],
        'mejor_alternativa_final': datos['mejor_alternativa_final'],
        'n_criterios': datos['n_criterios'],
        'n_alternativas': datos['n_alternativas'],
    })


@algoritmos_bp.get('/algoritmos/pso/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_plantilla():
    """Machote de Excel para capturar el experimento offline."""
    try:
        n = int(request.args.get('criterios', 5))
        a = int(request.args.get('alternativas', 9))
    except ValueError:
        return jsonify({'error': 'criterios y alternativas deben ser enteros.'}), 400
    buffer = generar_plantilla_excel(n, a)
    return send_file(
        buffer, as_attachment=True,
        download_name='plantilla_pso.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@algoritmos_bp.post('/algoritmos/pso/plantilla')
@roles_required('user', 'admin', 'superadmin')
def api_cargar_plantilla():
    """
    Recibe el machote llenado y devuelve el payload parseado (sin ejecutar):
    el frontend lo usa para poblar la interfaz y el usuario revisa antes
    de presionar Calcular.
    """
    archivo = request.files.get('archivo')
    if archivo is None or archivo.filename == '':
        return jsonify({'error': 'No se recibió ningún archivo.'}), 400
    if not archivo.filename.lower().endswith('.xlsx'):
        return jsonify({'error': 'El archivo debe ser un .xlsx.'}), 400
    try:
        payload = parsear_plantilla_excel(archivo)
        params = validar_entrada_pso(payload)  # misma validación que la ejecución
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify(params)


@algoritmos_bp.get('/ejecuciones')
@roles_required('user', 'admin', 'superadmin')
def api_listar_ejecuciones():
    """
    Lista ejecuciones para el módulo de comparación.
    Filtros opcionales: ?algoritmo=PSO&mias=1&limit=50
    """
    q = Ejecucion.query
    algoritmo = request.args.get('algoritmo')
    if algoritmo:
        q = q.filter(Ejecucion.algoritmo == algoritmo.upper())
    if request.args.get('mias') == '1':
        q = q.filter(Ejecucion.fk_user == session.get('user_id'))

    limit = min(int(request.args.get('limit', 50)), 200)
    ejecuciones = q.order_by(Ejecucion.fecha_ejecucion.desc()).limit(limit).all()
    return jsonify([e.to_dict_resumen() for e in ejecuciones])


@algoritmos_bp.get('/ejecuciones/<int:ejecucion_id>')
@roles_required('user', 'admin', 'superadmin')
def api_detalle_ejecucion(ejecucion_id):
    """Detalle completo de una ejecución (para gráficas y comparaciones)."""
    ejecucion = db.session.get(Ejecucion, ejecucion_id)
    if ejecucion is None:
        return jsonify({'error': 'Ejecución no encontrada.'}), 404
    detalle = ejecucion.to_dict_resumen()
    detalle.update({
        'parametros': ejecucion.parametros,
        'matriz_entrada': ejecucion.matriz_entrada,
        'resultados': ejecucion.resultados,
        'historico_gbf': ejecucion.historico_gbf,
    })
    return jsonify(detalle)


@algoritmos_bp.get('/ejecuciones/<int:ejecucion_id>/excel')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_excel(ejecucion_id):
    """Exportación a Excel bajo demanda, reconstruida desde PostgreSQL."""
    try:
        buffer = exportar_ejecucion_excel(ejecucion_id)
    except LookupError as e:
        return jsonify({'error': str(e)}), 404

    ejecucion = db.session.get(Ejecucion, ejecucion_id)
    nombre = (f"{ejecucion.algoritmo}_{ejecucion.id}_"
              f"{ejecucion.fecha_ejecucion.strftime('%Y%m%d_%H%M%S')}.xlsx")
    return send_file(
        buffer,
        as_attachment=True,
        download_name=nombre,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )