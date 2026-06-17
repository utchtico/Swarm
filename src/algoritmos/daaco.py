# src/algoritmos/daaco.py
# DA-ACO — Análisis Dimensional (ranking, calculado una sola vez) +
#          Ant Colony Optimization (mecánica de búsqueda)
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Cambios respecto a la versión original:
#   1. Función pura y síncrona (sin async, sin I/O de archivos).
#   2. Matriz dinámica NxM: n y a derivados del input.
#   3. 'w' sí se usa: pondera el índice de similitud del Análisis
#      Dimensional, igual patrón que en DA-BA.
#   4. Retorna historiales completos para persistencia, gráficas y Excel.
#
# IMPORTANTE — semántica confirmada con el equipo de investigación, fiel
# al original: a diferencia de DA-BA (donde el ranking DA se recalcula en
# CADA iteración), aquí el ranking DA se calcula UNA SOLA VEZ al inicio,
# y ese resultado (best_score) inicializa la feromona de TODAS las
# repeticiones de ACO por igual. La estructura de "T repeticiones" no es
# una optimización progresiva de T*T pasos acumulados: cada una de las T
# repeticiones es una corrida INDEPENDIENTE y completa de ACO (con la
# feromona reinicializada a best_score al comenzar, y T pasos internos de
# evaporación/refuerzo), usada para observar la consistencia del resultado
# bajo la misma condición inicial — no para refinarlo progresivamente.
# Por eso 'historico_gbf' y 'resultados_por_iteracion' aquí representan T
# corridas independientes, no T pasos de un mismo proceso acumulativo.

from datetime import datetime

import numpy as np
import pandas as pd


def ejecutar_daaco(matriz, w, alpha, beta, rho, Q, n_ants, T,
                   username: str = None, verbose: bool = False):
    """
    Ejecuta DA-ACO sobre una matriz de decisión de tamaño variable.

    Parámetros
    ----------
    matriz : list[list[float]]   filas = alternativas (a), columnas = criterios (n)
    w      : list[float]         peso por criterio (longitud n) — pondera el
                                  índice de similitud del Análisis Dimensional
    alpha  : float                peso de la feromona en la probabilidad de elección
    beta   : float                peso de la heurística en la probabilidad de elección
    rho    : float                tasa de evaporación de feromona, (0, 1)
    Q      : float                cantidad de feromona depositada por elección
    n_ants : int                  número de hormigas por paso interno de ACO
    T      : int                  número de REPETICIONES independientes del
                                  experimento de ACO (cada una con T pasos
                                  internos también, fiel al original)
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

    # ── Análisis Dimensional: ranking calculado UNA SOLA VEZ ────────────────
    solucion_ideal = x.mean(axis=0)
    razon = (x / solucion_ideal).abs()
    ponderado = razon.pow(weights.abs(), axis=1)
    indice_similitud = ponderado.prod(axis=1)

    orden = indice_similitud.sort_values(ascending=True)
    ranking_da_inicial = [int(i) + 1 for i in orden.index]
    best_score = float(orden.iloc[0])  # mejor (menor) índice de similitud

    _log("Ranking DA (una sola vez):", ranking_da_inicial, "| best_score =", best_score)
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

        # Feromona reinicializada con el mismo best_score en cada repetición
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
        'ranking_da_inicial':       ranking_da_inicial,
        'historiales': {
            'pheromone_final': pheromone.round(4).tolist(),
        },
    }
