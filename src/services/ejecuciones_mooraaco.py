# src/services/ejecuciones_mooraaco.py
# Validación, plantilla Excel y exportación específicas de MOORA-ACO.
#
# MOORA-ACO recibe w, EV (por criterio — cambio de diseño confirmado frente
# al selector global del HTML original) y los parámetros de ACO (alpha,
# beta, rho, Q, n_ants, T). La persistencia (guardar_ejecucion) es genérica
# y se reutiliza desde ejecuciones_pso.py.

from io import BytesIO

import pandas as pd

from src.services.ejecuciones_pso import guardar_ejecucion  # genérico, reutilizado

MIN_CRITERIOS    = 5
MIN_ALTERNATIVAS = 9
EV_VALIDOS = {'Max', 'Min'}

MATRIZ_DEFAULT = [
    [0.048, 0.047, 0.070, 0.087, 0.190],
    [0.053, 0.052, 0.066, 0.081, 0.058],
    [0.057, 0.057, 0.066, 0.076, 0.022],
    [0.062, 0.062, 0.063, 0.058, 0.007],
    [0.066, 0.066, 0.070, 0.085, 0.004],
    [0.070, 0.071, 0.066, 0.058, 0.003],
    [0.075, 0.075, 0.066, 0.047, 0.002],
    [0.079, 0.079, 0.066, 0.035, 0.002],
    [0.083, 0.083, 0.066, 0.051, 0.001],  # 0.001, no 0.000 — ACO divide por cada valor
]


def validar_entrada_mooraaco(payload: dict) -> dict:
    """
    Valida y normaliza el payload JSON del frontend para MOORA-ACO.

    Estructura esperada:
    {
      "matriz": [[...], ...],   # a filas x n columnas, todos los valores > 0
      "w": [...],               # longitud n
      "EV": ["Min", "Max", ...] # longitud n, cada valor "Min" o "Max"
      "alpha": 1, "beta": 2, "rho": 0.1, "Q": 100, "n_ants": 5, "T": 10
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
    if any(v <= 0 for fila in matriz for v in fila):
        raise ValueError("Todos los valores de 'matriz' deben ser mayores a 0 "
                         "(ACO calcula una heurística 1/valor).")

    w = payload.get('w')
    if not isinstance(w, list):
        raise ValueError(f"'w' debe ser una lista numérica de longitud {n}.")
    if len(w) != n:
        raise ValueError(f"'w' debe tener un valor por criterio: longitud {n}, recibió {len(w)}.")
    try:
        w = [float(v) for v in w]
    except (TypeError, ValueError):
        raise ValueError("Todos los valores de 'w' deben ser numéricos.")

    EV = payload.get('EV')
    if not isinstance(EV, list):
        raise ValueError(f"'EV' debe ser una lista de longitud {n} con valores 'Max' o 'Min'.")
    if len(EV) != n:
        raise ValueError(f"'EV' debe tener un valor por criterio: longitud {n}, recibió {len(EV)}.")
    if not all(ev in EV_VALIDOS for ev in EV):
        raise ValueError("Cada valor de 'EV' debe ser 'Max' o 'Min'.")

    def _float(nombre):
        try:
            return float(payload[nombre])
        except KeyError:
            raise ValueError(f"Falta el parámetro '{nombre}'.")
        except (TypeError, ValueError):
            raise ValueError(f"'{nombre}' debe ser numérico.")

    alpha = _float('alpha')
    beta  = _float('beta')
    rho   = _float('rho')
    if not (0 < rho < 1):
        raise ValueError("'rho' debe estar entre 0 y 1 (tasa de evaporación).")
    Q = _float('Q')

    def _int(nombre):
        try:
            return int(payload[nombre])
        except KeyError:
            raise ValueError(f"Falta el parámetro '{nombre}'.")
        except (TypeError, ValueError):
            raise ValueError(f"'{nombre}' debe ser un entero.")

    n_ants = _int('n_ants')
    if n_ants < 1:
        raise ValueError("'n_ants' debe ser al menos 1.")

    T = _int('T')
    if T < 1:
        raise ValueError("'T' debe ser al menos 1.")

    return {'matriz': matriz, 'w': w, 'EV': EV, 'alpha': alpha, 'beta': beta,
            'rho': rho, 'Q': Q, 'n_ants': n_ants, 'T': T}


def generar_plantilla_excel_mooraaco(n_criterios: int = MIN_CRITERIOS,
                                     n_alternativas: int = MIN_ALTERNATIVAS) -> BytesIO:
    """
    Genera un libro de 4 hojas para capturar un experimento de MOORA-ACO offline:
      Instrucciones | Matriz | Vectores (w y EV) | Parametros
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
    fmt_entrada_texto = libro.add_format({'font_name': 'Arial', 'font_color': '#0000FF', 'border': 1})
    fmt_param = libro.add_format({'font_name': 'Arial', 'border': 1})
    fmt_oculto = libro.add_format({'font_color': '#FFFFFF', 'font_size': 1})

    h = libro.add_worksheet('Instrucciones')
    h.set_column('A:A', 90)
    h.write('A1', 'Plantilla de experimento MOORA-ACO', fmt_titulo)
    instrucciones = [
        '1. Hoja "Matriz": capture la matriz de decisión. Filas = alternativas (A), '
        'columnas = criterios (C). Solo edite las celdas en azul. Todos los valores '
        'deben ser mayores a 0, ya que ACO calcula una heurística 1/valor.',
        '2. Hoja "Vectores": capture el peso w y la evaluación cardinal EV ("Max" o '
        '"Min") de cada criterio. MOORA-ACO permite un EV distinto por criterio.',
        '3. Hoja "Parametros": capture alpha (peso de feromona), beta (peso heurístico), '
        'rho (tasa de evaporación, entre 0 y 1), Q (feromona depositada), n_ants '
        '(número de hormigas) y T, que representa tanto el número de repeticiones '
        'independientes del experimento como el número de pasos internos de cada una.',
        '4. No cambie el nombre de las hojas ni elimine encabezados; el sistema los usa '
        'para leer el archivo.',
        '5. Guarde el archivo y súbalo en la sección Laboratorio de MOORA-ACO.',
    ]
    for i, t in enumerate(instrucciones):
        h.write(i + 2, 0, t, fmt_texto)
    h.write(len(instrucciones) + 4, 0, '__ALGORITMO__:MOORAACO', fmt_oculto)

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
    h.write(2, 0, 'EV', fmt_header)
    for c in range(n):
        h.write(2, c + 1, 'Min', fmt_entrada_texto)

    h = libro.add_worksheet('Parametros')
    h.set_column('A:A', 28)
    h.set_column('B:B', 12)
    h.write(0, 0, 'Parametro', fmt_header)
    h.write(0, 1, 'Valor', fmt_header)
    defaults = [('alpha', 1), ('beta', 2), ('rho', 0.1), ('Q', 100),
                ('n_ants', 5), ('T (repeticiones/pasos)', 10)]
    for i, (nombre, valor) in enumerate(defaults):
        h.write(i + 1, 0, nombre, fmt_param)
        h.write(i + 1, 1, valor, fmt_entrada)

    libro.close()
    buffer.seek(0)
    return buffer


def parsear_plantilla_excel_mooraaco(archivo) -> dict:
    """
    Lee una plantilla de MOORA-ACO llenada y devuelve el payload listo para
    validar_entrada_mooraaco.
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
    if 'ev' not in vectores:
        raise ValueError("En la hoja 'Vectores' falta la fila 'EV'.")
    EV = [str(v).strip().capitalize() for v in vectores['ev']]
    if not all(ev in EV_VALIDOS for ev in EV):
        raise ValueError("Cada valor de 'EV' en la hoja 'Vectores' debe ser 'Max' o 'Min'.")

    dfp = hojas['Parametros']
    valores = {}
    for idx, fila in zip(dfp.index, dfp.values.tolist()):
        clave = str(idx).split('(')[0].strip().lower()
        valores[clave] = fila[0]
    for p in ('alpha', 'beta', 'rho', 'q', 'n_ants', 't'):
        if p not in valores or pd.isna(valores[p]):
            raise ValueError(f"En la hoja 'Parametros' falta el valor de '{p}'.")

    return {
        'matriz': matriz,
        'w': [float(v) for v in vectores['w']],
        'EV': EV,
        'alpha': float(valores['alpha']),
        'beta': float(valores['beta']),
        'rho': float(valores['rho']),
        'Q': float(valores['q']),
        'n_ants': int(valores['n_ants']),
        'T': int(valores['t']),
        'algoritmo_detectado': 'MOORAACO',
    }
