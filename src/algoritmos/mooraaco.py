# src/algoritmos/mooraaco.py
# MOORA-ACO — Multi-Objective Optimization by Ratio Analysis (ranking,
#             calculado una sola vez) + Ant Colony Optimization (mecánica
#             de búsqueda)
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Cambios respecto a la versión original:
#   1. Función pura y síncrona (sin async, sin I/O de archivos).
#   2. Matriz dinámica NxM: n y a derivados del input.
#   3. EV (evaluación cardinal Max/Min) se vuelve configurable POR
#      CRITERIO, no un solo selector global como en el HTML original
#      (que aplicaba el mismo Min/Max a los 5 criterios por igual). Es
#      un cambio de diseño confirmado, más flexible que el original.
#   4. El bucle externo del original usaba una constante hardcodeada
#      itera_max=10 (ignorando cualquier input del usuario), mientras el
#      bucle interno sí usaba el parámetro n_iterations. Aquí ambos
#      bucles usan el mismo parámetro T, configurable — corrección
#      confirmada, no la asimetría original.
#   5. Igual semántica de "repeticiones independientes" que DA-ACO: el
#      ranking MOORA se calcula una sola vez al inicio, y cada una de
#      las T repeticiones reinicializa la feromona a ese mismo best_score
#      y corre T pasos internos de ACO — no es una optimización progresiva
#      acumulativa, sino T corridas independientes bajo la misma
#      condición inicial.

from datetime import datetime

import numpy as np
import pandas as pd


def ejecutar_mooraaco(matriz, w, EV, alpha, beta, rho, Q, n_ants, T,
                      username: str = None, verbose: bool = False):
    """
    Ejecuta MOORA-ACO sobre una matriz de decisión de tamaño variable.

    Parámetros
    ----------
    matriz : list[list[float]]   filas = alternativas (a), columnas = criterios (n)
                                  todos los valores deben ser > 0 (ACO calcula 1/valor)
    w      : list[float]         peso por criterio (longitud n)
    EV     : list[str]           "Max" o "Min" por criterio (longitud n) —
                                  configurable por criterio, a diferencia del
                                  selector global del HTML original
    alpha  : float                peso de la feromona
    beta   : float                peso de la heurística
    rho    : float                tasa de evaporación de feromona, (0, 1)
    Q      : float                cantidad de feromona depositada
    n_ants : int                  número de hormigas por paso interno de ACO
    T      : int                  número de repeticiones independientes (y
                                  también número de pasos internos de cada
                                  una, igual semántica que DA-ACO)
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

    # ── MOORA: ranking calculado UNA SOLA VEZ ────────────────────────────
    norm_factor = np.sqrt((x ** 2).sum(axis=1))
    normalizado = x.div(norm_factor.replace(0, 1e-9), axis=0)
    ponderado = normalizado * weights

    signo = pd.Series([1.0 if ev == 'Max' else -1.0 for ev in EV], index=col_names)
    puntuacion_global = (ponderado * signo).sum(axis=1)

    orden = puntuacion_global.sort_values(ascending=False)
    ranking_moora_inicial = [int(i) + 1 for i in orden.index]
    best_score = float(orden.iloc[0])  # mejor (mayor) puntuación global

    _log("Ranking MOORA (una sola vez):", ranking_moora_inicial, "| best_score =", best_score)
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
        'ranking_moora_inicial':    ranking_moora_inicial,
        'historiales': {
            'pheromone_final': pheromone.round(4).tolist(),
        },
    }
