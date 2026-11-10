/**
 * Flix2Flix - Netflix "My List" Importer
 * 
 * INSTRUCCIONES:
 * 1. Inicia sesión en tu NUEVA cuenta de Netflix en tu navegador.
 * 2. Abre cualquier página de Netflix (por ejemplo: https://www.netflix.com/browse).
 * 3. Abre la consola de desarrollador:
 *    - Mac: Cmd + Option + J
 *    - Windows/Linux: Ctrl + Shift + J (o F12 -> pestaña Consola)
 * 4. Pega tus IDs en el array `mis_ids` abajo.
 * 5. Pega todo este código en la consola y presiona Enter.
 * 
 * Nota: El script abrirá UNA SOLA ventana pequeña auxiliar que reutilizará para todos los títulos,
 * evitando que el bloqueador de ventanas emergentes de Chrome/Brave/Firefox interfiera.
 */

// Pega aquí los IDs de tus títulos (el script de exportación los copia automáticamente a tu portapapeles)
const mis_ids = [
    // "81093985",
    // "81011712",
];

async function importarListaNetflix(ids) {
    if (!ids || ids.length === 0) {
        console.error("❌ La lista de IDs está vacía. Agrega los IDs en el array 'mis_ids' antes de ejecutar.");
        alert("Flix2Flix: Agrega los IDs en 'mis_ids' antes de ejecutar.");
        return;
    }

    console.log(`%c🚀 Flix2Flix: Iniciando importación de ${ids.length} títulos...`, "color: #e50914; font-weight: bold; font-size: 14px;");
    console.log("ℹ️ Se abrirá 1 ventana auxiliar reutilizable. No la cierres manualmente.");

    // Abrir una única ventana auxiliar reutilizable
    const win = window.open('about:blank', 'Flix2FlixImportWindow', 'width=700,height=500');
    if (!win) {
        alert("⚠️ Tu navegador bloqueó la ventana emergente. Por favor permite las ventanas emergentes de Netflix y reintenta.");
        return;
    }

    let agregados = 0;
    let yaEstaban = 0;
    let errores = 0;

    for (let i = 0; i < ids.length; i++) {
        const id = ids[i].toString().trim();
        const progreso = `[${i + 1}/${ids.length}] (${Math.round(((i + 1) / ids.length) * 100)}%)`;
        console.log(`⏳ ${progreso} Navegando a ID: ${id}...`);

        try {
            win.location.href = `https://www.netflix.com/title/${id}`;

            // Esperar carga del DOM (polling para detectar los botones de Netflix)
            let btnAdd = null;
            let btnRemove = null;
            let attempts = 0;
            const maxAttempts = 15; // Hasta ~7.5 segundos por título

            while (attempts < maxAttempts) {
                await new Promise(r => setTimeout(r, 500));
                attempts++;

                try {
                    btnAdd = win.document.querySelector('button[data-uia="add-to-my-list"]');
                    btnRemove = win.document.querySelector('button[data-uia="remove-from-my-list"]');
                    if (btnAdd || btnRemove) break;
                } catch (e) {
                    // Posible error de cross-origin durante la transición de navegación, reintentar
                }
            }

            if (btnRemove) {
                console.log(`⏩ ${progreso} ID: ${id} ya estaba en Mi Lista.`);
                yaEstaban++;
            } else if (btnAdd) {
                btnAdd.click();
                console.log(`%c✅ ${progreso} ID: ${id} agregado con éxito a Mi Lista.`, "color: #46d369;");
                agregados++;
                await new Promise(r => setTimeout(r, 800));
            } else {
                console.warn(`⚠️ ${progreso} ID: ${id} no tiene botón disponible (posible contenido no disponible en tu región).`);
                errores++;
            }
        } catch (err) {
            console.error(`❌ ${progreso} Error procesando ID ${id}:`, err);
            errores++;
        }

        // Breve pausa para no saturar peticiones
        await new Promise(r => setTimeout(r, 700));
    }

    try {
        win.close();
    } catch (e) {}

    console.log("%c🎉 ¡Proceso de importación finalizado!", "color: #46d369; font-weight: bold; font-size: 16px;");
    console.log(`📊 Resumen:
- Agregados con éxito: ${agregados}
- Ya estaban en la lista: ${yaEstaban}
- No disponibles / Errores: ${errores}
- Total procesados: ${ids.length}`);

    alert(`Flix2Flix: Importación completada.\nAgregados: ${agregados}\nYa estaban: ${yaEstaban}\nErrores/Región: ${errores}`);
}

// Ejecutar
if (mis_ids.length > 0) {
    importarListaNetflix(mis_ids);
} else {
    console.log("%c👉 Pega tus IDs en el array 'mis_ids' arriba y llama a importarListaNetflix(mis_ids);", "color: #f59e0b; font-weight: bold;");
}

