import os

def obtener_rutas_experimento(username, today_str, algorithm, prefijo, ts):
    base_path = "Experiments"

    # Experiments/usuario/algoritmo/fecha
    carpeta = os.path.join(base_path, username, algorithm, today_str)
    os.makedirs(carpeta, exist_ok=True)

    excel_path = os.path.join(
        carpeta, f"{prefijo}-{ts}.xlsx"
    )
    csv_path = os.path.join(
        carpeta, f"{prefijo}-{ts}.csv"
    )

    return excel_path, csv_path
