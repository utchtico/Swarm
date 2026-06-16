# src/algoritmos/ba.py
# BA — Bat Algorithm
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Cambios respecto a la versión original:
#   1. Función pura y síncrona (sin async, sin I/O de archivos).
#   2. Matriz dinámica NxM: n y a derivados del input.
#   3. Parámetro 'w' eliminado de la firma: en la versión original se
#      recibía pero nunca se usaba dentro del cuerpo de la función
#      (parámetro fantasma sin efecto en el resultado). Documentado aquí
#      para que quede registro de que existió.
#   4. Retorna historiales completos para persistencia, gráficas y Excel,
#      con el mismo contrato de retorno usado por la familia PSO.
#   5. Fiel al original: la posición NO se acota a ningún rango (a
#      diferencia de PSO, que sí limita CP entre 0.2 y 0.8). Esto hace
#      que BA pueda divergir hacia valores muy grandes/negativos en
#      pocas iteraciones — es el comportamiento real del algoritmo
#      fuente, no un defecto de esta refactorización.

import math
import random
from datetime import datetime

import numpy as np
import pandas as pd


def ejecutar_ba(matriz, alpha, gamma, T, username: str = None, verbose: bool = False):
    """
    Ejecuta el Bat Algorithm clásico sobre una matriz de decisión de tamaño
    variable.

    Parámetros
    ----------
    matriz : list[list[float]]   filas = alternativas (a), columnas = criterios (n)
    alpha  : float                factor de reducción de la sonoridad (loudness)
    gamma  : float                factor de incremento de la tasa de pulso (pulse rate)
    T      : int                  número de iteraciones
    username : str                informativo (persistencia es externa)
    verbose   : bool              imprime detalle de cada iteración

    BA no recibe pesos por criterio (w): la función objetivo evalúa cada
    alternativa con la misma fórmula 1+2x-x^2 usada en PSO puro, tomando
    el mínimo entre los criterios de esa alternativa, sin ponderación.
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

    # Velocidad inicial aleatoria U(0,1)
    v = pd.DataFrame(
        [[round(random.uniform(0, 1), 3) for _ in range(n)] for _ in range(a)],
        columns=col_names)

    # Tasa de pulso (ri) U(0,1) y sonoridad (ai) U(1,2), una por murciélago
    ri = pd.Series(np.random.uniform(0, 1, size=a))
    ai = pd.Series(np.random.uniform(1, 2, size=a))
    ri_ini, ai_ini = ri.copy(), ai.copy()

    # Frecuencia inicial en 0 para todos los murciélagos/criterios
    f = pd.DataFrame([[0.0] * n], columns=col_names)

    # Aleatorios usados en la condición de paseo local, uno por murciélago
    rnd = pd.Series(np.random.uniform(0, 1, size=a))

    _log("Configuración:", "alpha=", alpha, "gamma=", gamma, "T=", T)

    Resultados   = []
    historico_gbf = []

    def fitness_min_por_alternativa(df_pos):
        """1+2x-x^2 evaluado por criterio, mínimo por fila (alternativa)."""
        valores = 1 + 2 * df_pos - df_pos ** 2
        return valores.min(axis=1)

    it = 0
    while it < T:
        _log(f"\n=== ITERACIÓN {it} ===")

        x_actual = len(x) - a
        fitness_actual = fitness_min_por_alternativa(x.iloc[x_actual:x_actual + a])
        fitness_actual.index = range(a)

        idx_mejor = int(fitness_actual.idxmin())
        gbf_iter  = float(fitness_actual.min())
        global_best = x.iloc[x_actual + idx_mejor]

        Resultados.append(idx_mejor + 1)
        historico_gbf.append(gbf_iter)
        _log("Mejor alternativa = A", idx_mejor + 1, "| fitness_min =", gbf_iter)

        # 1) Nueva frecuencia por criterio (beta aleatorio U(0,1))
        beta = [round(random.uniform(0, 1), 3) for _ in range(n)]
        nueva_frec = [round(fmin + (fmax - fmin) * b, 3) for b in beta]
        f.loc[len(f.index)] = nueva_frec
        f_actual = len(f) - 1

        # 2) Actualizar velocidad: V = V_anterior + (X_actual - global_best) * frecuencia
        v_actual = len(v) - a
        for i in range(a):
            fila_v = [
                round(v.iat[v_actual + i, j]
                      + (x.iat[x_actual + i, j] - global_best.iloc[j]) * f.iat[f_actual, j], 3)
                for j in range(n)
            ]
            v.loc[len(v.index)] = fila_v

        # 3) Actualizar posición: X = X_actual + V_nueva
        v_actual = len(v) - a
        for i in range(a):
            fila_x = [
                round(x.iat[x_actual + i, j] + v.iat[v_actual + i, j], 3)
                for j in range(n)
            ]
            x.loc[len(x.index)] = fila_x

        # 4) Paseo aleatorio local si todos los rnd > ri; si no, ya se usó
        #    la posición recién calculada en el paso 3 (rama "else" original)
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
                # Sobrescribe la posición recién generada en el paso 3
                for j in range(n):
                    x.iat[x_actual2 + i, j] = fila_x[j]

        # 5) Actualizar sonoridad (ai) y tasa de pulso (ri) si rand <= Ai
        #    y el nuevo fitness mejora al anterior
        x_actual3 = len(x) - a
        fitness_nuevo = fitness_min_por_alternativa(x.iloc[x_actual3:x_actual3 + a])
        fitness_nuevo.index = range(a)

        for i in range(a):
            if float(rnd.iloc[i]) <= float(ai.iloc[i]) and float(fitness_nuevo.iloc[i]) < float(fitness_actual.iloc[i]):
                ai.iloc[i] = alpha * ai.iloc[i]
                ri.iloc[i] = ri.iloc[i] * (1 - math.e ** (-gamma * 1))

        it += 1

    hora_fin         = datetime.now()
    tiempo_ejecucion = hora_fin - hora_inicio

    x_final = x.iloc[-a:].reset_index(drop=True)
    v_final = v.iloc[-a:].reset_index(drop=True)

    return {
        'mejor_alternativa':       Resultados[-10:],
        'iteraciones':             T,
        'hora_inicio':             hora_inicio.time().strftime('%H:%M:%S'),
        'fecha_inicio':            fecha_inicio.isoformat(),
        'hora_finalizacion':       hora_fin.time().strftime('%H:%M:%S'),
        'tiempo_ejecucion':        str(tiempo_ejecucion),
        'tiempo_ejecucion_seg':    tiempo_ejecucion.total_seconds(),
        'n_criterios':             n,
        'n_alternativas':          a,
        'criterios':               col_names,
        'alternativas_nombres':    candidates,
        'resultados_por_iteracion': Resultados,
        'historico_gbf':           [float(g) for g in historico_gbf],
        'gbf_final':               float(historico_gbf[-1]),
        'mejor_alternativa_final': int(Resultados[-1]),
        'gbest_final':             global_best.tolist(),
        'historiales': {
            'V':     v_final.round(3).values.tolist(),
            'CP':    x_final.round(3).values.tolist(),
            'PBEST': x_final.round(3).values.tolist(),  # BA no tiene PBEST propio; se usa la posición final
            'Fx':    [float(v) for v in fitness_nuevo.tolist()],
            'gbest': global_best.tolist(),
            'ai_final': ai.tolist(),
            'ri_final': ri.tolist(),
            'ai_inicial': ai_ini.tolist(),
            'ri_inicial': ri_ini.tolist(),
        },
    }
