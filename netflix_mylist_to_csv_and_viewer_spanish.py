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
    # Cargar scripts para integrarlos en el Hub Todo en Uno
    export_script = ""
    for cand in ("1-export_netflix_console.js", "export_netflix_console.js"):
        p = Path(cand)
        if p.exists():
            export_script = p.read_text(encoding="utf-8")
            break

    import_script = ""
    for cand in ("4-import_netflix_console.js", "import_netflix_console.js"):
        p = Path(cand)
        if p.exists():
            import_script = p.read_text(encoding="utf-8")
            break

    bookmarklet_url = ""
    for cand in ("1-bookmarklet.txt", "bookmarklet.txt"):
        p = Path(cand)
        if p.exists():
            txt = p.read_text(encoding="utf-8")
            m = re.search(r"javascript:(?:.*?)(?=\n```|$)", txt, re.DOTALL)
            if m:
                bookmarklet_url = "javascript:" + m.group(0).replace("javascript:", "").strip()
            break

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

        # Verificar si existe imagen en caché local ./imagenes/
        local_src = ""
        if vid:
            for ext in (".jpg", ".webp", ".png", ".jpeg"):
                cand = Path("imagenes") / f"{vid}{ext}"
                if cand.exists():
                    local_src = f"imagenes/{vid}{ext}"
                    break

        img_src = local_src if local_src else image

        card = []
        card.append(f'<div class="card{" seen-card" if visto=="true" else ""}" data-title="{title}" data-rank="{rank}" data-id="{vid}" data-seen="{visto}" data-img="{image}">')
        
        # Imagen con soporte de referrerpolicy, caché local y fallback
        card.append('  <div class="poster-container">')
        if img_src:
            fallback_attr = f' data-fallback="{image}"' if (local_src and image) else ''
            onerror_code = "if(this.dataset.fallback && this.src !== this.dataset.fallback){ this.src = this.dataset.fallback; } else { this.style.display=\\'none\\'; this.nextElementSibling.style.display=\\'flex\\'; }"
            card.append(f'    <img class="poster" src="{img_src}"{fallback_attr} alt="{title}" loading="lazy" referrerpolicy="no-referrer" onerror="{onerror_code}">')
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
  .btn-hub-highlight { background: linear-gradient(135deg, #e50914, #b91c1c); border-color: #ef4444; color: #fff; font-weight: 700; box-shadow: 0 2px 10px rgba(229,9,20,0.35); }
  .btn-hub-highlight:hover { background: linear-gradient(135deg, #f40612, #dc2626); }

  /* Hub Dialog Modal */
  .hub-dialog {
    background: #0f1422;
    color: var(--text);
    border: 1px solid #2a3854;
    border-radius: 16px;
    padding: 0;
    max-width: 820px;
    width: 94vw;
    max-height: 90vh;
    box-shadow: 0 25px 60px rgba(0,0,0,0.9), 0 0 30px rgba(229,9,20,0.15);
    outline: none;
    overflow: hidden;
  }
  .hub-dialog::backdrop {
    background: rgba(5, 7, 13, 0.8);
    backdrop-filter: blur(8px);
  }
  .hub-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 22px;
    background: #141c2e;
    border-bottom: 1px solid #222e47;
  }
  .hub-header h2 { margin: 0; font-size: 18px; font-weight: 800; display: flex; align-items: center; gap: 8px; color: #fff; }
  .hub-header .hub-sub { font-size: 12px; color: var(--muted); margin-top: 3px; }
  .btn-close-dialog { background: #1c263d; border: 1px solid #2d3b5b; color: var(--muted); border-radius: 8px; width: 32px; height: 32px; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .2s; }
  .btn-close-dialog:hover { background: #e50914; color: #fff; border-color: #e50914; }

  .hub-tabs {
    display: flex;
    background: #0d121f;
    border-bottom: 1px solid #222e47;
    padding: 0 16px;
    overflow-x: auto;
  }
  .hub-tab-btn {
    padding: 12px 18px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--muted);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all .2s;
    white-space: nowrap;
  }
  .hub-tab-btn:hover { color: #fff; }
  .hub-tab-btn.active { color: #e50914; border-bottom-color: #e50914; }

  .hub-body {
    padding: 22px;
    max-height: calc(90vh - 140px);
    overflow-y: auto;
  }
  .hub-panel { display: none; }
  .hub-panel.active { display: block; animation: fadeIn .2s; }

  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

  .task-card {
    background: #151d2f;
    border: 1px solid #25334e;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 16px;
  }
  .task-card h3 { margin: 0 0 8px 0; font-size: 15px; color: #f1f5f9; display: flex; align-items: center; gap: 8px; }
  .task-card p { margin: 0 0 14px 0; font-size: 13px; color: var(--muted); line-height: 1.5; }

  .code-pill {
    background: #0a0e18;
    border: 1px solid #25334e;
    border-radius: 8px;
    padding: 10px 14px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
    color: #38bdf8;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }

  .drop-zone {
    border: 2px dashed #2a3a5a;
    border-radius: 12px;
    padding: 28px 16px;
    text-align: center;
    background: #0c111d;
    cursor: pointer;
    transition: all .2s;
  }
  .drop-zone:hover, .drop-zone.drag-over {
    border-color: #3b82f6;
    background: #111a2e;
  }

  .bookmarklet-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 20px;
    background: #e50914;
    color: #fff !important;
    font-weight: 700;
    font-size: 12px;
    text-decoration: none;
    box-shadow: 0 4px 10px rgba(229,9,20,0.4);
    cursor: grab;
  }

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
        <button id="btnOpenHub" type="button" class="btn-action btn-hub-highlight" title="Centro de Tareas Todo en Uno (1, 2, 3 y 4)">🛠️ Tareas (1-2-3-4)</button>
        <button id="btnCopyIds" class="btn-action" title="Copia los IDs de los títulos pendientes para importar en tu nueva cuenta">📋 Copiar IDs</button>
        <button id="btnExport" class="btn-action btn-export-highlight">💾 Exportar CSV</button>
      </div>
    </div>
  </section>

  <section id="grid" class="grid">
    __CARDS__
  </section>
</main>

<dialog id="hubDialog" class="hub-dialog">
  <div class="hub-header">
    <div>
      <h2>🎬 Flix2Flix: Centro de Control Todo en Uno</h2>
      <div class="hub-sub">Ejecuta y gestiona tus 4 tareas de migración desde este mismo visor</div>
    </div>
    <button type="button" class="btn-close-dialog" id="btnCloseHub" aria-label="Cerrar">✕</button>
  </div>

  <div class="hub-tabs">
    <button type="button" class="hub-tab-btn active" data-target="panelTab1">📥 1. Exportar</button>
    <button type="button" class="hub-tab-btn" data-target="panelTab2">🔄 2. Fusionar CSV</button>
    <button type="button" class="hub-tab-btn" data-target="panelTab3">🖼️ 3. Caché Portadas</button>
    <button type="button" class="hub-tab-btn" data-target="panelTab4">🚀 4. Importar Cuenta Nueva</button>
  </div>

  <div class="hub-body">
    <!-- PANEL 1: EXPORTAR -->
    <div id="panelTab1" class="hub-panel active">
      <div class="task-card">
        <h3><span>⚡</span> Opción A: Script de Consola (Recomendado)</h3>
        <p>Avanza el carrusel horizontal de Netflix de forma automática y descarga <code>netflix_mylist.csv</code> en 5 segundos sin instalar nada.</p>
        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:12px;">
          <button type="button" class="btn btn-primary" id="btnCopyExtractor" style="font-size:13px; padding:9px 16px;">📋 Copiar Script Extractor (1 Clic)</button>
          <a href="https://www.netflix.com/browse/my-list" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="font-size:13px; padding:9px 16px;">↗️ Ir a Netflix Mi Lista</a>
        </div>
        <ol style="margin:0; padding-left:18px; font-size:12px; color:var(--muted); line-height:1.6;">
          <li>Haz clic en <strong>"Copiar Script Extractor"</strong>.</li>
          <li>Abre tu cuenta vieja de Netflix en <strong>netflix.com/browse/my-list</strong>.</li>
          <li>Abre la consola (<code>Cmd+Option+J</code> en Mac / <code>Ctrl+Shift+J</code> en Windows), pega (<code>Cmd+V</code>) y presiona <code>Enter</code>.</li>
        </ol>
      </div>

      <div class="task-card">
        <h3><span>⭐</span> Opción B: Marcador de 1 Clic (Bookmarklet)</h3>
        <p>Arrastra este botón a tu barra de favoritos/marcadores del navegador. Al estar en Netflix, solo haz un clic sobre él.</p>
        <div>
          <a class="bookmarklet-pill" href="__BOOKMARKLET_URL__" onclick="alert('¡Arrastra este botón a tu barra de marcadores/favoritos del navegador!'); return false;">⭐ Exportar Netflix</a>
        </div>
      </div>
    </div>

    <!-- PANEL 2: FUSIONAR CSV -->
    <div id="panelTab2" class="hub-panel">
      <div class="task-card">
        <h3><span>📥</span> Fusión Directa en este Visor (Sin Terminal)</h3>
        <p>Arrastra aquí el archivo <code>netflix_mylist.csv</code> recién descargado. Se incorporarán los títulos nuevos de inmediato en esta misma pantalla conservando tus vistos.</p>
        
        <div class="drop-zone" id="csvDropZone">
          <div style="font-size:32px; margin-bottom:6px;">📥</div>
          <div style="font-weight:700; font-size:14px; color:#f1f5f9;">Arrastra aquí tu nuevo CSV descargado</div>
          <div style="font-size:12px; color:var(--muted); margin-top:4px;">o haz clic aquí para examinar tus archivos</div>
          <input type="file" id="csvFileInput" accept=".csv" style="display:none">
        </div>

        <div id="hubMergeStatus" style="display:none; margin-top:14px; background:#064e3b; border:1px solid #059669; border-radius:8px; padding:12px; font-size:13px; color:#a7f3d0;">
          <div id="hubMergeSummary"></div>
          <div style="margin-top:10px;">
            <button type="button" class="btn btn-export-highlight" id="btnDownloadMergedCsv">💾 Descargar CSV Actualizado</button>
          </div>
        </div>
      </div>

      <div class="task-card">
        <h3><span>💻</span> Alternativa por Terminal (Python)</h3>
        <p>Si prefieres ejecutar la fusión desde la terminal:</p>
        <div class="code-pill">
          <span>python3 2-merge_csv.py</span>
          <button type="button" class="btn btn-secondary" id="btnCopyMergeCmd" style="padding:4px 8px; font-size:11px;">📋 Copiar</button>
        </div>
      </div>
    </div>

    <!-- PANEL 3: CACHE DE IMÁGENES -->
    <div id="panelTab3" class="hub-panel">
      <div class="task-card">
        <h3><span>🖼️</span> Estado de Portadas</h3>
        <p>Descarga las carátulas en tu disco local (<code>./imagenes/</code>) para que tu lista cargue al instante y funcione <strong>100% offline (sin internet)</strong>.</p>
        <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:14px;">
          <span class="stat-pill"><strong id="hubImgCount">0</strong> con portada oficial</span>
          <span class="stat-pill stat-seen">Modo híbrido (Local + CDN)</span>
        </div>
        <div class="code-pill">
          <span>python3 3-download_images.py</span>
          <button type="button" class="btn btn-secondary" id="btnCopyDownloadCmd" style="padding:4px 8px; font-size:11px;">📋 Copiar Comando</button>
        </div>
        <div style="font-size:12px; color:var(--muted); line-height:1.5;">
          ℹ️ Este comando descargará las imágenes a la carpeta <code>./imagenes/</code> a máxima velocidad con múltiples conexiones simultáneas y regenerará este visor automáticamente.
        </div>
      </div>
    </div>

    <!-- PANEL 4: IMPORTAR A NUEVA CUENTA -->
    <div id="panelTab4" class="hub-panel">
      <div class="task-card">
        <h3><span>🚀</span> Sincronizador Automatizado Anti-Bloqueo</h3>
        <p>Genera y copia el script con tus títulos ya incorporados para ejecutarlos en tu nueva cuenta de Netflix con ritmo humano de seguridad.</p>

        <div style="margin-bottom:16px; background:#0b0f19; border:1px solid #23304a; border-radius:10px; padding:12px;">
          <div style="font-weight:700; margin-bottom:8px; font-size:13px; color:#cbd5e1;">¿Qué títulos deseas importar?</div>
          <label style="display:block; margin-bottom:6px; cursor:pointer; font-size:13px;">
            <input type="radio" name="importScope" value="pending" checked style="accent-color:var(--accent);">
            <strong>Solo títulos pendientes</strong> (<span id="hubPendingCount">0</span> títulos) <span style="color:#22c55e;">[Recomendado]</span>
          </label>
          <label style="display:block; cursor:pointer; font-size:13px;">
            <input type="radio" name="importScope" value="all" style="accent-color:var(--accent);">
            <strong>Toda mi lista completa</strong> (<span id="hubTotalCount">0</span> títulos)
          </label>
        </div>

        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px;">
          <button type="button" class="btn btn-primary" id="btnCopyImporter" style="font-size:13px; padding:10px 18px; font-weight:700;">🚀 Copiar Script con mis IDs (1 Clic)</button>
          <a href="https://www.netflix.com/browse" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="font-size:13px; padding:10px 18px;">↗️ Abrir Netflix en Cuenta Nueva</a>
        </div>

        <ol style="margin:0; padding-left:18px; font-size:12px; color:var(--muted); line-height:1.6;">
          <li>Haz clic en <strong>"Copiar Script con mis IDs"</strong> (ya tiene tus títulos incrustados).</li>
          <li>Inicia sesión en tu <strong>cuenta nueva de Netflix</strong> en el navegador.</li>
          <li>Abre la consola (<code>Cmd+Option+J</code> / <code>Ctrl+Shift+J</code>), pega (<code>Cmd+V</code>) y presiona <code>Enter</code>.</li>
          <li>Aparecerá un panel flotante en Netflix que irá agregando cada título con barra de progreso en vivo y botones de pausa.</li>
        </ol>
      </div>
    </div>
  </div>
</dialog>

<div class="toast" id="toast">Copiado al portapapeles</div>

<script>
(function(){
  const SCRIPT_EXPORT = __SCRIPT_EXPORT_JSON__;
  const SCRIPT_IMPORT = __SCRIPT_IMPORT_JSON__;

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

  // Helper para construir tarjetas dinámicas (fusión en navegador)
  function createCardElement(item) {
    const card = document.createElement('div');
    const title = item.title || '(sin título)';
    const id = item.id || '';
    const img = item.img || '';
    const visto = item.visto ? 'true' : 'false';

    card.className = 'card' + (visto === 'true' ? ' seen-card' : '');
    card.dataset.title = title;
    card.dataset.id = id;
    card.dataset.seen = visto;
    card.dataset.img = img;
    card.dataset.rank = '999999';

    const watchUrl = `https://www.netflix.com/watch/${id}`;
    const titleUrl = `https://www.netflix.com/title/${id}`;

    let posterHtml = '';
    if (img) {
      posterHtml = `
        <img class="poster" src="${img}" alt="${title}" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
        <div class="poster-placeholder" style="display:none;"><span class="placeholder-icon">🎬</span><span class="placeholder-title">${title}</span></div>
      `;
    } else {
      posterHtml = `<div class="poster-placeholder"><span class="placeholder-icon">🍿</span><span class="placeholder-title">${title}</span></div>`;
    }

    card.innerHTML = `
      <div class="poster-container">${posterHtml}</div>
      <div class="card-body">
        <div class="title" title="${title}">${title}</div>
        <div class="idline">ID: ${id}</div>
        <label class="seen"><input type="checkbox" class="chk-seen" ${visto === 'true' ? 'checked' : ''}> Visto</label>
        <div class="row-actions">
          <a class="btn btn-secondary btn-title" href="${titleUrl}" target="_blank" rel="noopener noreferrer" title="Ficha en Netflix">
            <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" class="ext-icon"><path d="M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42 9.3-9.29H14V3z"></path><path d="M5 5h6v2H7v10h10v-4h2v6H5z"></path></svg>
          </a>
          <a class="btn btn-primary btn-watch" href="${watchUrl}" target="_blank" rel="noopener noreferrer">Ver</a>
        </div>
      </div>
    `;

    const chk = card.querySelector('.chk-seen');
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

    return card;
  }

  // Inicializar checkboxes y listeners en tarjetas iniciales
  const allCards = Array.from(grid.querySelectorAll('.card'));
  
  allCards.forEach(card => {
    const id = card.dataset.id;
    const chk = card.querySelector('.chk-seen');
    if (!id || !chk) return;

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

    const hubPending = document.getElementById('hubPendingCount');
    const hubTotal = document.getElementById('hubTotalCount');
    const hubImg = document.getElementById('hubImgCount');
    if (hubPending) hubPending.textContent = pending;
    if (hubTotal) hubTotal.textContent = total;
    if (hubImg) {
      const withImg = allCards.filter(c => c.dataset.img && c.dataset.img.trim()).length;
      hubImg.textContent = withImg;
    }
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
    const ids = [];
    allCards.forEach(card => {
      const chk = card.querySelector('.chk-seen');
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
    const csv = rows.join("\\n");
    const blob = new Blob(["\\ufeff" + csv], {type:"text/csv;charset=utf-8"});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = "netflix_mylist_actualizado.csv";
    document.body.appendChild(a);
    a.click();
    setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 120);
    showToast("💾 CSV descargado correctamente");
  });

  // ========== CONTROLADOR DEL HUB TODO EN UNO ==========
  const hubDialog = document.getElementById('hubDialog');
  const btnOpenHub = document.getElementById('btnOpenHub');
  const btnCloseHub = document.getElementById('btnCloseHub');

  if (btnOpenHub && hubDialog) {
    btnOpenHub.addEventListener('click', () => {
      updateCounters();
      hubDialog.showModal();
    });
  }
  if (btnCloseHub && hubDialog) {
    btnCloseHub.addEventListener('click', () => hubDialog.close());
    hubDialog.addEventListener('click', (e) => {
      if (e.target === hubDialog) hubDialog.close();
    });
  }

  // Pestañas del Hub
  document.querySelectorAll('.hub-tab-btn').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.hub-tab-btn').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.hub-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const target = document.getElementById(tab.dataset.target);
      if (target) target.classList.add('active');
    });
  });

  // Tarea 1: Copiar Extractor
  document.getElementById('btnCopyExtractor')?.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(SCRIPT_EXPORT);
      showToast("📋 ¡Script Extractor copiado al portapapeles!");
    } catch(e) {
      prompt("Copia el script manualmente:", SCRIPT_EXPORT);
    }
  });

  // Tarea 2: Fusión de CSV en navegador
  const dropZone = document.getElementById('csvDropZone');
  const fileInput = document.getElementById('csvFileInput');
  if (dropZone && fileInput) {
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      if (e.dataTransfer.files.length) handleCsvFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length) handleCsvFile(fileInput.files[0]);
    });
  }

  function handleCsvFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => mergeCsvContent(e.target.result);
    reader.readAsText(file);
  }

  function mergeCsvContent(csvText) {
    const lines = csvText.split(/\\r?\\n/).filter(l => l.trim().length > 0);
    if (lines.length < 2) return;

    const headers = lines[0].split(',').map(h => h.replace(/^["'\\s]+|["'\\s]+$/g, '').toLowerCase());
    const idIdx = headers.indexOf('id');
    let titleIdx = headers.indexOf('titulo');
    if (titleIdx === -1) titleIdx = headers.indexOf('title');
    let imgIdx = headers.indexOf('image_url');
    if (imgIdx === -1) imgIdx = headers.indexOf('image');
    let seenIdx = headers.indexOf('visto');
    if (seenIdx === -1) seenIdx = headers.indexOf('seen');

    if (idIdx === -1) {
      alert("El archivo CSV no contiene la columna 'id'.");
      return;
    }

    const existingIds = new Set(allCards.map(c => c.dataset.id));
    let newAdded = 0;
    let duplicates = 0;

    for (let i = 1; i < lines.length; i++) {
      const row = [];
      const re = /(?:^|,)(?:"([^"]*(?:""[^"]*)*)"|([^,]*))/g;
      let m;
      while ((m = re.exec(lines[i])) !== null) {
        let val = m[1] !== undefined ? m[1].replace(/""/g, '"') : m[2];
        row.push((val || '').trim());
      }

      const vid = row[idIdx] || '';
      if (!vid) continue;

      const title = (titleIdx !== -1 ? row[titleIdx] : '') || ('Netflix_' + vid);
      const img = (imgIdx !== -1 ? row[imgIdx] : '') || '';
      const isSeenVal = (seenIdx !== -1 ? row[seenIdx] : '').toLowerCase();
      const isSeen = ['1', 'true', 'yes', 'si', 'sí', 'x'].includes(isSeenVal);

      if (existingIds.has(vid)) {
        duplicates++;
        if (isSeen) {
          const existingCard = allCards.find(c => c.dataset.id === vid);
          if (existingCard) {
            const chk = existingCard.querySelector('.chk-seen');
            if (chk && !chk.checked) {
              chk.checked = true;
              existingCard.classList.add('seen-card');
              existingCard.dataset.seen = "true";
              seenMap[vid] = true;
            }
          }
        }
      } else {
        newAdded++;
        existingIds.add(vid);
        const newCard = createCardElement({ id: vid, title: title, img: img, visto: isSeen });
        grid.appendChild(newCard);
        allCards.push(newCard);
        if (isSeen) seenMap[vid] = true;
      }
    }

    saveSeenMap(seenMap);
    updateCounters();
    applyFilters();

    const statusBox = document.getElementById('hubMergeStatus');
    const summaryBox = document.getElementById('hubMergeSummary');
    if (statusBox && summaryBox) {
      statusBox.style.display = 'block';
      summaryBox.innerHTML = `<strong>¡Fusión exitosa!</strong> +${newAdded} nuevos títulos agregados, ${duplicates} ya existentes actualizados.<br>Total actual en tu lista: <strong>${allCards.length} títulos</strong>.`;
    }
    showToast(`🎉 +${newAdded} títulos agregados a tu lista`);
  }

  document.getElementById('btnDownloadMergedCsv')?.addEventListener('click', () => {
    btnExport.click();
  });
  document.getElementById('btnCopyMergeCmd')?.addEventListener('click', async () => {
    await navigator.clipboard.writeText('python3 2-merge_csv.py');
    showToast("📋 Comando 'python3 2-merge_csv.py' copiado");
  });

  // Tarea 3: Copiar comando de descarga de imágenes
  document.getElementById('btnCopyDownloadCmd')?.addEventListener('click', async () => {
    await navigator.clipboard.writeText('python3 3-download_images.py');
    showToast("📋 Comando 'python3 3-download_images.py' copiado");
  });

  // Tarea 4: Copiar Script de Importación con IDs embebidos
  document.getElementById('btnCopyImporter')?.addEventListener('click', async () => {
    const scope = document.querySelector('input[name="importScope"]:checked')?.value || 'pending';
    const targetIds = [];
    allCards.forEach(c => {
      const isSeen = c.querySelector('.chk-seen')?.checked;
      const id = c.dataset.id;
      if (!id) return;
      if (scope === 'pending') {
        if (!isSeen) targetIds.push(id);
      } else {
        targetIds.push(id);
      }
    });

    let code = SCRIPT_IMPORT;
    const jsonIds = JSON.stringify(targetIds, null, 4);
    code = code.replace(/const mis_ids = \\\\\\[[\\s\\S]*?\\\\\\];/, `const mis_ids = ${jsonIds};`);

    try {
      await navigator.clipboard.writeText(code);
      showToast(`🚀 ¡Script copiado con ${targetIds.length} títulos listos para importar!`);
    } catch(e) {
      prompt("Copia el script manualmente:", code);
    }
  });

  updateCounters();
  sortCards(sortSel.value);
})();
</script>
</body>
</html>"""
    html = (template
            .replace("__PAGE_TITLE__", _esc_html(page_title))
            .replace("__CARDS__", "\n".join(card_parts))
            .replace("__SCRIPT_EXPORT_JSON__", json.dumps(export_script, ensure_ascii=False))
            .replace("__SCRIPT_IMPORT_JSON__", json.dumps(import_script, ensure_ascii=False))
            .replace("__BOOKMARKLET_URL__", _esc_html(bookmarklet_url)))
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
