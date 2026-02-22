#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# V3
import argparse, csv, json, re, webbrowser
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from bs4 import BeautifulSoup

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
    soup = BeautifulSoup(html, "lxml")
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
    # Fallback
    if not items:
        for a in soup.select('a[href*="/watch/"]'):
            href = a.get("href") or ""
            m = re.search(r"/watch/(\d+)", href)
            if not m: continue
            vid = m.group(1)
            url = urljoin(base_url, f"/watch/{vid}")
            titulo = (a.get("aria-label") or (a.text or "")).strip() or "(sin título)"
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
            items.append(dict(row))
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
    # Render cards (incluye checkbox visto y 2 botones)
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
        card.append('<div class="card" data-title="' + title + '" data-rank="' + rank + '" data-id="' + vid + '">')
        if image:
            card.append('  <img class="poster" src="' + image + '" alt="' + title + '">')
        card.append('  <div class="card-body">')
        card.append('    <div class="title">' + title + '</div>')
        if vid:
            card.append('    <div class="idline">ID: ' + vid + '</div>')
        # checkbox visto
        card.append('    <label class="seen"><input type="checkbox" class="chk-seen" ' + ('checked' if visto=="true" else '') + '> Marcado como visto</label>')
        # botones
        if watch_url or title_url:
            card.append('    <div class="row-actions">')
            if title_url:
                card.append('      <a class="btn btn-secondary btn-title" href="' + title_url + '" target="_blank" rel="noopener noreferrer">')
                card.append('        <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" class="ext-icon"><path d="M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42 9.3-9.29H14V3z"></path><path d="M5 5h6v2H7v10h10v-4h2v6H5z"></path></svg>')
                card.append('      </a>')
            if watch_url:
                card.append('      <a class="btn btn-primary btn-watch" href="' + watch_url + '" target="_blank" rel="noopener noreferrer">Ver en Netflix</a>')
            card.append('    </div>')
        card.append('  </div>')
        card.append('</div>')
        card_parts.append("\n".join(card))

    template = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__PAGE_TITLE__</title>
<style>
  :root { --bg:#0b0d12; --panel:#121725; --text:#e5e7eb; --muted:#9aa0a6; --accent:#e50914; --card:#1a2031; --btn:#141c2c; --btn-stroke:#2a3550; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Noto Sans, Helvetica Neue, Arial; }
  header { position:sticky; top:0; background:rgba(11,13,18,.9); border-bottom:1px solid #222a3b; backdrop-filter: blur(4px); z-index:10; }
  .wrap { max-width:1200px; margin:0 auto; padding:14px 18px; }
  h1 { margin:0; font-size:22px; }
  .sub { color:var(--muted); font-size:13px; }
  .panel { background:var(--panel); border:1px solid #23304a; border-radius:14px; padding:12px; margin:16px 0; }
  .controls { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  select, button { padding:8px 10px; border-radius:10px; border:1px solid var(--btn-stroke); background:#0f1625; color:var(--text); font-size:14px; }
  .grid { display:grid; gap:12px; grid-template-columns: repeat(6, minmax(0,1fr)); padding-bottom:30px; }
  @media (max-width:1200px) { .grid { grid-template-columns: repeat(5,1fr); } }
  @media (max-width:1000px) { .grid { grid-template-columns: repeat(4,1fr); } }
  @media (max-width:800px)  { .grid { grid-template-columns: repeat(3,1fr); } }
  @media (max-width:600px)  { .grid { grid-template-columns: repeat(2,1fr); } }
  @media (max-width:420px)  { .grid { grid-template-columns: repeat(1,1fr); } }
  .card { background:var(--card); border:1px solid #2a3550; border-radius:14px; overflow:hidden; }
  .poster { display:block; width:100%; aspect-ratio:16/9; object-fit:cover; background:#0e1524; }
  .card-body { padding:10px 12px; }
  .title { font-size:14px; font-weight:700; margin:0 0 4px; }
  .idline { font-size:12px; color:var(--muted); }
  .seen { display:flex; gap:8px; align-items:center; font-size:13px; margin-top:6px; color:#d5d9e3; }
  .row-actions { display:inline-flex; gap:8px; nowrap:block; margin-top:8px; }
  .btn { display:inline-flex; align-items:center; gap:8px; padding:5px 7px; border-radius:10px; border:1px solid var(--btn-stroke); background: var(--btn); color:#e5e7eb; font-weight:700; text-decoration:none; }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-secondary { background: #99a3ba; }
  .ext-icon { width: 16px; height: 16px; }
</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1>__PAGE_TITLE__</h1>
    <div class="sub">Marca “visto”, ordena y exporta un CSV actualizado.</div>
  </div>
</header>

<main class="wrap">
  <section class="panel">
    <div class="controls">
      <label for="sort">Ordenar por:</label>
      <select id="sort">
        <option value="title-asc">Título A→Z</option>
        <option value="title-desc">Título Z→A</option>
        <option value="rank-asc">Rank ↑</option>
        <option value="rank-desc">Rank ↓</option>
      </select>
      <button id="btnExport">Exportar CSV actualizado</button>
    </div>
  </section>

  <section id="grid" class="grid">
    __CARDS__
  </section>
</main>

<script>
(function(){
  const grid = document.getElementById('grid');
  const sortSel = document.getElementById('sort');
  const btnExport = document.getElementById('btnExport');
  const STORAGE_KEY = 'netflix_mylist_seen_v1';

  // Cargar estado visto desde localStorage
  function loadSeenMap() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch(e) { return {}; }
  }
  function saveSeenMap(map) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  }

  const seenMap = loadSeenMap();

  // Inicializar checkboxes según localStorage
  Array.from(grid.querySelectorAll('.card')).forEach(card => {
    const id = card.dataset.id || card.dataset.title;
    const chk = card.querySelector('.chk-seen');
    if (!id || !chk) return;
    if (seenMap[id]) chk.checked = true;

    // Cambios de checkbox -> persistir
    chk.addEventListener('change', () => {
      if (chk.checked) seenMap[id] = true;
      else delete seenMap[id];
      saveSeenMap(seenMap);
    });

    // Click en botones watch/title -> marcar visto
    card.querySelectorAll('.btn-watch, .btn-title').forEach(a => {
      a.addEventListener('click', () => {
        chk.checked = true;
        seenMap[id] = true;
        saveSeenMap(seenMap);
      });
    });
  });

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
  sortCards(sortSel.value);

  // Exportar CSV con columna "visto"
  btnExport.addEventListener('click', () => {
    const headers = ["titulo","id","url","visto"];
    const rows = [headers.join(",")];
    Array.from(grid.querySelectorAll('.card')).forEach(card => {
      const title = (card.dataset.title || '').replace(/"/g,'""');
      const id = card.dataset.id || '';
      const url = (card.querySelector('.btn-watch')?.getAttribute('href') || '').replace(/"/g,'""');
      const chk = card.querySelector('.chk-seen');
      const visto = chk && chk.checked ? "1" : "";
      const line = ['"'+title+'"', id, '"'+url+'"', visto].join(",");
      rows.push(line);
    });
    const csv = rows.join("\\n");
    const blob = new Blob(["\\ufeff"+csv], {type:"text/csv;charset=utf-8"});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = "netflix_mylist_actualizado.csv";
    document.body.appendChild(a);
    a.click();
    setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 120);
  });
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
    if args.csv_in:
        items = read_items_from_csv(args.csv_in)
    else:
        if not args.html_file:
            raise SystemExit("Pasa un HTML o usa --csv-in.")
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
