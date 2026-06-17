// static/js/aco/laboratorio.js
// Laboratorio ACO: matriz de decisión dinámica (todos los valores deben
// ser > 0, ACO calcula una heurística 1/valor), parámetros alpha/beta/
// rho/Q/n_ants, stepper, tabs y gráfica de convergencia. Independiente de
// pso/laboratorio.js y ba/laboratorio.js a propósito: ACO no usa pesos w
// ni r1/r2, y tiene un parámetro adicional (n_ants) que ninguna otra
// familia tiene.

document.addEventListener('DOMContentLoaded', function () {
  const CFG = window.ALGO_CONFIG || {};
  const ALGORITMO = CFG.algoritmo || 'ACO';
  const ENDPOINT  = CFG.endpoint  || '/api/algoritmos/aco';
  let _labInicializado = false;

  // ===================== TABS =====================
  const tabs = {
    teo:  { btn: document.getElementById('tabTeo'),  panel: document.getElementById('panelTeo') },
    lab:  { btn: document.getElementById('tabLab'),  panel: document.getElementById('panelLab') },
    hist: { btn: document.getElementById('tabHist'), panel: document.getElementById('panelHist') },
  };

  function activarTab(nombre) {
    for (const [clave, t] of Object.entries(tabs)) {
      const activo = clave === nombre;
      t.btn.setAttribute('aria-selected', activo ? 'true' : 'false');
      t.btn.classList.toggle('border-slate-700', activo);
      t.btn.classList.toggle('font-medium', activo);
      t.btn.classList.toggle('text-gray-900', activo);
      t.btn.classList.toggle('border-transparent', !activo);
      t.btn.classList.toggle('text-gray-500', !activo);
      t.panel.classList.toggle('hidden', !activo);
    }
    window.scrollTo({ top: 0, behavior: 'instant' });
    if (nombre === 'hist') cargarHistorial();
    if (nombre === 'lab' && !_labInicializado) {
      _labInicializado = true;
      renderMatriz();
    }
  }
  tabs.teo.btn.addEventListener('click', () => activarTab('teo'));
  tabs.lab.btn.addEventListener('click', () => activarTab('lab'));
  tabs.hist.btn.addEventListener('click', () => activarTab('hist'));
  document.getElementById('irLaboratorio').addEventListener('click', () => activarTab('lab'));

  // ===================== STEPPER =====================
  function irAPaso(n) {
    for (let p = 1; p <= 3; p++) {
      document.getElementById('paso' + p).classList.toggle('hidden', p !== n);
    }
    document.querySelectorAll('.paso-btn').forEach((btn) => {
      const p = parseInt(btn.dataset.paso, 10);
      const circulo = btn.querySelector('.paso-circulo');
      const texto = btn.querySelector('.paso-texto');
      const activo = p === n;
      circulo.classList.toggle('bg-slate-700', activo);
      circulo.classList.toggle('text-white', activo);
      circulo.classList.toggle('bg-slate-200', !activo);
      circulo.classList.toggle('text-gray-600', !activo);
      texto.classList.toggle('font-medium', activo);
      texto.classList.toggle('text-gray-900', activo);
      texto.classList.toggle('text-gray-500', !activo);
    });
    window.scrollTo({ top: 0, behavior: 'instant' });
  }
  document.querySelectorAll('.paso-btn').forEach((btn) =>
    btn.addEventListener('click', () => irAPaso(parseInt(btn.dataset.paso, 10))));
  document.querySelectorAll('.ir-paso').forEach((btn) =>
    btn.addEventListener('click', () => irAPaso(parseInt(btn.dataset.ir, 10))));

  // ===================== ESTADO Y CONSTANTES =====================
  const MIN_CRITERIOS = 5, MIN_ALTERNATIVAS = 9;
  const MAX_CRITERIOS = 20, MAX_ALTERNATIVAS = 30;

  // NOTA: a diferencia de la matriz de referencia usada en PSO/BA, el último
  // valor de A9/C5 es 0.001 en vez de 0.000. ACO calcula una heurística
  // 1/valor, así que un cero exacto rompe la validación del backend.
  const MATRIZ_INICIAL = [
    [0.048, 0.047, 0.070, 0.087, 0.190],
    [0.053, 0.052, 0.066, 0.081, 0.058],
    [0.057, 0.057, 0.066, 0.076, 0.022],
    [0.062, 0.062, 0.063, 0.058, 0.007],
    [0.066, 0.066, 0.070, 0.085, 0.004],
    [0.070, 0.071, 0.066, 0.058, 0.003],
    [0.075, 0.075, 0.066, 0.047, 0.002],
    [0.079, 0.079, 0.066, 0.035, 0.002],
    [0.083, 0.083, 0.066, 0.051, 0.001],
  ];

  let nCriterios = MIN_CRITERIOS;
  let nAlternativas = MIN_ALTERNATIVAS;
  let grafica = null;

  const matrizHead = document.getElementById('matrizHead');
  const matrizBody = document.getElementById('matrizBody');
  const dimsLabel  = document.getElementById('dimensionesMatriz');
  const btnEjecutar = document.getElementById('ejecutarAlgo');
  const msgError = document.getElementById('mensajeError');

  const claseInput = 'bg-slate-300 border border-gray-300 text-gray-900 ' +
    'text-sm rounded p-1.5 w-full text-center';

  function crearInput(valor, id) {
    const inp = document.createElement('input');
    inp.type = 'number'; inp.step = 'any'; inp.min = '0.0001'; inp.required = true;
    inp.className = claseInput; inp.value = valor; inp.id = id;
    return inp;
  }

  // ===================== MATRIZ (sin w — ACO no pondera criterios) =====================
  const celdaId = (f, c) => `m_${f}_${c}`;

  function valorInicialMatriz(f, c) {
    return (f < MATRIZ_INICIAL.length && c < MATRIZ_INICIAL[0].length)
      ? MATRIZ_INICIAL[f][c] : 0.050;
  }

  function renderMatriz() {
    const previos = {};
    document.querySelectorAll('#matrizBody input').forEach((i) => { previos[i.id] = i.value; });

    matrizHead.innerHTML = '<th class="border border-slate-300 px-2 py-1 bg-slate-100"></th>';
    for (let c = 0; c < nCriterios; c++) {
      const th = document.createElement('th');
      th.className = 'border border-slate-300 px-2 py-1 bg-slate-100';
      th.textContent = 'C' + (c + 1);
      matrizHead.appendChild(th);
    }

    matrizBody.innerHTML = '';
    for (let f = 0; f < nAlternativas; f++) {
      const tr = document.createElement('tr');
      const th = document.createElement('th');
      th.className = 'border border-slate-300 px-2 py-1 bg-slate-100 text-left';
      th.textContent = 'A' + (f + 1);
      tr.appendChild(th);
      for (let c = 0; c < nCriterios; c++) {
        const td = document.createElement('td');
        td.className = 'border border-slate-300 p-1';
        const id = celdaId(f, c);
        td.appendChild(crearInput((id in previos) ? previos[id] : valorInicialMatriz(f, c), id));
        tr.appendChild(td);
      }
      matrizBody.appendChild(tr);
    }

    dimsLabel.textContent = `${nAlternativas} alternativas × ${nCriterios} criterios`;
  }

  document.getElementById('btnAddCriterio').addEventListener('click', () => {
    if (nCriterios < MAX_CRITERIOS) { nCriterios++; renderMatriz(); }
  });
  document.getElementById('btnDelCriterio').addEventListener('click', () => {
    if (nCriterios > MIN_CRITERIOS) { nCriterios--; renderMatriz(); }
  });
  document.getElementById('btnAddAlternativa').addEventListener('click', () => {
    if (nAlternativas < MAX_ALTERNATIVAS) { nAlternativas++; renderMatriz(); }
  });
  document.getElementById('btnDelAlternativa').addEventListener('click', () => {
    if (nAlternativas > MIN_ALTERNATIVAS) { nAlternativas--; renderMatriz(); }
  });

  // ===================== PLANTILLA EXCEL =====================
  const ALGORITMO_URL = ALGORITMO.toLowerCase();
  const enlacePlantilla = document.getElementById('descargarPlantilla');
  enlacePlantilla.addEventListener('click', () => {
    enlacePlantilla.href =
      `/api/algoritmos/${ALGORITMO_URL}/plantilla?criterios=${nCriterios}&alternativas=${nAlternativas}`;
  });

  document.getElementById('archivoPlantilla').addEventListener('change', function () {
    const msgErrorPlantilla = document.getElementById('mensajeErrorPlantilla');
    msgErrorPlantilla.classList.add('hidden');
    const estado = document.getElementById('estadoPlantilla');
    if (!this.files.length) return;
    const archivo = this.files[0];
    estado.textContent = 'Leyendo plantilla…';

    const fd = new FormData();
    fd.append('archivo', archivo);
    fetch(`/api/algoritmos/${ALGORITMO_URL}/plantilla`, { method: 'POST', body: fd })
      .then(async (resp) => {
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
        return data;
      })
      .then((p) => {
        const n = p.matriz[0].length;
        const a = p.matriz.length;
        if (n > MAX_CRITERIOS || a > MAX_ALTERNATIVAS) {
          throw new Error(`La plantilla (${a}×${n}) excede el máximo de la interfaz ` +
            `(${MAX_ALTERNATIVAS}×${MAX_CRITERIOS}).`);
        }
        nCriterios = n;
        nAlternativas = a;
        renderMatriz();
        for (let f = 0; f < a; f++)
          for (let c = 0; c < n; c++)
            document.getElementById(celdaId(f, c)).value = p.matriz[f][c];
        document.getElementById('alpha').value = p.alpha;
        document.getElementById('beta').value = p.beta;
        document.getElementById('rho').value = p.rho;
        document.getElementById('Q').value = p.Q;
        document.getElementById('n_ants').value = p.n_ants;
        document.getElementById('T').value = p.T;
        estado.textContent = `Plantilla cargada (${p.algoritmo_detectado || ALGORITMO}): ` +
          `${a} alternativas × ${n} criterios. Revise y presione Calcular.`;
      })
      .catch((err) => {
        estado.textContent = '';
        msgErrorPlantilla.textContent = err.message;
        msgErrorPlantilla.classList.remove('hidden');
      })
      .finally(() => { this.value = ''; });
  });

  // ===================== EJECUCIÓN =====================
  function leerNumero(el, nombre) {
    if (!el) throw new Error(`Falta el campo ${nombre}.`);
    const v = parseFloat(el.value);
    if (Number.isNaN(v)) throw new Error(`Valor inválido en ${nombre}.`);
    return v;
  }

  function construirPayload() {
    const matriz = [];
    for (let f = 0; f < nAlternativas; f++) {
      const fila = [];
      for (let c = 0; c < nCriterios; c++) {
        fila.push(leerNumero(document.getElementById(celdaId(f, c)),
          `la celda A${f + 1}/C${c + 1} de la matriz`));
      }
      matriz.push(fila);
    }
    const T = parseInt(document.getElementById('T').value, 10);
    if (Number.isNaN(T) || T < 1) throw new Error('T debe ser un entero mayor o igual a 1.');
    const n_ants = parseInt(document.getElementById('n_ants').value, 10);
    if (Number.isNaN(n_ants) || n_ants < 1) throw new Error('n_ants debe ser un entero mayor o igual a 1.');

    return {
      matriz,
      alpha: leerNumero(document.getElementById('alpha'), 'alpha'),
      beta:  leerNumero(document.getElementById('beta'), 'beta'),
      rho:   leerNumero(document.getElementById('rho'), 'rho'),
      Q:     leerNumero(document.getElementById('Q'), 'Q'),
      n_ants,
      T,
    };
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
      const resp = await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
      mostrarResultados(data);
      irAPaso(3);
    } catch (e) {
      msgError.textContent = e.message;
      msgError.classList.remove('hidden');
    } finally {
      btnEjecutar.disabled = false;
      btnEjecutar.textContent = 'Calcular';
    }
  });

  function mostrarResultados(datos) {
    document.getElementById('resultadosVacio').classList.add('hidden');
    const seccion = document.getElementById('seccionResultados');
    seccion.classList.remove('hidden');

    document.getElementById('cantidadIteraciones').textContent = datos.iteraciones;
    document.getElementById('fechaInicio').textContent = datos.fecha_inicio;
    document.getElementById('horaInicio').textContent = datos.hora_inicio;
    document.getElementById('horaFinalizacion').textContent = datos.hora_finalizacion;
    document.getElementById('tiempoEjecucion').textContent = datos.tiempo_ejecucion;
    document.getElementById('mejorFinal').textContent = `A${datos.mejor_alternativa_final}`;

    const cuerpo = document.getElementById('tablaResultados');
    cuerpo.innerHTML = '';
    const gbf = datos.historico_gbf || [];
    const resultados = datos.resultados_por_iteracion || [];
    for (let i = 0; i < resultados.length; i++) {
      const tr = document.createElement('tr');
      tr.innerHTML =
        `<td class="border border-slate-300 text-center px-2">${i + 1}</td>` +
        `<td class="border border-slate-300 text-center px-2">A${resultados[i]}</td>` +
        `<td class="border border-slate-300 text-center px-2">${gbf[i] !== undefined ? gbf[i].toFixed(4) : '—'}</td>`;
      cuerpo.appendChild(tr);
    }

    const ctx = document.getElementById('graficaConvergencia');
    if (grafica) grafica.destroy();
    grafica = new Chart(ctx, {
      type: 'line',
      data: {
        labels: gbf.map((_, i) => i + 1),
        datasets: [{
          label: 'Puntuación de feromona (ACO)',
          data: gbf,
          borderColor: '#334155',
          backgroundColor: 'rgba(51,65,85,0.08)',
          tension: 0.2,
        }],
      },
      options: {
        responsive: true,
        scales: {
          x: { title: { display: true, text: 'Iteración' } },
          y: { title: { display: true, text: 'Puntuación' } },
        },
      },
    });

    const idEj = datos.ejecucion_id;
    if (idEj) {
      const enlace = document.getElementById('descargarExcel');
      enlace.href = `/api/ejecuciones/${idEj}/excel`;
      enlace.classList.remove('hidden');
    }
  }

  // ===================== HISTORIAL =====================
  let histCache = null;
  function cargarHistorial() {
    const cargando = document.getElementById('histCargando');
    const vacio = document.getElementById('histVacio');
    const errorEl = document.getElementById('histError');
    const wrap = document.getElementById('histTablaWrap');

    if (histCache) { pintarHistorial(histCache); return; }

    cargando.classList.remove('hidden');
    vacio.classList.add('hidden');
    errorEl.classList.add('hidden');
    wrap.classList.add('hidden');

    fetch(`/api/ejecuciones?algoritmo=${ALGORITMO}`)
      .then(async (resp) => {
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
        return data;
      })
      .then((lista) => {
        histCache = lista;
        pintarHistorial(lista);
      })
      .catch((err) => {
        cargando.classList.add('hidden');
        errorEl.textContent = err.message;
        errorEl.classList.remove('hidden');
      });
  }

  function pintarHistorial(lista) {
    const cargando = document.getElementById('histCargando');
    const vacio = document.getElementById('histVacio');
    const wrap = document.getElementById('histTablaWrap');
    const cuerpo = document.getElementById('histCuerpo');
    cargando.classList.add('hidden');

    if (!lista.length) { vacio.classList.remove('hidden'); return; }
    wrap.classList.remove('hidden');
    cuerpo.innerHTML = '';
    lista.forEach((ej, idx) => {
      const tr = document.createElement('tr');
      tr.className = 'border-b border-slate-100';
      tr.innerHTML = `
        <td class="py-2 pr-3">${idx + 1}</td>
        <td class="py-2 pr-3">${new Date(ej.fecha_ejecucion).toLocaleString()}</td>
        <td class="py-2 pr-3">${ej.usuario || '—'}</td>
        <td class="py-2 pr-3">${ej.n_alternativas}×${ej.n_criterios}</td>
        <td class="py-2 pr-3">${ej.iteraciones}</td>
        <td class="py-2 pr-3">${ej.gbf_final !== null ? Number(ej.gbf_final).toFixed(4) : '—'}</td>
        <td class="py-2 pr-3">A${ej.mejor_alternativa_final ?? '—'}</td>
        <td class="py-2 pr-3">${ej.tiempo_ejecucion_seg ? ej.tiempo_ejecucion_seg.toFixed(2) + 's' : '—'}</td>
        <td class="py-2 text-right">
          <a href="/api/ejecuciones/${ej.id}/excel" class="text-slate-700 hover:underline">Excel</a>
        </td>`;
      cuerpo.appendChild(tr);
    });
  }
});