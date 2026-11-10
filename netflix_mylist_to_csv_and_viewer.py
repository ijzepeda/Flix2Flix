#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# V3 - English Version
import argparse, csv, json, re, webbrowser
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, unquote

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# ---------- Parsing Helpers ----------
def parse_ctx(raw_ctx: str) -> dict:
    if not raw_ctx: return {}
    try:
        return json.loads(unquote(raw_ctx))
    except Exception:
        try:
            return json.loads(unquote(unquote(raw_ctx)))
        except Exception:
            return {}

def extract_video_id(href: str, unified_entity_id: str, ctx: dict) -> str:
    vid = str(ctx.get("video_id") or "").strip()
    if vid.isdigit(): return vid
    if unified_entity_id:
        m = re.search(r":(\d+)$", unified_entity_id)
        if m: return m.group(1)
    if href:
        m = re.search(r"/watch/(\d+)", href)
        if m: return m.group(1)
    return ""

def get_title(anchor, ptrack_div):
    aria = (anchor.get("aria-label") or "").strip()
    if aria: return aria
    fb = ptrack_div.select_one(".fallback-text-container p.fallback-text")
    if fb and fb.text.strip(): return fb.text.strip()
    img = anchor.find("img")
    alt = (img.get("alt") or "").strip() if img else ""
    return alt

# ---------- Main HTML Parser ----------
def parse_html_any(html_content: str, base_url="https://www.netflix.com") -> list:
    if BeautifulSoup is None:
        raise SystemExit(
            "[ERROR] Se requiere la librería 'beautifulsoup4' para procesar archivos HTML.\n"
            "Instálala con: pip install beautifulsoup4\n"
            "Consejo: Si usaste el script de consola 'export_netflix_console.js', ya tienes 'netflix_mylist.csv'.\n"
            "Simplemente ejecuta: python3 netflix_mylist_to_csv_and_viewer.py netflix_mylist.csv --open"
        )
    soup = BeautifulSoup(html_content, "html.parser")
    items = []
    
    # Strategy 1: Legacy Netflix DOM (data-ui-tracking-context)
    ptrack_divs = soup.find_all("div", attrs={"data-ui-tracking-context": True})
    for div in ptrack_divs:
        raw_ctx = div.get("data-ui-tracking-context", "")
        ctx = parse_ctx(raw_ctx)
        
        anchor = div.find("a")
        if not anchor: continue
        href_orig = anchor.get("href") or ""
        href_clean = href_orig.split("?")[0] if href_orig else ""
        url_full = urljoin(base_url, href_clean) if href_clean else ""
        
        unified_id = div.get("data-unified-entity-id") or ""
        video_id = extract_video_id(href_clean, unified_id, ctx)
        if not video_id: continue
        
        title = get_title(anchor, div)
        if not title: title = f"Unknown_{video_id}"
        
        items.append({
            "title": title,
            "id": video_id,
            "url": url_full,
            "seen": ""
        })

    # Strategy 2: Modern Netflix UI (Virtualized carousel / My Netflix hub)
    if not items:
        # Find the "My List" / "Mi lista" section if available, else inspect whole document
        sections = soup.find_all("section")
        target_container = soup
        list_keywords = ["my list", "mi lista", "minha lista", "ma liste", "meine liste"]
        for sec in sections:
            h2 = sec.find("h2")
            if h2 and any(k in h2.get_text().strip().lower() for k in list_keywords):
                target_container = sec
                break

        anchors = target_container.find_all("a", href=True)
        seen_ids = set()
        for a in anchors:
            href = a.get("href", "")
            video_id = ""
            m_jbv = re.search(r"jbv=(\d+)", href)
            m_path = re.search(r"/(?:watch|title)/(\d+)", href)
            if m_jbv:
                video_id = m_jbv.group(1)
            elif m_path:
                video_id = m_path.group(1)
            
            if not video_id or video_id in seen_ids:
                continue
            seen_ids.add(video_id)

            title = (a.get("aria-label") or "").strip()
            if not title:
                img = a.find("img")
                if img:
                    title = (img.get("alt") or "").strip()
            if not title:
                fb = a.select_one(".fallback-text, p, span")
                if fb:
                    title = fb.get_text().strip()
            if not title:
                title = f"Netflix_{video_id}"

            url_full = f"https://www.netflix.com/title/{video_id}"
            items.append({
                "title": title,
                "id": video_id,
                "url": url_full,
                "seen": ""
            })

    return items

# ---------- CSV Readers/Writers ----------
def read_items_from_csv(csv_path: Path) -> list:
    items = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                "title": row.get("title") or row.get("titulo", ""),
                "id": row.get("id", ""),
                "url": row.get("url", ""),
                "seen": row.get("seen") or row.get("visto", "")
            })
    return items

def write_csv(items: list, out_path: Path):
    if not items: return
    keys = ["title", "id", "url", "seen"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(items)

# ---------- HTML Viewer Generator ----------
def write_viewer_html(items: list, out_path: Path, page_title="Netflix My List – Viewer"):
    # Convert dicts to JSON array string to inject into JS safely
    items_json = json.dumps(items, ensure_ascii=False)
    
    html_template = """<!DOCTYPE html>
<html lang="en">
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
  .panel { background:var(--panel); border:1px solid #23304a; border-radius:14px; padding:12px; margin:16px auto; max-width:1200px; display:flex; flex-wrap:wrap; gap:12px; align-items:center; justify-content:space-between; }
  .btn-export { background:var(--text); color:var(--bg); border:none; padding:8px 16px; border-radius:8px; font-weight:600; cursor:pointer; }
  .btn-export:hover { background:#fff; }
  select { background:var(--bg); color:var(--text); border:1px solid var(--btn-stroke); padding:8px; border-radius:8px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:16px; max-width:1200px; margin:0 auto; padding:0 18px 40px; }
  .card { background:var(--card); border:1px solid var(--btn-stroke); border-radius:12px; padding:16px; display:flex; flex-direction:column; gap:12px; }
  .card.seen { opacity: 0.5; }
  .title-row { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; }
  .title { font-size:16px; font-weight:600; line-height:1.3; margin:0; }
  .seen-label { display:flex; align-items:center; gap:6px; font-size:13px; color:var(--muted); cursor:pointer; background:rgba(0,0,0,0.2); padding:4px 8px; border-radius:6px; }
  .seen-label input { margin:0; width:16px; height:16px; accent-color:var(--accent); cursor:pointer; }
  .id-badge { display:inline-block; font-family:monospace; font-size:12px; color:var(--muted); background:rgba(255,255,255,0.05); padding:2px 6px; border-radius:4px; }
  .actions { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:auto; }
  .btn { text-align:center; text-decoration:none; font-size:13px; font-weight:500; padding:8px; border-radius:8px; border:1px solid var(--btn-stroke); color:var(--text); background:var(--btn); transition:all .2s; }
  .btn:hover { background:#1f2a40; }
  .btn-watch { background:var(--text); color:#000; border:none; }
  .btn-watch:hover { background:#fff; }
</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1>__PAGE_TITLE__</h1>
    <div class="sub" id="counter">Loading titles...</div>
  </div>
</header>
<div class="panel">
  <div>
    <label for="sortSel">Sort by: </label>
    <select id="sortSel">
      <option value="rank-asc">Original Order</option>
      <option value="title-asc">A-Z</option>
      <option value="title-desc">Z-A</option>
    </select>
  </div>
  <button class="btn-export" id="btnExport">Export CSV (with Progress)</button>
</div>
<div class="grid" id="grid"></div>

<script>
  // Inject items directly from Python
  const items = __ITEMS_JSON__;
  
  const grid = document.getElementById('grid');
  const sortSel = document.getElementById('sortSel');
  const btnExport = document.getElementById('btnExport');
  const counter = document.getElementById('counter');

  counter.textContent = items.length + " titles found";

  // Render cards
  items.forEach((item, index) => {
    const card = document.createElement('div');
    card.className = 'card' + (item.seen === '1' ? ' seen' : '');
    card.dataset.title = item.title;
    card.dataset.id = item.id;
    card.dataset.rank = index;

    card.innerHTML = `
      <div class="title-row">
        <h2 class="title" title="${item.title}">${item.title}</h2>
        <label class="seen-label">
          <input type="checkbox" class="chk-seen" ${item.seen === '1' ? 'checked' : ''}>
          Seen
        </label>
      </div>
      <div><span class="id-badge">ID: ${item.id}</span></div>
      <div class="actions">
        <a href="https://www.netflix.com/title/${item.id}" target="_blank" rel="noreferrer" class="btn">Title Page ↗</a>
        <a href="https://www.netflix.com/watch/${item.id}" target="_blank" rel="noreferrer" class="btn btn-watch">Watch ▶</a>
      </div>
    `;
    grid.appendChild(card);

    // Toggle seen class on checkbox change
    const chk = card.querySelector('.chk-seen');
    chk.addEventListener('change', (e) => {
      if(e.target.checked) {
        card.classList.add('seen');
      } else {
        card.classList.remove('seen');
      }
    });
  });

  // Sorting logic
  function getNum(val, def) { const n=parseInt(val,10); return isNaN(n)? def : n; }
  function sortCards(how) {
    const cards = Array.from(grid.querySelectorAll('.card'));
    let cmp;
    if (how === 'rank-asc') cmp = (a,b)=> getNum(a.dataset.rank, 999999) - getNum(b.dataset.rank, 999999);
    else if (how === 'title-asc') cmp = (a,b)=> (a.dataset.title||'').localeCompare(b.dataset.title||'');
    else if (how === 'title-desc') cmp = (a,b)=> (b.dataset.title||'').localeCompare(a.dataset.title||'');
    cards.sort(cmp);
    const frag = document.createDocumentFragment();
    for (const c of cards) frag.appendChild(c);
    grid.innerHTML = '';
    grid.appendChild(frag);
  }
  sortSel.addEventListener('change', ()=> sortCards(sortSel.value));

  // Export CSV
  btnExport.addEventListener('click', () => {
    const headers = ["title","id","url","seen"];
    const rows = [headers.join(",")];
    Array.from(grid.querySelectorAll('.card')).forEach(card => {
      const title = (card.dataset.title || '').replace(/"/g,'""');
      const id = card.dataset.id || '';
      const url = (card.querySelector('.btn-watch')?.getAttribute('href') || '').replace(/"/g,'""');
      const chk = card.querySelector('.chk-seen');
      const seen = chk && chk.checked ? "1" : "";
      const line = ['"'+title+'"', id, '"'+url+'"', seen].join(",");
      rows.push(line);
    });
    const csv = rows.join("\\n");
    const blob = new Blob(["\\ufeff"+csv], {type:"text/csv;charset=utf-8"});
    const urlObj = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = urlObj;
    a.download = "netflix_mylist_updated.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(urlObj);
  });
</script>
</body>
</html>"""

    html_content = html_template.replace("__PAGE_TITLE__", page_title).replace("__ITEMS_JSON__", items_json)
    out_path.write_text(html_content, encoding="utf-8")

def apply_viewing_history(items: list, history_csv_path: Path):
    """Marks items as seen if found in Netflix's official ViewingActivity.csv."""
    if not history_csv_path.exists():
        print(f"[WARN] Viewing history file not found: {history_csv_path}")
        return
    history_titles = set()
    with open(history_csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("Title") or row.get("title") or "").strip().lower()
            if title:
                history_titles.add(title)
                # Also add base show name before colons (e.g., "Breaking Bad: Season 1" -> "breaking bad")
                if ":" in title:
                    history_titles.add(title.split(":")[0].strip())

    marked = 0
    for it in items:
        item_title = (it.get("title") or "").strip().lower()
        if item_title in history_titles or any(item_title in ht or ht in item_title for ht in history_titles):
            it["seen"] = "1"
            marked += 1
    print(f"[INFO] Cross-referenced viewing history: {marked} titles marked as seen.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Flix2Flix - Netflix List Exporter & Viewer")
    ap.add_argument("input_file", nargs="?", type=Path, help="HTML file or CSV file with Netflix list")
    ap.add_argument("--csv-in", type=Path, help="Build viewer directly from CSV")
    ap.add_argument("--history-in", type=Path, help="Official NetflixViewingHistory.csv to mark seen titles")
    ap.add_argument("--out", type=Path, default=Path("netflix_mylist.csv"))
    ap.add_argument("--viewer-out", type=Path, default=Path("index.html")) # Default for GitHub Pages
    ap.add_argument("--base-url", default="https://www.netflix.com")
    ap.add_argument("--dedupe", action="store_true")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    items = []
    
    # 1. Determine input source (explicit --csv-in or positional input_file)
    target_csv = args.csv_in
    if not target_csv and args.input_file and args.input_file.suffix.lower() == ".csv":
        target_csv = args.input_file

    if target_csv:
        if not target_csv.exists():
            raise SystemExit(f"CSV file not found: {target_csv}")
        items = read_items_from_csv(target_csv)
    elif args.input_file:
        if not args.input_file.exists():
            raise SystemExit(f"Input file not found: {args.input_file}")
        html = args.input_file.read_text(encoding="utf-8", errors="ignore")
        items = parse_html_any(html, base_url=args.base_url)
    else:
        # Default fallback: check if netflix_mylist.csv exists in current folder
        default_csv = Path("netflix_mylist.csv")
        if default_csv.exists():
            print(f"[INFO] No input specified, using existing '{default_csv}'...")
            items = read_items_from_csv(default_csv)
        else:
            raise SystemExit("Pass an HTML/CSV file or use --csv-in.")

    # 2. Cross-reference with viewing activity if provided
    if args.history_in:
        apply_viewing_history(items, args.history_in)

    # 3. Deduplicate by video ID
    if args.dedupe:
        seen, deduped = set(), []
        for it in items:
            key = (it.get("id") or "").strip()
            if key and key not in seen:
                seen.add(key); deduped.append(it)
        items = deduped

    # Only write CSV if input was HTML, or if explicitly requested/modified
    if not target_csv or args.history_in or args.dedupe:
        write_csv(items, args.out)
        print(f" -> CSV saved to {args.out}")

    write_viewer_html(items, args.viewer_out)

    print(f"[OK] {len(items)} items processed.")
    print(f" -> Viewer saved to {args.viewer_out}")

    if args.open:
        webbrowser.open(args.viewer_out.absolute().as_uri())