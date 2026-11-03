# src/services/limites.py
# Topes máximos de entrada para todos los algoritmos.
#
# Sin estos límites, una sola petición con T, n_ants o una matriz enormes
# puede dejar al servidor ocupado durante minutos y guardar historiales
# gigantes en la base de datos. Los valores por defecto de la matriz
# coinciden con los que ya impone el frontend (static/js/*/laboratorio.js).
# Todos se pueden ajustar desde el .env sin tocar código.

import os

# Mismos mínimos que en cada servicio (matriz original 9x5). Se repiten aquí
# en vez de importarlos para que los servicios puedan importar este módulo
# sin crear un ciclo de imports.
MIN_CRITERIOS    = 5
MIN_ALTERNATIVAS = 9


def _entero_env(nombre: str, defecto: int) -> int:
    try:
        valor = int(os.environ.get(nombre, defecto))
    except (TypeError, ValueError):
        return defecto
    return valor if valor >= 1 else defecto


MAX_CRITERIOS    = _entero_env('MAX_CRITERIOS', 20)
MAX_ALTERNATIVAS = _entero_env('MAX_ALTERNATIVAS', 30)
MAX_T            = _entero_env('MAX_ITERACIONES', 1000)
MAX_N_ANTS       = _entero_env('MAX_N_ANTS', 1000)


def verificar_max_dimensiones(n: int, a: int) -> None:
    """Lanza ValueError si la matriz excede los criterios o alternativas permitidos."""
    if n > MAX_CRITERIOS:
        raise ValueError(f"La matriz admite como máximo {MAX_CRITERIOS} criterios (recibió {n}).")
    if a > MAX_ALTERNATIVAS:
        raise ValueError(f"La matriz admite como máximo {MAX_ALTERNATIVAS} alternativas (recibió {a}).")


def verificar_max_T(T: int) -> None:
    if T > MAX_T:
        raise ValueError(f"'T' admite como máximo {MAX_T} iteraciones (recibió {T}).")


def verificar_max_n_ants(n_ants: int) -> None:
    if n_ants > MAX_N_ANTS:
        raise ValueError(f"'n_ants' admite como máximo {MAX_N_ANTS} hormigas (recibió {n_ants}).")


def dimensiones_plantilla(args) -> tuple[int, int]:
    """
    Lee ?criterios= y ?alternativas= de la query string para generar una
    plantilla Excel. Valores no numéricos usan el mínimo; los demás se
    ajustan al rango [mínimo, máximo] permitido.
    """
    def _leer(clave, minimo, maximo):
        try:
            valor = int(args.get(clave, minimo))
        except (TypeError, ValueError):
            valor = minimo
        return max(minimo, min(valor, maximo))

    return (_leer('criterios', MIN_CRITERIOS, MAX_CRITERIOS),
            _leer('alternativas', MIN_ALTERNATIVAS, MAX_ALTERNATIVAS))
