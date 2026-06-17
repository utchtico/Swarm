# src/algoritmos/topsisba.py
# TOPSIS-BA — Technique for Order Preference by Similarity to Ideal Solution
#             (ranking) + Bat Algorithm (mecánica de búsqueda)
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Cambios respecto a la versión original:
#   1. Función pura y síncrona (sin async, sin I/O de archivos).
#   2. Matriz dinámica NxM: n y a derivados del input.
#   3. Igual que DA-BA y MOORA-BA, aquí 'w' SÍ se usa: pondera la matriz
#      normalizada antes de calcular las distancias TOPSIS.
#   4. Todos los criterios se tratan como "beneficio" (igual que el
#      original, donde benefit_attributes incluía los 5 índices).
#   5. Retorna historiales completos para persistencia, gráficas y Excel,
#      con el mismo contrato de retorno usado por PSO, BA, DA-BA y MOORA-BA.
#   6. Fiel al original: la posición NO se acota a ningún rango.
#
# Diferencia clave frente a DA-BA y MOORA-BA: TOPSIS normaliza cada columna
# (no cada fila como MOORA), pondera por w, calcula distancias a una
# solución ideal y anti-ideal, y la puntuación de proximidad relativa es
# s_worst / (s_best + s_worst). El ranking es ASCENDENTE — la alternativa
# con MENOR puntuación es la mejor, igual patrón que TOPSIS-PSO.

import math
import random
from datetime import datetime

import numpy as np
import pandas as pd


def ejecutar_topsisba(matriz, w, alpha, gamma, T, username: str = None, verbose: bool = False):
    """
    Ejecuta TOPSIS-BA sobre una matriz de decisión de tamaño variable.

    Parámetros
    ----------
    matriz : list[list[float]]   filas = alternativas (a), columnas = criterios (n)
    w      : list[float]         peso por criterio (longitud n) — pondera la
                                  matriz normalizada antes de calcular las
                                  distancias a la solución ideal/anti-ideal
    alpha  : float                factor de reducción de la sonoridad (loudness)
    gamma  : float                factor de incremento de la tasa de pulso (pulse rate)
    T      : int                  número de iteraciones
    """
    hora_inicio  = datetime.now()
    fecha_inicio = hora_inicio.date()

    a         = len(matriz)
    n         = len(matriz[0])
    col_names = [f'C{i+1}' for i in range(n)]
    candidates = [f'A{j+1}' for j in range(a)]

    _log = print if verbose else (lambda *args, **kwargs: None)

    fmin, fmax = 0, 1
    benefit_attributes = set(range(n))  # todos los criterios son "beneficio"

    x = pd.DataFrame(matriz, columns=col_names, dtype=float)
    weights = pd.Series(w, index=col_names)

    v = pd.DataFrame(
        [[round(random.uniform(0, 1), 3) for _ in range(n)] for _ in range(a)],
        columns=col_names)

    ri = pd.Series(np.random.uniform(0, 1, size=a))
    ai = pd.Series(np.random.uniform(1, 2, size=a))
    ri_ini, ai_ini = ri.copy(), ai.copy()

    f = pd.DataFrame([[0.0] * n], columns=col_names)
    rnd = pd.Series(np.random.uniform(0, 1, size=a))

    _log("Configuración:", "alpha=", alpha, "gamma=", gamma, "T=", T)

    Resultados        = []
    resultados_topsis_ini = []
    historico_gbf      = []

    def puntuacion_topsis(df_pos):
        """
        Normalización por columna (euclidiana para beneficio, L1 para
        costo) -> ponderación por w -> distancias a solución ideal y
        anti-ideal -> puntuación de proximidad relativa
        (s_worst / (s_best + s_worst)). Menor puntuación es mejor.
        """
        normalizado = df_pos.copy()
        for i in range(n):
            col = col_names[i]
            if i in benefit_attributes:
                norm = np.linalg.norm(df_pos[col])
            else:
                norm = np.linalg.norm(df_pos[col], ord=1)
            normalizado[col] = df_pos[col] / (norm if norm != 0 else 1e-9)

        ponderado = normalizado * weights
        ideal_best  = ponderado.max()
        ideal_worst = ponderado.min()

        s_best  = np.sqrt(((ponderado - ideal_best)  ** 2).sum(axis=1))
        s_worst = np.sqrt(((ponderado - ideal_worst) ** 2).sum(axis=1))
        denom = (s_best + s_worst).replace(0, 1e-9)
        return s_worst / denom

    it = 0
    while it < T:
        _log(f"\n=== ITERACIÓN {it} ===")

        x_actual = len(x) - a
        bloque_actual = x.iloc[x_actual:x_actual + a].reset_index(drop=True)

        puntuacion = puntuacion_topsis(bloque_actual)
        orden = puntuacion.sort_values(ascending=True)
        idx_mejor = int(orden.index[0])
        global_best = bloque_actual.iloc[idx_mejor]

        if it == 0:
            resultados_topsis_ini = [int(i) + 1 for i in orden.index]

        Resultados.append(idx_mejor + 1)

        # 1) Nueva frecuencia por criterio
        beta = [round(random.uniform(0, 1), 3) for _ in range(n)]
        nueva_frec = [round(fmin + (fmax - fmin) * b, 3) for b in beta]
        f.loc[len(f.index)] = nueva_frec
        f_actual = len(f) - 1

        # 2) Velocidad: V = V_anterior + (X_actual - global_best) * frecuencia
        v_actual = len(v) - a
        for i in range(a):
            fila_v = [
                round(v.iat[v_actual + i, j]
                      + (x.iat[x_actual + i, j] - global_best.iloc[j]) * f.iat[f_actual, j], 3)
                for j in range(n)
            ]
            v.loc[len(v.index)] = fila_v

        # 3) Posición: X = X_actual + V_nueva
        v_actual = len(v) - a
        for i in range(a):
            fila_x = [
                round(x.iat[x_actual + i, j] + v.iat[v_actual + i, j], 3)
                for j in range(n)
            ]
            x.loc[len(x.index)] = fila_x

        # 4) Paseo aleatorio local si todos rnd > ri
        if all(rnd > ri):
            _log("Paseo aleatorio local (todos rnd > ri)")
            promedio_sonoridad = float(ai.tail(a).mean())
            x_actual2 = len(x) - a
            for i in range(a):
                fila_x = [
                    round(x.iat[x_actual2 + i, j]
                          + round(random.uniform(-1, 1), 3) * promedio_sonoridad, 3)
                    for j in range(n)
                ]
                for j in range(n):
                    x.iat[x_actual2 + i, j] = fila_x[j]

        # 5) Recalcular puntuación TOPSIS sobre la nueva posición
        x_actual3 = len(x) - a
        bloque_nuevo = x.iloc[x_actual3:x_actual3 + a].reset_index(drop=True)
        puntuacion_nueva = puntuacion_topsis(bloque_nuevo)
        puntuacion_anterior = puntuacion_topsis(bloque_actual)

        gbf_iter = float(puntuacion_nueva.min())
        historico_gbf.append(gbf_iter)
        _log("Mejor alternativa = A", idx_mejor + 1, "| puntuación TOPSIS =", gbf_iter)

        # 6) Actualizar sonoridad (ai) y tasa de pulso (ri) si rand <= Ai
        #    y la nueva puntuación mejora a la anterior (menor es mejor en TOPSIS)
        for i in range(a):
            nueva  = float(puntuacion_nueva.iloc[i])
            previa = float(puntuacion_anterior.iloc[i])
            if float(rnd.iloc[i]) <= float(ai.iloc[i]) and nueva < previa:
                ai.iloc[i] = alpha * ai.iloc[i]
                ri.iloc[i] = ri.iloc[i] * (1 - math.e ** (-gamma * 1))

        it += 1

    hora_fin         = datetime.now()
    tiempo_ejecucion = hora_fin - hora_inicio

    x_final = x.iloc[-a:].reset_index(drop=True)
    v_final = v.iloc[-a:].reset_index(drop=True)

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
        'alternativas_nombres':     candidates,
        'resultados_por_iteracion': Resultados,
        'historico_gbf':            [float(g) for g in historico_gbf],
        'gbf_final':                float(historico_gbf[-1]),
        'mejor_alternativa_final':  int(Resultados[-1]),
        'gbest_final':              global_best.tolist(),
        'ranking_topsis_inicial':   resultados_topsis_ini,
        'historiales': {
            'V':     v_final.round(3).values.tolist(),
            'CP':    x_final.round(3).values.tolist(),
            'PBEST': x_final.round(3).values.tolist(),
            'Fx':    [float(v) for v in puntuacion_nueva.tolist()],
            'gbest': global_best.tolist(),
            'ai_final': ai.tolist(),
            'ri_final': ri.tolist(),
            'ai_inicial': ai_ini.tolist(),
            'ri_inicial': ri_ini.tolist(),
        },
    }
