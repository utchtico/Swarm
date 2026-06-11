# CAMBIOS — Integración Fases 1 y 2 + Reorganización de carpetas (Swarm)

## 📁 NUEVA ESTRUCTURA DE CARPETAS

```
swarm/
├── main.py                  # rutas de algoritmos legacy (se vacía en Fase 3/4)
├── requirements.txt
├── .env.example
├── scripts/setup_postgres.sh
├── docs/                    # ← antes static/doc/ + templates.zip (no se sirve al navegador)
├── src/
│   ├── algoritmos/          # ← antes Layout/   (cómputo puro)
│   ├── comparacion/         # ← antes Compara/  (se reescribe vs PG en Fase 6)
│   ├── api/                 # blueprints HTTP: auth, articles, algoritmos (JSON)
│   ├── services/            # validación, persistencia, exportación Excel
│   ├── models/              # SQLAlchemy
│   ├── utils/
│   └── views.py             # NUEVO: vistas puras (/, /acercade, /casoexperimental,
│                            #        /articulos, /publicaciones) como blueprint
├── templates/               # ← antes static/templates/ (convención Flask)
└── static/                  # solo assets: css, js, img, icons, src
```

Razones: `Layout` no describía su contenido; los templates dentro de `static/`
se servían como archivos planos (cualquiera podía descargar el fuente Jinja
visitando /static/templates/pso.html — detalle de seguridad); los documentos
de prueba no deben vivir bajo `static/`.

### Al integrar con tu repo completo
Mueve los 14 algoritmos restantes de `Layout/` a `src/algoritmos/` —
los imports de main.py ya apuntan ahí (`from src.algoritmos.X import ...`).
No hay más cambios: las URLs públicas no cambiaron, los assets siguen en
`/static/...`, y la BD no se entera.


Este árbol es tu versión de producción CON los cambios ya aplicados.
A diferencia de la entrega anterior (archivos sueltos + parches manuales),
aquí main.py, articles.py y requirements.txt ya vienen modificados.

## ⚠️ BUG CRÍTICO ENCONTRADO EN TU VERSIÓN DE PRODUCCIÓN

`Layout/pso.py` (línea 220) tenía:

    GBPtt = float(GBP.iat[GBP12, i])

`GBP` es un DataFrame de UNA columna; indexar la columna `i` lanza
`IndexError: index 1 is out of bounds` en la **segunda iteración** de
cualquier ejecución con T >= 2. Lo reproduje con tu código tal cual:
**POST /pso en producción está devolviendo 500 ahora mismo.**
(La versión previa usaba `GBP.loc[GBP12]`, que sí funcionaba; el cambio
a `.iat[fila, i]` introdujo la regresión.)

El pso.py refactorizado lo corrige de raíz (`GBP.iloc[GBP12].iloc[0]`).

## Archivos MODIFICADOS respecto a tu zip

| Archivo | Cambio |
|---|---|
| `main.py` | DATABASE_URL desde .env (fallback SQLite), Flask-Migrate, registro de `algoritmos_bp` y `views_bp`, imports `Layout.*` → `src.algoritmos.*`, `Flask(__name__)` sin template_folder, GET /pso ya no lee `request.form`, POST /pso es puente a la implementación nueva (persiste en BD, conserva contrato de pso.js), 5 vistas puras extraídas a src/views.py |
| `src/algoritmos/pso.py` | (antes Layout/pso.py) Refactor completo: matriz dinámica NxM, función pura síncrona, corrige el bug de GBP |
| `src/models/models.py` | + modelo `Ejecucion` (mixto: columnas reales + JSONB), `init_db` consciente de migraciones |
| `src/api/articles.py` | `db.func.datetime('now')` → `db.func.now()` (2 ocurrencias; lo primero era SQLite-only y truena en PG) |
| `requirements.txt` | Re-codificado **UTF-16 → UTF-8** (pip en Linux no lee UTF-16), + Flask-Migrate, + psycopg2-binary |

## Archivos NUEVOS

| Archivo | Propósito |
|---|---|
| `src/services/ejecuciones.py` | Validación de entrada, MATRIZ_DEFAULT (la 9x5 original), persistencia en PG, exportación Excel desde BD |
| `src/api/algoritmos.py` | API JSON: POST /api/algoritmos/pso (matriz dinámica), GET /api/ejecuciones, GET /api/ejecuciones/<id>, GET /api/ejecuciones/<id>/excel |
| `scripts/setup_postgres.sh` | Crea rol y bases doctorado_dev / doctorado_test |
| `.env.example` | Plantilla de variables (copiar a .env) |

## Archivos NO incluidos (los conservas de tu repo)

Los 14 algoritmos restantes de `Layout/` que retiraste del zip. main.py
los sigue importando, así que el árbol corre tal cual en tu repo completo.

## Puesta en marcha

```bash
# 1. PostgreSQL
chmod +x scripts/setup_postgres.sh && ./scripts/setup_postgres.sh

# 2. Entorno
cp .env.example .env        # ajustar DATABASE_URL y credenciales semilla
pip install -r requirements.txt

# 3. Migraciones (trazabilidad Alembic — commitear migrations/ al repo)
export FLASK_APP=main.py    # PowerShell: $env:FLASK_APP="main.py"
flask db init
flask db migrate -m "esquema inicial: users, articles, ejecucion"
flask db upgrade

# 4. Arrancar
python main.py              # o gunicorn
```

## Pruebas (ya ejecutadas en este árbol con pandas 3.0 / Flask 3.1)

✔ Boot de main.py con todas las rutas
✔ POST /pso (form-data del frontend actual) → 200, persiste en BD, mismo contrato para pso.js
✔ POST /api/algoritmos/pso con matriz 10x6 → 200, dimensiones derivadas
✔ Validación → 400 con mensaje claro (matriz bajo mínimo, w/r1/r2 de longitud errónea, no rectangular)
✔ GET /api/ejecuciones → listado
✔ GET /api/ejecuciones/<id>/excel → xlsx reconstruido desde BD (13 hojas)

Ejemplo de la ruta nueva:

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/algoritmos/pso \
  -H "Content-Type: application/json" \
  -d '{
    "matriz": [[0.048,0.047,0.070,0.087,0.190],
               [0.053,0.052,0.066,0.081,0.058],
               [0.057,0.057,0.066,0.076,0.022],
               [0.062,0.062,0.063,0.058,0.007],
               [0.066,0.066,0.070,0.085,0.004],
               [0.070,0.071,0.066,0.058,0.003],
               [0.075,0.075,0.066,0.047,0.002],
               [0.079,0.079,0.066,0.035,0.002],
               [0.083,0.083,0.066,0.051,0.000]],
    "w": [0.4,0.2,0.03,0.07,0.3],
    "wwi": 0.7, "c1": 2.5, "c2": 2.5, "T": 10,
    "r1": [0.4657,0.8956,0.3877,0.4902,0.5039],
    "r2": [0.5319,0.8185,0.8331,0.7677,0.1708]
  }'
```

(matriz: filas = alternativas, columnas = criterios; mínimo 9x5,
sin tope superior; w, r1 y r2 crecen con el número de criterios)

## Fases pendientes

- Fase 3/4: parser por familia + limpieza de las ~30 rutas de main.py
- Fase 5: frontend con matriz dinámica + gráfica de convergencia
  (el endpoint ya devuelve `historico_gbf`)
- Fase 6: reescribir Compara/ contra PostgreSQL con dimensiones variables
