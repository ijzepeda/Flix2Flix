// ==UserScript==
// @name         Flix2Flix - Netflix My List Sync (Importer)
// @namespace    https://github.com/ivanzepeda/Flix2Flix
// @version      1.0
// @description  Herramienta automatizada para importar/sincronizar títulos a "Mi Lista" en una cuenta nueva de Netflix de forma segura.
// @author       Flix2Flix
// @match        https://www.netflix.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    function addSyncButton() {
        if (document.getElementById('f2f-sync-nav-btn')) return;

        const nav = document.querySelector('.primary-navigation, nav[data-uia="navigation"], .header-profile-menu');
        if (!nav) return;

        const btn = document.createElement('button');
        btn.id = 'f2f-sync-nav-btn';
        btn.textContent = '🔄 Flix2Flix Sync';
        btn.style.cssText = `
            margin-left: 14px;
            padding: 5px 12px;
            background: #2563eb;
            color: #fff;
            border: none;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(0,0,0,0.5);
            transition: all 0.2s;
            z-index: 9999;
        `;
        btn.onmouseover = () => { btn.style.background = '#1d4ed8'; btn.style.transform = 'scale(1.05)'; };
        btn.onmouseout = () => { btn.style.background = '#2563eb'; btn.style.transform = 'scale(1)'; };
        btn.onclick = openSyncModal;

        nav.appendChild(btn);
    }

    function openSyncModal() {
        if (document.getElementById('f2f-sync-modal')) return;

        const modal = document.createElement('div');
        modal.id = 'f2f-sync-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.75);
            backdrop-filter: blur(5px);
            display: flex; align-items: center; justify-content: center;
            z-index: 999999;
            font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
            color: #f3f4f6;
        `;

        modal.innerHTML = `
            <div style="background:#111827; border:2px solid #2563eb; border-radius:14px; width:460px; max-width:92vw; padding:22px; box-shadow:0 20px 40px rgba(0,0,0,0.9);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <h3 style="margin:0; font-size:17px; font-weight:800; color:#60a5fa;">Flix2Flix: Sincronizar Mi Lista</h3>
                    <button id="f2f-modal-close" style="background:none; border:none; color:#9ca3af; font-size:18px; cursor:pointer;">✕</button>
                </div>
                <p style="font-size:12px; color:#9ca3af; margin:0 0 14px 0; line-height:1.4;">
                    Pega los IDs de tus películas/series a continuación. Puedes copiarlos con 1 clic en tu <code style="color:#60a5fa;">index.html</code> con el botón <em>"📋 Copiar IDs para Importar"</em>.
                </p>
                <textarea id="f2f-ids-input" placeholder='["81093985", "81011712"] o IDs separados por comas...' style="width:100%; height:90px; background:#0b0f19; border:1px solid #374151; border-radius:8px; padding:10px; color:#fff; font-family:monospace; font-size:12px; resize:none; outline:none; box-sizing:border-box;"></textarea>
                
                <div id="f2f-sync-status" style="display:none; margin:14px 0;">
                    <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                        <span id="f2f-status-text" style="color:#cbd5e1;">Iniciando...</span>
                        <span id="f2f-status-pct" style="font-weight:700; color:#60a5fa;">0%</span>
                    </div>
                    <div style="background:#1f2937; height:8px; border-radius:4px; overflow:hidden;">
                        <div id="f2f-status-bar" style="background:#2563eb; width:0%; height:100%; transition:width .2s;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-around; font-size:11px; margin-top:8px; text-align:center;">
                        <span style="color:#4ade80;">✅ <strong id="f2f-cnt-added">0</strong> agregados</span>
                        <span style="color:#93c5fd;">⏩ <strong id="f2f-cnt-exists">0</strong> ya estaban</span>
                        <span style="color:#f87171;">⚠️ <strong id="f2f-cnt-err">0</strong> omitidos</span>
                    </div>
                </div>

                <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
                    <button id="f2f-btn-start" style="padding:8px 18px; background:#2563eb; color:#fff; border:none; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer;">🚀 Iniciar Sincronización</button>
                    <button id="f2f-btn-pause" style="display:none; padding:8px 14px; background:#374151; color:#fff; border:none; border-radius:8px; font-weight:600; font-size:13px; cursor:pointer;">⏸️ Pausar</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Auto-pegar del portapapeles si es posible
        navigator.clipboard.readText().then(txt => {
            if (txt && (txt.includes('[') || txt.match(/\b\d{6,10}\b/))) {
                document.getElementById('f2f-ids-input').value = txt;
            }
        }).catch(() => {});

        document.getElementById('f2f-modal-close').onclick = () => modal.remove();

        const btnStart = document.getElementById('f2f-btn-start');
        const btnPause = document.getElementById('f2f-btn-pause');
        const statusBox = document.getElementById('f2f-sync-status');
        const statusText = document.getElementById('f2f-status-text');
        const statusPct = document.getElementById('f2f-status-pct');
        const statusBar = document.getElementById('f2f-status-bar');
        const cntAdded = document.getElementById('f2f-cnt-added');
        const cntExists = document.getElementById('f2f-cnt-exists');
        const cntErr = document.getElementById('f2f-cnt-err');
        const txtArea = document.getElementById('f2f-ids-input');

        let isPaused = false;
        btnPause.onclick = () => {
            isPaused = !isPaused;
            btnPause.textContent = isPaused ? '▶️ Reanudar' : '⏸️ Pausar';
            btnPause.style.background = isPaused ? '#059669' : '#374151';
        };

        btnStart.onclick = async () => {
            const raw = txtArea.value.trim();
            let ids = [];
            try {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) ids = parsed.map(String);
            } catch(e) {
                const matches = raw.match(/\b\d{6,10}\b/g);
                if (matches) ids = [...new Set(matches)];
            }
            ids = ids.filter(x => /^\d+$/.test(x));

            if (!ids.length) {
                alert("Por favor ingresa IDs numéricos válidos.");
                return;
            }

            btnStart.style.display = 'none';
            btnPause.style.display = 'inline-block';
            txtArea.disabled = true;
            statusBox.style.display = 'block';

            const win = window.open('about:blank', 'Flix2FlixSyncHelper', 'width=380,height=380,left=50,top=50');
            if (!win) {
                alert("Tu navegador bloqueó la ventana auxiliar. Permite popups en Netflix y reintenta.");
                modal.remove();
                return;
            }

            let added = 0, exists = 0, errs = 0;

            for (let i = 0; i < ids.length; i++) {
                while (isPaused) await new Promise(r => setTimeout(r, 400));

                const id = ids[i];
                const pct = Math.round(((i + 1) / ids.length) * 100);
                statusPct.textContent = `${pct}%`;
                statusBar.style.width = `${pct}%`;
                statusText.textContent = `[${i + 1}/${ids.length}] ID: ${id}...`;

                try {
                    win.location.href = `https://www.netflix.com/title/${id}`;
                    let btnAdd = null, btnRemove = null, attempts = 0;

                    while (attempts < 16) {
                        await new Promise(r => setTimeout(r, 500));
                        attempts++;
                        try {
                            btnAdd = win.document.querySelector('button[data-uia="add-to-my-list"], button[aria-label*="Mi lista" i], button[aria-label*="My List" i], button[aria-label*="Agregar" i]');
                            btnRemove = win.document.querySelector('button[data-uia="remove-from-my-list"], button[aria-label*="Eliminar de mi lista" i], button[aria-label*="Quitar de mi lista" i], button[aria-label*="Remove from My List" i]');
                            if (btnAdd || btnRemove) break;
                        } catch(e) {}
                    }

                    if (btnRemove) {
                        exists++;
                        cntExists.textContent = exists;
                    } else if (btnAdd) {
                        btnAdd.click();
                        added++;
                        cntAdded.textContent = added;
                        await new Promise(r => setTimeout(r, 600));
                    } else {
                        errs++;
                        cntErr.textContent = errs;
                    }
                } catch(e) {
                    errs++;
                    cntErr.textContent = errs;
                }

                // Delay humano variable (1.6s - 2.4s)
                const delay = 1600 + Math.floor(Math.random() * 800);
                await new Promise(r => setTimeout(r, delay));
            }

            try { win.close(); } catch(e) {}
            btnPause.style.display = 'none';
            btnStart.style.display = 'inline-block';
            btnStart.textContent = '✅ Finalizado (Cerrar)';
            btnStart.style.background = '#059669';
            btnStart.onclick = () => modal.remove();
            statusText.textContent = `¡Sincronización terminada! ${added} agregados.`;
        };
    }

    setInterval(addSyncButton, 2000);
})();

