# src/api/ejecuciones.py
# Endpoints de historial de ejecuciones — genéricos, independientes del algoritmo.
# No conocen wwi/c1/c2/r1/r2/alpha/gamma; solo leen el modelo Ejecucion por su
# campo `algoritmo` (string) y los campos estándar del contrato de retorno.

from flask import Blueprint, jsonify, request, send_file, session

from src.api.auth import roles_required
from src.models.models import db, Ejecucion
from src.services.ejecuciones_pso import exportar_ejecucion_excel

ejecuciones_bp = Blueprint('ejecuciones_api', __name__, url_prefix='/api')


# ── Historial de ejecuciones ─────────────────────────────────────────────────

@ejecuciones_bp.get('/ejecuciones')
@roles_required('user', 'admin', 'superadmin')
def api_listar_ejecuciones():
    rol = session.get('role')
    uid = session.get('user_id')
    q   = Ejecucion.query

    # Filtrar por algoritmo
    algoritmo = request.args.get('algoritmo')
    if algoritmo:
        q = q.filter(Ejecucion.algoritmo == algoritmo.upper())

    # Control de acceso: user solo ve las suyas; admin/superadmin ven todas
    if rol == 'user':
        q = q.filter(Ejecucion.fk_user == uid)

    limit       = min(int(request.args.get('limit', 50)), 200)
    ejecuciones = q.order_by(Ejecucion.fecha_ejecucion.desc()).limit(limit).all()
    return jsonify([e.to_dict_resumen() for e in ejecuciones])


@ejecuciones_bp.get('/ejecuciones/<int:ejecucion_id>')
@roles_required('user', 'admin', 'superadmin')
def api_detalle_ejecucion(ejecucion_id):
    ejecucion = db.session.get(Ejecucion, ejecucion_id)
    if ejecucion is None:
        return jsonify({'error': 'Ejecución no encontrada.'}), 404
    # Solo el dueño o admin puede ver el detalle
    if (session.get('role') == 'user'
            and ejecucion.fk_user != session.get('user_id')):
        return jsonify({'error': 'Sin permiso.'}), 403
    detalle = ejecucion.to_dict_resumen()
    detalle.update({
        'parametros':      ejecucion.parametros,
        'matriz_entrada':  ejecucion.matriz_entrada,
        'resultados':      ejecucion.resultados,
        'historico_gbf':   ejecucion.historico_gbf,
    })
    return jsonify(detalle)


@ejecuciones_bp.get('/ejecuciones/<int:ejecucion_id>/excel')
@roles_required('user', 'admin', 'superadmin')
def api_descargar_excel(ejecucion_id):
    ejecucion = db.session.get(Ejecucion, ejecucion_id)
    if ejecucion is None:
        return jsonify({'error': 'Ejecución no encontrada.'}), 404
    if (session.get('role') == 'user'
            and ejecucion.fk_user != session.get('user_id')):
        return jsonify({'error': 'Sin permiso.'}), 403
    try:
        buffer = exportar_ejecucion_excel(ejecucion_id)
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    nombre = (f"{ejecucion.algoritmo}_{ejecucion.id}_"
              f"{ejecucion.fecha_ejecucion.strftime('%Y%m%d_%H%M%S')}.xlsx")
    return send_file(buffer, as_attachment=True, download_name=nombre,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')