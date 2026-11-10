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
- **Centro de Control Todo en Uno (`index.html`):** Gestiona las 4 tareas directamente desde el visor web sin tener que abrir archivos de código ni memorizar comandos.
- **Auto-Extractor de Carrusel:** Recorre de forma automática el carrusel horizontal virtualizado de Netflix en 5 segundos y descarga directamente `netflix_mylist.csv`.
- **Fusión en el Navegador o Terminal:** Arrastra tu nuevo CSV directamente a `index.html` para actualizar tu lista en vivo sin salir del navegador, o usa `python3 2-merge_csv.py`.
- **Seguimiento ("Visto"):** Marca los títulos que ya viste y consérvalos entre respaldos.
- **Caché Local de Portadas:** Descarga carátulas a `./imagenes/` para usar tu catálogo 100% offline.
- **Importador Seguro Anti-Bloqueo:** Copia el script de importación con tus IDs pendientes ya inyectados para sincronizarlos en tu nueva cuenta con ritmo humano.

---

## 🌟 Solución Todo en Uno desde `index.html`
Solo abre [`index.html`](index.html) en tu navegador y haz clic en el botón rojo superior **`[ 🛠️ Tareas (1-2-3-4) ]`**. Se abrirá el panel interactivo con las 4 tareas accesibles con 1 clic:

1. **📥 1. Exportar:** Botón para copiar el script extractor al portapapeles y enlace directo a Netflix.
2. **🔄 2. Fusionar:** Zona drag-and-drop para arrastrar tu nuevo `netflix_mylist.csv` y fusionarlo en vivo en pantalla.
3. **🖼️ 3. Caché Portadas:** Estado de imágenes y comando para guardarlas offline.
4. **🚀 4. Importar:** Botón que genera y copia el script importador con tus IDs pendientes ya incrustados listo para pegar en tu nueva cuenta.

---

## Cómo Usar (Flujo Paso a Paso 1 → 2 → 3 → 4)

### Paso 1: Exportar tu Lista de Netflix (Cuenta Antigua)

Tienes **3 alternativas fáciles** para extraer tu lista completa sorteando el carrusel virtualizado:

#### Opción A (Recomendada): Script de Consola (Sin instalar nada, 5 segundos)
1. Entra a tu cuenta vieja de Netflix en tu navegador e ingresa a: **[netflix.com/browse/my-list](https://www.netflix.com/browse/my-list)**.
2. Abre la consola de desarrollador:
   - En Mac: `Cmd + Option + J`
   - En Windows/Linux: `Ctrl + Shift + J` (o `F12` y ve a la pestaña *Consola*).
3. Abre el archivo [`1-export_netflix_console.js`](1-export_netflix_console.js), copia todo su contenido, pégalo en la consola y presiona `Enter`.
4. El script avanzará automáticamente el carrusel, acumulará todos tus títulos sin duplicados y **descargará automáticamente `netflix_mylist.csv`**. Además, copiará la lista de IDs a tu portapapeles.

#### Opción B: Bookmarklet (1 Clic)
Consulta [`1-bookmarklet.txt`](1-bookmarklet.txt) para guardar un marcador en tu barra de favoritos. Al estar en Netflix, solo haz un clic sobre el marcador y se descargará tu lista.

#### Opción C: Userscript (Tampermonkey)
Si prefieres un botón visible integrado en la interfaz de Netflix, instala [`1-flix2flix_tampermonkey.user.js`](1-flix2flix_tampermonkey.user.js) con Tampermonkey o Violentmonkey. Aparecerá un botón rojo `[ 📥 Exportar Lista (CSV) ]` directamente en la página.

---

### Paso 2: Fusionar con Respaldos Anteriores (Extender tu Lista)

Si ya tenías un respaldo anterior con títulos marcados como "visto" y quieres **extender tu lista** con los nuevos títulos exportados sin perder tus marcas ni duplicar registros:

```bash
python3 2-merge_csv.py
```

El script automáticamente:
1. Detecta tu respaldo anterior (`netflix_mylist_actualizado.csv` o en `BACKUPS/`).
2. Detecta el nuevo CSV exportado.
3. Conserva tus títulos vistos (`visto = 1`).
4. Agrega los títulos nuevos que no estaban antes (deduplicando por ID).
5. Restaura automáticamente las portadas desde la caché histórica de respaldos.
6. Actualiza `netflix_mylist_actualizado.csv` y regenera tu visor `index.html` de inmediato.

---

### Paso 3: Descargar Portadas en Caché Local (Modo Offline)

Para evitar depender de las conexiones a los servidores de Netflix, protegerte contra URLs que expiren o títulos descatalogados, y hacer tu visor **100% utilizable sin internet (modo avión/offline)**:

```bash
python3 3-download_images.py
```

El script:
- Descarga concurrentemente las portadas a la carpeta `./imagenes/<id>.jpg` o `.webp`.
- Es totalmente seguro (no satura peticiones y reutiliza User-Agent de navegador).
- Actualiza de inmediato `index.html` para que use las imágenes locales, con fallback automático a la red si falta alguna.

---

### Paso 4: Sincronizar / Importar a tu Nueva Cuenta

Tienes **2 opciones seguras y automatizadas** para agregar todos tus títulos a tu nueva cuenta:

> [!NOTE]
> **¿Existe riesgo de baneo o detección de bot?**  
> **No.** La sincronización se ejecuta directamente en tu propio navegador con tu sesión ya autenticada y legítima (no con navegadores fantasma externos como Selenium/Puppeteer que sí son detectados). Para evitar límites de velocidad de peticiones (*Rate Limiting* / HTTP 429), los scripts incluyen **delays humanos con jitter aleatorio (1.6s a 2.4s)** y reutilizan una única ventana auxiliar pequeña.

#### Opción A: Script de Consola con HUD en Vivo
1. En tu `index.html`, haz clic en **"📋 Copiar IDs para Importar"** (copia solo los títulos pendientes que no has visto).
2. Abre Netflix en tu **nueva cuenta** en tu navegador (`netflix.com/browse`).
3. Abre la consola de desarrollador (`Cmd + Option + J` en Mac / `Ctrl + Shift + J` en Windows).
4. Copia y pega el contenido de [`4-import_netflix_console.js`](4-import_netflix_console.js) y presiona `Enter`.
5. Aparecerá un elegante panel flotante (HUD) en la esquina superior con barra de progreso, contador de éxitos y botones de **[ ⏸️ Pausar ]** y **[ ⏹️ Cancelar ]**. El script agregará cada título de forma secuencial y segura.

#### Opción B: Userscript para Tampermonkey
Instala [`4-sync_netflix_tampermonkey.user.js`](4-sync_netflix_tampermonkey.user.js). Aparecerá un botón azul `[ 🔄 Flix2Flix Sync ]` en la barra superior de Netflix para iniciar la sincronización interactiva con un clic.
