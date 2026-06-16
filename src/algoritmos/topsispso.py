# src/algoritmos/topsispso.py
# TOPSIS-PSO — Technique for Order Preference by Similarity to Ideal Solution
#              + Particle Swarm Optimization
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Cambios respecto a la versión original:
#   1. Función pura y síncrona (sin async, sin I/O de archivos).
#   2. Matriz dinámica NxM: n y a derivados del input.
#   3. Todos los criterios se tratan como "beneficio" (igual que el original,
#      donde benefit_attributes incluía los 5 índices).
#   4. r1 y r2 se ignoran como parámetros y se derivan del ranking TOPSIS
#      (mismo patrón que DA-PSO y MOORA-PSO).
#   5. Retorna historiales para persistencia, gráficas y Excel.

import random
from datetime import datetime

import numpy as np
import pandas as pd


def ejecutar_topsispso(matriz, w, wwi, c1, c2, T,
                       username: str = None, verbose: bool = False):
    """
    Ejecuta TOPSIS-PSO sobre una matriz de decisión de tamaño variable.

    Parámetros
    ----------
    matriz : list[list[float]]   filas = alternativas (a), columnas = criterios (n)
    w      : list[float]         peso por criterio (longitud n)
    wwi    : float               peso de inercia
    c1, c2 : float               coeficientes cognitivo y social
    T      : int                 número de iteraciones
    """
    hora_inicio  = datetime.now()
    fecha_inicio = hora_inicio.date()

    a          = len(matriz)
    n          = len(matriz[0])
    col_names  = [f'C{i+1}' for i in range(n)]
    candidates = [f'A{j+1}' for j in range(a)]

    _log = print if verbose else (lambda *args, **kwargs: None)

    RANGO_MIN, RANGO_MAX = 0, 1
    benefit_attributes = set(range(n))   # todos los criterios son "beneficio"

    x   = pd.DataFrame(matriz, columns=col_names, dtype=float)
    A1t = {col_names[i]: [row[i] for row in matriz] for i in range(n)}
    weights = pd.Series(w, index=col_names)

    Resultados      = []
    ResultadosTOPSIS = pd.DataFrame()
    Comparativo     = pd.DataFrame()

    # ── Helper: ranking TOPSIS sobre un DataFrame de posiciones ──────────────
    def topsis_ranking(df):
        """Normalización → ponderación → distancias a ideal/anti-ideal → ranking."""
        normalized = df.copy()
        for i in range(n):
            col = col_names[i]
            if i in benefit_attributes:
                norm = np.linalg.norm(df[col])
            else:
                norm = np.linalg.norm(df[col], ord=1)
            normalized[col] = df[col] / (norm if norm != 0 else 1e-9)

        weighted = normalized * weights
        ideal_best  = weighted.max()
        ideal_worst = weighted.min()

        s_best  = np.sqrt(((weighted - ideal_best)  ** 2).sum(axis=1))
        s_worst = np.sqrt(((weighted - ideal_worst) ** 2).sum(axis=1))
        denom   = (s_best + s_worst).replace(0, 1e-9)
        performance = s_worst / denom

        ranked = performance.sort_values(ascending=True)
        rank = pd.DataFrame({
            'Puntuación Global': ranked.values,
            'Alternativa':       ranked.index,
        }).reset_index(drop=True)
        return rank, performance, normalized, weighted

    # ── ITERACIÓN 1 ───────────────────────────────────────────────────────────
    _log("ITERACIÓN # 1 -----------------------")

    RankFin, _, _, _ = topsis_ranking(x)
    Valor1 = int(RankFin.iat[0, 1])
    Valor2 = int(RankFin.iat[1, 1])
    r1 = x.iloc[Valor1]
    r2 = x.iloc[Valor2]

    CMp1 = pd.DataFrame({'TOPSIS': [Valor1], 'TOPSISFIN': [0]})
    Comparativo = pd.concat([Comparativo, CMp1], ignore_index=True)

    _log("Controles iniciales:")
    _log("w(inertia) =", wwi, "| c1 =", c1, "| c2 =", c2, "| T =", T)

    V = pd.DataFrame(
        [[round(random.uniform(RANGO_MIN, RANGO_MAX), 3) for _ in range(n)]
         for _ in range(a)],
        columns=col_names)

    CP    = pd.DataFrame(A1t, dtype=float)
    PBEST = pd.DataFrame(A1t, dtype=float)

    RankFint0, perf0, _, _ = topsis_ranking(CP)
    CF = perf0.copy()
    Fx = perf0.copy()
    ResultadosTOPSIS = pd.concat([ResultadosTOPSIS, RankFint0], ignore_index=True)

    GBF = [float(RankFin.iat[0, 0])]
    Fx_index = int(RankFin.iat[0, 1])
    GBP = pd.DataFrame([x.iloc[Fx_index].values], columns=col_names)

    Resultados.append(Fx_index + 1)
    _log("Mejor alternativa = A", Fx_index + 1, "para la iteración 1")

    ValorFin = [int(RankFint0.iat[0, 1]), Fx_index + 1]
    CMp1 = pd.DataFrame({'TOPSIS': [ValorFin[0]], 'TOPSISFIN': [ValorFin[1]]})
    Comparativo = pd.concat([Comparativo, CMp1], ignore_index=True)

    # Actualizar r1/r2 con el ranking de la posición actual (igual que el original)
    r1 = x.iloc[int(RankFint0.iat[0, 1])]
    r2 = x.iloc[int(RankFint0.iat[1, 1])] if a > 1 else r1

    # ── ITERACIONES 2 a T ─────────────────────────────────────────────────────
    t = 1
    while t < T:
        _log("\n ITERACIÓN #", t + 1, "-----------------------")
        r1lt = r1.values.tolist()
        r2lt = r2.values.tolist()

        for j in range(a):
            otroV, otroCP = [], []
            CAA = len(CP) - a
            for i in range(n):
                Vtt1    = float(V.iat[CAA, i])
                PBESTtt = float(PBEST.iat[CAA, i])
                CPtt    = float(CP.iat[CAA, i])
                GBPtt   = float(GBP.iat[0, i])

                VFn  = round(wwi*Vtt1 + c1*r1lt[i]*(PBESTtt-CPtt)
                             + c2*r2lt[i]*(GBPtt-CPtt), 3)
                CPFn = round(VFn + CPtt, 3)
                CPFn = max(RANGO_MIN + 0.2, min(RANGO_MAX - 0.2, CPFn))

                otroV.append(float(VFn))
                otroCP.append(float(CPFn))
            V.loc[len(V.index)]   = otroV
            CP.loc[len(CP.index)] = otroCP

        xlen2 = CP.iloc[-a:].reset_index(drop=True)
        xlen2.columns = col_names
        RankFint2, perf2, _, _ = topsis_ranking(xlen2)
        CF = pd.concat([CF, perf2], ignore_index=True)
        Fx = pd.concat([Fx, perf2], ignore_index=True)
        ResultadosTOPSIS = pd.concat([ResultadosTOPSIS, RankFint2], ignore_index=True)

        # Actualizar PBEST: en TOPSIS, valores MÁS PEQUEÑOS de la puntuación
        # (distancia a la anti-ideal entre suma de distancias) son mejores
        CFactual   = len(CF) - a
        CFAnterior = CFactual - a
        for j in range(a):
            actual   = float(CF.iat[CFactual])
            anterior = float(CF.iat[CFAnterior])
            LxCP = []
            src_idx = CFactual if actual <= anterior else CFAnterior
            for z in range(n):
                LxCP.append(round(CP.iat[src_idx, z], 3))
            PBEST.loc[len(PBEST.index)] = LxCP
            CFactual   += 1
            CFAnterior += 1

        GBF.append(float(RankFint2.iat[0, 0]))
        Fx_index2 = int(RankFint2.iat[0, 1])
        GBP = pd.DataFrame([x.iloc[Fx_index2].values], columns=col_names)
        Resultados.append(Fx_index2 + 1)

        r1 = x.iloc[int(RankFint2.iat[0, 1])]
        r2 = x.iloc[int(RankFint2.iat[1, 1])] if a > 1 else r1

        ValorFin = [int(RankFint2.iat[0, 1]), Fx_index + 1]
        CMp1 = pd.DataFrame({'TOPSIS': [ValorFin[0]], 'TOPSISFIN': [ValorFin[1]]})
        Comparativo = pd.concat([Comparativo, CMp1], ignore_index=True)

        _log("Mejor alternativa = A", Fx_index2 + 1, "para la iteración", t + 1)
        t += 1

    hora_fin         = datetime.now()
    tiempo_ejecucion = hora_fin - hora_inicio

    return {
        'mejor_alternativa':          Resultados[-10:],
        'iteraciones':                T,
        'hora_inicio':                hora_inicio.time().strftime('%H:%M:%S'),
        'fecha_inicio':               fecha_inicio.isoformat(),
        'hora_finalizacion':          hora_fin.time().strftime('%H:%M:%S'),
        'tiempo_ejecucion':           str(tiempo_ejecucion),
        'tiempo_ejecucion_seg':       tiempo_ejecucion.total_seconds(),
        'n_criterios':                n,
        'n_alternativas':             a,
        'criterios':                  col_names,
        'alternativas_nombres':       candidates,
        'resultados_por_iteracion':   Resultados,
        'historico_gbf':              [float(g) for g in GBF],
        'gbf_final':                  float(GBF[-1]),
        'mejor_alternativa_final':    int(Resultados[-1]),
        'gbest_final':                GBP.iloc[0].tolist(),
        'historiales': {
            'V':     V.round(3).values.tolist(),
            'CP':    CP.round(3).values.tolist(),
            'PBEST': PBEST.round(3).values.tolist(),
            'Fx':    [float(v) for v in Fx.tolist()],
            'gbest': GBP.iloc[0].tolist(),
        },
    }
