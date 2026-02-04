from flask import Blueprint, request, jsonify
from sqlalchemy import select
from src.models.models import db, Author, Article, ArticleAuthor, ArticleCorresponding
from src.api.auth import roles_required
from sqlalchemy.orm import selectinload

bp = Blueprint("articles_api", __name__, url_prefix="/api/articles")

def _word_count(s): return len((s or "").split())

def _upsert_author(session, nombre, apellido):
    nombre = (nombre or "").strip(); apellido = (apellido or "").strip()
    stmt = select(Author).where(Author.nombre == nombre, Author.apellido == apellido)
    a = session.execute(stmt).scalar_one_or_none()
    if not a:
        a = Author(nombre=nombre, apellido=apellido)
        session.add(a)
    return a

@bp.post("/")
@roles_required("admin", "superadmin")
def create_article():
    d = request.get_json(force=True)

    # Validaciones mínimas
    if not d.get("titulo"):              return jsonify({"error":"titulo requerido"}), 400
    if not d.get("autores"):             return jsonify({"error":"al menos un autor principal"}), 400
    if not d.get("autores_corresp"):     return jsonify({"error":"al menos un autor de correspondencia"}), 400
    if _word_count(d.get("resumen","")) > 300:
        return jsonify({"error":"resumen > 300 palabras"}), 400

    art = Article(
        titulo=d["titulo"],
        tipo_evento=d["tipo_evento"],
        lugar_publicacion=d["lugar_publicacion"],
        url_articulo=d["url_articulo"],
        year_publicacion=int(d["year_publicacion"]),
        resumen=d["resumen"],
        visible=bool(d.get("visible", False)),
    )
    db.session.add(art)

    # Autores principales (orden)
    for i, au in enumerate(d["autores"], start=1):
        a = _upsert_author(db.session, au.get("nombre"), au.get("apellido"))
        art.authors.append(ArticleAuthor(author=a, orden=i))

    # Autores de correspondencia
    for au in d["autores_corresp"]:
        a = _upsert_author(db.session, au.get("nombre"), au.get("apellido"))
        art.correspondings.append(ArticleCorresponding(author=a))

    db.session.commit()
    return jsonify({"id": art.id}), 201

@bp.get("/")
@roles_required("admin", "superadmin")
def list_articles():
    only_visible = request.args.get("visible")

    # Base query
    q = db.select(Article)
    if only_visible in ("1", "true", "True"):
        q = q.where(Article.visible.is_(True))

    # Ordenar por created_at DESC; si hay NULL (filas antiguas), usa NOW para no perder orden
    q = q.order_by(db.func.coalesce(Article.created_at, db.func.datetime('now')).desc())

    rows = db.session.execute(q).scalars().all()

    def summarize(a: Article):
        t = a.titulo or ""
        r = a.resumen or ""
        # Muestra created_at real; si no existe, usa año de publicación como fallback
        fecha = (a.created_at.strftime("%Y-%m-%d %H:%M")
                 if getattr(a, "created_at", None) else f"01/01/{a.year_publicacion}")
        return {
            "id": a.id,
            "titulo": (t[:24] + "…") if len(t) > 24 else t,
            "descripcion": (r[:80] + "…") if len(r) > 80 else r,
            "fecha": fecha,
            "visible": a.visible,
            # opcional: expón ISO si lo quieres en front
            # "created_at": a.created_at.isoformat() if a.created_at else None,
        }

    return jsonify([summarize(a) for a in rows])


@bp.patch("/visibility")
@roles_required("admin", "superadmin")
def set_visibility():
    p = request.get_json(force=True)
    ids = p.get("ids") or []
    vis = bool(p.get("visible", True))
    if not ids:
        return jsonify({"error": "ids requeridos"}), 400
    db.session.execute(
        db.update(Article)
          .where(Article.id.in_(ids))
          .values(visible=vis, updated_at=db.func.now())  # <-- importante
    )
    db.session.commit()
    return jsonify({"updated": len(ids)})


@bp.get("/<int:article_id>")
@roles_required("admin", "superadmin")
def get_article(article_id: int):
    art = db.session.get(Article, article_id)
    if not art: return jsonify({"error":"no encontrado"}), 404
    autores = [{"id": l.author.id, "nombre": l.author.nombre, "apellido": l.author.apellido, "orden": l.orden} for l in art.authors]
    corresps = [{"id": l.author.id, "nombre": l.author.nombre, "apellido": l.author.apellido} for l in art.correspondings]
    return jsonify({
        "id": art.id, "titulo": art.titulo, "tipo_evento": art.tipo_evento,
        "lugar_publicacion": art.lugar_publicacion, "url_articulo": art.url_articulo,
        "year_publicacion": art.year_publicacion, "resumen": art.resumen,
        "visible": art.visible, "autores": autores, "autores_corresp": corresps,
    })

@bp.put("/<int:article_id>")
@roles_required("admin", "superadmin")
def update_article(article_id: int):
    d = request.get_json(force=True)
    art = db.session.get(Article, article_id)
    if not art:
        return jsonify({"error": "no encontrado"}), 404

    touched = False  # para saber si cambiamos campos simples

    for k in ("titulo", "tipo_evento", "lugar_publicacion", "url_articulo", "resumen"):
        if k in d:
            setattr(art, k, d[k]); touched = True
    if "year_publicacion" in d:
        art.year_publicacion = int(d["year_publicacion"]); touched = True
    if "visible" in d:
        art.visible = bool(d["visible"]); touched = True

    relations_touched = False

    if "autores" in d:
        art.authors.clear()
        for i, au in enumerate(d["autores"], start=1):
            a = _upsert_author(db.session, au.get("nombre"), au.get("apellido"))
            art.authors.append(ArticleAuthor(author=a, orden=i))
        relations_touched = True

    if "autores_corresp" in d:
        art.correspondings.clear()
        for au in d["autores_corresp"]:
            a = _upsert_author(db.session, au.get("nombre"), au.get("apellido"))
            art.correspondings.append(ArticleCorresponding(author=a))
        relations_touched = True

    # Si SOLO tocamos relaciones, onupdate no se dispara → forzamos updated_at
    if not touched and relations_touched:
        art.updated_at = db.func.now()

    db.session.commit()
    return jsonify({"ok": True})


@bp.delete("/<int:article_id>")
@roles_required("admin", "superadmin")
def delete_article(article_id: int):
    art = db.session.get(Article, article_id)
    if not art: return jsonify({"error":"no encontrado"}), 404
    db.session.delete(art)
    db.session.commit()
    return jsonify({"ok": True})

# src/api/articles.py

@bp.get("/public")
@roles_required("user","admin", "superadmin")
def list_public_articles():
    q = (
        db.select(Article)
          .where(Article.visible.is_(True))
          .options(
              selectinload(Article.authors).selectinload(ArticleAuthor.author),
              selectinload(Article.correspondings).selectinload(ArticleCorresponding.author),
          )
          .order_by(db.func.coalesce(Article.created_at, db.func.datetime('now')).desc())
    )
    arts = db.session.execute(q).scalars().unique().all()

    def to_dict(a: Article):
        autores = [
            {"nombre": l.author.nombre, "apellido": l.author.apellido, "orden": l.orden}
            for l in a.authors
        ]
        corresps = [
            {"nombre": l.author.nombre, "apellido": l.author.apellido}
            for l in a.correspondings
        ]
        return {
            "id": a.id,
            "titulo": a.titulo,
            "resumen": a.resumen,
            "lugar_publicacion": a.lugar_publicacion,
            "url_articulo": a.url_articulo,
            "year_publicacion": a.year_publicacion,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "autores": autores,
            "autores_corresp": corresps,
        }

    return jsonify([to_dict(a) for a in arts])

