# src/algoritmos/topsis.py
# TOPSIS — Technique for Order Preference by Similarity to Ideal Solution
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# A diferencia de TOPSIS-PSO/BA/ACO, este es el método MCDM puro: no hay
# metaheurística, no hay iteraciones — se calcula el ranking una sola vez
# y se devuelve directamente. Misma fórmula matemática que ya se usa como
# paso de ranking inicial en las variantes híbridas.
#
# La matriz de decisión es FIJA (no editable por el usuario, decisión
# confirmada): se muestra en el frontend para que el usuario vea con qué
# datos trabaja, pero solo el peso w es modificable.

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


def ejecutar_topsis(w, username: str = None, verbose: bool = False):
    """
    Ejecuta TOPSIS puro sobre la matriz de decisión fija del proyecto.

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
    benefit_attributes = set(range(n))  # todos los criterios son "beneficio"

    normalizado = x.copy()
    for i in range(n):
        col = col_names[i]
        if i in benefit_attributes:
            norm = np.linalg.norm(x[col])
        else:
            norm = np.linalg.norm(x[col], ord=1)
        normalizado[col] = x[col] / (norm if norm != 0 else 1e-9)

    ponderado = normalizado * weights
    ideal_best  = ponderado.max()
    ideal_worst = ponderado.min()

    s_best  = np.sqrt(((ponderado - ideal_best)  ** 2).sum(axis=1))
    s_worst = np.sqrt(((ponderado - ideal_worst) ** 2).sum(axis=1))
    denom = (s_best + s_worst).replace(0, 1e-9)
    puntuacion = s_worst / denom

    orden = puntuacion.sort_values(ascending=True)
    ranking = [int(i) + 1 for i in orden.index]
    puntuaciones_ordenadas = [float(v) for v in orden.values]

    _log("Ranking TOPSIS:", ranking)

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
