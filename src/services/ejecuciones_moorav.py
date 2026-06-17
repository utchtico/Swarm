# src/services/ejecuciones_moorav.py
# Validación y persistencia específicas de MOORA puro (MCDM, sin metaheurística).
#
# A diferencia de las familias PSO/BA/ACO, aquí no hay matriz editable ni
# iteraciones: la matriz es fija (ver MATRIZ_FIJA en src/algoritmos/moorav.py)
# y el único parámetro de entrada es w. EV está fijo a "Min" para los 5
# criterios (igual que el original, que nunca lo expuso como parámetro).
#
# Archivo propio, no comparte código con ejecuciones_topsis.py — mismo
# criterio de responsabilidad separada ya aplicado en PSO/BA/ACO.

from src.models.models import db, Ejecucion
from src.algoritmos.moorav import MATRIZ_FIJA

N_CRITERIOS = len(MATRIZ_FIJA[0])


def validar_entrada_moorav(payload: dict) -> dict:
    """
    Valida y normaliza el payload JSON del frontend para MOORA puro.

    Estructura esperada:
    {
      "w": [...]   # longitud N_CRITERIOS (5 en la matriz fija actual)
    }
    """
    if not isinstance(payload, dict):
        raise ValueError("El cuerpo de la petición debe ser un objeto JSON.")

    w = payload.get('w')
    if not isinstance(w, list):
        raise ValueError(f"'w' debe ser una lista numérica de longitud {N_CRITERIOS}.")
    if len(w) != N_CRITERIOS:
        raise ValueError(f"'w' debe tener un valor por criterio: longitud {N_CRITERIOS}, recibió {len(w)}.")
    try:
        w = [float(v) for v in w]
    except (TypeError, ValueError):
        raise ValueError("Todos los valores de 'w' deben ser numéricos.")

    return {'w': w}


def guardar_ejecucion_moorav(user_id: int, params: dict, datos: dict) -> Ejecucion:
    """
    Persiste el resultado de una ejecución de MOORA puro. No reutiliza
    guardar_ejecucion() de ejecuciones_pso.py porque ese contrato exige
    iteraciones/historico_gbf/resultados_por_iteracion, que aquí no existen:
    el ranking se calcula una sola vez, no iterativamente.

    user_id : id del usuario autenticado
    params  : dict de entrada validado (solo w)
    datos   : dict devuelto por ejecutar_moorav()
    """
    ejecucion = Ejecucion(
        algoritmo='MOORAV',
        fk_user=user_id,
        tiempo_ejecucion_seg=datos['tiempo_ejecucion_seg'],
        iteraciones=1,  # MCDM puro: una sola pasada, no T iteraciones
        n_criterios=datos['n_criterios'],
        n_alternativas=datos['n_alternativas'],
        gbf_final=datos['puntuaciones'][0] if datos.get('puntuaciones') else None,
        mejor_alternativa_final=datos.get('mejor_alternativa_final'),
        parametros={'w': params['w']},
        matriz_entrada={
            'n': datos['n_criterios'],
            'a': datos['n_alternativas'],
            'criterios': datos['criterios'],
            'alternativas': [f"A{i+1}" for i in range(datos['n_alternativas'])],
            'valores': datos['matriz'],
        },
        resultados=[
            {'orden': i + 1, 'alternativa': alt, 'puntuacion': datos['puntuaciones'][i]}
            for i, alt in enumerate(datos['mejor_alternativa'])
        ],
        historico_gbf=datos.get('puntuaciones', []),
        historiales=None,
    )
    db.session.add(ejecucion)
    db.session.commit()
    return ejecucion
