# Flix2Flix


		███████╗██╗     ██╗██╗  ██╗██████╗ ███████╗██╗     ██╗██╗  ██╗
		██╔════╝██║     ██║╚██╗██╔╝╚════██╗██╔════╝██║     ██║╚██╗██╔╝
		█████╗  ██║     ██║ ╚███╔╝  █████╔╝█████╗  ██║     ██║ ╚███╔╝ 
		██╔══╝  ██║     ██║ ██╔██╗ ██╔═══╝ ██╔══╝  ██║     ██║ ██╔██╗ 
		██║     ███████╗██║██╔╝ ██╗████████╗██║     ███████╗██║██╔╝ ██╗
		╚═╝     ╚══════╝╚═╝╚═╝  ╚═╝╚═══════╝╚═╝     ╚══════╝╚═╝╚═╝  ╚═╝
		                                                               
                 >> ACCOUNT MIGRATION TOOL <<

## Metflix My List Exporter & Viewer

When migrating to a new Netflix account, there is no native way to transfer your "My List" (To-Watch list). This project solves that by parsing a locally saved HTML of your Netflix list, converting it into a structured CSV, and generating an interactive HTML viewer to track what you've watched and easily open titles in your new account.

## Features
- **HTML to CSV:** Extracts all movie/show metadata, IDs, and URLs from your saved Netflix HTML.
- **Interactive Viewer:** Generates a modern UI web page to visualize your list.
- **Tracking:** Check off titles you have already watched.
- **Export Progress:** Export an updated, clean CSV (`titulo, id, url, visto`) directly from the viewer.
- **Quick Access:** "Watch on Netflix" buttons mapped to each title's unique ID.

## How to Use

### 1. Extract your Netflix Data
1. Log in to your old Netflix account on a desktop browser.
2. Go to your **My List** page.
3. Scroll all the way to the bottom to ensure all titles are lazy-loaded into the DOM.
4. Press `Ctrl + S` (or `Cmd + S`) and save the page as an HTML file (e.g., `list.html`).

### 2. Run the Script
Use the Python script to process your saved HTML file. This will output a comprehensive CSV file and an interactive HTML Viewer.

```bash
python3 netflix_mylist_to_csv_and_viewer.py list.html \
    --out netflix_mylist.csv \
    --viewer-out index.html \
    --dedupe \
    --open

```

*Note: The `--open` flag will automatically open the generated viewer in your default web browser.*

### 3. Manage your List

* Open `index.html`.
* Use the interface to sort your backlog or mark titles as "Seen".
* Click **Export CSV** in the viewer to download a clean, updated file (e.g., `netflix_mylist_actualizado.csv`) containing your progress.


### 4. Future Features

Once you have your list, you can import with a simple JS:


```
// 1. PAste here the ids of your titles
const mis_ids = [
    "81093985",
    "81011712", 
    // ... 
];

async function importarListaNetflix(ids) {
    console.log(`🚀 Start importing ${ids.length} titles...`);
    
    for (let i = 0; i < ids.length; i++) {
        const id = ids[i];
        console.log(`⏳ [${i+1}/${ids.length}] Procesando ID: ${id}`);
        
        // popup window
        let win = window.open(`https://www.netflix.com/title/${id}`, 'ImportWindow', 'width=800,height=600');
        
        // Wait 6 seconds to load DOM
        await new Promise(r => setTimeout(r, 6000)); 
        
        try {
            // Search boton "add to playlist"  
            let btnAdd = win.document.querySelector('button[data-uia="add-to-my-list"]');
            
            // if "remove-from-my-list",Then it is already added
            let btnRemove = win.document.querySelector('button[data-uia="remove-from-my-list"]');

            if (btnRemove) {
                console.log(`⏩ ID: ${id} Already there, Skipped...`);
            } else if (btnAdd) {
                btnAdd.click();
                console.log(`✅ ID: ${id} success.`);
                // Wait 1 second
                await new Promise(r => setTimeout(r, 1000)); 
            } else {
                console.log(`⚠️ No button for the ID: ${id}. Maybe not available in your region.`);
            }
        } catch(e) {
            console.error(`❌ Error on ID ${id} (closed the window too fast?):`, e);
        }
        
        win.close();
        //Wait 2 seconds
        await new Promise(r => setTimeout(r, 2000)); 
    }
    console.log("🎉 Import done!");
}

importarListaNetflix(mis_ids);
```
