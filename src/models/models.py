import os
import secrets
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash

from dotenv import load_dotenv

db = SQLAlchemy()
JSONVariant = db.JSON().with_variant(JSONB(), 'postgresql')


class User(db.Model):
    __tablename__ = 'user'

    id                   = db.Column(db.Integer, primary_key=True)
    username             = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email                = db.Column(db.String(120), unique=True, nullable=True,  index=True)
    password_hash        = db.Column(db.String(256), nullable=False)
    role                 = db.Column(db.String(20),  nullable=False, default='user')

    # Gestión de cuenta
    activo               = db.Column(db.Boolean, nullable=False, default=True)
    debe_cambiar_password = db.Column(db.Boolean, nullable=False, default=False)

    # Auditoría
    creado_en            = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    creado_por_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    ultimo_acceso        = db.Column(db.DateTime, nullable=True)

    ejecuciones  = db.relationship('Ejecucion', back_populates='usuario',
                                   foreign_keys='Ejecucion.fk_user')
    creado_por   = db.relationship('User', remote_side='User.id',
                                   foreign_keys=[creado_por_id])

    def to_dict(self):
        return {
            'id':           self.id,
            'username':     self.username,
            'email':        self.email or '',
            'role':         self.role,
            'activo':       self.activo,
            'debe_cambiar': self.debe_cambiar_password,
            'creado_en':    self.creado_en.isoformat() if self.creado_en else None,
            'ultimo_acceso':self.ultimo_acceso.isoformat() if self.ultimo_acceso else None,
            'creado_por':   self.creado_por.username if self.creado_por else None,
        }


class Ejecucion(db.Model):
    __tablename__ = 'ejecucion'

    id                    = db.Column(db.Integer, primary_key=True)
    algoritmo             = db.Column(db.String(30), nullable=False, index=True)
    fk_user               = db.Column(db.Integer, db.ForeignKey('user.id'),
                                      nullable=False, index=True)
    fecha_ejecucion       = db.Column(db.DateTime, server_default=func.now(),
                                      nullable=False, index=True)
    tiempo_ejecucion_seg  = db.Column(db.Float, nullable=False)
    iteraciones           = db.Column(db.Integer, nullable=False)
    n_criterios           = db.Column(db.Integer, nullable=False)
    n_alternativas        = db.Column(db.Integer, nullable=False)
    gbf_final             = db.Column(db.Float)
    mejor_alternativa_final = db.Column(db.Integer)

    parametros     = db.Column(JSONVariant, nullable=False)
    matriz_entrada = db.Column(JSONVariant, nullable=False)
    resultados     = db.Column(JSONVariant, nullable=False)
    historico_gbf  = db.Column(JSONVariant, nullable=False)
    historiales    = db.Column(JSONVariant)

    usuario = db.relationship('User', back_populates='ejecuciones',
                              foreign_keys=[fk_user])

    __table_args__ = (
        db.CheckConstraint('n_criterios >= 1',    name='ck_ejecucion_n_criterios'),
        db.CheckConstraint('n_alternativas >= 1', name='ck_ejecucion_n_alternativas'),
        db.CheckConstraint('iteraciones >= 1',    name='ck_ejecucion_iteraciones'),
        db.Index('ix_ejecucion_algoritmo_fecha',  'algoritmo', 'fecha_ejecucion'),
        db.Index('ix_ejecucion_user_algoritmo',   'fk_user',   'algoritmo'),
    )

    def to_dict_resumen(self):
        return {
            'id':                     self.id,
            'algoritmo':              self.algoritmo,
            'usuario':                self.usuario.username if self.usuario else None,
            'fecha_ejecucion':        self.fecha_ejecucion.isoformat() if self.fecha_ejecucion else None,
            'tiempo_ejecucion_seg':   self.tiempo_ejecucion_seg,
            'iteraciones':            self.iteraciones,
            'n_criterios':            self.n_criterios,
            'n_alternativas':         self.n_alternativas,
            'gbf_final':              self.gbf_final,
            'mejor_alternativa_final':self.mejor_alternativa_final,
        }


# ─────────────────────────── Article models (sin cambios) ───────────────────

class Author(db.Model):
    __tablename__ = 'author'
    id       = db.Column(db.Integer, primary_key=True)
    nombre   = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)


class Article(db.Model):
    __tablename__ = 'article'
    id                 = db.Column(db.Integer, primary_key=True)
    titulo             = db.Column(db.String(256), nullable=False)
    tipo_evento        = db.Column(db.String(64),  nullable=False)
    lugar_publicacion  = db.Column(db.String(128), nullable=False)
    url_articulo       = db.Column(db.String(512), nullable=False)
    year_publicacion   = db.Column(db.Integer, nullable=False, index=True)
    resumen            = db.Column(db.Text, nullable=False)
    visible            = db.Column(db.Boolean, default=False, nullable=False)
    created_at         = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    updated_at         = db.Column(db.DateTime, onupdate=func.now())
    authors            = db.relationship('ArticleAuthor', back_populates='article',
                                         cascade='all, delete-orphan',
                                         order_by='ArticleAuthor.orden')
    correspondings     = db.relationship('ArticleCorresponding', back_populates='article',
                                         cascade='all, delete-orphan')


class ArticleAuthor(db.Model):
    __tablename__ = 'article_author'
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), primary_key=True)
    author_id  = db.Column(db.Integer, db.ForeignKey('author.id'),  primary_key=True)
    orden      = db.Column(db.Integer, nullable=False, default=1)
    article    = db.relationship('Article', back_populates='authors')
    author     = db.relationship('Author', backref=db.backref('articles_authored',
                                                               cascade='all, delete-orphan'))
    __table_args__ = (
        db.UniqueConstraint('article_id', 'author_id', name='uq_article_author'),
        db.UniqueConstraint('article_id', 'orden',     name='uq_article_author_order'),
        db.CheckConstraint('orden >= 1',               name='ck_author_order_positive'),
    )


class ArticleCorresponding(db.Model):
    __tablename__ = 'article_corresponding'
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), primary_key=True)
    author_id  = db.Column(db.Integer, db.ForeignKey('author.id'),  primary_key=True)
    article    = db.relationship('Article', back_populates='correspondings')
    author     = db.relationship('Author', backref=db.backref('articles_corresponding',
                                                               cascade='all, delete-orphan'))
    __table_args__ = (
        db.UniqueConstraint('article_id', 'author_id', name='uq_article_corresponding'),
    )


# ─────────────────────────── init_db ────────────────────────────────────────

def init_db(app):
    load_dotenv()
    required = ['USER_USERNAME', 'USER_PASSWORD', 'ADMIN_USERNAME',
                'ADMIN_PASSWORD', 'SUPERADMIN_USERNAME', 'SUPERADMIN_PASSWORD']
    for var in required:
        if not os.getenv(var):
            raise EnvironmentError(f"Variable de entorno {var} faltante en .env")

    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if uri.startswith('sqlite'):
            db.create_all()

        inspector = inspect(db.engine)
        if not inspector.has_table('user'):
            print("[init_db] Tabla 'user' no existe — ejecuta 'flask db upgrade'.")
            return

        # Verificar si el esquema está actualizado antes de intentar sembrar
        columnas_actuales = {c['name'] for c in inspector.get_columns('user')}
        columnas_requeridas = {'email', 'activo', 'debe_cambiar_password'}
        if not columnas_requeridas.issubset(columnas_actuales):
            print("[init_db] Esquema desactualizado — ejecuta 'flask db upgrade' y reinicia.")
            return

        # Sembrar solo si no hay usuarios
        from sqlalchemy import text
        tiene_usuarios = db.session.execute(
            text('SELECT 1 FROM "user" LIMIT 1')
        ).first() is not None
        if not tiene_usuarios:
            seeds = [
                (os.getenv('USER_USERNAME'),       os.getenv('USER_PASSWORD'),       'user'),
                (os.getenv('ADMIN_USERNAME'),      os.getenv('ADMIN_PASSWORD'),      'admin'),
                (os.getenv('SUPERADMIN_USERNAME'), os.getenv('SUPERADMIN_PASSWORD'), 'superadmin'),
            ]
            db.session.add_all([
                User(username=u, password_hash=generate_password_hash(p),
                     role=r, activo=True, debe_cambiar_password=False)
                for u, p, r in seeds
            ])
            db.session.commit()