// static/js/comparacionPso.js
// Comparación de la familia PSO: una sola matriz de entrada,
// se ejecutan los 4 algoritmos en secuencia y se comparan resultados.

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
  const W_INICIAL  = [0.400, 0.200, 0.030, 0.070, 0.300];
  const R1_INICIAL = [0.4657, 0.8956, 0.3877, 0.4902, 0.5039];
  const R2_INICIAL = [0.5319, 0.8185, 0.8331, 0.7677, 0.1708];
  const r_aleatorio = () => Number(Math.random().toFixed(4));

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
  function valorInicialVector(prefijo, c) {
    const base = { w: W_INICIAL, r1: R1_INICIAL, r2: R2_INICIAL }[prefijo];
    if (c < base.length) return base[c];
    return prefijo === 'w' ? 0.100 : r_aleatorio();
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

    // w, R1 y R2 editables. R1/R2 solo los usa PSO; para los demás algoritmos
    // se ignoran (se derivan internamente), pero se muestran porque la
    // comparación incluye a PSO y ahí sí son entrada real del usuario.
    matrizVectores.innerHTML = '';
    const filasVector = [
      { prefijo: 'w',  etiqueta: 'w (peso)', bg: 'bg-blue-50',  bd: 'border-blue-200',  txt: 'text-blue-900' },
      { prefijo: 'r1', etiqueta: 'R1 (solo PSO)', bg: 'bg-sky-50', bd: 'border-sky-200', txt: 'text-sky-900' },
      { prefijo: 'r2', etiqueta: 'R2 (solo PSO)', bg: 'bg-sky-50', bd: 'border-sky-200', txt: 'text-sky-900' },
    ];
    for (const { prefijo, etiqueta, bg, bd, txt } of filasVector) {
      const tr = document.createElement('tr');
      const th = document.createElement('th');
      th.className = `border ${bd} px-2 py-1 ${bg} text-left ${txt}`;
      th.textContent = etiqueta;
      tr.appendChild(th);
      for (let c = 0; c < nCriterios; c++) {
        const td = document.createElement('td');
        td.className = `border ${bd} p-1 ${bg}`;
        const id = `${prefijo}_${c}`;
        td.appendChild(crearInput((id in previos) ? previos[id] : valorInicialVector(prefijo, c), id));
        tr.appendChild(td);
      }
      matrizVectores.appendChild(tr);
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
    const w = [];
    for (let c = 0; c < nCriterios; c++) {
      w.push(leerNumero(document.getElementById(`w_${c}`), `el peso w de C${c+1}`));
    }
    const T = parseInt(document.getElementById('T').value, 10);
    if (Number.isNaN(T) || T < 1) throw new Error('T debe ser un entero mayor o igual a 1.');

    return {
      matriz, w,
      wwi: leerNumero(document.getElementById('wwi'), 'el peso de inercia'),
      c1:  leerNumero(document.getElementById('c1'), 'c1'),
      c2:  leerNumero(document.getElementById('c2'), 'c2'),
      T,
    };
  }

  // ===================== EJECUCIÓN SECUENCIAL =====================
  const ALGORITMOS = [
    { id: 'pso',       endpoint: '/api/algoritmos/pso',       tieneR1R2: true  },
    { id: 'dapso',     endpoint: '/api/algoritmos/dapso',     tieneR1R2: false },
    { id: 'moorapso',  endpoint: '/api/algoritmos/moorapso',  tieneR1R2: false },
    { id: 'topsispso', endpoint: '/api/algoritmos/topsispso', tieneR1R2: false },
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

  async function ejecutarAlgoritmo({ id, endpoint, tieneR1R2 }, payloadBase, r1, r2) {
    setEstado(id, 'Ejecutando…', 'text-blue-500');
    const payload = { ...payloadBase };
    if (tieneR1R2) {
      payload.r1 = r1;
      payload.r2 = r2;
    }
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
    let payloadBase;
    try {
      payloadBase = construirPayloadBase();
    } catch (e) {
      msgError.textContent = e.message;
      msgError.classList.remove('hidden');
      return;
    }

    // R1/R2: leídos de la matriz (solo PSO los usa, pero deben venir del usuario)
    let r1, r2;
    try {
      r1 = []; r2 = [];
      for (let c = 0; c < nCriterios; c++) {
        r1.push(leerNumero(document.getElementById(`r1_${c}`), `R1 de C${c+1}`));
        r2.push(leerNumero(document.getElementById(`r2_${c}`), `R2 de C${c+1}`));
      }
    } catch (e) {
      msgError.textContent = e.message;
      msgError.classList.remove('hidden');
      return;
    }

    btnEjecutar.disabled = true;
    btnEjecutar.textContent = 'Calculando…';
    ALGORITMOS.forEach(({ id }) => setEstado(id, 'En cola', 'text-gray-400'));

    // Secuencial — igual que el comportamiento original, evita saturar el servidor
    for (const algo of ALGORITMOS) {
      await ejecutarAlgoritmo(algo, payloadBase, r1, r2);
    }

    btnEjecutar.disabled = false;
    btnEjecutar.textContent = 'Calcular comparación';
  });
});