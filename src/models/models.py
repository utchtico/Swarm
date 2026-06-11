import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from sqlalchemy.sql import func
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

db = SQLAlchemy()

# Tipo JSON portable:
#  - En PostgreSQL se materializa como JSONB (indexable, operadores ->, ->>, @>)
#  - En SQLite (fallback de desarrollo) se materializa como JSON de texto
JSONVariant = db.JSON().with_variant(JSONB(), 'postgresql')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    ejecuciones = db.relationship('Ejecucion', back_populates='usuario')


class Ejecucion(db.Model):
    """
    Registro de una ejecución de cualquier algoritmo (PSO, BA, ACO, híbridos...).

    Diseño mixto:
      - Columnas reales  -> todo lo que se filtra/agrega en SQL para el módulo
                            de comparación (algoritmo, usuario, fechas, tiempos,
                            dimensiones de la matriz, resultado final).
      - Columnas JSONB   -> todo lo de estructura variable (parámetros propios
                            de cada algoritmo, matriz de entrada NxM, históricos
                            por iteración). En PostgreSQL siguen siendo
                            consultables con operadores JSONB si hiciera falta.
    """
    __tablename__ = 'ejecucion'

    id = db.Column(db.Integer, primary_key=True)
    algoritmo = db.Column(db.String(30), nullable=False, index=True)
    fk_user = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    fecha_ejecucion = db.Column(db.DateTime, server_default=func.now(), nullable=False, index=True)
    tiempo_ejecucion_seg = db.Column(db.Float, nullable=False)  # float => AVG/MIN/MAX directos en SQL

    iteraciones = db.Column(db.Integer, nullable=False)
    n_criterios = db.Column(db.Integer, nullable=False)      # n (columnas de la matriz)
    n_alternativas = db.Column(db.Integer, nullable=False)   # a (filas de la matriz)

    # Resultado final "plano" para comparaciones rápidas sin abrir JSON
    gbf_final = db.Column(db.Float)
    mejor_alternativa_final = db.Column(db.Integer)

    # --- Estructura variable ---
    # {"wwi":0.7,"c1":2.5,"c2":2.5,"T":10,"w":[...],"r1":[...],"r2":[...]}
    parametros = db.Column(JSONVariant, nullable=False)
    # {"n":5,"a":9,"criterios":["C1",...],"alternativas":["A1",...],"valores":[[...],[...]]}
    matriz_entrada = db.Column(JSONVariant, nullable=False)
    # [{"iteracion":1,"mejor_alternativa":3,"gbf":1.123}, ...]
    resultados = db.Column(JSONVariant, nullable=False)
    # [1.123, 1.245, ...]  (uno por iteración; alimenta la gráfica de convergencia)
    historico_gbf = db.Column(JSONVariant, nullable=False)
    # Histórico completo de matrices para exportación a Excel y análisis
    # (Cronbach sobre posiciones, etc.):
    # {"V":[[...]], "CP":[[...]], "PBEST":[[...]], "CF":[[...]], "Fx":[...], "gbest":[...]}
    historiales = db.Column(JSONVariant)

    usuario = db.relationship('User', back_populates='ejecuciones')

    __table_args__ = (
        db.CheckConstraint('n_criterios >= 1', name='ck_ejecucion_n_criterios'),
        db.CheckConstraint('n_alternativas >= 1', name='ck_ejecucion_n_alternativas'),
        db.CheckConstraint('iteraciones >= 1', name='ck_ejecucion_iteraciones'),
        db.Index('ix_ejecucion_algoritmo_fecha', 'algoritmo', 'fecha_ejecucion'),
        db.Index('ix_ejecucion_user_algoritmo', 'fk_user', 'algoritmo'),
    )

    def to_dict_resumen(self):
        """Vista ligera para listados y comparaciones en el frontend."""
        return {
            'id': self.id,
            'algoritmo': self.algoritmo,
            'usuario': self.usuario.username if self.usuario else None,
            'fecha_ejecucion': self.fecha_ejecucion.isoformat() if self.fecha_ejecucion else None,
            'tiempo_ejecucion_seg': self.tiempo_ejecucion_seg,
            'iteraciones': self.iteraciones,
            'n_criterios': self.n_criterios,
            'n_alternativas': self.n_alternativas,
            'gbf_final': self.gbf_final,
            'mejor_alternativa_final': self.mejor_alternativa_final,
        }


def init_db(app):
    """
    Inicialización de la base de datos.

    IMPORTANTE (trazabilidad de migraciones):
      - En PostgreSQL el esquema lo gobierna Alembic (flask db upgrade).
        Aquí NO se ejecuta create_all() para no generar esquema fuera del
        historial de migraciones.
      - En SQLite (fallback de desarrollo rápido) sí se usa create_all().
      - El seeding de usuarios solo corre si la tabla 'user' ya existe.
    """
    load_dotenv()
    required_vars = ['USER_USERNAME', 'USER_PASSWORD', 'ADMIN_USERNAME',
                     'ADMIN_PASSWORD', 'SUPERADMIN_USERNAME', 'SUPERADMIN_PASSWORD']
    for var in required_vars:
        if not os.getenv(var):
            raise EnvironmentError(f"Variable de entorno {var} faltante en .env")

    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if uri.startswith('sqlite'):
            db.create_all()

        inspector = inspect(db.engine)
        if not inspector.has_table('user'):
            print("[init_db] La tabla 'user' aún no existe. "
                  "Ejecuta 'flask db upgrade' y reinicia para sembrar usuarios.")
            return

        if not User.query.first():
            users = [
                User(
                    username=os.getenv('USER_USERNAME'),
                    password_hash=generate_password_hash(os.getenv('USER_PASSWORD')),
                    role='user'
                ),
                User(
                    username=os.getenv('ADMIN_USERNAME'),
                    password_hash=generate_password_hash(os.getenv('ADMIN_PASSWORD')),
                    role='admin'
                ),
                User(
                    username=os.getenv('SUPERADMIN_USERNAME'),
                    password_hash=generate_password_hash(os.getenv('SUPERADMIN_PASSWORD')),
                    role='superadmin'
                )
            ]
            db.session.add_all(users)
            db.session.commit()


class Author(db.Model):
    __tablename__ = 'author'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)


class Article(db.Model):
    __tablename__ = 'article'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(256), nullable=False)
    tipo_evento = db.Column(db.String(64), nullable=False)
    lugar_publicacion = db.Column(db.String(128), nullable=False)
    url_articulo = db.Column(db.String(512), nullable=False)
    year_publicacion = db.Column(db.Integer, nullable=False, index=True)
    resumen = db.Column(db.Text, nullable=False)
    visible = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=func.now())

    authors = db.relationship(
        'ArticleAuthor', back_populates='article',
        cascade='all, delete-orphan', order_by='ArticleAuthor.orden'
    )
    correspondings = db.relationship(
        'ArticleCorresponding', back_populates='article',
        cascade='all, delete-orphan'
    )


class ArticleAuthor(db.Model):
    __tablename__ = 'article_author'
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), primary_key=True)
    author_id  = db.Column(db.Integer, db.ForeignKey('author.id'), primary_key=True)
    orden      = db.Column(db.Integer, nullable=False, default=1)
    article = db.relationship('Article', back_populates='authors')
    author  = db.relationship('Author', backref=db.backref('articles_authored', cascade='all, delete-orphan'))
    __table_args__ = (
        db.UniqueConstraint('article_id','author_id', name='uq_article_author'),
        db.UniqueConstraint('article_id','orden',     name='uq_article_author_order'),
        db.CheckConstraint('orden >= 1', name='ck_author_order_positive'),
    )


class ArticleCorresponding(db.Model):
    __tablename__ = 'article_corresponding'
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), primary_key=True)
    author_id  = db.Column(db.Integer, db.ForeignKey('author.id'), primary_key=True)
    article = db.relationship('Article', back_populates='correspondings')
    author  = db.relationship('Author', backref=db.backref('articles_corresponding', cascade='all, delete-orphan'))
    __table_args__ = (
        db.UniqueConstraint('article_id','author_id', name='uq_article_corresponding'),
    )
