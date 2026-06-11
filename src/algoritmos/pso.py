# Experimento PSO — versión con matriz de decisión dinámica (NxM)
# Doctorado en Tecnología
# Universidad Autónoma de Ciudad Juárez
#
# Cambios respecto a la versión anterior:
#   1. La matriz de decisión llega como parámetro (lista de listas);
#      n (criterios) y a (alternativas) se derivan de ella. Ya no hay
#      dimensiones hardcodeadas (n=5, a=9, columnas 'C1'..'C5', /5, Cc1..Cc5).
#   2. La función es síncrona (el async anterior era cosmético) y PURA:
#      no escribe archivos ni toca la base de datos. La persistencia vive
#      en src/services/ejecuciones.py. Esto permite testearla aislada.
#   3. Devuelve, además de las claves que ya consumía pso.js
#      (mejor_alternativa, iteraciones, hora_inicio, fecha_inicio,
#      hora_finalizacion, tiempo_ejecucion), los históricos completos
#      para persistencia, gráficas y exportación a Excel.
#
# La lógica numérica del algoritmo se preservó tal cual; con una matriz
# 9x5 el comportamiento es idéntico al de la versión original.

import random
from datetime import datetime

import pandas as pd


RANGO_MIN = 0
RANGO_MAX = 1


def ejecutar_pso(matriz, w, wwi, c1, c2, T, r1, r2, username: str = None, verbose: bool = False):
    """
    Ejecuta PSO sobre una matriz de decisión de tamaño variable.

    Parámetros
    ----------
    matriz : list[list[float]]   filas = alternativas (a), columnas = criterios (n)
    w      : list[float]         peso por criterio (longitud n)
    wwi    : float               peso de inercia
    c1, c2 : float               coeficientes cognitivo y social
    T      : int                 número de iteraciones
    r1, r2 : list[float]         vectores aleatorios (longitud n)
    username : str               solo informativo (la persistencia es externa)
    verbose : bool               imprime el detalle por iteración como la versión original
    """
    hora_inicio = datetime.now()
    fecha_inicio = hora_inicio.date()

    # ----- Dimensiones derivadas de la matriz (antes: n=5, a=9 fijos) -----
    a = len(matriz)            # alternativas (filas)
    n = len(matriz[0])         # criterios (columnas)
    col_names = [f'C{i+1}' for i in range(n)]
    candidates = [f'A{j+1}' for j in range(a)]

    _log = print if verbose else (lambda *args, **kwargs: None)

    _log("\n-------------------------------------------")
    _log("Construcción de la matriz de decisión")
    A1 = pd.DataFrame(matriz, columns=col_names, index=candidates, dtype=float)
    CP = pd.DataFrame(matriz, columns=col_names, dtype=float)      # primera posición del enjambre
    PBEST = pd.DataFrame(matriz, columns=col_names, dtype=float)   # primera mejor posición
    _log(A1, "\n")

    Resultados = []
    dim = n * a  # dimensión del enjambre (informativo)

    _log("PRIMERA ITERACIÓN -----------------------")
    _log("w(inertia) = ", wwi)
    _log("c1 = ", c1)
    _log("c2 = ", c2)
    _log("No. de iteraciones = ", T, "\n")
    _log("r1 = ", r1, "\n")
    _log("r2 = ", r2, "\n")
    _log("Rango de valores: (", RANGO_MIN, ",", RANGO_MAX, ") \n")

    # ----- CURRENT VELOCITY (V): aleatoria a x n -----
    V = pd.DataFrame(
        [[round(float(random.uniform(RANGO_MIN, RANGO_MAX)), 3) for _ in range(n)]
         for _ in range(a)],
        columns=col_names
    )
    _log("V(1)=")
    _log(V, "\n")

    _log("CP(1)=")
    _log(CP, "\n")

    # ----- FUNCIÓN OBJETIVO, CURRENT FITNESS (CF): 1 + 2x - x^2 -----
    CF = pd.DataFrame(
        [[round(1.0 + (2.0 * float(A1.iat[j, i])) - (float(A1.iat[j, i]) ** 2), 3)
          for i in range(n)]
         for j in range(a)],
        columns=col_names
    )
    _log("CF(1)=")
    _log(CF, "\n")

    Fx = CF.min(axis=1)

    _log("pbest(1)=")
    _log(PBEST, "\n")

    # ----- GLOBAL BEST FITNESS de la iteración 1 -----
    GBF = []
    pbestt = float(Fx.max())
    _log("pbestt(1)= ", pbestt, "\n")
    GBF.append(pbestt)
    _log("GBF(1)=", GBF, "\n")

    # ----- GLOBAL BEST POSITION de la iteración 1 -----
    Fx_index = 0
    for j in range(a):
        if round(float(GBF[0]), 3) == round(float(Fx[j]), 3):
            Fx_index = j

    columna = [float(A1.iat[Fx_index, i]) for i in range(n)]
    GBP = pd.DataFrame(columna)
    _log("gbest(1)=")
    _log(GBP)
    Resultados.append(Fx_index + 1)
    _log("           Mejor alternativa= A", Fx_index + 1, " para la iteración 1")
    _log("      ---------------------------------------------------------------")

    ###########################################################################
    # ITERACIONES 2 a T
    t = 1
    longseg = n  # antes: longseg=5 (literal); es el número de criterios

    while t < T:
        _log("\n ITERACIÓN #", t + 1, "-----------------------", "\n")

        # ----- 1) Actualización de velocidad y posición -----
        for j in range(a):
            otroV = []
            otroCP = []
            CAA = len(CP) - a
            GBP12 = len(GBP) - n
            for i in range(n):
                # 1-a) velocidad
                Vtt1 = float(V.iat[CAA, i])
                Vt11 = float(wwi * Vtt1)

                PBESTtt = float(PBEST.iat[CAA, i])
                rr1 = float(r1[i])
                CPtt = float(CP.iat[CAA, i])
                Vt12 = float(c1 * rr1 * (PBESTtt - CPtt))

                GBPtt = float(GBP.iloc[GBP12].iloc[0])
                rr2 = float(r2[i])
                Vt13 = float(c2 * rr2 * (GBPtt - CPtt))

                VFn = round(float(Vt11 + Vt12 + Vt13), 3)
                otroV.append(float(VFn))

                # 2-a) posición
                CPtt2 = float(CP.iat[CAA, i])
                CPFn = round(float(VFn) + float(CPtt2), 3)

                # 2-b) verificación de rango
                if CPFn < RANGO_MIN:
                    CPFn = RANGO_MIN + 0.2
                if CPFn > RANGO_MAX:
                    CPFn = RANGO_MAX - 0.2
                otroCP.append(float(CPFn))

                GBP12 = GBP12 + 1

            V.loc[len(V.index)] = otroV
            CP.loc[len(CP.index)] = otroCP

        # ----- 2) Función objetivo sobre las posiciones nuevas -----
        CAA = len(CP) - a
        for j in range(a):
            SI1 = [round(1.0 + (2.0 * float(CP.iat[CAA, i])) - (float(CP.iat[CAA, i]) ** 2), 3)
                   for i in range(n)]
            CF = pd.concat([CF, pd.DataFrame([SI1], columns=col_names)], ignore_index=True)
            CAA = CAA + 1

        # Fitness por alternativa: promedio de su renglón de posiciones
        # (antes: dat1/5 con "porque son 5 partículas" — ahora /n)
        CFPS = []
        altFXx = t * a
        for j in range(a):
            dat1 = 0.0
            for i in range(n):
                dat1 = dat1 + float(CP.iat[altFXx, i])
            altFXx = altFXx + 1
            dat1 = round(dat1 / n, 3)
            CFPS.append(float(dat1))
        Fx12 = pd.Series(CFPS)
        Fx = pd.concat([Fx, Fx12], ignore_index=True)

        # ----- 3) Actualización de PBEST -----
        # (antes: variables enumeradas Cc1..Cc5 — ahora dict dinámico por criterio)
        if t == 1:
            cont_act = n
            cont_ant = 0
        else:
            cont_act = longseg - n
            cont_ant = cont_act - n

        z1 = 0
        columnas_pbest = {}
        for j in range(n):
            longsegP = len(CP) - a
            actual = float(Fx.iat[cont_act])
            anterior = float(Fx.iat[cont_ant])
            LxCP = []

            if actual >= anterior:   # tomar CP actual
                for z in range(a):
                    x1 = CP.iat[longsegP, z1]
                    LxCP.append(round(x1, 3))
                    longsegP = longsegP + 1
            else:                    # conservar CP anterior
                for z in range(a):
                    longsegPt = longsegP - a
                    x1 = CP.iat[longsegPt, z1]
                    LxCP.append(round(x1, 3))
                    longsegP = longsegP + 1

            columnas_pbest[col_names[j]] = LxCP
            z1 = z1 + 1
            cont_ant = cont_ant + 1
            cont_act = cont_act + 1

        new_CPLxCont = pd.DataFrame(columnas_pbest)
        PBEST = pd.concat([PBEST, new_CPLxCont], ignore_index=True)

        # ----- 4) GLOBAL BEST FITNESS de la iteración -----
        pbestt2 = float(max(Fx12))
        GBF.append(pbestt2)

        # ----- 5) GLOBAL BEST POSITION de la iteración -----
        Fx_index = 0
        temp_GBP = len(Fx) - a
        for j in range(a):
            val1 = round(float(GBF[t]), 3)
            val2 = round(float(Fx[temp_GBP]), 3)
            if val1 == val2:
                Fx_index = j
            temp_GBP = temp_GBP + 1
        Fx_index = Fx_index + (a * t)

        columna = [float(CP.iat[Fx_index, i]) for i in range(n)]
        GBP = pd.concat([GBP, pd.Series(columna)], ignore_index=True)

        Fx_index = Fx_index - (a * t)
        Resultados.append(Fx_index + 1)

        # ----- Impresión de resultados de la iteración -----
        if verbose:
            seg = a * t
            _log("V(", t + 1, ") =")
            _log(V.iloc[seg:seg + a, :], "\n")
            _log("CP(", t + 1, ") =")
            _log(CP.iloc[seg:seg + a, :], "\n")
            _log("pbest(", t + 1, ") =")
            _log(PBEST.iloc[seg:seg + a], "\n,")
            _log("GBF =", GBF[t], "\n")
            _log("gbest(", t + 1, ") =")
            _log(GBP.iloc[(len(GBP) - n):len(GBP)], "\n")
            _log("           Mejor alternativa= A", Fx_index + 1, " para la iteración", t + 1)
            _log("      ---------------------------------------------------------------")

        t = t + 1

    hora_fin = datetime.now()
    tiempo_ejecucion = hora_fin - hora_inicio

    _log("\n**************************")
    _log("Resultados Finales")
    _log("**************************")
    _log("   Iteración", "  Mejor_alternativa")
    for i in range(T):
        _log("       ", i + 1, "        ", "A", Resultados[i])

    alternativas = Resultados[-10:]
    gbest_final = [float(x) for x in GBP.iloc[(len(GBP) - n):len(GBP)].values.ravel()]

    return {
        # --- Claves que ya consumía el frontend (compatibilidad) ---
        "mejor_alternativa": alternativas,
        "iteraciones": t,
        "hora_inicio": hora_inicio.time().strftime('%H:%M:%S'),
        "fecha_inicio": fecha_inicio.isoformat(),
        "hora_finalizacion": hora_fin.time().strftime('%H:%M:%S'),
        "tiempo_ejecucion": str(tiempo_ejecucion),

        # --- Nuevas claves para persistencia, gráficas y exportación ---
        "tiempo_ejecucion_seg": tiempo_ejecucion.total_seconds(),
        "n_criterios": n,
        "n_alternativas": a,
        "criterios": col_names,
        "alternativas_nombres": candidates,
        "resultados_por_iteracion": Resultados,           # mejor alternativa de cada iteración
        "historico_gbf": [float(g) for g in GBF],          # convergencia para la gráfica
        "gbf_final": float(GBF[-1]),
        "mejor_alternativa_final": int(Resultados[-1]),
        "gbest_final": gbest_final,
        "historiales": {
            "V": V.round(3).values.tolist(),
            "CP": CP.round(3).values.tolist(),
            "PBEST": PBEST.round(3).values.tolist(),
            "CF": CF.round(3).values.tolist(),
            "Fx": [float(x) for x in Fx.tolist()],
            "gbest": [float(x) for x in GBP.values.ravel()],
        },
    }
