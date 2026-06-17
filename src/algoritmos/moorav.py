# src/algoritmos/moorav.py
# MOORA — Multi-Objective Optimization by Ratio Analysis
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Igual que TOPSIS puro: no hay metaheurística, no hay iteraciones — se
# calcula el ranking una sola vez y se devuelve directamente.
#
# La matriz de decisión es FIJA (no editable, mismo criterio que TOPSIS
# puro): se muestra en el frontend de solo lectura. EV (evaluación
# cardinal Max/Min) también está fijo a "Min" para los 5 criterios,
# igual que en el original — el HTML legacy nunca lo expuso como
# parámetro (a diferencia de MOORA-ACO, donde sí se hizo configurable
# por venir ya como parámetro en esa firma). El único input del usuario
# es w.

from datetime import datetime

import numpy as np
import pandas as pd

MATRIZ_FIJA = [
    [0.048, 0.047, 0.070, 0.087, 0.190],
    [0.053, 0.052, 0.066, 0.081, 0.058],
    [0.057, 0.057, 0.066, 0.076, 0.022],
    [0.062, 0.062, 0.063, 0.058, 0.007],
    [0.066, 0.066, 0.070, 0.085, 0.004],
    [0.070, 0.071, 0.066, 0.058, 0.003],
    [0.075, 0.075, 0.066, 0.047, 0.002],
    [0.079, 0.079, 0.066, 0.035, 0.002],
    [0.083, 0.083, 0.066, 0.051, 0.000],
]

EV_FIJO = ['Min'] * len(MATRIZ_FIJA[0])


def ejecutar_moorav(w, username: str = None, verbose: bool = False):
    """
    Ejecuta MOORA puro sobre la matriz de decisión fija del proyecto.

    Parámetros
    ----------
    w : list[float]   peso por criterio (longitud 5, una por columna de
                       la matriz fija)
    """
    hora_inicio  = datetime.now()
    fecha_inicio = hora_inicio.date()

    n = len(MATRIZ_FIJA[0])
    a = len(MATRIZ_FIJA)
    col_names = [f'C{i+1}' for i in range(n)]

    if len(w) != n:
        raise ValueError(f"'w' debe tener {n} valores (uno por criterio), recibió {len(w)}.")

    _log = print if verbose else (lambda *args, **kwargs: None)

    x = pd.DataFrame(MATRIZ_FIJA, columns=col_names, dtype=float)
    weights = pd.Series(w, index=col_names)

    norm_factor = np.sqrt((x ** 2).sum(axis=1))
    normalizado = x.div(norm_factor.replace(0, 1e-9), axis=0)
    ponderado = normalizado * weights

    signo = pd.Series([1.0 if ev == 'Max' else -1.0 for ev in EV_FIJO], index=col_names)
    puntuacion_global = (ponderado * signo).sum(axis=1)

    orden = puntuacion_global.sort_values(ascending=False)
    ranking = [int(i) + 1 for i in orden.index]
    puntuaciones_ordenadas = [float(v) for v in orden.values]

    _log("Ranking MOORA:", ranking)

    hora_fin         = datetime.now()
    tiempo_ejecucion = hora_fin - hora_inicio

    return {
        'mejor_alternativa':       ranking,
        'puntuaciones':            puntuaciones_ordenadas,
        'mejor_alternativa_final': ranking[0],
        'hora_inicio':             hora_inicio.time().strftime('%H:%M:%S'),
        'fecha_inicio':            fecha_inicio.isoformat(),
        'hora_finalizacion':       hora_fin.time().strftime('%H:%M:%S'),
        'tiempo_ejecucion':        str(tiempo_ejecucion),
        'tiempo_ejecucion_seg':    tiempo_ejecucion.total_seconds(),
        'n_criterios':             n,
        'n_alternativas':          a,
        'criterios':               col_names,
        'matriz':                  MATRIZ_FIJA,
    }
