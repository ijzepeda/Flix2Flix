// ==UserScript==
// @name         Flix2Flix - Netflix My List Exporter
// @namespace    https://github.com/ivanzepeda/Flix2Flix
// @version      1.0
// @description  Agrega un botón en Netflix para exportar automáticamente "Mi Lista" a CSV, sorteando el scroll virtualizado.
// @author       Flix2Flix
// @match        https://www.netflix.com/*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    function addExportButton() {
        if (document.getElementById('flix2flix-export-btn')) return;

        // Intentar ubicar la sección de Mi Lista
        const sections = Array.from(document.querySelectorAll('section[data-uia^="carousel-row-section"], section.carousel-row'));
        let targetHeader = null;
        const listNames = ['my list', 'mi lista', 'minha lista', 'ma liste', 'meine liste'];

        for (const sec of sections) {
            const h2 = sec.querySelector('h2, [data-uia*="row-header"]');
            if (h2 && listNames.some(name => h2.textContent.toLowerCase().includes(name))) {
                targetHeader = h2;
                break;
            }
        }

        // Si no se encuentra el h2 pero estamos en /browse/my-list, añadir al nav o barra superior
        const container = targetHeader ? targetHeader.parentElement : document.querySelector('nav[data-uia="navigation"]');
        if (!container) return;

        const btn = document.createElement('button');
        btn.id = 'flix2flix-export-btn';
        btn.textContent = '📥 Exportar Lista (CSV)';
        btn.style.cssText = `
            margin-left: 14px;
            padding: 6px 14px;
            background: #e50914;
            color: #fff;
            border: none;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
            z-index: 9999;
            transition: transform 0.2s, background 0.2s;
        `;
        btn.onmouseover = () => { btn.style.background = '#f40612'; btn.style.transform = 'scale(1.05)'; };
        btn.onmouseout = () => { btn.style.background = '#e50914'; btn.style.transform = 'scale(1)'; };

        btn.onclick = async () => {
            btn.disabled = true;
            btn.textContent = '⏳ Extrayendo...';
            try {
                await runExporter((status) => {
                    btn.textContent = status;
                });
                btn.textContent = '✅ ¡Exportado!';
                setTimeout(() => {
                    btn.textContent = '📥 Exportar Lista (CSV)';
                    btn.disabled = false;
                }, 3000);
            } catch (err) {
                console.error(err);
                btn.textContent = '❌ Error';
                setTimeout(() => {
                    btn.textContent = '📥 Exportar Lista (CSV)';
                    btn.disabled = false;
                }, 3000);
            }
        };

        container.appendChild(btn);
    }

    async function runExporter(onProgress) {
        const sections = Array.from(document.querySelectorAll('section[data-uia^="carousel-row-section"], section.carousel-row'));
        let targetSection = null;
        const listNames = ['my list', 'mi lista', 'minha lista', 'ma liste', 'meine liste'];

        for (const sec of sections) {
            const heading = sec.querySelector('h2, [data-uia*="row-header"]');
            if (heading && listNames.some(name => heading.textContent.toLowerCase().includes(name))) {
                targetSection = sec;
                break;
            }
        }

        if (!targetSection) {
            targetSection = sections.find(s => s.querySelector('a[data-uia="standard-card"], a[href*="jbv="]')) || document;
        }

        const titlesMap = new Map();

        function extractImageUrl(anchor, videoId) {
            try {
                const fc = window.netflix?.falcorCache;
                if (fc && fc.videos && fc.videos[videoId]) {
                    const v = fc.videos[videoId];
                    const b = v.boxArt || v.boxart;
                    if (b?.value?.url) return b.value.url;
                    if (typeof b?.url === 'string') return b.url;
                }
            } catch (e) {}

            let img = anchor.querySelector('img');
            if (!img) {
                const card = anchor.closest('[data-uia*="card"], .slider-item, div[class*="cache-1tbetht"]') || anchor.parentElement;
                if (card) img = card.querySelector('img');
            }
            if (img) {
                const src = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                if (src && !src.startsWith('data:') && !src.includes('placeholder')) return src;
            }
            return '';
        }

        function harvest() {
            const anchors = targetSection.querySelectorAll('a[href*="jbv="], a[href*="/watch/"], a[href*="/title/"]');
            let added = 0;
            anchors.forEach(a => {
                const href = a.getAttribute('href') || '';
                let videoId = '';
                const mJbv = href.match(/jbv=(\d+)/);
                const mPath = href.match(/\/(?:watch|title)\/(\d+)/);
                if (mJbv) videoId = mJbv[1];
                else if (mPath) videoId = mPath[1];
                if (!videoId) return;

                let title = (a.getAttribute('aria-label') || '').trim();
                const img = a.querySelector('img');
                if (img && !title) title = (img.getAttribute('alt') || '').trim();
                if (!title) title = `Netflix_${videoId}`;

                const imageUrl = extractImageUrl(a, videoId);

                if (titlesMap.has(videoId)) {
                    const existing = titlesMap.get(videoId);
                    if (!existing.image_url && imageUrl) existing.image_url = imageUrl;
                    if ((!existing.title || existing.title.startsWith('Netflix_')) && title && !title.startsWith('Netflix_')) existing.title = title;
                } else {
                    titlesMap.set(videoId, {
                        title: title,
                        id: videoId,
                        url: `https://www.netflix.com/title/${videoId}`,
                        image_url: imageUrl
                    });
                    added++;
                }
            });
            return added;
        }

        harvest();
        onProgress(`Extrayendo (${titlesMap.size})...`);

        const btnRight = targetSection.querySelector('button[data-uia="carousel-hawkins-right-button"], button[aria-label*="more titles"], button[aria-label*="más títulos"]');

        if (btnRight) {
            let stag = 0;
            let step = 0;
            while (stag < 4 && step < 120) {
                step++;
                const isDis = btnRight.getAttribute('aria-disabled') === 'true' || btnRight.offsetParent === null;
                if (isDis && stag > 1) break;

                btnRight.click();
                await new Promise(r => setTimeout(r, 650));
                const added = harvest();
                if (added === 0) stag++;
                else stag = 0;
                onProgress(`Paso ${step} (${titlesMap.size} títulos)`);
            }
        }

        const items = Array.from(titlesMap.values());
        if (items.length === 0) throw new Error("No items found");

        const csvRows = ['"title","id","url","seen","image_url"'];
        items.forEach(it => {
            const cleanTitle = it.title.replace(/"/g, '""');
            const cleanImg = (it.image_url || '').replace(/"/g, '""');
            csvRows.push(`"${cleanTitle}","${it.id}","${it.url}","","${cleanImg}"`);
        });

        const blob = new Blob(["\uFEFF" + csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "netflix_mylist.csv";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Monitorear cambios dinámicos de URL y render en SPA de Netflix
    setInterval(addExportButton, 2000);
})();

