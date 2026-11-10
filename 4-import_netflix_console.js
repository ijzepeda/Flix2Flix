/**
 * Flix2Flix - 4-import_netflix_console.js
 * Sincronizador Automatizado de "Mi Lista" para tu Nueva Cuenta de Netflix
 * 
 * SEGURIDAD Y ANTI-BOT:
 * - Corre 100% dentro de tu navegador con tu sesión activa legítima (sin riesgo de detección de bots).
 * - Incorpora delays humanos variables con jitter (1.6s - 2.5s) para evitar "Rate Limiting" (HTTP 429).
 * - Incluye HUD flotante con barra de progreso en vivo y botones de [Pausar], [Reanudar] y [Cancelar].
 * - Reutiliza UNA SOLA ventana auxiliar para no abrir cientos de pestañas ni saturar la memoria.
 * 
 * INSTRUCCIONES:
 * 1. En tu index.html, haz clic en el botón "📋 Copiar IDs para Importar" (copia los IDs pendientes).
 * 2. Inicia sesión en tu NUEVA cuenta de Netflix en tu navegador.
 * 3. Abre https://www.netflix.com/browse
 * 4. Abre la consola de desarrollador:
 *    - Mac: Cmd + Option + J
 *    - Windows/Linux: Ctrl + Shift + J (o F12 -> Consola)
 * 5. Pega todo este código y presiona Enter.
 * 6. Si no pegaste los IDs en 'mis_ids' abajo, el script los leerá automáticamente de tu portapapeles.
 */

// Si deseas, puedes pegar tus IDs aquí directamente (o dejarlo vacío para lectura automática)
const mis_ids = [
    // "81093985",
    // "81011712",
];

(async function flix2flixImporter() {
    console.log("%c🎬 Flix2Flix: Iniciando herramienta de sincronización...", "color: #e50914; font-weight: bold; font-size: 15px;");

    // 1. Obtener lista de IDs
    let idList = Array.isArray(mis_ids) && mis_ids.length > 0 ? [...mis_ids] : [];

    if (idList.length === 0) {
        try {
            const clipText = await navigator.clipboard.readText();
            if (clipText && clipText.trim()) {
                try {
                    const parsed = JSON.parse(clipText);
                    if (Array.isArray(parsed) && parsed.length > 0) {
                        idList = parsed.map(String);
                        console.log(`📋 Se leyeron ${idList.length} IDs automáticamente desde el portapapeles.`);
                    }
                } catch(e) {
                    const matches = clipText.match(/\b\d{6,10}\b/g);
                    if (matches && matches.length > 0) {
                        idList = [...new Set(matches)];
                        console.log(`📋 Se detectaron ${idList.length} IDs numéricos en el texto del portapapeles.`);
                    }
                }
            }
        } catch(e) {
            // El navegador pudo bloquear lectura de portapapeles sin gesto de usuario
        }
    }

    if (idList.length === 0) {
        const input = prompt("Flix2Flix: Pega aquí los IDs (JSON o separados por comas):", "");
        if (!input || !input.trim()) {
            console.warn("❌ Operación cancelada por el usuario (no se ingresaron IDs).");
            return;
        }
        try {
            const parsed = JSON.parse(input);
            idList = Array.isArray(parsed) ? parsed.map(String) : [];
        } catch(e) {
            const matches = input.match(/\b\d{6,10}\b/g);
            idList = matches ? [...new Set(matches)] : [];
        }
    }

    // Filtrar IDs válidos y eliminar duplicados
    idList = [...new Set(idList.map(x => String(x).trim()))].filter(x => /^\d+$/.test(x));

    if (idList.length === 0) {
        alert("Flix2Flix: No se detectaron IDs válidos.");
        return;
    }

    console.log(`%c🚀 Iniciando sincronización de ${idList.length} títulos...`, "color: #3b82f6; font-weight: bold;");

    // 2. Crear HUD / Interfaz flotante en Netflix
    const hudId = 'flix2flix-sync-hud';
    let oldHud = document.getElementById(hudId);
    if (oldHud) oldHud.remove();

    const hud = document.createElement('div');
    hud.id = hudId;
    hud.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        width: 340px;
        background: #111827;
        color: #f3f4f6;
        border: 2px solid #e50914;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.8), 0 0 15px rgba(229,9,20,0.3);
        z-index: 999999;
        font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
        font-size: 13px;
    `;

    hud.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <strong style="color:#e50914; font-size:15px; font-weight:800;">Flix2Flix Sync</strong>
            <span id="f2f-badge" style="background:#1f2937; padding:2px 8px; border-radius:10px; font-size:11px; color:#9ca3af;">En progreso</span>
        </div>
        <div id="f2f-current" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:#cbd5e1; margin-bottom:8px;">Iniciando...</div>
        <div style="background:#1f2937; height:8px; border-radius:4px; overflow:hidden; margin-bottom:10px;">
            <div id="f2f-bar" style="background:#e50914; width:0%; height:100%; transition:width .2s;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:12px; color:#9ca3af; margin-bottom:12px;">
            <span>Progreso: <strong id="f2f-pct" style="color:#fff;">0%</strong></span>
            <span><strong id="f2f-count" style="color:#fff;">0</strong> / ${idList.length}</span>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; font-size:11px; margin-bottom:12px; text-align:center;">
            <div style="background:#064e3b; color:#a7f3d0; padding:4px; border-radius:6px;"><span id="f2f-added">0</span> agregados</div>
            <div style="background:#1e3a5f; color:#bfdbfe; padding:4px; border-radius:6px;"><span id="f2f-exists">0</span> ya estaban</div>
            <div style="background:#7f1d1d; color:#fecaca; padding:4px; border-radius:6px;"><span id="f2f-error">0</span> omitidos</div>
        </div>
        <div style="display:flex; gap:8px;">
            <button id="f2f-btn-pause" style="flex:1; padding:6px; background:#374151; color:#fff; border:none; border-radius:6px; font-weight:600; cursor:pointer;">⏸️ Pausar</button>
            <button id="f2f-btn-stop" style="flex:1; padding:6px; background:#4b1818; color:#fca5a5; border:none; border-radius:6px; font-weight:600; cursor:pointer;">⏹️ Cancelar</button>
        </div>
    `;
    document.body.appendChild(hud);

    // Variables de control de estado
    let isPaused = false;
    let isCancelled = false;

    const btnPause = document.getElementById('f2f-btn-pause');
    const btnStop = document.getElementById('f2f-btn-stop');
    const elCurrent = document.getElementById('f2f-current');
    const elBar = document.getElementById('f2f-bar');
    const elPct = document.getElementById('f2f-pct');
    const elCount = document.getElementById('f2f-count');
    const elAdded = document.getElementById('f2f-added');
    const elExists = document.getElementById('f2f-exists');
    const elError = document.getElementById('f2f-error');
    const badge = document.getElementById('f2f-badge');

    btnPause.addEventListener('click', () => {
        isPaused = !isPaused;
        btnPause.textContent = isPaused ? '▶️ Continuar' : '⏸️ Pausar';
        btnPause.style.background = isPaused ? '#059669' : '#374151';
        badge.textContent = isPaused ? 'En pausa' : 'En progreso';
        badge.style.color = isPaused ? '#facc15' : '#9ca3af';
    });

    btnStop.addEventListener('click', () => {
        if (confirm("¿Deseas detener la sincronización de Flix2Flix?")) {
            isCancelled = true;
            badge.textContent = 'Cancelado';
        }
    });

    // 3. Abrir UNA SOLA ventana auxiliar compacta reutilizable
    const win = window.open('about:blank', 'Flix2FlixHelper', 'width=380,height=380,left=50,top=50');
    if (!win) {
        alert("⚠️ Tu navegador bloqueó la ventana auxiliar. Permite las ventanas emergentes en Netflix y reintenta.");
        hud.remove();
        return;
    }

    let addedCount = 0;
    let existsCount = 0;
    let errorCount = 0;

    for (let i = 0; i < idList.length; i++) {
        if (isCancelled) break;

        // Esperar si está en pausa
        while (isPaused && !isCancelled) {
            await new Promise(r => setTimeout(r, 400));
        }
        if (isCancelled) break;

        const id = idList[i];
        const progressPct = Math.round(((i + 1) / idList.length) * 100);

        elCount.textContent = i + 1;
        elPct.textContent = `${progressPct}%`;
        elBar.style.width = `${progressPct}%`;
        elCurrent.textContent = `[${i + 1}/${idList.length}] ID: ${id}...`;

        try {
            win.location.href = `https://www.netflix.com/title/${id}`;

            let btnAdd = null;
            let btnRemove = null;
            let attempts = 0;
            const maxAttempts = 16; // Hasta 8 segundos por título

            while (attempts < maxAttempts && !isCancelled) {
                await new Promise(r => setTimeout(r, 500));
                attempts++;

                try {
                    // Múltiples selectores robustos para soportar diferentes idiomas y versiones de interfaz
                    btnAdd = win.document.querySelector([
                        'button[data-uia="add-to-my-list"]',
                        'button[aria-label*="Mi lista" i]',
                        'button[aria-label*="My List" i]',
                        'button[aria-label*="Agregar" i]',
                        'button[data-uia*="my-list-add"]'
                    ].join(','));

                    btnRemove = win.document.querySelector([
                        'button[data-uia="remove-from-my-list"]',
                        'button[aria-label*="Eliminar de mi lista" i]',
                        'button[aria-label*="Quitar de mi lista" i]',
                        'button[aria-label*="Remove from My List" i]',
                        'button[data-uia*="my-list-remove"]'
                    ].join(','));

                    if (btnAdd || btnRemove) break;
                } catch(e) {
                    // Reintentar si el DOM estaba transicionando entre páginas
                }
            }

            if (btnRemove) {
                existsCount++;
                elExists.textContent = existsCount;
                elCurrent.textContent = `⏩ ID: ${id} ya estaba en Mi Lista`;
                console.log(`⏩ [${i+1}/${idList.length}] ID: ${id} ya estaba agregado.`);
            } else if (btnAdd) {
                btnAdd.click();
                addedCount++;
                elAdded.textContent = addedCount;
                elCurrent.textContent = `✅ ID: ${id} agregado con éxito`;
                console.log(`%c✅ [${i+1}/${idList.length}] ID: ${id} agregado a Mi Lista.`, "color: #10b981;");
                // Delay breve para registrar el clic en el servidor de Netflix
                await new Promise(r => setTimeout(r, 600));
            } else {
                errorCount++;
                elError.textContent = errorCount;
                elCurrent.textContent = `⚠️ ID: ${id} no disponible`;
                console.warn(`⚠️ [${i+1}/${idList.length}] ID: ${id} no disponible o no tiene botón.`);
            }
        } catch(err) {
            errorCount++;
            elError.textContent = errorCount;
            console.error(`❌ Error en ID ${id}:`, err);
        }

        // Delay humano aleatorio con jitter (1.6s - 2.4s) para máxima seguridad y evitar límites de velocidad
        const humanDelay = 1600 + Math.floor(Math.random() * 800);
        await new Promise(r => setTimeout(r, humanDelay));
    }

    try { win.close(); } catch(e) {}

    // Resumen final en HUD
    badge.textContent = isCancelled ? 'Detenido' : 'Completado';
    badge.style.color = '#10b981';
    btnPause.style.display = 'none';
    btnStop.textContent = 'Cerrar Panel';
    btnStop.style.background = '#374151';
    btnStop.style.color = '#fff';
    btnStop.onclick = () => hud.remove();

    elCurrent.innerHTML = `<strong>¡Listo!</strong> ${addedCount} agregados con éxito.`;

    console.log("%c🎉 ¡Sincronización finalizada!", "color: #10b981; font-weight: bold; font-size: 16px;");
    console.table({
        "Total analizados": idList.length,
        "Agregados nuevos": addedCount,
        "Ya estaban en la lista": existsCount,
        "No disponibles": errorCount
    });
})();
