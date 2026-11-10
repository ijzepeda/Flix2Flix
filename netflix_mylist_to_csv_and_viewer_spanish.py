#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# V3
import argparse, csv, json, re, webbrowser
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, unquote

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# ---------- parsing helpers igual que antes ----------
def _parse_ctx(raw_ctx: str) -> dict:
    if not raw_ctx: return {}
    try:
        return json.loads(unquote(raw_ctx))
    except Exception:
        try:
            return json.loads(unquote(unquote(raw_ctx)))
        except Exception:
            return {}

def _extract_video_id(href: str, unified_entity_id: str, ctx: dict) -> str:
    vid = str(ctx.get("video_id") or "").strip()
    if vid.isdigit(): return vid
    if unified_entity_id:
        m = re.search(r":(\d+)$", unified_entity_id)
        if m: return m.group(1)
    if href:
        m = re.search(r"/watch/(\d+)", href)
        if m: return m.group(1)
    return ""

def _get_title(anchor, ptrack_div):
    aria = (anchor.get("aria-label") or "").strip()
    if aria: return aria
    fb = ptrack_div.select_one(".fallback-text-container p.fallback-text")
    if fb and fb.text.strip(): return fb.text.strip()
    img = anchor.find("img")
    alt = (img.get("alt") if img else "") or ""
    alt = alt.strip()
    if alt: return alt
    txt = (anchor.get_text() or "").strip()
    return re.sub(r"\s+", " ", txt)

def parse_html_any(html: str, base_url: str = "https://www.netflix.com"):
    if BeautifulSoup is None:
        raise SystemExit(
            "[ERROR] Se requiere la librería 'beautifulsoup4' para procesar archivos HTML.\n"
            "Instálala con: pip install beautifulsoup4\n"
            "Consejo: Si usaste el script de consola 'export_netflix_console.js', ya tienes 'netflix_mylist.csv'.\n"
            "Simplemente ejecuta: python3 netflix_mylist_to_csv_and_viewer_spanish.py netflix_mylist.csv --open"
        )
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # Primario
    for ptrack in soup.select("[data-ui-tracking-context]"):
        ctx = _parse_ctx(ptrack.get("data-ui-tracking-context",""))
        a = ptrack.find("a", href=True) or ptrack.select_one("a[href]")
        if not a: continue
        href = a.get("href","")
        unified = str(ctx.get("unifiedEntityId") or "")
        vid = _extract_video_id(href, unified, ctx)
        url = urljoin(base_url, f"/watch/{vid}") if vid else urljoin(base_url, href)
        try:
            tctx = parse_qs(urlparse(href).query).get("tctx", [None])[0]
        except Exception:
            tctx = None
        titulo = _get_title(a, ptrack) or "(sin título)"
        img = a.find("img")
        image_url = img.get("src","").strip() if img else ""
        container = ptrack.find_parent("div", class_="title-card")
        container_id = container.get("id","") if container else ""
        items.append({
            "titulo": titulo, "id": vid, "url": url, "href_original": href,
            "unifiedEntityId": unified, "list_id": ctx.get("list_id",""),
            "location": ctx.get("location",""), "rank": ctx.get("rank",""),
            "row": ctx.get("row",""), "track_id": ctx.get("track_id",""),
            "request_id": ctx.get("request_id",""), "lolomo_id": ctx.get("lolomo_id",""),
            "image_key": ctx.get("image_key",""), "supp_video_id": ctx.get("supp_video_id",""),
            "appView": ctx.get("appView",""), "image_url": image_url,
            "aria_label": "", "titulo_fallback": "", "container_id": container_id,
            "tracking_uuid": ptrack.get("data-tracking-uuid",""), "tctx": tctx,
        })
    # Fallback / Modern Netflix UI
    if not items:
        sections = soup.find_all("section")
        target_container = soup
        list_keywords = ["my list", "mi lista", "minha lista", "ma liste", "meine liste"]
        for sec in sections:
            h2 = sec.find("h2")
            if h2 and any(k in h2.get_text().strip().lower() for k in list_keywords):
                target_container = sec
                break

        for a in target_container.find_all("a", href=True):
            href = a.get("href") or ""
            vid = ""
            m_jbv = re.search(r"jbv=(\d+)", href)
            m_watch = re.search(r"/(?:watch|title)/(\d+)", href)
            if m_jbv:
                vid = m_jbv.group(1)
            elif m_watch:
                vid = m_watch.group(1)
            if not vid:
                continue

            url = urljoin(base_url, f"/title/{vid}")
            titulo = (a.get("aria-label") or "").strip()
            if not titulo:
                img = a.find("img")
                if img:
                    titulo = (img.get("alt") or "").strip()
            if not titulo:
                titulo = (a.text or "").strip() or f"Netflix_{vid}"

            img = a.find("img")
            image_url = img.get("src","").strip() if img else ""
            items.append({
                "titulo": titulo, "id": vid, "url": url, "href_original": href,
                "unifiedEntityId": "", "list_id": "", "location": "", "rank": "",
                "row": "", "track_id": "", "request_id": "", "lolomo_id": "",
                "image_key": "", "supp_video_id": "", "appView": "",
                "image_url": image_url, "aria_label": "", "titulo_fallback": "",
                "container_id": "", "tracking_uuid": "", "tctx": "",
            })
    return items

# ---------- CSV ----------
CSV_FIELDS = [
    "titulo","id","url","href_original","unifiedEntityId","list_id","location",
    "rank","row","track_id","request_id","lolomo_id","image_key","supp_video_id",
    "appView","image_url","aria_label","titulo_fallback","container_id",
    "tracking_uuid","tctx","visto"
]

def write_csv(items, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for it in items:
            if "visto" not in it:
                it["visto"] = ""  # vacío por defecto
            w.writerow(it)

def read_items_from_csv(csv_path: Path):
    items = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            d = dict(row)
            # Normalizar nombres de columnas inglés/español
            if "title" in d and ("titulo" not in d or not d["titulo"]):
                d["titulo"] = d["title"]
            if "seen" in d and ("visto" not in d or not d["visto"]):
                d["visto"] = d["seen"]
            items.append(d)
    return items

# ---------- Viewer (HTML con checkboxes + export) ----------
def _esc_html(s):
    if s is None: return ""
    return (str(s).replace("&","&amp;").replace("<","&lt;")
                 .replace(">","&gt;").replace('"',"&quot;"))

def _derive_base(url_str, default="https://www.netflix.com"):
    try:
        p = urlparse(url_str or "")
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    except Exception:
        pass
    return default

def build_simple_viewer_html(items, page_title="Netflix My List – Viewer"):
    # Render cards (incluye poster, placeholder, checkbox visto y botones)
    card_parts = []
    for it in items:
        title = _esc_html(it.get("titulo") or "(sin título)")
        watch_url = _esc_html(it.get("url") or "")
        image = _esc_html(it.get("image_url") or "")
        vid   = _esc_html(it.get("id") or "")
        rank  = _esc_html(it.get("rank") or "")
        visto = "true" if str(it.get("visto","")).strip().lower() in ("1","true","yes","si","sí","x") else "false"

        base = _derive_base(watch_url, "https://www.netflix.com")
        title_url = _esc_html(urljoin(base, "/title/" + vid)) if vid else ""

        card = []
        card.append(f'<div class="card{" seen-card" if visto=="true" else ""}" data-title="{title}" data-rank="{rank}" data-id="{vid}" data-seen="{visto}" data-img="{image}">')
        
        # Imagen con soporte de referrerpolicy y placeholder de fallback
        card.append('  <div class="poster-container">')
        if image:
            card.append(f'    <img class="poster" src="{image}" alt="{title}" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';">')
            card.append(f'    <div class="poster-placeholder" style="display:none;"><span class="placeholder-icon">🎬</span><span class="placeholder-title">{title}</span></div>')
        else:
            card.append(f'    <div class="poster-placeholder"><span class="placeholder-icon">🍿</span><span class="placeholder-title">{title}</span></div>')
        card.append('  </div>')

        card.append('  <div class="card-body">')
        card.append(f'    <div class="title" title="{title}">{title}</div>')
        if vid:
            card.append(f'    <div class="idline">ID: {vid}</div>')
        # Checkbox visto
        card.append(f'    <label class="seen"><input type="checkbox" class="chk-seen" {"checked" if visto=="true" else ""}> Visto</label>')
        # Botones
        if watch_url or title_url:
            card.append('    <div class="row-actions">')
            if title_url:
                card.append(f'      <a class="btn btn-secondary btn-title" href="{title_url}" target="_blank" rel="noopener noreferrer" title="Ficha en Netflix">')
                card.append('        <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" class="ext-icon"><path d="M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42 9.3-9.29H14V3z"></path><path d="M5 5h6v2H7v10h10v-4h2v6H5z"></path></svg>')
                card.append('      </a>')
            if watch_url:
                card.append(f'      <a class="btn btn-primary btn-watch" href="{watch_url}" target="_blank" rel="noopener noreferrer">Ver</a>')
            card.append('    </div>')
        card.append('  </div>')
        card.append('</div>')
        card_parts.append("\n".join(card))

    template = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>__PAGE_TITLE__</title>
<style>
  :root { 
    --bg:#0b0d12; 
    --panel:#121725; 
    --text:#e5e7eb; 
    --muted:#9aa0a6; 
    --accent:#e50914; 
    --card:#1a2031; 
    --btn:#141c2c; 
    --btn-stroke:#2a3550; 
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Noto Sans, Helvetica Neue, Arial; }
  header { position:sticky; top:0; background:rgba(11,13,18,.95); border-bottom:1px solid #222a3b; backdrop-filter: blur(8px); z-index:100; }
  .wrap { max-width:1300px; margin:0 auto; padding:14px 18px; }
  
  .header-content { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; }
  h1 { margin:0; font-size:20px; font-weight:800; letter-spacing:-0.5px; }
  .sub { color:var(--muted); font-size:13px; margin-top:2px; }
  
  .stats-badge { display:flex; gap:8px; align-items:center; }
  .stat-pill { background:#161f33; border:1px solid var(--btn-stroke); border-radius:20px; padding:4px 12px; font-size:13px; color:#cbd5e1; }
  .stat-seen { border-color:#22c55e; color:#4ade80; }
  .stat-pending { border-color:#eab308; color:#facc15; }

  .panel { background:var(--panel); border:1px solid #23304a; border-radius:14px; padding:12px 16px; margin:16px 0; }
  .controls { display:flex; gap:12px; align-items:center; justify-content:space-between; flex-wrap:wrap; }
  
  .search-box { flex:1; min-width:220px; max-width:380px; }
  .search-box input { width:100%; padding:8px 14px; border-radius:10px; border:1px solid var(--btn-stroke); background:#0a0f1d; color:var(--text); font-size:14px; outline:none; transition:border .2s; }
  .search-box input:focus { border-color:var(--accent); }

  .filter-pills { display:flex; gap:6px; }
  .btn-filter { padding:6px 12px; border-radius:8px; border:1px solid var(--btn-stroke); background:#0f1625; color:var(--muted); font-size:13px; font-weight:600; cursor:pointer; transition:all .2s; }
  .btn-filter:hover { background:#19243a; color:#fff; }
  .btn-filter.active { background:var(--accent); border-color:var(--accent); color:#fff; }

  .sort-box { display:flex; align-items:center; gap:8px; font-size:13px; color:var(--muted); }
  select { padding:7px 10px; border-radius:8px; border:1px solid var(--btn-stroke); background:#0f1625; color:var(--text); font-size:13px; cursor:pointer; }
  
  .action-buttons { display:flex; gap:8px; }
  .btn-action { padding:7px 14px; border-radius:8px; border:1px solid var(--btn-stroke); background:#0f1625; color:var(--text); font-size:13px; font-weight:600; cursor:pointer; transition:all .2s; }
  .btn-action:hover { background:#1b2842; }
  .btn-export-highlight { background:#2563eb; border-color:#3b82f6; color:#fff; }
  .btn-export-highlight:hover { background:#1d4ed8; }

  .grid { display:grid; gap:14px; grid-template-columns: repeat(6, minmax(0,1fr)); padding-bottom:40px; }
  @media (max-width:1200px) { .grid { grid-template-columns: repeat(5,1fr); } }
  @media (max-width:1000px) { .grid { grid-template-columns: repeat(4,1fr); } }
  @media (max-width:800px)  { .grid { grid-template-columns: repeat(3,1fr); } }
  @media (max-width:600px)  { .grid { grid-template-columns: repeat(2,1fr); } }
  @media (max-width:420px)  { .grid { grid-template-columns: repeat(1,1fr); } }

  .card { background:var(--card); border:1px solid #23304a; border-radius:12px; overflow:hidden; display:flex; flex-direction:column; transition:transform .2s, border-color .2s; }
  .card:hover { transform: translateY(-3px); border-color:#384c75; }
  .card.seen-card { opacity:0.55; }
  .card.seen-card:hover { opacity:0.9; }

  .poster-container { position:relative; width:100%; aspect-ratio:16/9; overflow:hidden; background:#0a0f1d; }
  .poster { display:block; width:100%; height:100%; object-fit:cover; transition:transform .3s; }
  .card:hover .poster { transform: scale(1.04); }
  
  .poster-placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; width:100%; height:100%; background:linear-gradient(135deg, #131c2e, #0b0f19); color:var(--muted); padding:10px; text-align:center; }
  .placeholder-icon { font-size:26px; margin-bottom:4px; opacity:0.6; }
  .placeholder-title { font-size:11px; line-height:1.2; font-weight:600; color:#94a3b8; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }

  .card-body { padding:10px 12px; display:flex; flex-direction:column; flex:1; gap:6px; }
  .title { font-size:13px; font-weight:700; line-height:1.3; color:#f1f5f9; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
  .idline { font-size:11px; color:var(--muted); font-family:monospace; }
  
  .seen { display:flex; gap:6px; align-items:center; font-size:12px; color:#cbd5e1; cursor:pointer; margin-top:auto; padding-top:6px; }
  .seen input { width:15px; height:15px; cursor:pointer; accent-color:var(--accent); }
  
  .row-actions { display:grid; grid-template-columns: auto 1fr; gap:6px; margin-top:6px; }
  .btn { display:inline-flex; align-items:center; justify-content:center; gap:6px; padding:6px 10px; border-radius:6px; border:1px solid var(--btn-stroke); background:var(--btn); color:#e5e7eb; font-weight:600; font-size:12px; text-decoration:none; transition:background .2s; }
  .btn:hover { background:#1e293b; }
  .btn-primary { background:var(--accent); border-color:var(--accent); color:#fff; }
  .btn-primary:hover { background:#b91c1c; }
  .btn-secondary { background:#1e293b; color:#cbd5e1; }
  .ext-icon { width:14px; height:14px; fill:currentColor; }

  .toast { position:fixed; bottom:20px; right:20px; background:#10b981; color:#fff; padding:10px 18px; border-radius:8px; font-weight:600; font-size:13px; box-shadow:0 4px 12px rgba(0,0,0,0.5); z-index:9999; opacity:0; transform:translateY(10px); transition:all .3s; pointer-events:none; }
  .toast.show { opacity:1; transform:translateY(0); }
</style>
</head>
<body>
<header>
  <div class="wrap">
    <div class="header-content">
      <div>
        <h1>__PAGE_TITLE__</h1>
        <div class="sub">Gestiona tu lista, marca vistos y exporta a tu nueva cuenta.</div>
      </div>
      <div class="stats-badge" id="counterStats">
        <span class="stat-pill"><strong id="totalCount">0</strong> en lista</span>
        <span class="stat-pill stat-seen"><strong id="seenCount">0</strong> vistos</span>
        <span class="stat-pill stat-pending"><strong id="pendingCount">0</strong> pendientes</span>
      </div>
    </div>
  </div>
</header>

<main class="wrap">
  <section class="panel">
    <div class="controls">
      <div class="search-box">
        <input type="search" id="searchInput" placeholder="🔍 Buscar por título o ID...">
      </div>
      
      <div class="filter-pills" id="filterPills">
        <button type="button" class="btn-filter active" data-filter="all">Todos (<span id="pillAll">0</span>)</button>
        <button type="button" class="btn-filter" data-filter="pending">⏳ Pendientes (<span id="pillPending">0</span>)</button>
        <button type="button" class="btn-filter" data-filter="seen">✅ Vistos (<span id="pillSeen">0</span>)</button>
      </div>

      <div class="sort-box">
        <label for="sort">Ordenar:</label>
        <select id="sort">
          <option value="title-asc">Título A→Z</option>
          <option value="title-desc">Título Z→A</option>
          <option value="rank-asc">Orden Original ↑</option>
          <option value="rank-desc">Orden Original ↓</option>
        </select>
      </div>

      <div class="action-buttons">
        <button id="btnCopyIds" class="btn-action" title="Copia los IDs de los títulos pendientes para importar en tu nueva cuenta">📋 Copiar IDs para Importar</button>
        <button id="btnExport" class="btn-action btn-export-highlight">💾 Exportar CSV</button>
      </div>
    </div>
  </section>

  <section id="grid" class="grid">
    __CARDS__
  </section>
</main>

<div class="toast" id="toast">Copiado al portapapeles</div>

<script>
(function(){
  const grid = document.getElementById('grid');
  const sortSel = document.getElementById('sort');
  const searchInput = document.getElementById('searchInput');
  const filterPills = document.getElementById('filterPills');
  const btnExport = document.getElementById('btnExport');
  const btnCopyIds = document.getElementById('btnCopyIds');
  const toast = document.getElementById('toast');
  const STORAGE_KEY = 'netflix_mylist_seen_v1';

  let currentFilter = 'all';

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
  }

  function loadSeenMap() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch(e) { return {}; }
  }
  function saveSeenMap(map) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  }

  const seenMap = loadSeenMap();

  // Inicializar checkboxes y listeners
  const allCards = Array.from(grid.querySelectorAll('.card'));
  
  allCards.forEach(card => {
    const id = card.dataset.id;
    const chk = card.querySelector('.chk-seen');
    if (!id || !chk) return;

    // Si ya venía marcado en el CSV (dataset.seen="true") o en localStorage
    if (seenMap[id] !== undefined) {
      chk.checked = !!seenMap[id];
    } else if (card.dataset.seen === "true") {
      chk.checked = true;
      seenMap[id] = true;
    }

    if (chk.checked) card.classList.add('seen-card');

    chk.addEventListener('change', () => {
      if (chk.checked) {
        seenMap[id] = true;
        card.classList.add('seen-card');
        card.dataset.seen = "true";
      } else {
        delete seenMap[id];
        card.classList.remove('seen-card');
        card.dataset.seen = "false";
      }
      saveSeenMap(seenMap);
      updateCounters();
      applyFilters();
    });

    card.querySelectorAll('.btn-watch, .btn-title').forEach(a => {
      a.addEventListener('click', () => {
        chk.checked = true;
        seenMap[id] = true;
        card.classList.add('seen-card');
        card.dataset.seen = "true";
        saveSeenMap(seenMap);
        updateCounters();
        applyFilters();
      });
    });
  });

  saveSeenMap(seenMap);

  // Contadores en tiempo real
  function updateCounters() {
    let seen = 0;
    allCards.forEach(c => {
      const chk = c.querySelector('.chk-seen');
      if (chk && chk.checked) seen++;
    });
    const total = allCards.length;
    const pending = total - seen;

    document.getElementById('totalCount').textContent = total;
    document.getElementById('seenCount').textContent = seen;
    document.getElementById('pendingCount').textContent = pending;
    
    document.getElementById('pillAll').textContent = total;
    document.getElementById('pillSeen').textContent = seen;
    document.getElementById('pillPending').textContent = pending;
  }

  // Filtrado y búsqueda
  function applyFilters() {
    const query = (searchInput.value || '').trim().toLowerCase();
    allCards.forEach(card => {
      const title = (card.dataset.title || '').toLowerCase();
      const id = (card.dataset.id || '').toLowerCase();
      const isSeen = card.querySelector('.chk-seen')?.checked;

      const matchesSearch = !query || title.includes(query) || id.includes(query);
      let matchesFilter = true;
      if (currentFilter === 'pending') matchesFilter = !isSeen;
      else if (currentFilter === 'seen') matchesFilter = isSeen;

      card.style.display = (matchesSearch && matchesFilter) ? '' : 'none';
    });
  }

  searchInput.addEventListener('input', applyFilters);

  filterPills.querySelectorAll('.btn-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      filterPills.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      applyFilters();
    });
  });

  // Ordenamiento
  function getNum(v, d) { const n = Number(v); return Number.isFinite(n) ? n : d; }
  function sortCards(how) {
    const cards = Array.from(grid.children);
    let cmp;
    if (how === 'title-asc') cmp = (a,b)=> (a.dataset.title||'').localeCompare(b.dataset.title||'');
    else if (how === 'title-desc') cmp = (a,b)=> (b.dataset.title||'').localeCompare(a.dataset.title||'');
    else if (how === 'rank-asc') cmp = (a,b)=> getNum(a.dataset.rank, 9e9) - getNum(b.dataset.rank, 9e9);
    else if (how === 'rank-desc') cmp = (a,b)=> getNum(b.dataset.rank, -1) - getNum(a.dataset.rank, -1);
    else cmp = (a,b)=> (a.dataset.title||'').localeCompare(b.dataset.title||'');
    cards.sort(cmp);
    const frag = document.createDocumentFragment();
    for (const c of cards) frag.appendChild(c);
    grid.innerHTML = '';
    grid.appendChild(frag);
  }
  sortSel.addEventListener('change', ()=> sortCards(sortSel.value));

  // Copiar IDs al portapapeles
  btnCopyIds.addEventListener('click', async () => {
    // Tomar solo los visibles o los pendientes
    const ids = [];
    allCards.forEach(card => {
      const chk = card.querySelector('.chk-seen');
      // Si el filtro actual es 'all' o 'pending', copiamos pendientes. Si es 'seen', copiamos vistos.
      if (currentFilter === 'seen') {
        if (chk && chk.checked) ids.push(card.dataset.id);
      } else {
        if (chk && !chk.checked) ids.push(card.dataset.id);
      }
    });

    const json = JSON.stringify(ids, null, 2);
    try {
      await navigator.clipboard.writeText(json);
      showToast(`📋 ¡${ids.length} IDs copiados al portapapeles!`);
    } catch (e) {
      prompt("Copia los IDs manualmente:", json);
    }
  });

  // Exportar CSV
  btnExport.addEventListener('click', () => {
    const headers = ["titulo","id","url","image_url","visto"];
    const rows = [headers.join(",")];
    allCards.forEach(card => {
      const title = (card.dataset.title || '').replace(/"/g,'""');
      const id = card.dataset.id || '';
      const url = (card.querySelector('.btn-watch')?.getAttribute('href') || ('https://www.netflix.com/title/' + id)).replace(/"/g,'""');
      const img = (card.dataset.img || '').replace(/"/g,'""');
      const chk = card.querySelector('.chk-seen');
      const visto = chk && chk.checked ? "1" : "";
      rows.push(['"'+title+'"', id, '"'+url+'"', '"'+img+'"', visto].join(","));
    });
    const csv = rows.join("\n");
    const blob = new Blob(["\ufeff"+csv], {type:"text/csv;charset=utf-8"});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = "netflix_mylist_actualizado.csv";
    document.body.appendChild(a);
    a.click();
    setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 120);
    showToast("💾 CSV descargado correctamente");
  });

  updateCounters();
  sortCards(sortSel.value);
})();
</script>
</body>
</html>"""
    html = (template
            .replace("__PAGE_TITLE__", _esc_html(page_title))
            .replace("__CARDS__", "\n".join(card_parts)))
    return html

def write_viewer_html(items, out_path: Path, page_title="Netflix My List – Viewer"):
    html = build_simple_viewer_html(items, page_title=page_title)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="HTML de Netflix → CSV + Viewer con 'visto' y export.")
    ap.add_argument("html_file", type=Path, nargs="?", help="HTML de 'Mi Lista' (opcional si usas --csv-in)")
    ap.add_argument("--csv-in", type=Path, help="CSV ya generado para construir solo el viewer")
    ap.add_argument("--out", type=Path, default=Path("netflix_mylist.csv"))
    ap.add_argument("--viewer-out", type=Path, default=Path("netflix_mylist_viewer.html"))
    ap.add_argument("--base-url", default="https://www.netflix.com")
    ap.add_argument("--dedupe", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    # items desde CSV o HTML
    target_csv = args.csv_in
    if not target_csv and args.html_file and args.html_file.suffix.lower() == ".csv":
        target_csv = args.html_file

    if target_csv:
        items = read_items_from_csv(target_csv)
    else:
        if not args.html_file:
            default_csv = Path("netflix_mylist.csv")
            if default_csv.exists():
                print(f"[INFO] Usando archivo existente '{default_csv}'...")
                items = read_items_from_csv(default_csv)
            else:
                raise SystemExit("Pasa un archivo HTML o CSV, o usa --csv-in.")
        else:
            html = args.html_file.read_text(encoding="utf-8", errors="ignore")
            items = parse_html_any(html, base_url=args.base_url)

    # dedupe por id/href
    if args.dedupe:
        seen, deduped = set(), []
        for it in items:
            key = (it.get("id") or it.get("href_original") or "").strip()
            if key and key not in seen:
                seen.add(key); deduped.append(it)
        items = deduped

    # escribir CSV base (con col 'visto' vacía si no existe)
    write_csv(items, args.out)

    # viewer con “visto”
    write_viewer_html(items, args.viewer_out, page_title="Netflix My List – Viewer (Con Visto)")

    print(f"[OK] Items: {len(items)}")
    print(f"[OK] CSV: {args.out.resolve()}")
    print(f"[OK] Viewer: {args.viewer_out.resolve()}")

    if args.open:
        webbrowser.open(args.viewer_out.resolve().as_uri())

if __name__ == "__main__":
    main()
