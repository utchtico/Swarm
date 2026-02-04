import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from sqlalchemy.sql import func

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)


def init_db(app):
    load_dotenv()
    required_vars = ['USER_USERNAME', 'USER_PASSWORD', 'ADMIN_USERNAME', 'ADMIN_PASSWORD', 'SUPERADMIN_USERNAME', 'SUPERADMIN_PASSWORD']
    for var in required_vars:
        if not os.getenv(var):
            raise EnvironmentError(f"Variable de entorno {var} faltante en .env")

    with app.app_context():
        db.create_all()
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
