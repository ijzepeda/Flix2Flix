/**
 * Flix2Flix - Netflix "My List" Auto-Scroller & Exporter
 * 
 * INSTRUCCIONES:
 * 1. Abre Netflix en tu navegador (Chrome, Edge, Firefox, Brave, Safari).
 * 2. Ve a https://www.netflix.com/browse/my-list
 * 3. Abre la consola de desarrollador:
 *    - Mac: Cmd + Option + J
 *    - Windows/Linux: Ctrl + Shift + J (o F12 -> pestaña Consola)
 * 4. Pega todo este código y presiona Enter.
 * 5. El script recorrerá automáticamente el carrusel de "Mi Lista" y descargará 'netflix_mylist.csv'.
 */

(async function exportNetflixMyList() {
    console.log("%c🎬 Flix2Flix: Iniciando extractor de Mi Lista...", "color: #e50914; font-weight: bold; font-size: 14px;");

    // 1. Identificar la fila de "Mi lista" / "My List"
    const sections = Array.from(document.querySelectorAll('section[data-uia^="carousel-row-section"], section.carousel-row'));
    let targetSection = null;

    const listNames = ['my list', 'mi lista', 'minha lista', 'ma liste', 'meine liste', 'la mia lista', 'マイリスト', '내가 찜한 콘텐츠', '我的待看列表'];

    for (const sec of sections) {
        const heading = sec.querySelector('h2, [data-uia*="row-header"]');
        if (heading) {
            const txt = heading.textContent.trim().toLowerCase();
            if (listNames.some(name => txt.includes(name))) {
                targetSection = sec;
                break;
            }
        }
    }

    if (!targetSection) {
        console.warn("⚠️ No se encontró una fila explícita llamada 'Mi lista'. Buscando carrusel con tarjetas...");
        targetSection = sections.find(s => s.querySelector('a[data-uia="standard-card"], a[href*="jbv="]')) || document;
    }

    const sectionTitle = targetSection.querySelector('h2')?.textContent.trim() || "Mi Lista / My List";
    console.log(`📌 Fila detectada: "${sectionTitle}"`);

    // 2. Mapa para acumular títulos únicos (ID -> datos)
    const titlesMap = new Map();

    function harvestCards() {
        // Enlaces que contienen el ID del título (jbv=, /watch/ o /title/)
        const anchors = targetSection.querySelectorAll('a[href*="jbv="], a[href*="/watch/"], a[href*="/title/"]');
        let newCount = 0;

        anchors.forEach(a => {
            const href = a.getAttribute('href') || '';
            let videoId = '';

            const mJbv = href.match(/jbv=(\d+)/);
            const mPath = href.match(/\/(?:watch|title)\/(\d+)/);

            if (mJbv) videoId = mJbv[1];
            else if (mPath) videoId = mPath[1];

            if (!videoId) return;

            // Obtener título legible e imagen
            let title = (a.getAttribute('aria-label') || '').trim();
                const img = a.querySelector('img');
                let imageUrl = '';
                if (img) {
                    if (!title) title = (img.getAttribute('alt') || '').trim();
                    imageUrl = img.currentSrc || img.src || '';
                }
                if (!title) {
                    const fallback = a.querySelector('.fallback-text, p, span');
                    if (fallback) title = fallback.textContent.trim();
                }
                if (!title) {
                    title = `Netflix_${videoId}`;
                }

                if (!titlesMap.has(videoId)) {
                    titlesMap.set(videoId, {
                        title: title,
                        id: videoId,
                        url: `https://www.netflix.com/title/${videoId}`,
                        image_url: imageUrl,
                        seen: ""
                    });
                    newCount++;
                }
            });

        return newCount;
    }

    // Extracción de lo visible inicialmente
    harvestCards();
    console.log(`🔎 Títulos iniciales visibles: ${titlesMap.size}`);

    // 3. Simular scroll horizontal automático para sortear la virtualización
    const btnRight = targetSection.querySelector('button[data-uia="carousel-hawkins-right-button"], button[aria-label*="more titles"], button[aria-label*="más títulos"]');

    if (btnRight) {
        console.log("🔄 Recorriendo carrusel automáticamente (esto tomará pocos segundos)...");
        let stagnation = 0;
        let step = 0;
        const maxSteps = 120; // Hasta ~600 títulos

        while (stagnation < 4 && step < maxSteps) {
            step++;

            // Verificar si el botón está deshabilitado o invisible
            const isDisabled = btnRight.getAttribute('aria-disabled') === 'true' ||
                btnRight.getAttribute('tabindex') === '-1' ||
                btnRight.disabled ||
                btnRight.offsetParent === null;

            if (isDisabled && stagnation > 1) {
                console.log("⏹️ Fin del carrusel alcanzado (botón desactivado).");
                break;
            }

            btnRight.click();

            // Esperar animación y carga de nuevos slots virtuales en el DOM
            await new Promise(r => setTimeout(r, 650));

            const added = harvestCards();
            if (added === 0) {
                stagnation++;
            } else {
                stagnation = 0;
                console.log(`➡️ [Paso ${step}] +${added} nuevos | Total acumulado: ${titlesMap.size}`);
            }
        }
    } else {
        console.log("ℹ️ No se detectó botón de avance lateral. Todos los títulos disponibles ya están en pantalla.");
    }

    const items = Array.from(titlesMap.values());

    if (items.length === 0) {
        console.error("❌ No se pudieron extraer títulos. Asegúrate de estar en https://www.netflix.com/browse/my-list");
        alert("Flix2Flix: No se encontraron títulos. Abre https://www.netflix.com/browse/my-list y vuelve a intentarlo.");
        return;
    }

    console.log(`%c🎉 ¡Éxito! Se han extraído ${items.length} títulos de tu lista.`, "color: #46d369; font-weight: bold; font-size: 14px;");

    // 4. Generar CSV compatible con Flix2Flix (con imagen)
    const csvRows = ['"title","id","url","seen","image_url"'];
    items.forEach(it => {
        const cleanTitle = it.title.replace(/"/g, '""');
        const cleanImg = (it.image_url || '').replace(/"/g, '""');
        csvRows.push(`"${cleanTitle}","${it.id}","${it.url}","","${cleanImg}"`);
    });
    const csvString = "\uFEFF" + csvRows.join("\n"); // BOM para UTF-8 correcto en Excel/Numbers/Python

    // 5. Descargar automáticamente el archivo CSV
    const blob = new Blob([csvString], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "netflix_mylist.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // 6. Copiar los IDs al portapapeles para importación rápida
    const idList = items.map(it => it.id);
    const jsonIds = JSON.stringify(idList, null, 2);
    try {
        await navigator.clipboard.writeText(jsonIds);
        console.log("%c📋 Lista de IDs copiada al portapapeles lista para importar en tu otra cuenta.", "color: #3b82f6;");
    } catch (e) {
        // Si el foco del portapapeles falla, no pasa nada grave
    }

    console.table(items.slice(0, 15));
    if (items.length > 15) {
        console.log(`... y ${items.length - 15} títulos más en 'netflix_mylist.csv'.`);
    }

    console.log("%c💾 Archivo 'netflix_mylist.csv' descargado con éxito.", "color: #46d369; font-weight: bold;");
})();

