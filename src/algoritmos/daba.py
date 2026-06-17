# src/algoritmos/daba.py
# DA-BA — Análisis Dimensional (ranking) + Bat Algorithm (mecánica de búsqueda)
# NOTA: 'DA' aquí significa Análisis Dimensional (Dimensional Analysis),
# NO Dragonfly Algorithm. Es uno de los métodos MCDM del proyecto junto a
# TOPSIS y MOORA — ver templates/mcdm/da.html para la explicación completa.
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Cambios respecto a la versión original:
#   1. Función pura y síncrona (sin async, sin I/O de archivos).
#   2. Matriz dinámica NxM: n y a derivados del input.
#   3. A diferencia de BA puro, aquí 'w' SÍ se usa: pondera el índice de
#      similitud DA en cada iteración (mismo patrón que DA-PSO).
#   4. Retorna historiales completos para persistencia, gráficas y Excel,
#      con el mismo contrato de retorno usado por PSO y BA.
#   5. Fiel al original: la posición NO se acota a ningún rango — BA puede
#      divergir hacia valores muy grandes/negativos en pocas iteraciones;
#      es el comportamiento real del algoritmo fuente.
#
# Diferencia clave frente a BA puro: en cada iteración, el Análisis
# Dimensional calcula una solución ideal (promedio por criterio) y un
# índice de similitud ponderado por w (producto sucesivo de (xi/si)^wi).
# Las alternativas se rankean en orden ASCENDENTE — la de MENOR índice de
# similitud es la mejor, y esa es la que se usa como global_best para la
# mecánica de BA (frecuencia, velocidad, paseo aleatorio, actualización de
# sonoridad/tasa de pulso).

import math
import random
from datetime import datetime

import numpy as np
import pandas as pd


def ejecutar_daba(matriz, w, alpha, gamma, T, username: str = None, verbose: bool = False):
    """
    Ejecuta DA-BA sobre una matriz de decisión de tamaño variable.

    Parámetros
    ----------
    matriz : list[list[float]]   filas = alternativas (a), columnas = criterios (n)
    w      : list[float]         peso por criterio (longitud n) — pondera el
                                  índice de similitud DA en cada iteración
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
    resultados_da_ini  = []   # ranking DA de la primera iteración, informativo
    historico_gbf      = []

    def ranking_analisis_dimensional(df_pos):
        """
        Solución ideal (promedio por criterio) -> índice de similitud
        ponderado por w (producto sucesivo de (xi/si)^wi) -> ranking
        ascendente. Devuelve (orden_indices, valores_indice_similitud)
        donde orden_indices[0] es la alternativa con MENOR índice
        (la mejor, según el método de Análisis Dimensional).
        """
        solucion_ideal = df_pos.mean(axis=0)
        razon = (df_pos / solucion_ideal).abs()
        ponderado = razon.pow(weights.abs(), axis=1)
        indice_similitud = ponderado.prod(axis=1)

        orden = indice_similitud.sort_values(ascending=True)
        return list(orden.index), indice_similitud

    it = 0
    while it < T:
        _log(f"\n=== ITERACIÓN {it} ===")

        x_actual = len(x) - a
        bloque_actual = x.iloc[x_actual:x_actual + a].reset_index(drop=True)

        orden, _ = ranking_analisis_dimensional(bloque_actual)
        idx_mejor = orden[0]
        global_best = bloque_actual.iloc[idx_mejor]
        fitness_actual_idx_mejor = idx_mejor  # se usa abajo para comparar mejora

        if it == 0:
            resultados_da_ini = [o + 1 for o in orden]

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

        # 5) Recalcular ranking DA sobre la nueva posición, para comparar mejora
        x_actual3 = len(x) - a
        bloque_nuevo = x.iloc[x_actual3:x_actual3 + a].reset_index(drop=True)
        _, indice_similitud_nuevo = ranking_analisis_dimensional(bloque_nuevo)
        _, indice_similitud_anterior = ranking_analisis_dimensional(bloque_actual)

        gbf_iter = float(indice_similitud_nuevo.min())
        historico_gbf.append(gbf_iter)
        _log("Mejor alternativa = A", idx_mejor + 1, "| índice de similitud =", gbf_iter)

        # 6) Actualizar sonoridad (ai) y tasa de pulso (ri) si rand <= Ai
        #    y el nuevo índice de similitud mejora al anterior (menor es mejor)
        for i in range(a):
            nuevo  = float(indice_similitud_nuevo.iloc[i])
            previo = float(indice_similitud_anterior.iloc[i])
            if float(rnd.iloc[i]) <= float(ai.iloc[i]) and nuevo < previo:
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
        'ranking_da_inicial':       resultados_da_ini,
        'historiales': {
            'V':     v_final.round(3).values.tolist(),
            'CP':    x_final.round(3).values.tolist(),
            'PBEST': x_final.round(3).values.tolist(),
            'Fx':    [float(v) for v in indice_similitud_nuevo.tolist()],
            'gbest': global_best.tolist(),
            'ai_final': ai.tolist(),
            'ri_final': ri.tolist(),
            'ai_inicial': ai_ini.tolist(),
            'ri_inicial': ri_ini.tolist(),
        },
    }
