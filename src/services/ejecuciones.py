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


def generar_plantilla_excel(n_criterios: int = 5, n_alternativas: int = 9) -> BytesIO:
    """
    Genera el machote de Excel para capturar un experimento offline.
    Hojas: Instrucciones, Matriz (a x n), Parametros (w/R1/R2 por criterio
    + escalares wwi/c1/c2/T). Se puede ampliar agregando filas/columnas
    directamente en el archivo: al subirlo, las dimensiones se leen de la hoja.
    """
    n = max(n_criterios, MIN_CRITERIOS)
    a = max(n_alternativas, MIN_ALTERNATIVAS)
    cols = [f'C{i+1}' for i in range(n)]
    idx = [f'A{j+1}' for j in range(a)]

    # Prellenado con el caso de estudio donde aplica, 0.050 en celdas nuevas
    valores = [[MATRIZ_DEFAULT[f][c] if f < len(MATRIZ_DEFAULT) and c < len(MATRIZ_DEFAULT[0])
                else 0.050 for c in range(n)] for f in range(a)]
    w_def = [0.400, 0.200, 0.030, 0.070, 0.300]
    r1_def = [0.4657, 0.8956, 0.3877, 0.4902, 0.5039]
    r2_def = [0.5319, 0.8185, 0.8331, 0.7677, 0.1708]
    rellena = lambda base, largo, defecto: [base[i] if i < len(base) else defecto
                                            for i in range(largo)]

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        pd.DataFrame({'Instrucciones': [
            'PLANTILLA DE EXPERIMENTO PSO',
            '',
            '1. Hoja "Matriz": capture la matriz de decisión.',
            '   - Filas = alternativas (A1, A2, ...), columnas = criterios (C1, C2, ...).',
            f'   - Puede agregar filas y columnas (mínimo {MIN_ALTERNATIVAS} x {MIN_CRITERIOS}).',
            '   - Mantenga los encabezados con el formato A# / C#.',
            '2. Hoja "Parametros": capture w, R1 y R2 (un valor por criterio,',
            '   las columnas deben coincidir con las de la Matriz) y los',
            '   escalares wwi, c1, c2 y T.',
            '3. Guarde el archivo y súbalo en la sección Laboratorio con',
            '   el botón "Cargar plantilla".',
        ]}).to_excel(writer, sheet_name='Instrucciones', index=False)

        pd.DataFrame(valores, columns=cols, index=idx).to_excel(writer, sheet_name='Matriz')

        param_filas = pd.DataFrame(
            [rellena(w_def, n, 0.100), rellena(r1_def, n, 0.5000), rellena(r2_def, n, 0.5000)],
            columns=cols, index=['w', 'R1', 'R2'])
        param_filas.to_excel(writer, sheet_name='Parametros', startrow=0)
        pd.DataFrame({'Parametro': ['wwi', 'c1', 'c2', 'T'],
                      'Valor': [0.7, 2.5, 2.5, 10]}).to_excel(
            writer, sheet_name='Parametros', startrow=6, index=False)

    buffer.seek(0)
    return buffer


def parsear_plantilla_excel(archivo) -> dict:
    """
    Lee un machote llenado y devuelve el payload listo para validar_entrada_pso.
    archivo: file-like (request.files['archivo']).
    Lanza ValueError con mensaje claro ante cualquier problema de formato.
    """
    try:
        matriz_df = pd.read_excel(archivo, sheet_name='Matriz', index_col=0)
        archivo.seek(0)
        params_df = pd.read_excel(archivo, sheet_name='Parametros', index_col=0, nrows=3)
        archivo.seek(0)
        escalares_df = pd.read_excel(archivo, sheet_name='Parametros', skiprows=6)
    except ValueError as e:
        raise ValueError(f"No se pudo leer la plantilla: {e}. "
                         "Verifique que existan las hojas 'Matriz' y 'Parametros'.")

    matriz_df = matriz_df.dropna(how='all').dropna(axis=1, how='all')
    if matriz_df.isna().any().any():
        raise ValueError("La hoja 'Matriz' tiene celdas vacías dentro del rango de datos.")

    n = matriz_df.shape[1]

    def _fila_param(nombre):
        if nombre not in params_df.index:
            raise ValueError(f"Falta la fila '{nombre}' en la hoja 'Parametros'.")
        fila = params_df.loc[nombre].dropna()
        if len(fila) != n:
            raise ValueError(f"'{nombre}' tiene {len(fila)} valores; la matriz tiene {n} criterios.")
        return [float(v) for v in fila]

    escalares = dict(zip(escalares_df.iloc[:, 0], escalares_df.iloc[:, 1]))
    for clave in ('wwi', 'c1', 'c2', 'T'):
        if clave not in escalares or pd.isna(escalares[clave]):
            raise ValueError(f"Falta el valor de '{clave}' en la hoja 'Parametros'.")

    return {
        'matriz': [[float(v) for v in fila] for fila in matriz_df.values],
        'w': _fila_param('w'),
        'r1': _fila_param('R1'),
        'r2': _fila_param('R2'),
        'wwi': float(escalares['wwi']),
        'c1': float(escalares['c1']),
        'c2': float(escalares['c2']),
        'T': int(escalares['T']),
    }


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
        # Gráfica de convergencia nativa sobre los datos de la hoja GBF
        n_iter = len(ejecucion.historico_gbf)
        if n_iter > 1:
            libro = writer.book
            chart = libro.add_chart({'type': 'line'})
            chart.add_series({
                'name': 'GBF (Global Best Fitness)',
                'categories': ['GBF', 1, 0, n_iter, 0],
                'values': ['GBF', 1, 1, n_iter, 1],
                'line': {'color': '#3B82F6', 'width': 2.25},
                'marker': {'type': 'circle', 'size': 5,
                           'fill': {'color': '#3B82F6'}},
            })
            chart.set_title({'name': 'Convergencia del algoritmo'})
            chart.set_x_axis({'name': 'Iteración'})
            chart.set_y_axis({'name': 'GBF'})
            chart.set_legend({'none': True})
            chart.set_size({'width': 640, 'height': 380})
            writer.sheets['GBF'].insert_chart('D2', chart)

        if hist.get('gbest'):
            pd.DataFrame(hist['gbest'], columns=['gbest']).to_excel(
                writer, sheet_name='gbest')

        # --- Resultados por iteración ---
        pd.DataFrame(ejecucion.resultados).to_excel(
            writer, sheet_name='Resultados', index=False)

    buffer.seek(0)
    return buffer


# =====================================================================
# PLANTILLA EXCEL ("machote"): descarga para llenar offline y re-subida
# =====================================================================

def generar_plantilla_excel(n_criterios: int = MIN_CRITERIOS,
                            n_alternativas: int = MIN_ALTERNATIVAS) -> BytesIO:
    """
    Genera un libro con 4 hojas para capturar un experimento offline:
      Instrucciones | Matriz | Vectores (w, R1, R2) | Parametros
    Las celdas a llenar van en azul (convención: entradas del usuario).
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
                                   'bg_color': '#E2E8F0', 'border': 1,
                                   'align': 'center'})
    fmt_entrada = libro.add_format({'font_name': 'Arial', 'font_color': '#0000FF',
                                    'border': 1, 'num_format': '0.000'})
    fmt_param = libro.add_format({'font_name': 'Arial', 'border': 1})

    # --- Instrucciones ---
    h = libro.add_worksheet('Instrucciones')
    h.set_column('A:A', 90)
    h.write('A1', 'Plantilla de experimento PSO', fmt_titulo)
    instrucciones = [
        '1. Hoja "Matriz": capture la matriz de decisión. Filas = alternativas (A), '
        'columnas = criterios (C). Solo edite las celdas en azul.',
        '2. Hoja "Vectores": capture el peso w y los vectores R1 y R2, un valor por criterio.',
        '3. Hoja "Parametros": capture el peso de inercia (wwi), c1, c2 y la cantidad '
        'de iteraciones (T).',
        '4. No cambie el nombre de las hojas ni elimine encabezados; el sistema los usa '
        'para leer el archivo.',
        '5. Guarde el archivo y súbalo en la sección Laboratorio del algoritmo PSO.',
    ]
    for i, t in enumerate(instrucciones):
        h.write(i + 2, 0, t, fmt_texto)

    # --- Matriz ---
    h = libro.add_worksheet('Matriz')
    h.write(0, 0, '', fmt_header)
    for c, nombre in enumerate(cols):
        h.write(0, c + 1, nombre, fmt_header)
        h.set_column(c + 1, c + 1, 10)
    for f, nombre in enumerate(filas):
        h.write(f + 1, 0, nombre, fmt_header)
        for c in range(n):
            h.write_blank(f + 1, c + 1, None, fmt_entrada)

    # --- Vectores ---
    h = libro.add_worksheet('Vectores')
    h.write(0, 0, '', fmt_header)
    for c, nombre in enumerate(cols):
        h.write(0, c + 1, nombre, fmt_header)
        h.set_column(c + 1, c + 1, 10)
    for f, nombre in enumerate(['w', 'R1', 'R2']):
        h.write(f + 1, 0, nombre, fmt_header)
        for c in range(n):
            h.write_blank(f + 1, c + 1, None, fmt_entrada)

    # --- Parametros ---
    h = libro.add_worksheet('Parametros')
    h.set_column('A:A', 28)
    h.set_column('B:B', 12)
    h.write(0, 0, 'Parametro', fmt_header)
    h.write(0, 1, 'Valor', fmt_header)
    defaults = [('wwi (peso de inercia)', 0.7), ('c1', 2.5), ('c2', 2.5),
                ('T (iteraciones)', 10)]
    for i, (nombre, valor) in enumerate(defaults):
        h.write(i + 1, 0, nombre, fmt_param)
        h.write(i + 1, 1, valor, fmt_entrada)

    libro.close()
    buffer.seek(0)
    return buffer


def parsear_plantilla_excel(archivo) -> dict:
    """
    Lee una plantilla llenada y devuelve el payload listo para validar_entrada_pso.
    Lanza ValueError con mensajes claros si el archivo no cumple el formato.
    """
    try:
        hojas = pd.read_excel(archivo, sheet_name=None, index_col=0)
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
    if dfv.isna().any().any():
        raise ValueError("La hoja 'Vectores' tiene celdas vacías; complete w, R1 y R2.")
    vectores = {str(idx).strip().lower(): fila for idx, fila in
                zip(dfv.index, dfv.values.tolist())}
    faltantes = [v for v in ('w', 'r1', 'r2') if v not in vectores]
    if faltantes:
        raise ValueError(f"En la hoja 'Vectores' faltan las filas: {', '.join(faltantes)}.")

    dfp = hojas['Parametros']
    valores = {}
    for idx, fila in zip(dfp.index, dfp.values.tolist()):
        clave = str(idx).split('(')[0].strip().lower()
        valores[clave] = fila[0]
    for p in ('wwi', 'c1', 'c2', 't'):
        if p not in valores or pd.isna(valores[p]):
            raise ValueError(f"En la hoja 'Parametros' falta el valor de '{p}'.")

    return {
        'matriz': matriz,
        'w':  [float(v) for v in vectores['w']],
        'r1': [float(v) for v in vectores['r1']],
        'r2': [float(v) for v in vectores['r2']],
        'wwi': float(valores['wwi']),
        'c1': float(valores['c1']),
        'c2': float(valores['c2']),
        'T': int(valores['t']),
    }