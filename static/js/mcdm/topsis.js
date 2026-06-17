// static/js/mcdm/topsis.js
// TOPSIS puro (MCDM, sin metaheurística): matriz de solo lectura, único
// parámetro editable es el peso w por criterio. Sin tabs, sin stepper,
// sin historial — es una página de una sola sección porque no hay
// iteraciones que comparar.

document.addEventListener('DOMContentLoaded', function () {
  const matrizHead = document.getElementById('matrizHead');
  const matrizBody = document.getElementById('matrizBody');
  const pesosWrap  = document.getElementById('pesosWrap');
  const btnEjecutar = document.getElementById('ejecutarTopsis');
  const msgError = document.getElementById('mensajeError');

  // La matriz se pide al backend en la primera carga (de solo lectura,
  // fija) para no duplicarla hardcodeada también en el frontend.
  let matrizActual = null;
  let nCriterios = 0;

  function renderMatrizSoloLectura(matriz, criterios) {
    matrizHead.innerHTML = '<th class="border border-slate-300 px-2 py-1 bg-slate-100"></th>';
    criterios.forEach((c) => {
      const th = document.createElement('th');
      th.className = 'border border-slate-300 px-2 py-1 bg-slate-100';
      th.textContent = c;
      matrizHead.appendChild(th);
    });

    matrizBody.innerHTML = '';
    matriz.forEach((fila, f) => {
      const tr = document.createElement('tr');
      const th = document.createElement('th');
      th.className = 'border border-slate-300 px-2 py-1 bg-slate-100 text-left';
      th.textContent = `A${f + 1}`;
      tr.appendChild(th);
      fila.forEach((valor) => {
        const td = document.createElement('td');
        td.className = 'border border-slate-300 px-2 py-1 text-center text-gray-600';
        td.textContent = valor;
        tr.appendChild(td);
      });
      matrizBody.appendChild(tr);
    });
  }

  function renderPesos(criterios, valoresIniciales) {
    pesosWrap.innerHTML = '';
    criterios.forEach((c, i) => {
      const div = document.createElement('div');
      const label = document.createElement('label');
      label.className = 'block mb-1 text-xs font-medium text-gray-700';
      label.textContent = c;
      const input = document.createElement('input');
      input.type = 'number'; input.step = 'any'; input.required = true;
      input.id = `w_${i}`;
      input.value = valoresIniciales[i];
      input.className = 'bg-slate-300 border border-gray-300 text-gray-900 ' +
        'text-sm rounded p-1.5 w-full text-center';
      div.appendChild(label);
      div.appendChild(input);
      pesosWrap.appendChild(div);
    });
  }

  const W_INICIAL = [0.400, 0.200, 0.030, 0.070, 0.300];

  // Primera carga: solo pedimos la matriz fija para pintarla, sin
  // ejecutar el algoritmo ni generar una ejecución en el historial.
  function inicializar() {
    fetch('/api/algoritmos/topsis/matriz')
      .then(async (resp) => {
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
        return data;
      })
      .then((data) => {
        matrizActual = data.matriz;
        nCriterios = data.n_criterios;
        renderMatrizSoloLectura(data.matriz, data.criterios);
        renderPesos(data.criterios, W_INICIAL);
      })
      .catch((err) => {
        msgError.textContent = err.message;
        msgError.classList.remove('hidden');
      });
  }

  function leerNumero(el, nombre) {
    const v = parseFloat(el.value);
    if (Number.isNaN(v)) throw new Error(`Valor inválido en ${nombre}.`);
    return v;
  }

  function construirPayload() {
    const w = [];
    for (let c = 0; c < nCriterios; c++) {
      w.push(leerNumero(document.getElementById(`w_${c}`), `el peso w del criterio ${c + 1}`));
    }
    return { w };
  }

  btnEjecutar.addEventListener('click', async function () {
    msgError.classList.add('hidden');
    let payload;
    try {
      payload = construirPayload();
    } catch (e) {
      msgError.textContent = e.message;
      msgError.classList.remove('hidden');
      return;
    }

    btnEjecutar.disabled = true;
    btnEjecutar.textContent = 'Calculando…';
    try {
      const resp = await fetch('/api/algoritmos/topsis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
      mostrarResultados(data);
    } catch (e) {
      msgError.textContent = e.message;
      msgError.classList.remove('hidden');
    } finally {
      btnEjecutar.disabled = false;
      btnEjecutar.textContent = 'Calcular';
    }
  });

  let grafica = null;

  function mostrarResultados(datos) {
    document.getElementById('resultadosVacio').classList.add('hidden');
    document.getElementById('seccionResultados').classList.remove('hidden');

    document.getElementById('mejorFinal').textContent = `A${datos.mejor_alternativa_final}`;
    document.getElementById('tiempoEjecucion').textContent = datos.tiempo_ejecucion;
    document.getElementById('fechaInicio').textContent = datos.fecha_inicio;
    document.getElementById('horaInicio').textContent = datos.hora_inicio;

    const cuerpo = document.getElementById('tablaResultados');
    cuerpo.innerHTML = '';
    const ranking = datos.mejor_alternativa || [];
    const puntuaciones = datos.puntuaciones || [];
    for (let i = 0; i < ranking.length; i++) {
      const tr = document.createElement('tr');
      tr.innerHTML =
        `<td class="border border-slate-200 text-center px-2">${i + 1}</td>` +
        `<td class="border border-slate-200 text-center px-2">A${ranking[i]}</td>` +
        `<td class="border border-slate-200 text-center px-2">${puntuaciones[i] !== undefined ? puntuaciones[i].toFixed(4) : '—'}</td>`;
      cuerpo.appendChild(tr);
    }

    // Gráfica de barras horizontales del ranking final, ordenada de mejor
    // a peor (de arriba a abajo), mismo estilo Chart.js que PSO/BA/ACO.
    const ctx = document.getElementById('graficaRanking');
    if (grafica) grafica.destroy();
    grafica = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ranking.map((alt) => `A${alt}`),
        datasets: [{
          label: 'Puntuación',
          data: puntuaciones,
          backgroundColor: 'rgba(59, 130, 246, 0.7)',
          borderColor: 'rgb(59, 130, 246)',
          borderWidth: 1,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: {
          title: { display: true, text: 'Clasificación final por alternativa' },
          legend: { display: false },
        },
        scales: {
          x: { title: { display: true, text: 'Puntuación' } },
          y: { title: { display: true, text: 'Alternativa' }, reverse: false },
        },
      },
    });

    if (datos.ejecucion_id) {
      const enlace = document.getElementById('descargarExcel');
      enlace.href = `/api/ejecuciones/${datos.ejecucion_id}/excel`;
      enlace.classList.remove('hidden');
      histCache = null;  // fuerza recargar el historial, ya que hay una ejecución nueva
      cargarHistorial();
    }
  }

  // ===================== HISTORIAL (paginado, estilo Material Design) =====================
  const histCargando = document.getElementById('histCargando');
  const histVacio = document.getElementById('histVacio');
  const histError = document.getElementById('histError');
  const histTablaWrap = document.getElementById('histTablaWrap');
  const histCuerpo = document.getElementById('histCuerpo');
  const histResumen = document.getElementById('histResumen');
  const histFilasPorPagina = document.getElementById('histFilasPorPagina');
  const histRangoPagina = document.getElementById('histRangoPagina');
  const histPagAnterior = document.getElementById('histPagAnterior');
  const histPagSiguiente = document.getElementById('histPagSiguiente');

  let histCache = null;   // lista completa traída del backend (hasta 50, ver límite del endpoint)
  let histPagina = 0;     // página actual, 0-indexada

  function estadoHistorial(mostrar) {
    for (const [el, vis] of [[histCargando, 'cargando'], [histVacio, 'vacio'],
      [histError, 'error'], [histTablaWrap, 'tabla']]) {
      el.classList.toggle('hidden', mostrar !== vis);
    }
  }

  function formatearFecha(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' }) +
      ' ' + d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
  }

  function filasPorPagina() {
    return parseInt(histFilasPorPagina.value, 10) || 10;
  }

  function renderPaginaHistorial() {
    const porPagina = filasPorPagina();
    const total = histCache.length;
    const totalPaginas = Math.max(1, Math.ceil(total / porPagina));
    histPagina = Math.min(histPagina, totalPaginas - 1);

    const inicio = histPagina * porPagina;
    const fin = Math.min(inicio + porPagina, total);
    const pagina = histCache.slice(inicio, fin);

    histCuerpo.innerHTML = '';
    for (const e of pagina) {
      const tr = document.createElement('tr');
      tr.className = 'border-b border-slate-100 hover:bg-slate-50';
      tr.innerHTML =
        `<td class="py-2 pr-3 text-gray-400">${e.id}</td>` +
        `<td class="py-2 pr-3">${formatearFecha(e.fecha_ejecucion)}</td>` +
        `<td class="py-2 pr-3">${e.usuario ?? '—'}</td>` +
        `<td class="py-2 pr-3">${e.n_alternativas}×${e.n_criterios}</td>` +
        `<td class="py-2 pr-3 font-medium">A${e.mejor_alternativa_final ?? '—'}</td>` +
        `<td class="py-2 pr-3">${e.gbf_final !== null && e.gbf_final !== undefined ? Number(e.gbf_final).toFixed(4) : '—'}</td>` +
        `<td class="py-2 pr-3">${(e.tiempo_ejecucion_seg ?? 0).toFixed(3)} s</td>` +
        `<td class="py-2 text-right">
           <a href="/api/ejecuciones/${e.id}/excel"
             class="inline-block text-sm text-gray-700 bg-slate-200 hover:bg-slate-300 rounded-lg px-3 py-1.5">XLSX</a>
         </td>`;
      histCuerpo.appendChild(tr);
    }

    histRangoPagina.textContent = total === 0 ? '0–0 de 0' : `${inicio + 1}–${fin} de ${total}`;
    histPagAnterior.disabled = histPagina === 0;
    histPagSiguiente.disabled = fin >= total;
    histResumen.textContent = `${total} ejecución${total === 1 ? '' : 'es'} registrada${total === 1 ? '' : 's'}`;
    histResumen.classList.remove('hidden');
  }

  histFilasPorPagina.addEventListener('change', () => { histPagina = 0; renderPaginaHistorial(); });
  histPagAnterior.addEventListener('click', () => { histPagina--; renderPaginaHistorial(); });
  histPagSiguiente.addEventListener('click', () => { histPagina++; renderPaginaHistorial(); });

  function cargarHistorial() {
    if (histCache) return;
    estadoHistorial('cargando');
    fetch('/api/ejecuciones?algoritmo=TOPSIS')
      .then(async (resp) => {
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
        return data;
      })
      .then((lista) => {
        histCache = lista;
        histPagina = 0;
        if (!lista.length) { estadoHistorial('vacio'); histResumen.classList.add('hidden'); return; }
        estadoHistorial('tabla');
        renderPaginaHistorial();
      })
      .catch((err) => { histError.textContent = err.message; estadoHistorial('error'); });
  }

  inicializar();
  cargarHistorial();
});
