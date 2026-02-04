(function () {
  // Si esta página no tiene el formulario, salir sin romper otras vistas
  if (!document.getElementById('article-form')) return;

  const API = {
    list: async () => {
      const r = await fetch('/api/articles', { cache: 'no-store', headers: { 'Accept': 'application/json' } });
      if (!r.ok) throw new Error(`GET /api/articles ${r.status}`);
      return r.json();
    },
    create: async (payload) => {
      try {
        const r = await fetch('/api/articles', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(payload)
        });
        const body = await r.json().catch(() => ({}));
        return { ok: r.ok, status: r.status, body };
      } catch (e) {
        return { ok: false, status: 0, body: { error: e.message } };
      }
    },
    patchVisibility: async (ids, visible) => {
      const r = await fetch('/api/articles/visibility', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ ids, visible })
      });
      if (!r.ok) throw new Error(`PATCH /api/articles/visibility ${r.status}`);
      return r.json().catch(() => ({}));
    }
  };

  // ------- Helpers -------
  const $ = (sel, parent = document) => parent.querySelector(sel);
  const $$ = (sel, parent = document) => [...parent.querySelectorAll(sel)];
  const wordCount = (text) => (text || '').trim().split(/\s+/).filter(Boolean).length;
  const escapeHtml = (s) => (s || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));

  function makeAuthorRow(kind = 'author') { // kind: 'author' | 'corresp'
    const row = document.createElement('div');
    row.className = `grid grid-cols-2 gap-2 ${kind}-row`;
    // ⚠️ Para autores principales usamos clases "autor-*" (en español) porque el serializador las busca así.
    const isAutor = (kind === 'author');
    row.innerHTML = `
      <input type="text" class="form-input ${isAutor ? 'autor-nombre' : 'corresp-nombre'}" placeholder="Nombre (s)" />
      <div class="flex gap-2">
        <input type="text" class="form-input ${isAutor ? 'autor-apellido' : 'corresp-apellido'} flex-1" placeholder="Apellidos" />
        <button type="button" class="px-3 rounded-md border border-gray-300 hover:bg-gray-50 remove-${kind}" title="Quitar" aria-label="Quitar">×</button>
      </div>`;
    return row;
  }

  function serializeForm() {
    const autores = $$('#autores-container .author-row').map(r => ({
      nombre: $('.autor-nombre', r).value.trim(),
      apellido: $('.autor-apellido', r).value.trim()
    })).filter(a => a.nombre || a.apellido);

    const corresps = $$('#corresp-container .corresp-row').map(r => ({
      nombre: $('.corresp-nombre', r).value.trim(),
      apellido: $('.corresp-apellido', r).value.trim()
    })).filter(a => a.nombre || a.apellido);

    return {
      titulo: $('#titulo').value.trim(),
      autores,
      autores_corresp: corresps,
      tipo_evento: $('#tipo_evento').value,
      lugar_publicacion: $('#lugar_publicacion').value.trim(),
      url_articulo: $('#url_articulo').value.trim(),
      year_publicacion: parseInt($('#year_publicacion').value, 10),
      resumen: $('#resumen').value.trim(),
      visible: false
    };
  }

  // ------- UI: Resumen contador -------
  const resumenEl = document.getElementById('resumen');
  const resumenCount = document.getElementById('resumen-count');
  resumenEl.addEventListener('input', () => {
    resumenCount.textContent = wordCount(resumenEl.value);
  });

  // ------- UI: Add/remove autores -------
  $('#btn-add-autor').addEventListener('click', () => {
    $('#autores-container').appendChild(makeAuthorRow('author'));
  });
  $('#autores-container').addEventListener('click', (e) => {
    if (e.target.closest('.remove-author')) {
      const rows = $$('#autores-container .author-row');
      if (rows.length > 1) e.target.closest('.author-row').remove();
    }
  });
  $('#btn-add-corresp').addEventListener('click', () => {
    $('#corresp-container').appendChild(makeAuthorRow('corresp'));
  });
  $('#corresp-container').addEventListener('click', (e) => {
    if (e.target.closest('.remove-corresp')) {
      const rows = $$('#corresp-container .corresp-row');
      if (rows.length > 1) e.target.closest('.corresp-row').remove();
    }
  });

  // Si por cualquier motivo el HTML vino sin filas iniciales, crea una por defecto
  if ($$('#autores-container .author-row').length === 0) {
    $('#autores-container').appendChild(makeAuthorRow('author'));
  }
  if ($$('#corresp-container .corresp-row').length === 0) {
    $('#corresp-container').appendChild(makeAuthorRow('corresp'));
  }

  // ------- Submit crear artículo -------
  const form = document.getElementById('article-form');
  const formMsg = document.getElementById('form-msg');
  const btnSubmit = document.getElementById('btn-submit');
  const btnReset = document.getElementById('btn-reset');

  btnReset.addEventListener('click', () => {
    form.reset();
    $('#autores-container').innerHTML = '';
    $('#corresp-container').innerHTML = '';
    $('#autores-container').appendChild(makeAuthorRow('author'));
    $('#corresp-container').appendChild(makeAuthorRow('corresp'));
    resumenCount.textContent = '0';
    formMsg.textContent = '';
    formMsg.className = 'text-sm mt-2';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    formMsg.textContent = '';
    formMsg.className = 'text-sm mt-2';
    btnSubmit.disabled = true;

    const payload = serializeForm();

    // Validaciones mínimas del front (el backend valida también)
    if (!payload.autores.length) {
      formMsg.textContent = 'Debes añadir al menos un autor principal.';
      formMsg.classList.add('text-red-600');
      btnSubmit.disabled = false;
      return;
    }
    if (!payload.autores_corresp.length) {
      formMsg.textContent = 'Debes añadir al menos un autor de correspondencia.';
      formMsg.classList.add('text-red-600');
      btnSubmit.disabled = false;
      return;
    }
    const wc = wordCount(payload.resumen);
    if (wc > 300) {
      formMsg.textContent = `Resumen excede 300 palabras (${wc}).`;
      formMsg.classList.add('text-red-600');
      btnSubmit.disabled = false;
      return;
    }

    const { ok, status, body } = await API.create(payload);
    if (!ok) {
      formMsg.textContent = body?.error || `Error (${status || 'red'}).`;
      formMsg.classList.add('text-red-600');
    } else {
      formMsg.textContent = 'Artículo guardado correctamente.';
      formMsg.classList.add('text-green-600');
      btnReset.click();
      await loadArticles();
    }
    btnSubmit.disabled = false;
  });

  // ------- Listado y visibilidad -------
  const listMsg = document.getElementById('list-msg');
  const tbody = document.getElementById('articles-body');

  async function loadArticles() {
    listMsg.textContent = '';
    tbody.innerHTML = '<tr><td class="py-3 text-gray-500" colspan="4">Cargando…</td></tr>';
    try {
      const rows = await API.list();
      if (!Array.isArray(rows) || rows.length === 0) {
        tbody.innerHTML = '<tr><td class="py-3 text-gray-500" colspan="4">Sin artículos.</td></tr>';
        return;
      }
      tbody.innerHTML = '';
      for (const a of rows) {
        const tr = document.createElement('tr');
        tr.className = 'border-b last:border-0';
        tr.dataset.id = a.id;
        tr.innerHTML = `
          <td class="py-2 pr-4">${escapeHtml(a.titulo || '')}</td>
          <td class="py-2 pr-4">${escapeHtml(a.descripcion || '')}</td>
          <td class="py-2 pr-4">${escapeHtml(a.fecha || '')}</td>
          <td class="py-2"><input type="checkbox" class="vis-toggle h-4 w-4" ${a.visible ? 'checked' : ''}/></td>`;
        tbody.appendChild(tr);
      }
    } catch (e) {
      tbody.innerHTML = '<tr><td class="py-3 text-red-600" colspan="4">Error al cargar.</td></tr>';
    }
  }

  const btnSaveVis = document.getElementById('btn-save-visibility');
  document.getElementById('btn-reload').addEventListener('click', loadArticles);

  btnSaveVis.addEventListener('click', async () => {
    const idsAll = $$('#articles-body tr').map(tr => Number(tr.dataset.id));
    if (idsAll.length === 0) return;

    const idsOn = $$('#articles-body .vis-toggle:checked').map(c => Number(c.closest('tr').dataset.id));
    const setOff = idsAll.filter(id => !idsOn.includes(id));

    listMsg.textContent = 'Guardando…';
    listMsg.className = 'text-sm mt-2';
    btnSaveVis.disabled = true;

    try {
      const promises = [];
      if (idsOn.length)  promises.push(API.patchVisibility(idsOn, true));
      if (setOff.length) promises.push(API.patchVisibility(setOff, false));
      await Promise.all(promises);

      listMsg.textContent = 'Visibilidad actualizada.';
      listMsg.classList.add('text-green-600');
      await loadArticles();
    } catch (e) {
      listMsg.textContent = 'Error al actualizar visibilidad.';
      listMsg.classList.add('text-red-600');
    } finally {
      btnSaveVis.disabled = false;
    }
  });

  // Init
  loadArticles();
})();
