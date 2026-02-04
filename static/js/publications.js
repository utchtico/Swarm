(function () {
    const root = document.getElementById('publicaciones-root');
    if (!root) return;

    const MONTHS_ES = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];
    const $ = (sel, p = document) => p.querySelector(sel);
    const escapeHtml = (s) => (s || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));

    function parseFecha(a) {
        // Prioriza created_at; si no existe, arma 1/enero/<year_publicacion>
        if (a.created_at) {
            const d = new Date(a.created_at);
            return `${d.getDate()} ${MONTHS_ES[d.getMonth()]} ${d.getFullYear()}`;
        }
        return a.year_publicacion ? `01 Enero ${a.year_publicacion}` : '';
    }

    function sourceText(a) {
        // Usa lugar_publicacion si viene; si no, dominio limpio del URL
        if (a.lugar_publicacion && a.lugar_publicacion.trim()) return a.lugar_publicacion;
        try {
            const host = new URL(a.url_articulo).hostname.replace(/^www\./, '');
            return host;
        } catch { return ''; }
    }

    function esCorresp(a, nombre, apellido) {
        return (a.autores_corresp || []).some(c =>
            (c.nombre || '') === (nombre || '') && (c.apellido || '') === (apellido || '')
        );
    }

    function renderArticulo(a) {
        const MONTHS_ES = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ];
        const escapeHtml = (s) => (s || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));

        function parseFecha() {
            if (a.created_at) {
                const d = new Date(a.created_at);
                return `${d.getDate()} ${MONTHS_ES[d.getMonth()]} ${d.getFullYear()}`;
            }
            return a.year_publicacion ? `01 Enero ${a.year_publicacion}` : '';
        }

        function sourceText() {
            if (a.lugar_publicacion && a.lugar_publicacion.trim()) return a.lugar_publicacion;
            try { return new URL(a.url_articulo).hostname.replace(/^www\./, ''); } catch { return ''; }
        }

        const fecha = parseFecha();
        const pubtxt = sourceText();

        const autoresHTML = (a.autores || [])
            .sort((x, y) => (x.orden || 999) - (y.orden || 999))
            .map(p => `<li><span class="underline">${escapeHtml([p.nombre, p.apellido].filter(Boolean).join(' '))}</span></li>`)
            .join('');

        const correspsHTML = (a.autores_corresp || [])
            .map(p => `<li><span class="underline">${escapeHtml([p.nombre, p.apellido].filter(Boolean).join(' '))}</span></li>`)
            .join('');

        const publicadoEn = a.url_articulo
            ? `<a href="${escapeHtml(a.url_articulo)}" target="_blank" rel="noopener noreferrer">${escapeHtml(pubtxt || 'Ver fuente')}</a>`
            : escapeHtml(pubtxt || '');

        const enlaceArticulo = a.url_articulo
            ? `<a href="${escapeHtml(a.url_articulo)}" target="_blank" rel="noopener noreferrer">Ver artículo</a>`
            : `<span class="text-gray-500">Sin enlace</span>`;

        return `
    <article class="publicacion bg-white rounded-md shadow p-6">
      <h2 class="text-xl font-semibold mb-4">${escapeHtml(a.titulo || '')}</h2>
      <p class="text-sm leading-6 text-gray-800 mb-4">${escapeHtml(a.resumen || '')}</p>

      <div class="grid md:grid-cols-4 gap-4 text-sm">
        <div>
          <div class="font-medium mb-1">Autor(es):</div>
          <ul class="list-disc pl-4 space-y-1">${autoresHTML || '<li class="text-gray-500">—</li>'}</ul>
        </div>
        <div>
          <div class="font-medium mb-1">Autor(es) de correspondencia:</div>
          <ul class="list-disc pl-4 space-y-1">${correspsHTML || '<li class="text-gray-500">—</li>'}</ul>
        </div>
        <div>
          <div class="font-medium mb-1">Fecha publicado:</div>
          <div>${escapeHtml(fecha)}</div>
        </div>
        <div>
          <div class="font-medium mb-1">Publicado en:</div>
          <div>${publicadoEn}</div>
          <div class="mt-2 font-medium">Enlace del artículo:</div>
          <div>${enlaceArticulo}</div>
        </div>
      </div>
    </article>
  `;
    }

    async function load() {
        root.innerHTML = `<div class="text-gray-500">Cargando…</div>`;
        try {
            const r = await fetch('/api/articles/public', { headers: { 'Accept': 'application/json' }, cache: 'no-store' });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const items = await r.json();

            if (!Array.isArray(items) || items.length === 0) {
                root.innerHTML = `<div class="text-gray-500">No hay publicaciones visibles aún.</div>`;
                return;
            }
            root.innerHTML = items.map(renderArticulo).join('');
        } catch (e) {
            root.innerHTML = `<div class="text-red-600">Error al cargar publicaciones.</div>`;
        }
    }

    load();
})();
