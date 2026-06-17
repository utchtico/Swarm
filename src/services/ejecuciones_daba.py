# src/services/ejecuciones_daba.py
# Validación, plantilla Excel y exportación específicas de DA-BA.
#
# A diferencia de BA puro, DA-BA SÍ recibe pesos por criterio (w): el método
# DA los usa para ponderar el índice de similitud en cada iteración. No
# recibe r1/r2 (eso es exclusivo de la familia PSO). La persistencia
# (guardar_ejecucion) es genérica y se reutiliza desde ejecuciones_pso.py.

from io import BytesIO

import pandas as pd

from src.services.ejecuciones_pso import guardar_ejecucion  # genérico, reutilizado

MIN_CRITERIOS    = 5
MIN_ALTERNATIVAS = 9

MATRIZ_DEFAULT = [
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


def validar_entrada_daba(payload: dict) -> dict:
    """
    Valida y normaliza el payload JSON del frontend para DA-BA.

    Estructura esperada:
    {
      "matriz": [[...], ...],   # a filas x n columnas
      "w": [...],               # longitud n — pondera el índice de similitud DA
      "alpha": 0.9, "gamma": 0.9, "T": 10
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

    w = payload.get('w')
    if not isinstance(w, list):
        raise ValueError(f"'w' debe ser una lista numérica de longitud {n}.")
    if len(w) != n:
        raise ValueError(f"'w' debe tener un valor por criterio: longitud {n}, recibió {len(w)}.")
    try:
        w = [float(v) for v in w]
    except (TypeError, ValueError):
        raise ValueError("Todos los valores de 'w' deben ser numéricos.")

    def _float(nombre):
        try:
            return float(payload[nombre])
        except KeyError:
            raise ValueError(f"Falta el parámetro '{nombre}'.")
        except (TypeError, ValueError):
            raise ValueError(f"'{nombre}' debe ser numérico.")

    alpha = _float('alpha')
    gamma = _float('gamma')

    try:
        T = int(payload['T'])
    except KeyError:
        raise ValueError("Falta el parámetro 'T'.")
    except (TypeError, ValueError):
        raise ValueError("'T' debe ser un entero.")
    if T < 1:
        raise ValueError("'T' debe ser al menos 1.")

    return {'matriz': matriz, 'w': w, 'alpha': alpha, 'gamma': gamma, 'T': T}


def generar_plantilla_excel_daba(n_criterios: int = MIN_CRITERIOS,
                                 n_alternativas: int = MIN_ALTERNATIVAS) -> BytesIO:
    """
    Genera un libro de 4 hojas para capturar un experimento de DA-BA offline:
      Instrucciones | Matriz | Vectores (solo w) | Parametros (alpha, gamma, T)
    """
    n = max(int(n_criterios), MIN_CRITERIOS)
    a = max(int(n_alternativas), MIN_ALTERNATIVAS)
    cols = [f'C{i+1}' for i in range(n)]
    filas = [f'A{j+1}' for j in range(a)]

    buffer = BytesIO()
    import xlsxwriter
    libro = xlsxwriter.Workbook(buffer, {'in_memory': True})
    fmt_titulo = libro.add_format({'bold': True, 'font_name': 'Arial', 'font_size': 12})
    fmt_texto = libro.add_format({'font_name': 'Arial', 'text_wrap': True, 'valign': 'top'})
    fmt_header = libro.add_format({'bold': True, 'font_name': 'Arial',
                                   'bg_color': '#E2E8F0', 'border': 1, 'align': 'center'})
    fmt_entrada = libro.add_format({'font_name': 'Arial', 'font_color': '#0000FF',
                                    'border': 1, 'num_format': '0.000'})
    fmt_param = libro.add_format({'font_name': 'Arial', 'border': 1})
    fmt_oculto = libro.add_format({'font_color': '#FFFFFF', 'font_size': 1})

    h = libro.add_worksheet('Instrucciones')
    h.set_column('A:A', 90)
    h.write('A1', 'Plantilla de experimento DA-BA', fmt_titulo)
    instrucciones = [
        '1. Hoja "Matriz": capture la matriz de decisión. Filas = alternativas (A), '
        'columnas = criterios (C). Solo edite las celdas en azul.',
        '2. Hoja "Vectores": capture el peso w, un valor por criterio. DA-BA usa w '
        'para ponderar el índice de similitud del método DA en cada iteración.',
        '3. Hoja "Parametros": capture alpha (reduce la sonoridad), gamma (incrementa '
        'la tasa de pulso) y la cantidad de iteraciones (T).',
        '4. No cambie el nombre de las hojas ni elimine encabezados; el sistema los usa '
        'para leer el archivo.',
        '5. Guarde el archivo y súbalo en la sección Laboratorio de DA-BA.',
    ]
    for i, t in enumerate(instrucciones):
        h.write(i + 2, 0, t, fmt_texto)
    h.write(len(instrucciones) + 4, 0, '__ALGORITMO__:DABA', fmt_oculto)

    h = libro.add_worksheet('Matriz')
    h.write(0, 0, '', fmt_header)
    for c, nombre in enumerate(cols):
        h.write(0, c + 1, nombre, fmt_header)
        h.set_column(c + 1, c + 1, 10)
    for f, nombre in enumerate(filas):
        h.write(f + 1, 0, nombre, fmt_header)
        for c in range(n):
            h.write_blank(f + 1, c + 1, None, fmt_entrada)

    h = libro.add_worksheet('Vectores')
    h.write(0, 0, '', fmt_header)
    for c, nombre in enumerate(cols):
        h.write(0, c + 1, nombre, fmt_header)
        h.set_column(c + 1, c + 1, 10)
    h.write(1, 0, 'w', fmt_header)
    for c in range(n):
        h.write_blank(1, c + 1, None, fmt_entrada)

    h = libro.add_worksheet('Parametros')
    h.set_column('A:A', 28)
    h.set_column('B:B', 12)
    h.write(0, 0, 'Parametro', fmt_header)
    h.write(0, 1, 'Valor', fmt_header)
    defaults = [('alpha', 0.9), ('gamma', 0.9), ('T (iteraciones)', 10)]
    for i, (nombre, valor) in enumerate(defaults):
        h.write(i + 1, 0, nombre, fmt_param)
        h.write(i + 1, 1, valor, fmt_entrada)

    libro.close()
    buffer.seek(0)
    return buffer


def parsear_plantilla_excel_daba(archivo) -> dict:
    """
    Lee una plantilla de DA-BA llenada y devuelve el payload listo para
    validar_entrada_daba.
    """
    try:
        hojas = pd.read_excel(archivo, sheet_name=None, index_col=0)
        archivo.seek(0)
    except Exception:
        raise ValueError("No se pudo leer el archivo. Verifique que sea un .xlsx válido.")

    for requerida in ('Matriz', 'Vectores', 'Parametros'):
        if requerida not in hojas:
            raise ValueError(f"Falta la hoja '{requerida}' en la plantilla.")

    dfm = hojas['Matriz']
    if dfm.isna().any().any():
        raise ValueError("La hoja 'Matriz' tiene celdas vacías; complete todos los valores.")
    try:
        matriz = [[float(v) for v in fila] for fila in dfm.values.tolist()]
    except (TypeError, ValueError):
        raise ValueError("La hoja 'Matriz' contiene valores no numéricos.")

    dfv = hojas['Vectores']
    vectores = {str(idx).strip().lower(): fila for idx, fila in
                zip(dfv.index, dfv.values.tolist())}
    if 'w' not in vectores:
        raise ValueError("En la hoja 'Vectores' falta la fila 'w'.")
    if any(pd.isna(v) for v in vectores['w']):
        raise ValueError("La hoja 'Vectores' tiene celdas vacías en 'w'.")

    dfp = hojas['Parametros']
    valores = {}
    for idx, fila in zip(dfp.index, dfp.values.tolist()):
        clave = str(idx).split('(')[0].strip().lower()
        valores[clave] = fila[0]
    for p in ('alpha', 'gamma', 't'):
        if p not in valores or pd.isna(valores[p]):
            raise ValueError(f"En la hoja 'Parametros' falta el valor de '{p}'.")

    return {
        'matriz': matriz,
        'w': [float(v) for v in vectores['w']],
        'alpha': float(valores['alpha']),
        'gamma': float(valores['gamma']),
        'T': int(valores['t']),
        'algoritmo_detectado': 'DABA',
    }
