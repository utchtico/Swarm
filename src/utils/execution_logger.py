# src/utils/execution_logger.py
# Logger estructurado para trazabilidad de ejecuciones de algoritmos.
# Genera un archivo .log por ejecución en logs/<algoritmo>/ con el mismo
# nivel de detalle que el legacy imprimía por consola.
#
# Uso:
#   from src.utils.execution_logger import ExecutionLogger
#   log = ExecutionLogger('BA', username='admin')
#   log.header(params)
#   log.iteracion(it, FuncObj, IF_maxt, fitness, global_best, ...)
#   log.resumen_final(resultados, hora_inicio, hora_fin)
#   log.close()

import os
from datetime import datetime
from io import StringIO

import pandas as pd


class ExecutionLogger:
    """
    Escribe un archivo .log detallado por ejecución en:
        logs/<algoritmo>/<algoritmo>_<usuario>_<timestamp>.log

    Refleja fielmente la salida que el legacy imprimía por stdout,
    columna por columna, iteración por iteración.
    """

    def __init__(self, algoritmo: str, username: str = 'unknown',
                 base_dir: str = None):
        self.algoritmo = algoritmo.upper()
        self.username  = username or 'unknown'
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]
        self.timestamp = ts

        # logs/<ALGORITMO>/
        if base_dir is None:
            base_dir = os.path.join(
                os.path.abspath(os.path.dirname(os.path.dirname(
                    os.path.dirname(__file__)))),  # raíz del proyecto
                'logs', self.algoritmo
            )
        os.makedirs(base_dir, exist_ok=True)

        filename = f'{self.algoritmo}_{self.username}_{ts}.log'
        self._path = os.path.join(base_dir, filename)
        self._f = open(self._path, 'w', encoding='utf-8')
        self._write(f'# Swarm · {self.algoritmo} · usuario: {self.username}')
        self._write(f'# Inicio: {datetime.now().isoformat()}')
        self._write('')

    # ── API pública ───────────────────────────────────────────────────────────

    def header(self, params: dict, matriz, v_inicial,
               ri, ai, f_inicial, fmin, fmax, rnd):
        """Bloque de inicialización — igual al encabezado del legacy."""
        n = len(matriz)
        d = len(matriz[0])
        cols = [f'C{i+1}' for i in range(d)]
        cands = [f'A{i+1}' for i in range(n)]

        self._sep('Construcción de la matriz de decisión')
        self._df(pd.DataFrame(matriz, index=cands, columns=cols),
                 label='Posición inicial=')
        self._sep('Controles iniciales')
        self._write('Configuración de parámetros:')
        for k, v in params.items():
            self._write(f'             {k} {v}')
        self._write('')
        self._df(pd.DataFrame(v_inicial, index=cands, columns=cols),
                 label='Velocidad inicial=')
        self._write(' Tasa de pulso (Pulse rate)')
        self._write(str(pd.Series(ri)) + '\n')
        self._write(' Sonoridad (Loudness)')
        self._write(str(pd.Series(ai)) + '\n')
        self._write(' Frecuencia')
        self._write(str(pd.DataFrame([f_inicial], columns=cols)) + '\n')
        self._write(f' Rango de frecuencia: [ {fmin} , {fmax} ]')
        self._write(' Valores Aleatorios')
        self._write(str(pd.Series(rnd)) + '\n')
        self._write('-' * 50)

    def iteracion(self, it: int, FuncObj: list, IF_maxt: float,
                  fitness_df, global_best_df,
                  nueva_f_df, v_act_df, x_act_df,
                  nueva_pos_df, nueva_vel_df,
                  IF_maxt_prev: float, IF_maxNt: float,
                  rama: str):
        """Una iteración completa del bucle — mismo formato que el legacy."""
        self._write(f'\n =======================================================')
        self._write(f'ITERACIÓN # {it}\n')
        self._write(f' Función objetivo=  {FuncObj}')
        self._write(f' Función objetivo(min)=  [{IF_maxt}]')
        self._df(fitness_df, label='fitness ')
        self._write('El mejor global local: ')
        self._write(global_best_df.to_string() + '\n')
        self._write(' Nuevas frecuencias: ')
        self._write(nueva_f_df.to_string() + '\n')
        self._write('-----')
        self._df(v_act_df, label='\n velocidad actualizada')
        self._df(x_act_df, label='\n Posición actualizada')
        if rama == 'local':
            self._df(nueva_pos_df, label='\n Nuevas posiciones (paseo local)')
        else:
            self._df(nueva_pos_df, label='\n Nueva posición generada')
            self._df(nueva_vel_df, label='\n Nueva velocidad generada')
        self._write(f'\n fitness_min=  {IF_maxt_prev}')
        self._write(f' nuevo_fitness_min=  {IF_maxNt}\n')

    def resumen_final(self, resultados: list,
                      hora_inicio: datetime, hora_fin: datetime,
                      alpha, gamma, iter_max):
        """Bloque de resultados finales — igual al cierre del legacy."""
        self._write('\n\n**************************')
        self._write('Resultados Finales')
        self._write('**************************')
        self._write('   Iteración   Mejor_alternativa')
        self._write('  ---------------------------------')
        for i, alt in enumerate(resultados):
            self._write(f'        {i + 1}          A {alt}')
        self._write('  ---------------------------------')
        self._write('')
        self._write(f'Algoritmo {self.algoritmo}')
        self._write(f'alpha: {alpha}  gamma: {gamma}  iteraciones: {iter_max}')
        self._write(f'Hora de inicio: {hora_inicio.time()}')
        self._write(f'Hora de finalización: {hora_fin.time()}')
        self._write(f'Tiempo de ejecución: {hora_fin - hora_inicio}')

    def close(self):
        self._f.flush()
        self._f.close()

    @property
    def path(self):
        return self._path

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _write(self, texto: str):
        self._f.write(texto + '\n')

    def _sep(self, titulo: str):
        self._write(f'\n-------------------------------------------')
        self._write(titulo)

    def _df(self, df, label: str = ''):
        if label:
            self._write(label)
        self._write(df.to_string())
        self._write('')
