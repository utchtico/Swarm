# src/services/ejecuciones_pso.py
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

# Algoritmos de la familia PSO que sí reciben R1/R2 como entrada del usuario.
# Los demás (DA-PSO, MOORA-PSO, TOPSIS-PSO) los derivan internamente del
# ranking de su método — ver tiene_r1r2 en ALGO_CONFIG del frontend.
ALGORITMOS_CON_R1R2 = {'PSO'}

NOMBRES_ALGORITMO = {
    'PSO':       'PSO',
    'DAPSO':     'DA-PSO',
    'MOORAPSO':  'MOORA-PSO',
    'TOPSISPSO': 'TOPSIS-PSO',
}


def generar_plantilla_excel(n_criterios: int = MIN_CRITERIOS,
                            n_alternativas: int = MIN_ALTERNATIVAS,
                            algoritmo: str = 'PSO') -> BytesIO:
    """
    Genera un libro para capturar un experimento offline, ajustado a la
    variante de PSO indicada:
      Instrucciones | Matriz | Vectores (w[, R1, R2]) | Parametros

    algoritmo : 'PSO' | 'DAPSO' | 'MOORAPSO' | 'TOPSISPSO'
                Determina si la hoja Vectores incluye R1/R2 y queda
                registrado en la hoja Instrucciones para que el sistema
                sepa qué variante es al volver a cargar el archivo.
    """
    algoritmo = (algoritmo or 'PSO').upper()
    if algoritmo not in NOMBRES_ALGORITMO:
        algoritmo = 'PSO'
    tiene_r1r2 = algoritmo in ALGORITMOS_CON_R1R2
    nombre_legible = NOMBRES_ALGORITMO[algoritmo]

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
    fmt_nota = libro.add_format({'font_name': 'Arial', 'italic': True,
                                 'font_color': '#6B7280', 'text_wrap': True})
    # Celda oculta donde se guarda el identificador de algoritmo — el sistema
    # la lee al volver a subir el archivo; el usuario no necesita tocarla.
    fmt_oculto = libro.add_format({'font_color': '#FFFFFF', 'font_size': 1})

    # --- Instrucciones ---
    h = libro.add_worksheet('Instrucciones')
    h.set_column('A:A', 90)
    h.write('A1', f'Plantilla de experimento {nombre_legible}', fmt_titulo)
    instrucciones = [
        '1. Hoja "Matriz": capture la matriz de decisión. Filas = alternativas (A), '
        'columnas = criterios (C). Solo edite las celdas en azul.',
    ]
    if tiene_r1r2:
        instrucciones.append(
            '2. Hoja "Vectores": capture el peso w y los vectores R1 y R2, '
            'un valor por criterio.')
    else:
        instrucciones.append(
            '2. Hoja "Vectores": capture únicamente el peso w, un valor por '
            f'criterio. {nombre_legible} no requiere R1 ni R2 como entrada: '
            'el algoritmo los calcula automáticamente a partir del ranking '
            'de su propio método de decisión multicriterio en cada iteración.')
    instrucciones += [
        '3. Hoja "Parametros": capture el peso de inercia (wwi), c1, c2 y la cantidad '
        'de iteraciones (T).',
        '4. No cambie el nombre de las hojas ni elimine encabezados; el sistema los usa '
        'para leer el archivo.',
        f'5. Guarde el archivo y súbalo en la sección Laboratorio de {nombre_legible}.',
    ]
    for i, t in enumerate(instrucciones):
        h.write(i + 2, 0, t, fmt_texto)

    fila_marca = len(instrucciones) + 4
    h.write(fila_marca, 0, f'__ALGORITMO__:{algoritmo}', fmt_oculto)

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

    filas_vector = ['w', 'R1', 'R2'] if tiene_r1r2 else ['w']
    for f, nombre in enumerate(filas_vector):
        h.write(f + 1, 0, nombre, fmt_header)
        for c in range(n):
            h.write_blank(f + 1, c + 1, None, fmt_entrada)

    if not tiene_r1r2:
        fila_nota = len(filas_vector) + 2
        h.merge_range(fila_nota, 0, fila_nota, n,
                      f'R1 y R2 no aplican a {nombre_legible}: se derivan '
                      'automáticamente del ranking del método y no se '
                      'capturan en esta plantilla.', fmt_nota)

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


def _detectar_algoritmo_instrucciones(archivo) -> str:
    """
    Lee la hoja 'Instrucciones' buscando la marca __ALGORITMO__:<NOMBRE>
    escrita por generar_plantilla_excel. Si no la encuentra (plantilla
    antigua o editada a mano), asume PSO por compatibilidad.
    """
    try:
        df_instr = pd.read_excel(archivo, sheet_name='Instrucciones', header=None)
        archivo.seek(0)
    except Exception:
        return 'PSO'

    for valor in df_instr.values.flatten():
        texto = str(valor)
        if texto.startswith('__ALGORITMO__:'):
            candidato = texto.split(':', 1)[1].strip().upper()
            if candidato in NOMBRES_ALGORITMO:
                return candidato
    return 'PSO'


def parsear_plantilla_excel(archivo, algoritmo_esperado: str = None) -> dict:
    """
    Lee una plantilla llenada y devuelve el payload listo para validar_entrada_pso.
    Lanza ValueError con mensajes claros si el archivo no cumple el formato.

    El algoritmo de la plantilla se detecta automáticamente desde la marca
    oculta en la hoja Instrucciones. Si algoritmo_esperado se indica y no
    coincide con el detectado, se rechaza el archivo para evitar cargar,
    por ejemplo, una plantilla de DA-PSO en el laboratorio de PSO.

    El payload de retorno incluye 'algoritmo_detectado' para que el llamador
    pueda informar al usuario qué variante se cargó.
    """
    try:
        hojas = pd.read_excel(archivo, sheet_name=None, index_col=0)
        archivo.seek(0)
    except Exception:
        raise ValueError("No se pudo leer el archivo. Verifique que sea un .xlsx válido.")

    algoritmo_detectado = _detectar_algoritmo_instrucciones(archivo)
    tiene_r1r2 = algoritmo_detectado in ALGORITMOS_CON_R1R2

    if algoritmo_esperado:
        algoritmo_esperado = algoritmo_esperado.upper()
        if algoritmo_esperado != algoritmo_detectado:
            nombre_esp = NOMBRES_ALGORITMO.get(algoritmo_esperado, algoritmo_esperado)
            nombre_det = NOMBRES_ALGORITMO.get(algoritmo_detectado, algoritmo_detectado)
            raise ValueError(
                f"Esta plantilla corresponde a {nombre_det}, pero intenta "
                f"cargarla en el laboratorio de {nombre_esp}. Descargue la "
                f"plantilla correcta desde {nombre_esp} o cárguela en su "
                "laboratorio correspondiente.")

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

    filas_requeridas = ('w', 'r1', 'r2') if tiene_r1r2 else ('w',)
    faltantes = [v for v in filas_requeridas if v not in vectores]
    if faltantes:
        raise ValueError(f"En la hoja 'Vectores' faltan las filas: {', '.join(faltantes)}.")
    if any(pd.isna(v) for v in vectores.get('w', [])):
        raise ValueError("La hoja 'Vectores' tiene celdas vacías en 'w'.")
    if tiene_r1r2 and (any(pd.isna(v) for v in vectores.get('r1', []))
                       or any(pd.isna(v) for v in vectores.get('r2', []))):
        raise ValueError("La hoja 'Vectores' tiene celdas vacías en R1 o R2.")

    dfp = hojas['Parametros']
    valores = {}
    for idx, fila in zip(dfp.index, dfp.values.tolist()):
        clave = str(idx).split('(')[0].strip().lower()
        valores[clave] = fila[0]
    for p in ('wwi', 'c1', 'c2', 't'):
        if p not in valores or pd.isna(valores[p]):
            raise ValueError(f"En la hoja 'Parametros' falta el valor de '{p}'.")

    resultado = {
        'matriz': matriz,
        'w':  [float(v) for v in vectores['w']],
        'wwi': float(valores['wwi']),
        'c1': float(valores['c1']),
        'c2': float(valores['c2']),
        'T': int(valores['t']),
        'algoritmo_detectado': algoritmo_detectado,
    }
    if tiene_r1r2:
        resultado['r1'] = [float(v) for v in vectores['r1']]
        resultado['r2'] = [float(v) for v in vectores['r2']]
    else:
        # El algoritmo los deriva internamente; se rellenan en 0 para que
        # validar_entrada_pso (que siempre exige r1/r2 por firma) no falle.
        n = len(resultado['w'])
        resultado['r1'] = [0.0] * n
        resultado['r2'] = [0.0] * n

    return resultado