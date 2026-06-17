// static/js/comparacionGeneral.js
// Comparación General: una sola matriz de entrada, se ejecutan las nueve
// variantes híbridas (DA/MOORA/TOPSIS x PSO/BA/ACO) en secuencia.
//
// Cada familia tiene su propio esquema de parámetros:
//   PSO: wwi, c1, c2 (R1/R2 NO se envían — el backend los deriva del
//        ranking de cada método, igual que en sus laboratorios individuales)
//   BA:  alpha, gamma
//   ACO: alpha, beta, rho, Q, n_ants
// w (peso por criterio) lo usan las nueve variantes.
// EV (Min/Max por criterio) solo lo usan las tres variantes MOORA.

document.addEventListener('DOMContentLoaded', function () {
  // ===================== ESTADO DE LA MATRIZ =====================
  const MIN_CRITERIOS = 5, MAX_CRITERIOS = 15;
  const MIN_ALTERNATIVAS = 9, MAX_ALTERNATIVAS = 30;
  let nCriterios = MIN_CRITERIOS;
  let nAlternativas = MIN_ALTERNATIVAS;

  // 0.001, no 0.000 en A9/C5 — las variantes de ACO calculan 1/valor
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
  const W_INICIAL = [0.400, 0.200, 0.030, 0.070, 0.300];
  const EV_INICIAL = 'Min';

  const matrizHead = document.getElementById('matrizHead');
  const matrizBody = document.getElementById('matrizBody');
  const matrizVectores = document.getElementById('matrizVectores');
  const dimsLabel = document.getElementById('dimensionesMatriz');
  const claseInput = 'w-full bg-white border border-gray-300 rounded px-1 py-0.5 text-sm text-center';

  const celdaId = (f, c) => `m_${f}_${c}`;

  function crearInput(valor, id) {
    const inp = document.createElement('input');
    inp.type = 'number'; inp.step = 'any'; inp.min = '0.0001'; inp.required = true;
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
    document.querySelectorAll('#matrizBody input, #matrizVectores input, #matrizVectores select')
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

    matrizVectores.innerHTML = '';

    // Fila w — la usan las nueve variantes
    const trW = document.createElement('tr');
    const thW = document.createElement('th');
    thW.className = 'border border-blue-200 px-2 py-1 bg-blue-50 text-left text-blue-900';
    thW.textContent = 'w (peso)';
    trW.appendChild(thW);
    for (let c = 0; c < nCriterios; c++) {
      const td = document.createElement('td');
      td.className = 'border border-blue-200 p-1 bg-blue-50';
      const id = `w_${c}`;
      td.appendChild(crearInput((id in previos) ? previos[id] : valorInicialW(c), id));
      trW.appendChild(td);
    }
    matrizVectores.appendChild(trW);

    // Fila EV — solo aplica a MOORA-PSO, MOORA-BA, MOORA-ACO
    const trEv = document.createElement('tr');
    const thEv = document.createElement('th');
    thEv.className = 'border border-emerald-200 px-2 py-1 bg-emerald-50 text-left text-emerald-900';
    thEv.textContent = 'EV (Max/Min) — solo MOORA-PSO/BA/ACO';
    trEv.appendChild(thEv);
    for (let c = 0; c < nCriterios; c++) {
      const td = document.createElement('td');
      td.className = 'border border-emerald-200 p-1 bg-emerald-50';
      const id = `ev_${c}`;
      const select = document.createElement('select');
      select.id = id;
      select.className = 'w-full bg-white border border-gray-300 rounded p-1 text-sm text-center';
      ['Min', 'Max'].forEach((opcion) => {
        const option = document.createElement('option');
        option.value = opcion;
        option.textContent = opcion;
        select.appendChild(option);
      });
      select.value = (id in previos) ? previos[id] : EV_INICIAL;
      td.appendChild(select);
      trEv.appendChild(td);
    }
    matrizVectores.appendChild(trEv);

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

  // ===================== LECTURA DE CAMPOS =====================
  function leerNumero(el, nombre) {
    const v = parseFloat(el.value);
    if (Number.isNaN(v)) throw new Error(`Valor inválido en ${nombre}.`);
    return v;
  }

  function leerMatriz() {
    const matriz = [];
    for (let f = 0; f < nAlternativas; f++) {
      const fila = [];
      for (let c = 0; c < nCriterios; c++) {
        fila.push(leerNumero(document.getElementById(celdaId(f, c)), `la celda A${f+1}/C${c+1}`));
      }
      matriz.push(fila);
    }
    return matriz;
  }

  function leerVector(prefijo, nombre) {
    const v = [];
    for (let c = 0; c < nCriterios; c++) {
      const el = document.getElementById(`${prefijo}_${c}`);
      if (!el) throw new Error(`Falta el campo ${nombre} de C${c + 1}.`);
      v.push(prefijo === 'ev' ? el.value : leerNumero(el, `${nombre} de C${c + 1}`));
    }
    return v;
  }

  // ===================== EJECUCIÓN SECUENCIAL =====================
  // Cada entrada construye su propio payload — los esquemas de parámetros
  // de PSO, BA y ACO no se parecen entre sí, así que no hay un payload
  // "base" único como en las comparaciones por familia.
  const ALGORITMOS = [
    {
      id: 'dapso', endpoint: '/api/algoritmos/dapso',
      payload: (matriz, w) => ({
        matriz, w,
        wwi: leerNumero(document.getElementById('wwi'), 'wwi'),
        c1:  leerNumero(document.getElementById('c1'), 'c1'),
        c2:  leerNumero(document.getElementById('c2'), 'c2'),
        T:   leerT(),
      }),
    },
    {
      id: 'moorapso', endpoint: '/api/algoritmos/moorapso',
      payload: (matriz, w, EV) => ({
        matriz, w, EV,
        wwi: leerNumero(document.getElementById('wwi'), 'wwi'),
        c1:  leerNumero(document.getElementById('c1'), 'c1'),
        c2:  leerNumero(document.getElementById('c2'), 'c2'),
        T:   leerT(),
      }),
    },
    {
      id: 'topsispso', endpoint: '/api/algoritmos/topsispso',
      payload: (matriz, w) => ({
        matriz, w,
        wwi: leerNumero(document.getElementById('wwi'), 'wwi'),
        c1:  leerNumero(document.getElementById('c1'), 'c1'),
        c2:  leerNumero(document.getElementById('c2'), 'c2'),
        T:   leerT(),
      }),
    },
    {
      id: 'daba', endpoint: '/api/algoritmos/daba',
      payload: (matriz, w) => ({
        matriz, w,
        alpha: leerNumero(document.getElementById('alphaBa'), 'alpha (BA)'),
        gamma: leerNumero(document.getElementById('gamma'), 'gamma'),
        T:     leerT(),
      }),
    },
    {
      id: 'mooraba', endpoint: '/api/algoritmos/mooraba',
      payload: (matriz, w, EV) => ({
        matriz, w, EV,
        alpha: leerNumero(document.getElementById('alphaBa'), 'alpha (BA)'),
        gamma: leerNumero(document.getElementById('gamma'), 'gamma'),
        T:     leerT(),
      }),
    },
    {
      id: 'topsisba', endpoint: '/api/algoritmos/topsisba',
      payload: (matriz, w) => ({
        matriz, w,
        alpha: leerNumero(document.getElementById('alphaBa'), 'alpha (BA)'),
        gamma: leerNumero(document.getElementById('gamma'), 'gamma'),
        T:     leerT(),
      }),
    },
    {
      id: 'daaco', endpoint: '/api/algoritmos/daaco',
      payload: (matriz, w) => ({
        matriz, w,
        alpha:  leerNumero(document.getElementById('alphaAco'), 'alpha (ACO)'),
        beta:   leerNumero(document.getElementById('beta'), 'beta'),
        rho:    leerNumero(document.getElementById('rho'), 'rho'),
        Q:      leerNumero(document.getElementById('Q'), 'Q'),
        n_ants: leerEntero(document.getElementById('n_ants'), 'n_ants'),
        T:      leerT(),
      }),
    },
    {
      id: 'mooraaco', endpoint: '/api/algoritmos/mooraaco',
      payload: (matriz, w, EV) => ({
        matriz, w, EV,
        alpha:  leerNumero(document.getElementById('alphaAco'), 'alpha (ACO)'),
        beta:   leerNumero(document.getElementById('beta'), 'beta'),
        rho:    leerNumero(document.getElementById('rho'), 'rho'),
        Q:      leerNumero(document.getElementById('Q'), 'Q'),
        n_ants: leerEntero(document.getElementById('n_ants'), 'n_ants'),
        T:      leerT(),
      }),
    },
    {
      id: 'topsisaco', endpoint: '/api/algoritmos/topsisaco',
      payload: (matriz, w) => ({
        matriz, w,
        alpha:  leerNumero(document.getElementById('alphaAco'), 'alpha (ACO)'),
        beta:   leerNumero(document.getElementById('beta'), 'beta'),
        rho:    leerNumero(document.getElementById('rho'), 'rho'),
        Q:      leerNumero(document.getElementById('Q'), 'Q'),
        n_ants: leerEntero(document.getElementById('n_ants'), 'n_ants'),
        T:      leerT(),
      }),
    },
  ];

  function leerT() {
    const T = parseInt(document.getElementById('T').value, 10);
    if (Number.isNaN(T) || T < 1) throw new Error('T debe ser un entero mayor o igual a 1.');
    return T;
  }
  function leerEntero(el, nombre) {
    const v = parseInt(el.value, 10);
    if (Number.isNaN(v) || v < 1) throw new Error(`${nombre} debe ser un entero mayor o igual a 1.`);
    return v;
  }

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
        `<td class="border border-slate-200 text-center px-1">${i + 1}</td>` +
        `<td class="border border-slate-200 text-center px-1">A${resultados[i] ?? '—'}</td>` +
        `<td class="border border-slate-200 text-center px-1">${gbf[i] !== undefined ? gbf[i].toFixed(4) : '—'}</td>`;
      cuerpo.appendChild(tr);
    }
  }

  async function ejecutarAlgoritmo(algo, matriz, w, EV) {
    setEstado(algo.id, 'Ejecutando…', 'text-blue-500');
    let payload;
    try {
      payload = algo.payload(matriz, w, EV);
    } catch (e) {
      setEstado(algo.id, e.message, 'text-red-600');
      return;
    }
    try {
      const resp = await fetch(algo.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
      renderResultadoTarjeta(algo.id, data);
      setEstado(algo.id, 'Completado', 'text-green-600');
    } catch (err) {
      setEstado(algo.id, err.message, 'text-red-600');
    }
  }

  const btnEjecutar = document.getElementById('ejecutarComparacion');
  const msgError = document.getElementById('mensajeError');

  btnEjecutar.addEventListener('click', async function () {
    msgError.classList.add('hidden');
    let matriz, w, EV;
    try {
      matriz = leerMatriz();
      w = leerVector('w', 'w');
      EV = leerVector('ev', 'EV');
    } catch (e) {
      msgError.textContent = e.message;
      msgError.classList.remove('hidden');
      return;
    }

    btnEjecutar.disabled = true;
    btnEjecutar.textContent = 'Calculando…';
    ALGORITMOS.forEach(({ id }) => setEstado(id, 'En cola', 'text-gray-400'));

    // Secuencial — nueve ejecuciones completas, evita saturar el servidor
    for (const algo of ALGORITMOS) {
      await ejecutarAlgoritmo(algo, matriz, w, EV);
    }

    btnEjecutar.disabled = false;
    btnEjecutar.textContent = 'Calcular comparación general';
  });
});
