// static/js/pso.js
// Laboratorio PSO: matriz de decisión unificada con vectores w/R1/R2,
// plantilla Excel (descarga/carga), stepper y gráfica de convergencia.

document.addEventListener('DOMContentLoaded', function () {
    // ===================== CONFIGURACIÓN DEL ALGORITMO =====================
    // Cada template hijo define window.ALGO_CONFIG antes de cargar este script
    const CFG = window.ALGO_CONFIG || {};
    const ALGORITMO = CFG.algoritmo || 'PSO';
    const ENDPOINT = CFG.endpoint || '/api/algoritmos/pso';
    const TIENE_R1R2 = CFG.tiene_r1r2 !== false;  // default: true (PSO los usa)

    // ===================== TABS (Teoría es el tab inicial) =====================
    const tabs = {
        teo: { btn: document.getElementById('tabTeo'), panel: document.getElementById('panelTeo') },
        lab: { btn: document.getElementById('tabLab'), panel: document.getElementById('panelLab') },
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
        // Render inicial de la matriz: solo cuando el laboratorio es visible por primera vez
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
    const MIN_CRITERIOS = 5;
    const MIN_ALTERNATIVAS = 9;
    const MAX_CRITERIOS = 20;
    const MAX_ALTERNATIVAS = 30;

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
    const R1_INICIAL = [0.4657, 0.8956, 0.3877, 0.4902, 0.5039];
    const R2_INICIAL = [0.5319, 0.8185, 0.8331, 0.7677, 0.1708];

    let nCriterios = MIN_CRITERIOS;
    let nAlternativas = MIN_ALTERNATIVAS;
    let grafica = null;

    const matrizHead = document.getElementById('matrizHead');
    const matrizBody = document.getElementById('matrizBody');
    const matrizVectores = document.getElementById('matrizVectores');
    const dimsLabel = document.getElementById('dimensionesMatriz');
    const btnEjecutar = document.getElementById('ejecutarAlgo');
    const msgError = document.getElementById('mensajeError');
    const msgErrorPlantilla = document.getElementById('mensajeErrorPlantilla');

    const claseInput = 'bg-slate-300 border border-gray-300 text-gray-900 ' +
        'text-sm rounded p-1.5 w-full text-center';
    const claseInputVector = 'bg-blue-50 border border-blue-200 text-gray-900 ' +
        'text-sm rounded p-1.5 w-full text-center';

    function crearInput(valor, id, clase) {
        const inp = document.createElement('input');
        inp.type = 'number';
        inp.step = 'any';
        inp.required = true;
        inp.className = clase || claseInput;
        inp.value = valor;
        if (id) inp.id = id;
        return inp;
    }

    // ===================== MATRIZ UNIFICADA (datos + w/R1/R2) =====================
    const celdaId = (f, c) => `m_${f}_${c}`;
    const r_aleatorio = () => Number(Math.random().toFixed(4));

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
        // Conservar lo escrito por el usuario antes de re-renderizar
        const previos = {};
        document.querySelectorAll('#matrizBody input, #matrizVectores input')
            .forEach((i) => { previos[i.id] = i.value; });

        // Cabecera C1..Cn
        matrizHead.innerHTML = '<th class="border border-slate-300 px-2 py-1 bg-slate-100"></th>';
        for (let c = 0; c < nCriterios; c++) {
            const th = document.createElement('th');
            th.className = 'border border-slate-300 px-2 py-1 bg-slate-100';
            th.textContent = 'C' + (c + 1);
            matrizHead.appendChild(th);
        }

        // Filas de alternativas
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

        // Filas de vectores por criterio
        // R1 y R2 se deshabilitan (con nota) cuando el algoritmo los deriva internamente
        matrizVectores.innerHTML = '';
        // w siempre editable; R1/R2 solo cuando el algoritmo los necesita como entrada
        // Si tiene_r1r2=false: fila de encabezado informativo, sin celdas de datos
        const configVectores = [
            { prefijo: 'w', label: 'w (peso)', mostrar: true },
            { prefijo: 'r1', label: 'R1', mostrar: TIENE_R1R2 },
            { prefijo: 'r2', label: 'R2', mostrar: TIENE_R1R2 },
        ];
        for (const { prefijo, label, mostrar } of configVectores) {
            const tr = document.createElement('tr');
            const th = document.createElement('th');

            if (mostrar) {
                // Fila editable normal
                th.className = 'border border-blue-200 px-2 py-1 bg-blue-50 text-left text-blue-900';
                th.textContent = label;
                tr.appendChild(th);
                for (let c = 0; c < nCriterios; c++) {
                    const td = document.createElement('td');
                    td.className = 'border border-blue-200 p-1 bg-blue-50';
                    const id = `${prefijo}_${c}`;
                    td.appendChild(crearInput(
                        (id in previos) ? previos[id] : valorInicialVector(prefijo, c),
                        id, claseInputVector));
                    tr.appendChild(td);
                }
            } else {
                // Fila informativa — celda única que abarca todas las columnas
                th.className = 'border border-slate-200 px-2 py-1 bg-slate-50 text-left';
                th.innerHTML = `<span class="font-semibold text-gray-500">${label}</span>
                    <span class="ml-2 text-xs text-gray-400 font-normal italic">
                        Derivado automáticamente por el algoritmo
                    </span>`;
                th.colSpan = nCriterios + 1;
                tr.appendChild(th);
            }
            matrizVectores.appendChild(tr);
        }

        dimsLabel.textContent = `${nAlternativas} alternativas × ${nCriterios} criterios`;
    }

    // ===================== BOTONES +/− =====================
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
    // El link de descarga incluye las dimensiones actuales de la matriz
    const enlacePlantilla = document.getElementById('descargarPlantilla');
    enlacePlantilla.addEventListener('click', () => {
        enlacePlantilla.href =
            `/api/algoritmos/pso/plantilla?criterios=${nCriterios}&alternativas=${nAlternativas}`;
    });

    document.getElementById('archivoPlantilla').addEventListener('change', function () {
        msgErrorPlantilla.classList.add('hidden');
        const estado = document.getElementById('estadoPlantilla');
        if (!this.files.length) return;
        const archivo = this.files[0];
        estado.textContent = 'Leyendo plantilla…';

        const fd = new FormData();
        fd.append('archivo', archivo);
        fetch('/api/algoritmos/pso/plantilla', { method: 'POST', body: fd })
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
                // Poblar matriz y vectores
                for (let f = 0; f < a; f++)
                    for (let c = 0; c < n; c++)
                        document.getElementById(celdaId(f, c)).value = p.matriz[f][c];
                for (let c = 0; c < n; c++) {
                    document.getElementById(`w_${c}`).value = p.w[c];
                    document.getElementById(`r1_${c}`).value = p.r1[c];
                    document.getElementById(`r2_${c}`).value = p.r2[c];
                }
                // Escalares
                document.getElementById('wwi').value = p.wwi;
                document.getElementById('c1').value = p.c1;
                document.getElementById('c2').value = p.c2;
                document.getElementById('T').value = p.T;
                estado.textContent = `Plantilla cargada: ${a} alternativas × ${n} criterios. Revise y presione Calcular.`;
            })
            .catch((err) => {
                estado.textContent = '';
                msgErrorPlantilla.textContent = err.message;
                msgErrorPlantilla.classList.remove('hidden');
            })
            .finally(() => { this.value = ''; });
    });

    // ===================== HISTORIAL =====================
    const histCargando = document.getElementById('histCargando');
    const histVacio = document.getElementById('histVacio');
    const histError = document.getElementById('histError');
    const histTablaWrap = document.getElementById('histTablaWrap');
    const histCuerpo = document.getElementById('histCuerpo');
    let histCache = null;  // evita recargar al alternar tabs; el filtro sí recarga

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

    function cargarHistorial() {
        if (histCache) return;  // ya renderizado
        estadoHistorial('cargando');
        fetch(`/api/ejecuciones?algoritmo=${ALGORITMO}`)
            .then(async (resp) => {
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
                return data;
            })
            .then((lista) => {
                histCache = lista;
                if (!lista.length) { estadoHistorial('vacio'); return; }
                histCuerpo.innerHTML = '';
                for (const e of lista) {
                    const tr = document.createElement('tr');
                    tr.className = 'border-b border-slate-100 hover:bg-slate-50';
                    tr.innerHTML =
                        `<td class="py-2 pr-3 text-gray-400">${e.id}</td>` +
                        `<td class="py-2 pr-3">${formatearFecha(e.fecha_ejecucion)}</td>` +
                        `<td class="py-2 pr-3">${e.usuario ?? '—'}</td>` +
                        `<td class="py-2 pr-3">${e.n_alternativas}×${e.n_criterios}</td>` +
                        `<td class="py-2 pr-3">${e.iteraciones}</td>` +
                        `<td class="py-2 pr-3">${e.gbf_final ?? '—'}</td>` +
                        `<td class="py-2 pr-3 font-medium">A${e.mejor_alternativa_final ?? '—'}</td>` +
                        `<td class="py-2 pr-3">${(e.tiempo_ejecucion_seg ?? 0).toFixed(2)} s</td>` +
                        `<td class="py-2 text-right whitespace-nowrap">
               <button type="button" data-accion="ver" data-id="${e.id}"
                 class="text-sm text-white bg-slate-700 hover:bg-slate-800 rounded-lg px-3 py-1.5">Ver resultados</button>
               <button type="button" data-accion="reutilizar" data-id="${e.id}"
                 class="text-sm text-gray-700 bg-slate-200 hover:bg-slate-300 rounded-lg px-3 py-1.5">Reutilizar datos</button>
               <a href="/api/ejecuciones/${e.id}/excel"
                 class="inline-block text-sm text-gray-700 bg-slate-200 hover:bg-slate-300 rounded-lg px-3 py-1.5">XLSX</a>
             </td>`;
                    histCuerpo.appendChild(tr);
                }
                estadoHistorial('tabla');
            })
            .catch((err) => { histError.textContent = err.message; estadoHistorial('error'); });
    }

    histCuerpo.addEventListener('click', (ev) => {
        const btn = ev.target.closest('button[data-accion]');
        if (!btn) return;
        const id = btn.dataset.id;
        btn.disabled = true;
        fetch(`/api/ejecuciones/${id}`)
            .then(async (resp) => {
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
                return data;
            })
            .then((det) => {
                if (btn.dataset.accion === 'ver') {
                    verEjecucionPasada(det);
                } else {
                    reutilizarEjecucion(det);
                }
            })
            .catch((err) => { histError.textContent = err.message; histError.classList.remove('hidden'); })
            .finally(() => { btn.disabled = false; });
    });

    function verEjecucionPasada(det) {
        const fecha = det.fecha_ejecucion ? new Date(det.fecha_ejecucion) : null;
        renderResultados({
            ejecucion_id: det.id,
            resultados_por_iteracion: (det.resultados || []).map((r) => r.mejor_alternativa),
            historico_gbf: det.historico_gbf || [],
            iteraciones: det.iteraciones,
            hora_inicio: fecha ? fecha.toLocaleTimeString('es-MX') : '—',
            fecha_inicio: fecha ? fecha.toLocaleDateString('es-MX') : '—',
            hora_finalizacion: '—',
            tiempo_ejecucion: `${(det.tiempo_ejecucion_seg ?? 0).toFixed(2)} s`,
            mejor_alternativa_final: det.mejor_alternativa_final,
        });
        activarTab('lab');
        irAPaso(3);
    }

    function reutilizarEjecucion(det) {
        const me = det.matriz_entrada || {};
        const p = det.parametros || {};
        const matriz = me.valores || [];
        if (!matriz.length) {
            histError.textContent = 'La ejecución no tiene matriz registrada.';
            histError.classList.remove('hidden');
            return;
        }
        nAlternativas = matriz.length;
        nCriterios = matriz[0].length;
        renderMatriz();
        for (let f = 0; f < nAlternativas; f++)
            for (let c = 0; c < nCriterios; c++)
                document.getElementById(celdaId(f, c)).value = matriz[f][c];
        for (let c = 0; c < nCriterios; c++) {
            document.getElementById(`w_${c}`).value = (p.w || [])[c] ?? '';
            document.getElementById(`r1_${c}`).value = (p.r1 || [])[c] ?? '';
            document.getElementById(`r2_${c}`).value = (p.r2 || [])[c] ?? '';
        }
        document.getElementById('wwi').value = p.wwi ?? '';
        document.getElementById('c1').value = p.c1 ?? '';
        document.getElementById('c2').value = p.c2 ?? '';
        document.getElementById('T').value = p.T ?? '';
        const estado = document.getElementById('estadoPlantilla');
        estado.textContent = `Datos cargados desde la ejecución #${det.id} ` +
            `(${nAlternativas}×${nCriterios}). Ajuste lo necesario y presione Calcular.`;
        activarTab('lab');
        irAPaso(1);
    }

    // ===================== RECOLECCIÓN Y VALIDACIÓN =====================
    function leerNumero(input, nombre) {
        const v = parseFloat(input.value);
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
        const vector = (prefijo, nombre) => {
            const arr = [];
            for (let c = 0; c < nCriterios; c++) {
                arr.push(leerNumero(document.getElementById(`${prefijo}_${c}`), `${nombre} C${c + 1}`));
            }
            return arr;
        };
        const T = parseInt(document.getElementById('T').value, 10);
        if (Number.isNaN(T) || T < 1) throw new Error('T debe ser un entero mayor o igual a 1.');

        return {
            matriz,
            w: vector('w', 'el peso w de'),
            r1: vector('r1', 'R1 de'),
            r2: vector('r2', 'R2 de'),
            wwi: leerNumero(document.getElementById('wwi'), 'el peso de inercia'),
            c1: leerNumero(document.getElementById('c1'), 'c1'),
            c2: leerNumero(document.getElementById('c2'), 'c2'),
            T,
        };
    }

    function mostrarError(texto) {
        msgError.textContent = texto;
        msgError.classList.remove('hidden');
    }

    // ===================== EJECUCIÓN =====================
    btnEjecutar.addEventListener('click', function () {
        msgError.classList.add('hidden');
        let payload;
        try {
            payload = construirPayload();
        } catch (e) {
            mostrarError(e.message);
            return;
        }

        btnEjecutar.disabled = true;
        btnEjecutar.textContent = 'Calculando…';

        fetch(ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
            .then(async (resp) => {
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || `Error ${resp.status}`);
                return data;
            })
            .then(renderResultados)
            .catch((err) => mostrarError(err.message))
            .finally(() => {
                btnEjecutar.disabled = false;
                btnEjecutar.textContent = 'Calcular';
            });
    });

    // ===================== RESULTADOS =====================
    function renderResultados(data) {
        histCache = null;  // una ejecución nueva debe reflejarse en el historial
        document.getElementById('resultadosVacio').classList.add('hidden');
        document.getElementById('seccionResultados').classList.remove('hidden');
        irAPaso(3);

        const cuerpo = document.getElementById('tablaResultados');
        cuerpo.innerHTML = '';
        const resultados = data.resultados_por_iteracion || [];
        const gbf = data.historico_gbf || [];
        for (let i = 0; i < resultados.length; i++) {
            const tr = document.createElement('tr');
            tr.innerHTML =
                `<td class="border border-slate-300 text-center">${i + 1}</td>` +
                `<td class="border border-slate-300 text-center">A${resultados[i]}</td>` +
                `<td class="border border-slate-300 text-center">${(gbf[i] ?? '').toString().slice(0, 8)}</td>`;
            cuerpo.appendChild(tr);
        }

        document.getElementById('cantidadIteraciones').textContent = data.iteraciones;
        document.getElementById('horaInicio').textContent = data.hora_inicio;
        document.getElementById('fechaInicio').textContent = data.fecha_inicio;
        document.getElementById('horaFinalizacion').textContent = data.hora_finalizacion;
        document.getElementById('tiempoEjecucion').textContent = data.tiempo_ejecucion;
        document.getElementById('mejorFinal').textContent = 'A' + data.mejor_alternativa_final;

        const enlace = document.getElementById('descargarExcel');
        enlace.href = `/api/ejecuciones/${data.ejecucion_id}/excel`;
        enlace.classList.remove('hidden');

        const etiquetas = gbf.map((_, i) => i + 1);
        const ctx = document.getElementById('graficaConvergencia');
        if (grafica) grafica.destroy();
        grafica = new Chart(ctx, {
            type: 'line',
            data: {
                labels: etiquetas,
                datasets: [{
                    label: 'GBF (Global Best Fitness)',
                    data: gbf,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.15)',
                    fill: true,
                    tension: 0.15,
                    pointRadius: 3,
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Convergencia del algoritmo' },
                    legend: { display: false },
                },
                scales: {
                    x: { title: { display: true, text: 'Iteración' } },
                    y: { title: { display: true, text: 'GBF' } },
                },
            },
        });
    }

    document.getElementById('algoForm').addEventListener('submit', (e) => e.preventDefault());

    renderMatriz();
});