import os
from datetime import date
from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate

from src.models.models import db, init_db
from src.security import init_security
from src.services.email import mail
from src.api.auth import auth_bp
from src.api.articles import bp as articles_api
from src.api.algoritmos.pso import algoritmos_bp as algoritmos_pso_bp
from src.api.ejecuciones import ejecuciones_bp
from src.api.algoritmos.ba import algoritmos_ba_bp
from src.api.algoritmos.aco import algoritmos_aco_bp
from src.api.algoritmos.topsis import algoritmos_topsis_bp
from src.api.algoritmos.moorav import algoritmos_moorav_bp
from src.api.admin import admin_bp
from src.views import views_bp
from src.api.vistas.pso import pso_bp
from src.api.vistas.ba import ba_bp
from src.api.vistas.aco import aco_bp
from src.api.vistas.compara import compara_bp

# ── Base de datos (SQLite fallback) ──────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'db', 'swarm.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ── Configuración de Flask ────────────────────────────────────────────────────
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']    = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY']                 = os.environ.get('SECRET_KEY', 'dev-insecure-key')

init_security(app)

db.init_app(app)
mail.init_app(app)

migrate = Migrate(app, db)
init_db(app)

# ── Blueprints ────────────────────────────────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(articles_api)
app.register_blueprint(algoritmos_pso_bp)  # /api/algoritmos/{pso,dapso,moorapso,topsispso}
app.register_blueprint(ejecuciones_bp)      # /api/ejecuciones/*  (genérico, todas las familias)
app.register_blueprint(algoritmos_ba_bp)    # /api/algoritmos/ba, /api/algoritmos/ba/plantilla
app.register_blueprint(algoritmos_aco_bp)   # /api/algoritmos/aco, /api/algoritmos/aco/plantilla
app.register_blueprint(algoritmos_topsis_bp)  # /api/algoritmos/topsis (MCDM puro, sin metaheurística)
app.register_blueprint(algoritmos_moorav_bp)  # /api/algoritmos/moorav (MCDM puro, sin metaheurística)
app.register_blueprint(admin_bp)        # /admin/*
app.register_blueprint(views_bp)        # /, /acercade, /publicaciones, etc.
app.register_blueprint(pso_bp)          # /pso, /dapso, /moorapso, /topsispso
app.register_blueprint(ba_bp)           # /ba, /daba, /mooraba, /topsisba
app.register_blueprint(aco_bp)          # /aco, /daaco, /mooraaco, /topsisaco, /topsis, /moorav, /da
app.register_blueprint(compara_bp)      # /comparacionGeneral, /comparacionBa, etc.

# ── Arranque ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)