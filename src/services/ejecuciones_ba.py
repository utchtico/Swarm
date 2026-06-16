# src/services/ejecuciones_ba.py
# Validación, persistencia y exportación específicas del Bat Algorithm.
#
# BA tiene un esquema de parámetros propio (alpha, gamma) que no se parece
# en nada al de la familia PSO (wwi, c1, c2, r1, r2) — por eso vive separado
# de ejecuciones_pso.py en lugar de forzarse dentro de validar_entrada_pso.
# La persistencia (guardar_ejecucion) y el modelo Ejecucion sí son
# genéricos y se reutilizan tal cual desde src.services.ejecuciones_pso.

from io import BytesIO

import pandas as pd

from src.services.ejecuciones_pso import guardar_ejecucion  # genérico, reutilizado

MIN_CRITERIOS    = 5
MIN_ALTERNATIVAS = 9

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


def validar_entrada_ba(payload: dict) -> dict:
    """
    Valida y normaliza el payload JSON del frontend para BA.
    Lanza ValueError con un mensaje claro si algo no cuadra.

    Estructura esperada:
    {
      "matriz": [[...], ...],   # a filas x n columnas
      "alpha": 2.5, "gamma": 2.5, "T": 10
    }

    Nota: BA no recibe pesos por criterio (w) ni vectores r1/r2 — su
    función objetivo no los usa (ver src/algoritmos/ba.py).
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

    return {'matriz': matriz, 'alpha': alpha, 'gamma': gamma, 'T': T}


def generar_plantilla_excel_ba(n_criterios: int = MIN_CRITERIOS,
                               n_alternativas: int = MIN_ALTERNATIVAS) -> BytesIO:
    """
    Genera un libro de 3 hojas para capturar un experimento de BA offline:
      Instrucciones | Matriz | Parametros (alpha, gamma, T)
    Sin hoja de Vectores: BA no recibe w, R1 ni R2 como entrada.
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
    h.write('A1', 'Plantilla de experimento BA (Bat Algorithm)', fmt_titulo)
    instrucciones = [
        '1. Hoja "Matriz": capture la matriz de decisión. Filas = alternativas (A), '
        'columnas = criterios (C). Solo edite las celdas en azul.',
        '2. BA no requiere pesos por criterio (w) ni vectores R1/R2 como entrada: '
        'su función objetivo evalúa cada alternativa directamente, sin ponderación.',
        '3. Hoja "Parametros": capture alpha (reduce la sonoridad), gamma (incrementa '
        'la tasa de pulso) y la cantidad de iteraciones (T).',
        '4. No cambie el nombre de las hojas ni elimine encabezados; el sistema los usa '
        'para leer el archivo.',
        '5. Guarde el archivo y súbalo en la sección Laboratorio de BA.',
    ]
    for i, t in enumerate(instrucciones):
        h.write(i + 2, 0, t, fmt_texto)
    h.write(len(instrucciones) + 4, 0, '__ALGORITMO__:BA', fmt_oculto)

    h = libro.add_worksheet('Matriz')
    h.write(0, 0, '', fmt_header)
    for c, nombre in enumerate(cols):
        h.write(0, c + 1, nombre, fmt_header)
        h.set_column(c + 1, c + 1, 10)
    for f, nombre in enumerate(filas):
        h.write(f + 1, 0, nombre, fmt_header)
        for c in range(n):
            h.write_blank(f + 1, c + 1, None, fmt_entrada)

    h = libro.add_worksheet('Parametros')
    h.set_column('A:A', 28)
    h.set_column('B:B', 12)
    h.write(0, 0, 'Parametro', fmt_header)
    h.write(0, 1, 'Valor', fmt_header)
    defaults = [('alpha', 2.5), ('gamma', 2.5), ('T (iteraciones)', 10)]
    for i, (nombre, valor) in enumerate(defaults):
        h.write(i + 1, 0, nombre, fmt_param)
        h.write(i + 1, 1, valor, fmt_entrada)

    libro.close()
    buffer.seek(0)
    return buffer


def parsear_plantilla_excel_ba(archivo) -> dict:
    """
    Lee una plantilla de BA llenada y devuelve el payload listo para
    validar_entrada_ba. Lanza ValueError con mensajes claros si el
    archivo no cumple el formato.
    """
    try:
        hojas = pd.read_excel(archivo, sheet_name=None, index_col=0)
        archivo.seek(0)
    except Exception:
        raise ValueError("No se pudo leer el archivo. Verifique que sea un .xlsx válido.")

    for requerida in ('Matriz', 'Parametros'):
        if requerida not in hojas:
            raise ValueError(f"Falta la hoja '{requerida}' en la plantilla.")

    dfm = hojas['Matriz']
    if dfm.isna().any().any():
        raise ValueError("La hoja 'Matriz' tiene celdas vacías; complete todos los valores.")
    try:
        matriz = [[float(v) for v in fila] for fila in dfm.values.tolist()]
    except (TypeError, ValueError):
        raise ValueError("La hoja 'Matriz' contiene valores no numéricos.")

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
        'alpha': float(valores['alpha']),
        'gamma': float(valores['gamma']),
        'T': int(valores['t']),
        'algoritmo_detectado': 'BA',
    }
