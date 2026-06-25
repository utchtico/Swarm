# src/algoritmos/ba.py
# BAT Algorithm (Bat Algorithm) — Yang, 2010
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Metaheurística basada en el comportamiento de ecolocalización de los
# murciélagos. Cada murciélago tiene posición, velocidad, frecuencia,
# tasa de pulso (ri) y sonoridad (Ai). La función objetivo es
# min(1 + 2x - x²) aplicada por criterio en cada alternativa.
#
# Parámetros de entrada:
#   alpha  — factor de reducción de sonoridad (Ai ← alpha * Ai)
#   gamma  — factor de incremento de tasa de pulso (ri ← ri*(1 - e^(-gamma*t)))
#   T      — número de iteraciones

import random
from datetime import datetime
from math import e

import numpy as np
import pandas as pd

from src.utils.execution_logger import ExecutionLogger

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


def _func_objetivo(fila):
    """min(1 + 2x - x²) sobre los d criterios de una alternativa."""
    return min(round(float(1 + 2 * v - v * v), 3) for v in fila)


def ejecutar_ba(alpha, gamma, T, matriz=None, username=None, verbose=False):
    """
    Ejecuta el BAT Algorithm.

    Parámetros
    ----------
    alpha    : factor de reducción de sonoridad  [0, 1]
    gamma    : factor de incremento de pulso     [0, ∞)
    T        : número de iteraciones             ≥ 1
    matriz   : list[list[float]] opcional — si None usa MATRIZ_FIJA
    """
    hora_inicio  = datetime.now()
    fecha_inicio = hora_inicio.date()
    iter_max = T

    datos_matriz = matriz if matriz is not None else MATRIZ_FIJA
    n = len(datos_matriz)
    d = len(datos_matriz[0])
    cols = [f'C{i+1}' for i in range(d)]
    fmin, fmax = 0, 1

    # ── Inicialización ────────────────────────────────────────────────────────
    x = pd.DataFrame(datos_matriz, columns=cols, dtype=float)

    v = pd.DataFrame(
        [[round(random.uniform(0, 1), 3) for _ in range(d)] for _ in range(n)],
        columns=cols
    )

    ri     = pd.Series(np.random.uniform(0, 1, size=n))
    ri_ini = ri.copy()

    ai     = pd.Series(np.random.uniform(1, 2, size=n))
    ai_ini = ai.copy()

    f   = pd.DataFrame([[0.0] * d], columns=cols)
    rnd = pd.Series(np.random.uniform(0, 1, size=n))

    # ── Logger ────────────────────────────────────────────────────────────────
    logger = ExecutionLogger('BA', username=username)
    logger.header(
        params={'alpha': alpha, 'gamma': gamma, 'Número de iteraciones': T},
        matriz=datos_matriz,
        v_inicial=v.values.tolist(),
        ri=ri_ini.values.tolist(),
        ai=ai_ini.values.tolist(),
        f_inicial=[0.0] * d,
        fmin=fmin, fmax=fmax,
        rnd=rnd.values.tolist(),
    )

    # ── Bucle principal ───────────────────────────────────────────────────────
    resultados    = []
    historico_gbf = []
    it = 0

    while it < T:

        # ── Función objetivo ──────────────────────────────────────────────────
        x_base  = len(x) - n
        FuncObj = []
        fitness_rows = []
        for j in range(n):
            fila_actual = [x.iat[x_base + j, c] for c in range(d)]
            fo = _func_objetivo(fila_actual)
            FuncObj.append(fo)
            fitness_rows.append([round(float(1 + 2*v_ - v_*v_), 3)
                                  for v_ in fila_actual])
        fitness_df = pd.DataFrame(fitness_rows, columns=cols)

        IF_maxt    = min(FuncObj)
        mejor_idx  = FuncObj.index(IF_maxt)

        # gbest sin offset — replica el comportamiento del legacy
        gbest_row   = [x.iat[mejor_idx, c] for c in range(d)]
        global_best = pd.DataFrame([gbest_row], columns=cols)
        resultados.append(mejor_idx + 1)
        historico_gbf.append(IF_maxt)

        # ── Frecuencia ────────────────────────────────────────────────────────
        nueva_f = [round(fmin + (fmax - fmin) * round(random.uniform(0, 1), 3), 3)
                   for _ in range(d)]
        f = pd.concat([f, pd.DataFrame([nueva_f], columns=cols)], ignore_index=True)
        f_actual = len(f) - 1
        nueva_f_df = f.iloc[[f_actual]]

        # ── Velocidad: v = v + (x - gbest) * f ───────────────────────────────
        v_base   = len(v) - n
        nuevas_v = []
        for i in range(n):
            fila_v = []
            for c in range(d):
                vi = round(v.iat[v_base + i, c]
                           + (x.iat[x_base + i, c] - global_best.iat[0, c])
                           * f.iat[f_actual, c], 3)
                fila_v.append(vi)
            nuevas_v.append(fila_v)
        v = pd.concat([v, pd.DataFrame(nuevas_v, columns=cols)], ignore_index=True)
        v_act_df = v.iloc[len(v) - n:]

        # ── Posición: x = x + v ───────────────────────────────────────────────
        v_base   = len(v) - n
        nuevas_x = []
        for i in range(n):
            fila_x = [round(x.iat[x_base + i, c] + v.iat[v_base + i, c], 3)
                      for c in range(d)]
            nuevas_x.append(fila_x)
        x = pd.concat([x, pd.DataFrame(nuevas_x, columns=cols)], ignore_index=True)
        x_act_df = x.iloc[len(x) - n:]

        # ── Bifurcación ───────────────────────────────────────────────────────
        Ai_promedio = float(ai[-n:].mean())

        if all(rnd > ri):
            rama = 'local'
            x_base  = len(x) - n
            local_x = []
            for i in range(n):
                fila = [round(x.iat[x_base + i, c]
                              + round(random.uniform(-1, 1), 3) * Ai_promedio, 3)
                        for c in range(d)]
                local_x.append(fila)
            x = pd.concat([x, pd.DataFrame(local_x, columns=cols)], ignore_index=True)
            nueva_pos_df = x.iloc[len(x) - n:]
            nueva_vel_df = pd.DataFrame(columns=cols)  # no aplica en rama local
        else:
            rama = 'else'
            x_base = len(x) - n
            v_base = len(v) - n
            nv_x, nv_v = [], []
            for i in range(n):
                fila_v, fila_x = [], []
                for c in range(d):
                    vi = round(v.iat[v_base + i, c]
                               + (x.iat[x_base + i, c] - global_best.iat[0, c])
                               * f.iat[f_actual, c], 3)
                    xi = round(x.iat[x_base + i, c] + vi, 3)
                    fila_v.append(vi)
                    fila_x.append(xi)
                nv_v.append(fila_v)
                nv_x.append(fila_x)
            x = pd.concat([x, pd.DataFrame(nv_x, columns=cols)], ignore_index=True)
            v = pd.concat([v, pd.DataFrame(nv_v, columns=cols)], ignore_index=True)
            nueva_pos_df = x.iloc[len(x) - n:]
            nueva_vel_df = v.iloc[len(v) - n:]

        # ── FO nueva ──────────────────────────────────────────────────────────
        x_base_new = len(x) - n
        FuncObjN   = []
        for j in range(n):
            fo = _func_objetivo([x.iat[x_base_new + j, c] for c in range(d)])
            FuncObjN.append(fo)
        IF_maxNt = min(FuncObjN)

        # ── Logger: iteración completa ────────────────────────────────────────
        logger.iteracion(
            it=it,
            FuncObj=FuncObj,
            IF_maxt=IF_maxt,
            fitness_df=fitness_df,
            global_best_df=global_best,
            nueva_f_df=nueva_f_df,
            v_act_df=v_act_df,
            x_act_df=x_act_df,
            nueva_pos_df=nueva_pos_df,
            nueva_vel_df=nueva_vel_df,
            IF_maxt_prev=IF_maxt,
            IF_maxNt=IF_maxNt,
            rama=rama,
        )

        # ── Actualizar Ai y ri ────────────────────────────────────────────────
        ai_base  = len(ai) - n
        ri_base  = len(ri) - n
        rnd_base = 0

        for j in range(n):
            ai_idx  = ai_base + j
            ri_idx  = ri_base + j
            rnd_idx = rnd_base + j
            if rnd.iat[rnd_idx] <= ai.iat[ai_idx]:
                if FuncObjN[j] < FuncObj[j]:
                    ai.iat[ai_idx] = alpha * ai.iat[ai_idx]
                    ri.iat[ri_idx] = ri.iat[ri_idx] * (1 - e ** (-gamma * 1))

        it += 1

    # ── Resultado final ───────────────────────────────────────────────────────
    hora_fin         = datetime.now()
    tiempo_ejecucion = hora_fin - hora_inicio

    logger.resumen_final(
        resultados=resultados,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        alpha=alpha, gamma=gamma, iter_max=T,
    )
    logger.close()

    return {
        'mejor_alternativa':        resultados[-10:],
        'historico_gbf':            historico_gbf,
        'gbf_final':                historico_gbf[-1] if historico_gbf else None,
        'mejor_alternativa_final':  resultados[-1] if resultados else None,
        'iteraciones':              T,
        'resultados_por_iteracion': resultados,
        'alternativas_nombres':     [f'A{i+1}' for i in range(n)],
        'criterios':                cols,
        'n_criterios':              d,
        'n_alternativas':           n,
        'matriz':                   datos_matriz,
        'hora_inicio':              hora_inicio.time().strftime('%H:%M:%S'),
        'fecha_inicio':             fecha_inicio.isoformat(),
        'hora_finalizacion':        hora_fin.time().strftime('%H:%M:%S'),
        'tiempo_ejecucion':         str(tiempo_ejecucion),
        'tiempo_ejecucion_seg':     tiempo_ejecucion.total_seconds(),
        'historiales':              None,
        'log_path':                 logger.path,
    }