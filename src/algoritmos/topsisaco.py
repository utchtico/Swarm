# src/algoritmos/topsisaco.py
# TOPSIS-ACO — Technique for Order Preference by Similarity to Ideal
#              Solution (ranking, calculado una sola vez) + Ant Colony
#              Optimization (mecánica de búsqueda)
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Cambios respecto a la versión original:
#   1. Función pura y síncrona (sin async, sin I/O de archivos).
#   2. Matriz dinámica NxM: n y a derivados del input.
#   3. El bucle externo del original usaba una constante hardcodeada
#      itera_max=10 (ignorando cualquier input del usuario), mientras el
#      bucle interno sí usaba el parámetro n_iterations. Aquí ambos
#      bucles usan el mismo parámetro T, configurable — misma corrección
#      ya aplicada en DA-ACO y MOORA-ACO.
#   4. Todos los criterios se tratan como "beneficio" (igual que el
#      original, donde benefit_attributes incluía los 5 índices, y mismo
#      trato que TOPSIS-BA — no se expone como parámetro porque el
#      dataset fuente no varía este aspecto).
#   5. Igual semántica de "repeticiones independientes" que DA-ACO y
#      MOORA-ACO: el ranking TOPSIS se calcula una sola vez al inicio, y
#      cada una de las T repeticiones reinicializa la feromona a ese
#      mismo best_score y corre T pasos internos de ACO.

from datetime import datetime

import numpy as np
import pandas as pd


def ejecutar_topsisaco(matriz, w, alpha, beta, rho, Q, n_ants, T,
                       username: str = None, verbose: bool = False):
    """
    Ejecuta TOPSIS-ACO sobre una matriz de decisión de tamaño variable.

    Parámetros
    ----------
    matriz : list[list[float]]   filas = alternativas (a), columnas = criterios (n)
                                  todos los valores deben ser > 0 (ACO calcula 1/valor)
    w      : list[float]         peso por criterio (longitud n)
    alpha  : float                peso de la feromona
    beta   : float                peso de la heurística
    rho    : float                tasa de evaporación de feromona, (0, 1)
    Q      : float                cantidad de feromona depositada
    n_ants : int                  número de hormigas por paso interno de ACO
    T      : int                  número de repeticiones independientes (y
                                  también número de pasos internos de cada
                                  una, igual semántica que DA-ACO/MOORA-ACO)
    """
    hora_inicio  = datetime.now()
    fecha_inicio = hora_inicio.date()

    a         = len(matriz)
    n         = len(matriz[0])
    col_names = [f'C{i+1}' for i in range(n)]
    candidates = list(range(a))

    _log = print if verbose else (lambda *args, **kwargs: None)

    x = pd.DataFrame(matriz, columns=col_names, dtype=float)
    weights = pd.Series(w, index=col_names)
    benefit_attributes = set(range(n))  # todos los criterios son "beneficio"

    # ── TOPSIS: ranking calculado UNA SOLA VEZ ───────────────────────────
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
    ranking_topsis_inicial = [int(i) + 1 for i in orden.index]
    best_score = float(orden.iloc[0])  # mejor (menor) puntuación de proximidad

    _log("Ranking TOPSIS (una sola vez):", ranking_topsis_inicial, "| best_score =", best_score)
    _log("Configuración:", "alpha=", alpha, "beta=", beta, "rho=", rho,
         "Q=", Q, "n_ants=", n_ants, "T=", T)

    Resultados   = []
    historico_gbf = []

    def calcular_probabilidades(criterio, pheromone, heuristica):
        probabilidades = (pheromone[criterio] ** alpha) * (heuristica ** beta)
        probabilidades = np.nan_to_num(
            probabilidades, nan=0.0,
            posinf=np.nanmax(probabilidades) if np.isfinite(probabilidades).any() else 1.0)
        suma = np.sum(probabilidades)
        if suma == 0:
            return np.full(a, 1.0 / a)
        return probabilidades / suma

    # ── T repeticiones independientes, cada una con T pasos internos de ACO ──
    for repeticion in range(T):
        _log(f"\n=== REPETICIÓN {repeticion} (independiente, feromona reinicializada) ===")

        pheromone = np.ones((n, a)) * best_score

        for paso in range(T):
            heuristica = 1 / (x.values + 1e-10)
            for hormiga in range(n_ants):
                elecciones = []
                for criterio in range(n):
                    probabilidades = calcular_probabilidades(
                        criterio, pheromone, heuristica[:, criterio])
                    probabilidades = np.maximum(probabilidades, 0)
                    probabilidades /= np.sum(probabilidades)
                    elegida = int(np.random.choice(a, p=probabilidades))
                    elecciones.append(elegida)

                for criterio, elegida in enumerate(elecciones):
                    pheromone[criterio, elegida] += Q / (x.values[elegida, criterio] + 1e-10)

            pheromone *= (1 - rho)

        puntuacion_por_alternativa = np.sum(x.values.T * pheromone, axis=1)
        idx_mejor = int(np.argmax(puntuacion_por_alternativa))
        gbf_iter  = float(puntuacion_por_alternativa[idx_mejor])

        Resultados.append(idx_mejor + 1)
        historico_gbf.append(gbf_iter)
        _log("Mejor alternativa de la repetición =", idx_mejor + 1, "| puntuación =", gbf_iter)

    hora_fin         = datetime.now()
    tiempo_ejecucion = hora_fin - hora_inicio

    return {
        'mejor_alternativa':        Resultados[-10:],
        'iteraciones':              T,
        'hora_inicio':              hora_inicio.time().strftime('%H:%M:%S'),
        'fecha_inicio':             fecha_inicio.isoformat(),
        'hora_finalizacion':        hora_fin.time().strftime('%H:%M:%S'),
        'tiempo_ejecucion':         str(tiempo_ejecucion),
        'tiempo_ejecucion_seg':     tiempo_ejecucion.total_seconds(),
        'n_criterios':              n,
        'n_alternativas':           a,
        'criterios':                col_names,
        'alternativas_nombres':     [f'A{j+1}' for j in range(a)],
        'resultados_por_iteracion': Resultados,
        'historico_gbf':            [float(g) for g in historico_gbf],
        'gbf_final':                float(historico_gbf[-1]),
        'mejor_alternativa_final':  int(Resultados[-1]),
        'ranking_topsis_inicial':   ranking_topsis_inicial,
        'historiales': {
            'pheromone_final': pheromone.round(4).tolist(),
        },
    }
