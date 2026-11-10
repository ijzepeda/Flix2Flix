# Flix2Flix

		███████╗██╗     ██╗██╗  ██╗██████╗ ███████╗██╗     ██╗██╗  ██╗
		██╔════╝██║     ██║╚██╗██╔╝╚════██╗██╔════╝██║     ██║╚██╗██╔╝
		█████╗  ██║     ██║ ╚███╔╝  █████╔╝█████╗  ██║     ██║ ╚███╔╝ 
		██╔══╝  ██║     ██║ ██╔██╗ ██╔═══╝ ██╔══╝  ██║     ██║ ██╔██╗ 
		██║     ███████╗██║██╔╝ ██╗████████╗██║     ███████╗██║██╔╝ ██╗
		╚═╝     ╚══════╝╚═╝╚═╝  ╚═╝╚═══════╝╚═╝     ╚══════╝╚═╝╚═╝  ╚═╝
		                                                               
                 >> ACCOUNT MIGRATION TOOL <<

## Netflix My List Exporter & Viewer

When migrating to a new Netflix account, there is no native way to transfer your "My List" (To-Watch list). This project solves that by automatically extracting your Netflix watchlist into a structured CSV, generating an interactive HTML viewer to track what you've watched, and providing an automated importer for your new account.

---

### ⚠️ Nota sobre la actualización reciente de Netflix
Netflix cambió su interfaz web: reemplazó la cuadrícula estática vertical (`/browse/my-list`) por el nuevo hub **"Mi Netflix"** con filas de **carrusel horizontal virtualizado**.
Al hacer scroll lateral, Netflix desmonta ("borra") los elementos que salen de la pantalla para ahorrar memoria (`data-virtual-slot`), por lo que **guardar la página con `Ctrl + S` ya no funciona** (solo capturaría los 10 títulos visibles en ese segundo).

**Flix2Flix ahora incluye herramientas automatizadas que resuelven este problema al 100%.**

---

## Características
- **Auto-Extractor de Carrusel:** Recorre de forma automática el carrusel horizontal virtualizado de Netflix en 5 segundos y descarga directamente `netflix_mylist.csv`.
- **Visor Interactivo:** Genera una página web moderna (`index.html`) para visualizar y filtrar tu lista.
- **Seguimiento ("Visto"):** Marca los títulos que ya viste.
- **Cruce con Historial Oficial:** Soporta cruzar con tu `NetflixViewingHistory.csv` oficial de Netflix para marcar automáticamente lo ya visto.
- **Importador a Cuenta Nueva:** Script de JavaScript para importar todos tus títulos a tu nueva cuenta automáticamente.

---

## Cómo Usar

### Paso 1: Exportar tu Lista de Netflix

Tienes **3 alternativas fáciles** para extraer tu lista completa:

#### Opción A (Recomendada): Script de Consola (Sin instalar nada, 5 segundos)
1. Entra a tu cuenta vieja de Netflix en tu navegador e ingresa a: **[netflix.com/browse/my-list](https://www.netflix.com/browse/my-list)**.
2. Abre la consola de desarrollador:
   - En Mac: `Cmd + Option + J`
   - En Windows/Linux: `Ctrl + Shift + J` (o `F12` y ve a la pestaña *Consola*).
3. Abre el archivo [`export_netflix_console.js`](export_netflix_console.js), copia todo su contenido, pégalo en la consola y presiona `Enter`.
4. El script avanzará automáticamente el carrusel, acumulará todos tus títulos sin duplicados y **descargará automáticamente `netflix_mylist.csv`**. Además, copiará la lista de IDs a tu portapapeles.

#### Opción B: Bookmarklet (1 Clic)
Consulta [`bookmarklet.txt`](bookmarklet.txt) para guardar un marcador en tu barra de favoritos. Al estar en Netflix, solo haz un clic sobre el marcador y se descargará tu lista.

#### Opción C: Userscript (Tampermonkey)
Si prefieres un botón visible integrado en la interfaz de Netflix, instala [`flix2flix_tampermonkey.user.js`](flix2flix_tampermonkey.user.js) con Tampermonkey o Violentmonkey. Aparecerá un botón rojo `[ 📥 Exportar Lista (CSV) ]` directamente en la página.

#### Opción D: Backup Oficial de Netflix
- **Historial de visionado instantáneo:** Visita [netflix.com/viewingactivity](https://www.netflix.com/viewingactivity) y haz clic abajo en **"Descargar todo"** para obtener `NetflixViewingHistory.csv`.
- **Copia completa de la cuenta (GDPR):** Solicita la descarga de todos los datos de tu cuenta en [netflix.com/account/getmyinfo](https://www.netflix.com/account/getmyinfo).

---

### Paso 2: Fusionar con Respaldos Anteriores (Extender tu Lista)

Si ya tenías un respaldo anterior con títulos marcados como "visto" y quieres **extender tu lista** con los nuevos títulos exportados sin perder tus marcas ni duplicar registros:

```bash
python3 merge_csv.py
```

El script automáticamente:
1. Detecta tu respaldo anterior (`netflix_mylist_actualizado.csv` o en `BACKUPS/`).
2. Detecta el nuevo CSV exportado.
3. Conserva tus títulos vistos (`visto = 1`).
4. Agrega los títulos nuevos que no estaban antes (deduplicando por ID).
5. Actualiza `netflix_mylist_actualizado.csv` y regenera tu visor `index.html` de inmediato.

---

### Paso 3: Generar o Explorar tu Visor Interactivo (Manual)

Si deseas regenerar el visor web manualmente a partir de cualquier archivo CSV:

```bash
python3 netflix_mylist_to_csv_and_viewer.py netflix_mylist_actualizado.csv \
    --viewer-out index.html \
    --dedupe \
    --open
```

*(Opcional: Si descargaste tu historial oficial `NetflixViewingHistory.csv`, añade `--history-in NetflixViewingHistory.csv` para marcar automáticamente todo lo que ya viste).*

---

### Paso 4: Importar tu Lista a la Nueva Cuenta

1. Inicia sesión en tu **nueva cuenta de Netflix** en el navegador.
2. Abre la consola (`Cmd + Option + J` en Mac / `Ctrl + Shift + J` en Windows).
3. Pega los IDs extraídos (el script de exportación los copia automáticamente a tu portapapeles, o puedes tomarlos de tu CSV) y corre el script de importación:

```javascript
// 1. Pega aquí los IDs de tus títulos extraídos
const mis_ids = [
    "81093985",
    "81011712",
    // ...
];

async function importarListaNetflix(ids) {
    console.log(`🚀 Iniciando importación de ${ids.length} títulos...`);
    
    for (let i = 0; i < ids.length; i++) {
        const id = ids[i];
        console.log(`⏳ [${i+1}/${ids.length}] Procesando ID: ${id}`);
        
        let win = window.open(`https://www.netflix.com/title/${id}`, 'ImportWindow', 'width=800,height=600');
        
        // Esperar a que cargue la página
        await new Promise(r => setTimeout(r, 5000)); 
        
        try {
            let btnAdd = win.document.querySelector('button[data-uia="add-to-my-list"]');
            let btnRemove = win.document.querySelector('button[data-uia="remove-from-my-list"]');

            if (btnRemove) {
                console.log(`⏩ ID: ${id} ya estaba en la lista. Omitido.`);
            } else if (btnAdd) {
                btnAdd.click();
                console.log(`✅ ID: ${id} agregado con éxito.`);
                await new Promise(r => setTimeout(r, 1000)); 
            } else {
                console.log(`⚠️ ID: ${id} no tiene botón disponible (posible bloqueo regional).`);
            }
        } catch(e) {
            console.error(`❌ Error en ID ${id}:`, e);
        }
        
        win.close();
        await new Promise(r => setTimeout(r, 1500)); 
    }
    console.log("🎉 ¡Importación finalizada!");
}

importarListaNetflix(mis_ids);
```
