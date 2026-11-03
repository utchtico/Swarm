# Swarm — Algoritmos de optimización por enjambre

Backend en Flask para experimentación con algoritmos de optimización por enjambre
(PSO, BA, ACO y sus variantes híbridas con DA/MOORA/TOPSIS) y métodos MCDM puros
(TOPSIS, MOORA, Análisis Dimensional). Proyecto de Doctorado en Tecnología — UACJ.

## Requisitos previos

- Python 3.12 o superior
- PostgreSQL 14 o superior (en producción / máquinas compartidas). Para
  desarrollo local sin instalar nada de base de datos, el proyecto también
  funciona con SQLite — ver la sección de variables de entorno más abajo.
- Git

## 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd swarm
```

## 2. Crear y activar el entorno virtual

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (cmd)
.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate
```

## 3. Instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

No hace falta crear ninguna carpeta a mano (ni `Experiments/` ni `db/`):
el proyecto las crea automáticamente la primera vez que necesita guardar
algo en ellas.

## 4. Configurar las variables de entorno

Crea un archivo `.env` en la raíz del proyecto (al lado de `main.py`).
Estas seis variables son **obligatorias** — sin ellas el arranque falla
con un error explícito indicando cuál falta:

```env
SECRET_KEY=reemplaza-esto-por-una-clave-larga-y-aleatoria

USER_USERNAME=usuario
USER_PASSWORD=defina-una-contrasena-segura

ADMIN_USERNAME=admin
ADMIN_PASSWORD=defina-una-contrasena-segura

SUPERADMIN_USERNAME=superadmin
SUPERADMIN_PASSWORD=defina-una-contrasena-segura
```

Estas tres cuentas (`user`, `admin`, `superadmin`) se siembran automáticamente
en la base de datos la primera vez que el proyecto arranca y encuentra la
tabla de usuarios vacía. Si ya existen usuarios, este paso se omite —
seguro de volver a ejecutar.

### Conexión a la base de datos

Si **no** se define `DATABASE_URL`, el proyecto usa SQLite por defecto
(`db/swarm.db`, creado automáticamente) — útil para probar rápido sin
instalar PostgreSQL. Para usar PostgreSQL, agrega al `.env`:

```env
DATABASE_URL=postgresql://usuario_pg:contrasena_pg@localhost:5432/swarm
```

Ajusta usuario, contraseña, host, puerto y nombre de base de datos según tu
instalación. La base de datos (`swarm` en el ejemplo) debe existir de
antemano — créala con `createdb swarm` o desde `psql`:

```sql
CREATE DATABASE swarm;
```

### Variables opcionales

```env
# Tiempo de inactividad antes de cerrar sesión, en minutos (por defecto 480)
SESSION_IDLE_MINUTES=480

# Forzar cookies de sesión solo por HTTPS (déjalo en 0 mientras no haya
# HTTPS real configurado; en 1 las sesiones no funcionarán por HTTP plano)
SESSION_COOKIE_SECURE=0

# Modo debug de Flask (0 por defecto). Solo actívalo en tu máquina: con
# FLASK_DEBUG=1 la consola de errores permite ejecutar código en el servidor.
FLASK_DEBUG=0

# Topes de entrada para los algoritmos (valores por defecto mostrados)
MAX_CRITERIOS=20
MAX_ALTERNATIVAS=30
MAX_ITERACIONES=1000
MAX_N_ANTS=1000

# Tamaño máximo de archivo subido (plantillas Excel), en MB
MAX_UPLOAD_MB=5

# Envío de correo (invitaciones, recuperación de contraseña). Si se omiten,
# el envío de correo queda configurado pero sin credenciales válidas.
MAIL_USERNAME=correo@gmail.com
MAIL_APP_PASSWORD=contrasena_de_aplicacion_de_gmail
```

## 5. Aplicar las migraciones de base de datos

**Este paso es obligatorio si usas PostgreSQL.** Crea todas las tablas
(usuarios, ejecuciones, artículos) con el esquema correcto. Flask necesita
saber dónde está la aplicación — defínelo con la variable `FLASK_APP`:

```bash
# Windows (PowerShell)
$env:FLASK_APP="main.py"

flask db init

flask db migrate -m "esquema inicial: users, articles, ejecucion"

flask db upgrade

python main.py

# Windows (cmd)
set FLASK_APP=main.py && flask db upgrade

# Linux / macOS
export FLASK_APP=main.py
flask db upgrade
```

Si usas SQLite (sin `DATABASE_URL` definida), **no ejecutes este paso**: el
primer arranque (`python main.py`) ya crea el esquema automáticamente, y
correr `flask db upgrade` justo después puede fallar con un error de
"la tabla ya existe" porque ambos mecanismos intentarían crear las mismas
tablas. Con SQLite simplemente salta directo al paso 6.

Si en el futuro se agregan nuevas migraciones al repositorio, basta con
volver a correr `flask db upgrade` para aplicarlas — no se pierden datos
existentes.

## 6. Arrancar el servidor

```bash
python main.py
```

Por defecto corre en `http://localhost:5001`. Para cambiar el puerto:

```bash
# Windows (PowerShell)
$env:PORT=8080; python main.py

# Linux / macOS
PORT=8080 python main.py
```

En el primer arranque verás en la consola la confirmación de que se
sembraron los tres usuarios (`user`, `admin`, `superadmin`) con las
contraseñas definidas en el `.env`. Inicia sesión con cualquiera de ellos
desde `http://localhost:5001/login`.

## Resumen de comandos (todo junto)

Con PostgreSQL:

```bash
git clone <URL_DEL_REPOSITORIO>
cd swarm
python -m venv .venv
source .venv/bin/activate          # o el equivalente de Windows, ver paso 2
python -m pip install --upgrade pip
pip install -r requirements.txt
# crear el archivo .env con las variables del paso 4, incluyendo DATABASE_URL
export FLASK_APP=main.py          # ver paso 5 para el equivalente en Windows
flask db upgrade
python main.py
```

Con SQLite (sin instalar PostgreSQL, solo para probar):

```bash
git clone <URL_DEL_REPOSITORIO>
cd swarm
python -m venv .venv
source .venv/bin/activate          # o el equivalente de Windows, ver paso 2
python -m pip install --upgrade pip
pip install -r requirements.txt
# crear el archivo .env con las variables del paso 4, SIN DATABASE_URL
python main.py
```

## Estructura del proyecto

```
src/
  algoritmos/        Lógica matemática pura de cada algoritmo
  services/          Validación de entrada y persistencia por familia
  api/algoritmos/     Endpoints JSON de ejecución (uno por algoritmo)
  api/vistas/         Rutas que renderizan templates
  models/            Modelos SQLAlchemy
templates/           HTML (Jinja2) organizado por familia de algoritmo
static/              CSS y JS, organizado igual que templates/
migrations/          Historial de Alembic / Flask-Migrate
```

## Notas

- El frontend usa Tailwind vía CDN (`cdn.tailwindcss.com`) directamente en
  cada template — no se necesita correr ningún build de Node/npm para que
  el proyecto funcione. El `package.json` con el script de Tailwind es de
  una etapa anterior del proyecto y no es parte del flujo de arranque actual.
- La carpeta `Experiments/` (archivos Excel/CSV de cada ejecución, organizados
  por usuario/algoritmo/fecha) y `db/` (base de datos SQLite, si se usa) están
  en `.gitignore` y se recrean automáticamente; no necesitan ninguna acción
  manual.
