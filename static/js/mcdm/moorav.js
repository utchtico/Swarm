// static/js/mcdm/moorav.js
// MOORA puro (MCDM, sin metaheurística): matriz de solo lectura, único
// parámetro editable es el peso w por criterio. Sin tabs, sin stepper,
// sin historial — es una página de una sola sección porque no hay
// iteraciones que comparar. Mismo patrón que static/js/mcdm/topsis.js.

document.addEventListener('DOMContentLoaded', function () {
  const matrizHead = document.getElementById('matrizHead');
  const matrizBody = document.getElementById('matrizBody');
  const pesosWrap  = document.getElementById('pesosWrap');
  const btnEjecutar = document.getElementById('ejecutarMoorav');
  const msgError = document.getElementById('mensajeError');

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
    fetch('/api/algoritmos/moorav/matriz')
      .then(async (resp) => {
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
        return data;
      })
      .then((data) => {
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
      const resp = await fetch('/api/algoritmos/moorav', {
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
  }

  inicializar();
});
