# src/algoritmos/aco.py
# ACO — Ant Colony Optimization
# Universidad Autónoma de Ciudad Juárez · Doctorado en Tecnología
#
# Cambios respecto a la versión original:
#   1. Función pura y síncrona (sin async, sin I/O de archivos).
#   2. Matriz dinámica NxM: n y a derivados del input.
#   3. Parámetro 'w' eliminado de la firma: en la versión original se
#      recibía pero nunca se usaba dentro del cuerpo de la función
#      (parámetro fantasma sin efecto en el resultado, igual patrón que
#      se encontró en BA). Documentado aquí para que quede registro de
#      que existió.
#   4. Retorna historiales completos para persistencia, gráficas y Excel,
#      con el mismo contrato de retorno usado por PSO y BA.
#
# Diferencia estructural frente a PSO/BA: ACO no tiene una "posición" que
# evolucione iteración a iteración. La matriz de decisión es una referencia
# FIJA durante toda la ejecución, usada para calcular una heurística simple
# (1/valor). Lo que evoluciona es una matriz de feromona de tamaño
# (criterios x alternativas): en cada iteración, n_ants hormigas eligen
# (de forma probabilística, ponderando feromona^alpha * heurística^beta)
# una alternativa por cada criterio, refuerzan la feromona de su elección,
# y al final de la iteración toda la feromona se evapora en un factor rho.
# La mejor alternativa de la iteración es la que maximiza la suma de
# feromona ponderada por la matriz de decisión transpuesta.

from datetime import datetime

import numpy as np
import pandas as pd


def ejecutar_aco(matriz, alpha, beta, rho, Q, n_ants, T,
                 username: str = None, verbose: bool = False):
    """
    Ejecuta Ant Colony Optimization sobre una matriz de decisión de tamaño
    variable.

    Parámetros
    ----------
    matriz : list[list[float]]   filas = alternativas (a), columnas = criterios (n)
                                  matriz de referencia FIJA — no evoluciona
    alpha  : float                peso de la feromona en la probabilidad de elección
    beta   : float                peso de la heurística en la probabilidad de elección
    rho    : float                tasa de evaporación de feromona, (0, 1)
    Q      : float                cantidad de feromona depositada por elección
    n_ants : int                  número de hormigas por iteración
    T      : int                  número de iteraciones
    """
    hora_inicio  = datetime.now()
    fecha_inicio = hora_inicio.date()

    a         = len(matriz)
    n         = len(matriz[0])
    col_names = [f'C{i+1}' for i in range(n)]
    candidates = list(range(a))  # índices 0..a-1, fiel al original (candidates = [1..9] en datos pero se usa como índice)

    _log = print if verbose else (lambda *args, **kwargs: None)

    xP = pd.DataFrame(matriz, columns=col_names)

    # Feromona: una fila por criterio, una columna por alternativa
    pheromone = np.ones((n, a))

    def calcular_probabilidades(criterio, pheromone, heuristica):
        probabilidades = (pheromone[criterio] ** alpha) * (heuristica ** beta)
        probabilidades[probabilidades < 0] = 0
        suma = np.sum(probabilidades)
        if suma == 0:
            return np.full(a, 1.0 / a)
        return probabilidades / suma

    _log("Configuración:", "alpha=", alpha, "beta=", beta, "rho=", rho,
         "Q=", Q, "n_ants=", n_ants, "T=", T)

    Resultados   = []
    historico_gbf = []

    for it in range(T):
        _log(f"\n=== ITERACIÓN {it} ===")
        heuristica = 1 / (xP.values + 1e-10)

        for hormiga in range(n_ants):
            elecciones = []
            for criterio in range(n):
                probabilidades = calcular_probabilidades(
                    criterio, pheromone, heuristica[:, criterio])
                elegida = int(np.random.choice(a, p=probabilidades))
                elecciones.append(elegida)

            for criterio, elegida in enumerate(elecciones):
                pheromone[criterio, elegida] += Q / (xP.values[elegida, criterio] + 1e-10)

        # Evaporación de feromona al final de la iteración
        pheromone *= (1 - rho)

        # Mejor alternativa: la que maximiza la suma de feromona ponderada
        # por la matriz de decisión transpuesta (xP.T tiene forma n x a,
        # igual que pheromone, así que la multiplicación es elemento a
        # elemento y se suma por alternativa)
        puntuacion_por_alternativa = np.sum(xP.values.T * pheromone, axis=0)
        idx_mejor = int(np.argmax(puntuacion_por_alternativa))
        gbf_iter  = float(puntuacion_por_alternativa[idx_mejor])

        Resultados.append(idx_mejor + 1)
        historico_gbf.append(gbf_iter)
        _log("Mejor alternativa = A", idx_mejor + 1, "| puntuación =", gbf_iter)

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
        'historiales': {
            'pheromone_final': pheromone.round(4).tolist(),
        },
    }
