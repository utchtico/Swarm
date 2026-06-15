import random
from datetime import datetime
import pandas as pd


def ejecutar_dapso(matriz, w, wwi, c1, c2, T, username: str = None, verbose: bool = False):
    hora_inicio  = datetime.now()
    fecha_inicio = hora_inicio.date()
    a         = len(matriz)
    n         = len(matriz[0])
    col_names = [f'C{i+1}' for i in range(n)]
    candidates = [f'A{j+1}' for j in range(a)]
    _log = print if verbose else (lambda *args, **kwargs: None)
    RANGO_MIN, RANGO_MAX = 0, 1

    x  = pd.DataFrame(matriz, columns=col_names, dtype=float)
    A1t = {col_names[i]: [row[i] for row in matriz] for i in range(n)}
    Resultados = []

    def calcular_ranking(df_pos):
        St = [round(df_pos.iloc[:, j].sum() / a, 3) for j in range(n)]
        S  = pd.DataFrame(St, columns=["Solución ideal"])
        ISSFO = pd.DataFrame(columns=col_names)
        for j in range(a):
            fila = []
            for i in range(n):
                d1 = float(df_pos.iat[j, i])
                d2 = float(S.iat[i, 0])
                d3 = round(d1 / d2, 3) if d2 != 0 else 0
                fila.append(round(abs(d3) ** abs(float(w[i])), 3))
            ISSFO = pd.concat([ISSFO, pd.DataFrame([fila], columns=col_names)], ignore_index=True)
        PST_vals = []
        for j in range(a):
            prod = 1.0
            for z in range(n):
                prod *= float(ISSFO.iat[j, z])
            PST_vals.append(round(prod, 3))
        cf_series = pd.Series(PST_vals)
        pst_df = pd.DataFrame(PST_vals, columns=["Índice de similitud"])
        pst_df.sort_values("Índice de similitud", ascending=False, inplace=True)
        rank = pd.DataFrame({"Índice de similitud": pst_df["Índice de similitud"].values,
                              "Ranking": pst_df.index})
        return rank, cf_series

    # Iteración 1
    RankFin, _ = calcular_ranking(x)
    Valor1 = int(RankFin.iat[0, 1])
    Valor2 = int(RankFin.iat[1, 1])
    r1 = x.iloc[Valor1]
    r2 = x.iloc[Valor2]

    V = pd.DataFrame([[round(random.uniform(RANGO_MIN, RANGO_MAX), 3) for _ in range(n)]
                      for _ in range(a)], columns=col_names)
    CP    = pd.DataFrame(A1t, dtype=float)
    PBEST = pd.DataFrame(A1t, dtype=float)

    RankFint0, cf0 = calcular_ranking(CP)
    CF = cf0.copy()
    Fx = cf0.copy()

    GBF = [float(RankFin.iat[0, 0])]
    Fx_index = int(RankFin.iat[0, 1])
    GBP = pd.DataFrame([x.iloc[Fx_index].values], columns=col_names)
    Resultados.append(Fx_index + 1)

    # Iteraciones 2..T
    t = 1
    while t < T:
        r1lt = r1.values.tolist()
        r2lt = r2.values.tolist()
        for j in range(a):
            otroV, otroCP = [], []
            CAA = len(CP) - a
            for i in range(n):
                Vtt1 = float(V.iat[CAA, i])
                PBESTtt = float(PBEST.iat[CAA, i])
                CPtt = float(CP.iat[CAA, i])
                GBPtt = float(GBP.iat[0, i])
                VFn = round(wwi*Vtt1 + c1*r1lt[i]*(PBESTtt-CPtt) + c2*r2lt[i]*(GBPtt-CPtt), 3)
                CPFn = round(VFn + CPtt, 3)
                CPFn = max(RANGO_MIN + 0.2, min(RANGO_MAX - 0.2, CPFn))
                otroV.append(float(VFn))
                otroCP.append(float(CPFn))
            V.loc[len(V.index)]  = otroV
            CP.loc[len(CP.index)] = otroCP

        xlen2 = CP.iloc[-a:].reset_index(drop=True)
        xlen2.columns = col_names
        RankFint2, cf_t = calcular_ranking(xlen2)
        CF = pd.concat([CF, cf_t], ignore_index=True)
        Fx = pd.concat([Fx, cf_t], ignore_index=True)

        CFactual, CFAnterior = len(CF) - a, len(CF) - 2*a
        for j in range(a):
            LxCP = []
            if float(CF.iat[CFactual]) >= float(CF.iat[CFAnterior]):
                for z in range(n): LxCP.append(round(CP.iat[CFactual, z], 3))
            else:
                for z in range(n): LxCP.append(round(CP.iat[CFAnterior, z], 3))
            PBEST.loc[len(PBEST.index)] = LxCP
            CFactual += 1; CFAnterior += 1

        GBF.append(float(RankFint2.iat[0, 0]))
        Fx_index2 = int(RankFint2.iat[0, 1])
        GBP = pd.DataFrame([x.iloc[Fx_index2].values], columns=col_names)
        Resultados.append(Fx_index2 + 1)
        r1 = x.iloc[int(RankFint2.iat[0, 1])]
        r2 = x.iloc[int(RankFint2.iat[1, 1])] if a > 1 else r1
        t += 1

    hora_fin = datetime.now()
    tiempo_ejecucion = hora_fin - hora_inicio
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
        'historico_gbf':           [float(g) for g in GBF],
        'gbf_final':               float(GBF[-1]),
        'mejor_alternativa_final': int(Resultados[-1]),
        'gbest_final':             GBP.iloc[0].tolist(),
        'historiales': {
            'V':     V.round(3).values.tolist(),
            'CP':    CP.round(3).values.tolist(),
            'PBEST': PBEST.round(3).values.tolist(),
            'Fx':    [float(v) for v in Fx.tolist()],
            'gbest': GBP.iloc[0].tolist(),
        },
    }