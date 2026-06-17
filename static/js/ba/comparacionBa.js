// static/js/ba/comparacionBa.js
// Comparación de la familia BA: una sola matriz de entrada,
// se ejecutan los 4 algoritmos en secuencia y se comparan resultados.
// El peso w (fila editable) solo se envía a DA-BA, MOORA-BA y TOPSIS-BA;
// BA puro lo ignora porque su función objetivo no pondera criterios.

document.addEventListener('DOMContentLoaded', function () {
  // ===================== ESTADO DE LA MATRIZ =====================
  const MIN_CRITERIOS = 5, MAX_CRITERIOS = 15;
  const MIN_ALTERNATIVAS = 9, MAX_ALTERNATIVAS = 30;
  let nCriterios = MIN_CRITERIOS;
  let nAlternativas = MIN_ALTERNATIVAS;

  const MATRIZ_INICIAL = [
    [0.048, 0.047, 0.070, 0.087, 0.190],
    [0.053, 0.052, 0.066, 0.081, 0.058],
    [0.057, 0.057, 0.066, 0.076, 0.022],
    [0.062, 0.062, 0.063, 0.058, 0.007],
    [0.066, 0.066, 0.070, 0.085, 0.004],
    [0.070, 0.071, 0.066, 0.058, 0.003],
    [0.075, 0.075, 0.066, 0.047, 0.002],
    [0.079, 0.079, 0.066, 0.035, 0.002],
    [0.083, 0.083, 0.066, 0.051, 0.000],
  ];
  const W_INICIAL = [0.400, 0.200, 0.030, 0.070, 0.300];

  const matrizHead = document.getElementById('matrizHead');
  const matrizBody = document.getElementById('matrizBody');
  const matrizVectores = document.getElementById('matrizVectores');
  const dimsLabel = document.getElementById('dimensionesMatriz');
  const claseInput = 'w-full bg-white border border-gray-300 rounded px-1 py-0.5 text-sm text-center';

  const celdaId = (f, c) => `m_${f}_${c}`;

  function crearInput(valor, id) {
    const inp = document.createElement('input');
    inp.type = 'number'; inp.step = 'any'; inp.required = true;
    inp.className = claseInput; inp.value = valor; inp.id = id;
    return inp;
  }

  function valorInicialMatriz(f, c) {
    return (f < MATRIZ_INICIAL.length && c < MATRIZ_INICIAL[0].length)
      ? MATRIZ_INICIAL[f][c] : 0.050;
  }
  function valorInicialW(c) {
    return c < W_INICIAL.length ? W_INICIAL[c] : 0.100;
  }

  function renderMatriz() {
    const previos = {};
    document.querySelectorAll('#matrizBody input, #matrizVectores input')
      .forEach((i) => { previos[i.id] = i.value; });

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

    // Fila de pesos w — editable porque DA-BA/MOORA-BA/TOPSIS-BA la usan;
    // BA puro la ignora al construir su payload (ver más abajo)
    matrizVectores.innerHTML = '';
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.className = 'border border-blue-200 px-2 py-1 bg-blue-50 text-left text-blue-900';
    th.textContent = 'w (peso) — no aplica a BA puro';
    tr.appendChild(th);
    for (let c = 0; c < nCriterios; c++) {
      const td = document.createElement('td');
      td.className = 'border border-blue-200 p-1 bg-blue-50';
      const id = `w_${c}`;
      td.appendChild(crearInput((id in previos) ? previos[id] : valorInicialW(c), id));
      tr.appendChild(td);
    }
    matrizVectores.appendChild(tr);

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

  renderMatriz();

  // ===================== CONSTRUCCIÓN DEL PAYLOAD =====================
  function leerNumero(el, nombre) {
    const v = parseFloat(el.value);
    if (Number.isNaN(v)) throw new Error(`Valor inválido en ${nombre}.`);
    return v;
  }

  function construirPayloadBase() {
    const matriz = [];
    for (let f = 0; f < nAlternativas; f++) {
      const fila = [];
      for (let c = 0; c < nCriterios; c++) {
        fila.push(leerNumero(document.getElementById(celdaId(f, c)), `la celda A${f+1}/C${c+1}`));
      }
      matriz.push(fila);
    }
    const T = parseInt(document.getElementById('T').value, 10);
    if (Number.isNaN(T) || T < 1) throw new Error('T debe ser un entero mayor o igual a 1.');

    return {
      matriz,
      alpha: leerNumero(document.getElementById('alpha'), 'alpha'),
      gamma: leerNumero(document.getElementById('gamma'), 'gamma'),
      T,
    };
  }

  // ===================== EJECUCIÓN SECUENCIAL =====================
  const ALGORITMOS = [
    { id: 'ba',        endpoint: '/api/algoritmos/ba',        tieneW: false },
    { id: 'daba',      endpoint: '/api/algoritmos/daba',      tieneW: true  },
    { id: 'mooraba',   endpoint: '/api/algoritmos/mooraba',   tieneW: true  },
    { id: 'topsisba',  endpoint: '/api/algoritmos/topsisba',  tieneW: true  },
  ];

  function setEstado(id, texto, claseColor) {
    const el = document.getElementById(`estado_${id}`);
    el.textContent = texto;
    el.className = `text-xs ${claseColor}`;
  }

  function renderResultadoTarjeta(id, datos) {
    document.getElementById(`gbf_${id}`).textContent =
      datos.gbf_final !== undefined ? Number(datos.gbf_final).toFixed(4) : '—';
    document.getElementById(`alt_${id}`).textContent =
      datos.mejor_alternativa_final !== undefined ? `A${datos.mejor_alternativa_final}` : '—';
    document.getElementById(`tiempo_${id}`).textContent = datos.tiempo_ejecucion || '—';
    document.getElementById(`iter_${id}`).textContent = datos.iteraciones ?? '—';

    const cuerpo = document.getElementById(`tabla_${id}`);
    cuerpo.innerHTML = '';
    const gbf = datos.historico_gbf || [];
    const resultados = datos.resultados_por_iteracion || datos.mejor_alternativa || [];
    const n = Math.max(gbf.length, resultados.length);
    for (let i = 0; i < n; i++) {
      const tr = document.createElement('tr');
      tr.innerHTML =
        `<td class="border border-slate-200 text-center px-2">${i + 1}</td>` +
        `<td class="border border-slate-200 text-center px-2">A${resultados[i] ?? '—'}</td>` +
        `<td class="border border-slate-200 text-center px-2">${gbf[i] !== undefined ? gbf[i].toFixed(4) : '—'}</td>`;
      cuerpo.appendChild(tr);
    }
  }

  async function ejecutarAlgoritmo({ id, endpoint, tieneW }, payloadBase, w) {
    setEstado(id, 'Ejecutando…', 'text-blue-500');
    const payload = { ...payloadBase };
    if (tieneW) payload.w = w;
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
      renderResultadoTarjeta(id, data);
      setEstado(id, 'Completado', 'text-green-600');
    } catch (err) {
      setEstado(id, err.message, 'text-red-600');
    }
  }

  const btnEjecutar = document.getElementById('ejecutarComparacion');
  const msgError = document.getElementById('mensajeError');

  btnEjecutar.addEventListener('click', async function () {
    msgError.classList.add('hidden');
    let payloadBase, w;
    try {
      payloadBase = construirPayloadBase();
      w = [];
      for (let c = 0; c < nCriterios; c++) {
        w.push(leerNumero(document.getElementById(`w_${c}`), `el peso w de C${c + 1}`));
      }
    } catch (e) {
      msgError.textContent = e.message;
      msgError.classList.remove('hidden');
      return;
    }

    btnEjecutar.disabled = true;
    btnEjecutar.textContent = 'Calculando…';
    ALGORITMOS.forEach(({ id }) => setEstado(id, 'En cola', 'text-gray-400'));

    // Secuencial — evita saturar el servidor con las 4 ejecuciones a la vez
    for (const algo of ALGORITMOS) {
      await ejecutarAlgoritmo(algo, payloadBase, w);
    }

    btnEjecutar.disabled = false;
    btnEjecutar.textContent = 'Calcular comparación';
  });
});
