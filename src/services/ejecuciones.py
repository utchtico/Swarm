# src/services/ejecuciones.py
# Capa de servicios para las ejecuciones de algoritmos.
#
# Separación de responsabilidades:
#   - Layout/pso.py (y futuros algoritmos)  -> cómputo puro, sin I/O
#   - este módulo                            -> persistencia en PostgreSQL
#                                               y exportación a Excel bajo demanda
#
# El Excel deja de ser el medio de almacenamiento (eso ahora es PostgreSQL)
# y pasa a ser solo un formato de salida que se reconstruye desde la BD
# cuando el usuario lo solicita.

from io import BytesIO

import pandas as pd

from src.models.models import db, Ejecucion


# Mínimos definidos por la especificación del proyecto:
# "siendo el mínimo el ya establecido" (matriz original 9x5)
MIN_CRITERIOS = 5
MIN_ALTERNATIVAS = 9

# Matriz de decisión original (la que antes vivía hardcodeada dentro de
# Layout/pso.py como A1t, aquí transpuesta a fila=alternativa).
# La usa la ruta vieja POST /pso —cuyo formulario aún no envía matriz—
# para mantener el frontend actual funcionando sin cambios.
MATRIZ_DEFAULT = [
    # C1     C2     C3     C4     C5
    [0.048, 0.047, 0.070, 0.087, 0.190],  # A1
    [0.053, 0.052, 0.066, 0.081, 0.058],  # A2
    [0.057, 0.057, 0.066, 0.076, 0.022],  # A3
    [0.062, 0.062, 0.063, 0.058, 0.007],  # A4
    [0.066, 0.066, 0.070, 0.085, 0.004],  # A5
    [0.070, 0.071, 0.066, 0.058, 0.003],  # A6
    [0.075, 0.075, 0.066, 0.047, 0.002],  # A7
    [0.079, 0.079, 0.066, 0.035, 0.002],  # A8
    [0.083, 0.083, 0.066, 0.051, 0.000],  # A9
]


def validar_entrada_pso(payload: dict) -> dict:
    """
    Valida y normaliza el payload JSON del frontend para PSO.
    Lanza ValueError con un mensaje claro si algo no cuadra.

    Estructura esperada:
    {
      "matriz": [[...], ...],   # a filas x n columnas
      "w":  [...],              # longitud n
      "wwi": 0.7, "c1": 2.5, "c2": 2.5, "T": 10,
      "r1": [...], "r2": [...]  # longitud n
    }
    """
    if not isinstance(payload, dict):
        raise ValueError("El cuerpo de la petición debe ser un objeto JSON.")

    matriz = payload.get('matriz')
    if not isinstance(matriz, list) or not matriz:
        raise ValueError("'matriz' es obligatoria y debe ser una lista de filas.")
    if not all(isinstance(fila, list) and fila for fila in matriz):
        raise ValueError("Cada fila de 'matriz' debe ser una lista no vacía.")

    n = len(matriz[0])
    a = len(matriz)
    if any(len(fila) != n for fila in matriz):
        raise ValueError("Todas las filas de 'matriz' deben tener la misma cantidad de criterios.")
    if n < MIN_CRITERIOS:
        raise ValueError(f"La matriz requiere al menos {MIN_CRITERIOS} criterios (recibió {n}).")
    if a < MIN_ALTERNATIVAS:
        raise ValueError(f"La matriz requiere al menos {MIN_ALTERNATIVAS} alternativas (recibió {a}).")

    try:
        matriz = [[float(v) for v in fila] for fila in matriz]
    except (TypeError, ValueError):
        raise ValueError("Todos los valores de 'matriz' deben ser numéricos.")

    def _vector(nombre):
        vec = payload.get(nombre)
        if not isinstance(vec, list):
            raise ValueError(f"'{nombre}' debe ser una lista numérica de longitud {n}.")
        if len(vec) != n:
            raise ValueError(
                f"'{nombre}' debe tener un valor por criterio: longitud {n}, recibió {len(vec)}."
            )
        try:
            return [float(v) for v in vec]
        except (TypeError, ValueError):
            raise ValueError(f"Todos los valores de '{nombre}' deben ser numéricos.")

    w = _vector('w')
    r1 = _vector('r1')
    r2 = _vector('r2')

    def _float(nombre):
        try:
            return float(payload[nombre])
        except KeyError:
            raise ValueError(f"Falta el parámetro '{nombre}'.")
        except (TypeError, ValueError):
            raise ValueError(f"'{nombre}' debe ser numérico.")

    wwi = _float('wwi')
    c1 = _float('c1')
    c2 = _float('c2')

    try:
        T = int(payload['T'])
    except KeyError:
        raise ValueError("Falta el parámetro 'T'.")
    except (TypeError, ValueError):
        raise ValueError("'T' debe ser un entero.")
    if T < 1:
        raise ValueError("'T' debe ser al menos 1.")

    return {'matriz': matriz, 'w': w, 'wwi': wwi, 'c1': c1, 'c2': c2,
            'T': T, 'r1': r1, 'r2': r2}


def guardar_ejecucion(algoritmo: str, user_id: int, params: dict, datos: dict) -> Ejecucion:
    """
    Persiste en PostgreSQL el resultado devuelto por un algoritmo.

    algoritmo : 'PSO', 'BA', 'ACO', ...
    user_id   : id del usuario autenticado
    params    : dict de entrada validado (matriz incluida)
    datos     : dict devuelto por ejecutar_<algoritmo>()
    """
    n = datos['n_criterios']
    a = datos['n_alternativas']

    ejecucion = Ejecucion(
        algoritmo=algoritmo,
        fk_user=user_id,
        tiempo_ejecucion_seg=datos['tiempo_ejecucion_seg'],
        iteraciones=datos['iteraciones'],
        n_criterios=n,
        n_alternativas=a,
        gbf_final=datos.get('gbf_final'),
        mejor_alternativa_final=datos.get('mejor_alternativa_final'),
        parametros={k: v for k, v in params.items() if k != 'matriz'},
        matriz_entrada={
            'n': n,
            'a': a,
            'criterios': datos['criterios'],
            'alternativas': datos['alternativas_nombres'],
            'valores': params['matriz'],
        },
        resultados=[
            {'iteracion': i + 1, 'mejor_alternativa': alt, 'gbf': datos['historico_gbf'][i]}
            for i, alt in enumerate(datos['resultados_por_iteracion'])
        ],
        historico_gbf=datos['historico_gbf'],
        historiales=datos.get('historiales'),
    )
    db.session.add(ejecucion)
    db.session.commit()
    return ejecucion


def exportar_ejecucion_excel(ejecucion_id: int) -> BytesIO:
    """
    Reconstruye un Excel legible desde la base de datos (descarga bajo demanda).
    Mantiene las hojas del formato anterior para no romper hábitos de revisión,
    pero ahora con encabezados de criterios reales (C1..Cn) y una hoja de
    resumen de la ejecución.
    """
    ejecucion = db.session.get(Ejecucion, ejecucion_id)
    if ejecucion is None:
        raise LookupError(f"No existe la ejecución con id {ejecucion_id}.")

    me = ejecucion.matriz_entrada
    cols = me['criterios']
    idx = me['alternativas']
    params = ejecucion.parametros
    hist = ejecucion.historiales or {}

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # --- Resumen de la ejecución ---
        pd.DataFrame([{
            'Algoritmo': ejecucion.algoritmo,
            'Usuario': ejecucion.usuario.username if ejecucion.usuario else '',
            'Fecha de ejecución': ejecucion.fecha_ejecucion.strftime('%d/%m/%Y %H:%M:%S'),
            'Tiempo de ejecución (s)': ejecucion.tiempo_ejecucion_seg,
            'Iteraciones': ejecucion.iteraciones,
            'Criterios (n)': ejecucion.n_criterios,
            'Alternativas (a)': ejecucion.n_alternativas,
            'GBF final': ejecucion.gbf_final,
            'Mejor alternativa final': f"A{ejecucion.mejor_alternativa_final}",
        }]).T.rename(columns={0: 'Valor'}).to_excel(writer, sheet_name='Resumen')

        # --- Parámetros iniciales ---
        pd.DataFrame([{
            'w(inertia)': params.get('wwi'),
            'c1': params.get('c1'),
            'c2': params.get('c2'),
            'No. de iteraciones': params.get('T'),
        }]).to_excel(writer, sheet_name='Iniciales', index=False)
        pd.DataFrame(params.get('r1', [])).to_excel(writer, sheet_name='r1')
        pd.DataFrame(params.get('r2', [])).to_excel(writer, sheet_name='r2')
        pd.DataFrame(params.get('w', [])).to_excel(writer, sheet_name='w')

        # --- Matriz de decisión ---
        pd.DataFrame(me['valores'], columns=cols, index=idx).to_excel(
            writer, sheet_name='Matriz')

        # --- Históricos por iteración ---
        if hist.get('V'):
            pd.DataFrame(hist['V'], columns=cols).to_excel(writer, sheet_name='Velocity')
        if hist.get('CP'):
            pd.DataFrame(hist['CP'], columns=cols).to_excel(writer, sheet_name='Position')
        if hist.get('PBEST'):
            pd.DataFrame(hist['PBEST'], columns=cols).to_excel(writer, sheet_name='PBEST')
        if hist.get('Fx') is not None:
            pd.DataFrame(hist['Fx'], columns=['Fx']).to_excel(writer, sheet_name='Fx')
        pd.DataFrame(ejecucion.historico_gbf, columns=['GBF']).to_excel(
            writer, sheet_name='GBF')
        if hist.get('gbest'):
            pd.DataFrame(hist['gbest'], columns=['gbest']).to_excel(
                writer, sheet_name='gbest')

        # --- Resultados por iteración ---
        pd.DataFrame(ejecucion.resultados).to_excel(
            writer, sheet_name='Resultados', index=False)

    buffer.seek(0)
    return buffer
