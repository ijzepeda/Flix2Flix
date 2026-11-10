#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flix2Flix - Merge CSV Backups & Update Viewer

Combina un respaldo previo de Netflix (conservando el estado de "visto")
con un nuevo respaldo exportado, deduplica por ID y regenera index.html.
"""

import argparse
import csv
from pathlib import Path
import sys
import webbrowser

from netflix_mylist_to_csv_and_viewer_spanish import (
    CSV_FIELDS,
    build_simple_viewer_html,
    write_viewer_html,
)

def build_image_cache() -> dict:
    """
    Compila un mapa de ID -> image_url a partir de todos los respaldos existentes.
    Permite restaurar las portadas aunque un archivo intermedio las haya omitido.
    """
    cache = {}
    sources = [
        Path("netflix_mylist.csv"),
        Path("netflix_mylist_actualizado.csv"),
    ]
    backups_dir = Path("BACKUPS")
    if backups_dir.exists():
        sources.extend(sorted(backups_dir.glob("*.csv")))

    for p in sources:
        if not p.exists():
            continue
        try:
            with p.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vid = str(row.get("id") or "").strip()
                    img = str(row.get("image_url") or row.get("image") or "").strip()
                    if vid and img and vid not in cache:
                        cache[vid] = img
        except Exception:
            continue
    return cache

def normalize_row(row: dict, image_cache: dict = None) -> dict:
    vid = str(row.get("id") or "").strip()
    titulo = (row.get("titulo") or row.get("title") or "").strip()
    if not titulo:
        titulo = f"Netflix_{vid}" if vid else "Sin título"

    url = (row.get("url") or "").strip()
    if not url and vid:
        url = f"https://www.netflix.com/title/{vid}"

    image_url = (row.get("image_url") or row.get("image") or "").strip()
    if not image_url and image_cache and vid in image_cache:
        image_url = image_cache[vid]

    visto_val = str(row.get("visto") or row.get("seen") or "").strip().lower()
    visto = "1" if visto_val in ("1", "true", "yes", "si", "sí", "x") else ""

    item = {k: row.get(k, "") for k in CSV_FIELDS}
    item["id"] = vid
    item["titulo"] = titulo
    item["url"] = url
    item["image_url"] = image_url
    item["visto"] = visto
    return item

def merge_csv_files(base_path: Path, new_path: Path, image_cache: dict = None) -> tuple[list, dict]:
    merged = {}
    order = []

    # 1. Cargar base existente
    if base_path.exists():
        with base_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = normalize_row(row, image_cache=image_cache)
                vid = item["id"]
                if vid:
                    merged[vid] = item
                    order.append(vid)

    base_count = len(merged)
    base_seen = sum(1 for x in merged.values() if x["visto"] == "1")

    # 2. Combinar nuevo archivo
    new_added = 0
    new_duplicates = 0

    if new_path.exists():
        with new_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = normalize_row(row, image_cache=image_cache)
                vid = item["id"]
                if not vid:
                    continue

                if vid in merged:
                    new_duplicates += 1
                    # Conservar estado de visto
                    if item["visto"] == "1":
                        merged[vid]["visto"] = "1"
                    # Si el nuevo tiene título más descriptivo, actualizarlo
                    if (not merged[vid]["titulo"] or merged[vid]["titulo"].startswith("Netflix_")) and item["titulo"]:
                        merged[vid]["titulo"] = item["titulo"]
                    # Conservar imagen si la base la tiene o el nuevo la trae
                    if not merged[vid].get("image_url"):
                        if item.get("image_url"):
                            merged[vid]["image_url"] = item["image_url"]
                        elif image_cache and vid in image_cache:
                            merged[vid]["image_url"] = image_cache[vid]
                else:
                    new_added += 1
                    merged[vid] = item
                    order.append(vid)

    # Asegurar que todas las imágenes posibles estén pobladas
    for vid, it in merged.items():
        if not it.get("image_url") and image_cache and vid in image_cache:
            it["image_url"] = image_cache[vid]

    # Lista final en orden respetando originales + nuevos
    final_items = [merged[vid] for vid in order]

    stats = {
        "base_count": base_count,
        "base_seen": base_seen,
        "new_added": new_added,
        "new_duplicates": new_duplicates,
        "total": len(final_items),
        "total_seen": sum(1 for x in final_items if x["visto"] == "1"),
        "total_images": sum(1 for x in final_items if bool(x.get("image_url"))),
    }
    return final_items, stats

def main():
    parser = argparse.ArgumentParser(description="Flix2Flix: Fusionar respaldos CSV y actualizar index.html")
    parser.add_argument("--base", type=Path, help="CSV base existente con tu progreso (default: netflix_mylist_actualizado.csv)")
    parser.add_argument("--new", type=Path, help="Nuevo CSV descargado (ej: BACKUPS/netflix_mylist-10nov26.csv)")
    parser.add_argument("--out", type=Path, default=Path("netflix_mylist_actualizado.csv"), help="Archivo CSV de salida")
    parser.add_argument("--viewer-out", type=Path, default=Path("index.html"), help="Ruta de index.html")
    parser.add_argument("--open", action="store_true", help="Abrir index.html en el navegador al finalizar")
    args = parser.parse_args()

    # Autodetectar base
    base_file = args.base
    if not base_file:
        if Path("netflix_mylist_actualizado.csv").exists():
            base_file = Path("netflix_mylist_actualizado.csv")
        elif Path("BACKUPS/netflix_mylist-01Ago25.csv").exists():
            base_file = Path("BACKUPS/netflix_mylist-01Ago25.csv")
        elif Path("netflix_mylist.csv").exists():
            base_file = Path("netflix_mylist.csv")
        else:
            sys.exit("❌ No se encontró un archivo CSV base existente.")

    # Autodetectar nuevo
    new_file = args.new
    if not new_file:
        # Buscar el más reciente en BACKUPS
        backups_dir = Path("BACKUPS")
        if backups_dir.exists():
            csv_files = sorted(backups_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
            for f in csv_files:
                if f != base_file:
                    new_file = f
                    break
        if not new_file:
            sys.exit("❌ No se indicó --new y no se encontró un nuevo CSV en BACKUPS/")

    print(f"📂 Archivo base: {base_file}")
    print(f"📥 Archivo nuevo: {new_file}")

    image_cache = build_image_cache()
    if image_cache:
        print(f"🖼️  Portadas cargadas desde respaldos: {len(image_cache)}")

    items, stats = merge_csv_files(base_file, new_file, image_cache=image_cache)

    # Escribir CSV actualizado
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(items)

    # Actualizar index.html
    write_viewer_html(items, args.viewer_out, page_title="Netflix My List – Viewer (Con Visto)")

    print("\n" + "=" * 50)
    print("🎉 ¡FUSIÓN COMPLETADA CON ÉXITO!")
    print(f"- Títulos en respaldo anterior: {stats['base_count']} ({stats['base_seen']} vistos)")
    print(f"- Nuevos títulos agregados:    +{stats['new_added']}")
    print(f"- Coincidentes actualizados:    {stats['new_duplicates']}")
    print(f"- TOTAL EN TU LISTA:            {stats['total']} títulos ({stats['total_seen']} vistos)")
    print(f"- Títulos con portada:          {stats['total_images']} / {stats['total']}")
    if stats['total'] - stats['total_images'] > 0:
        print(f"- Títulos con póster temático:  {stats['total'] - stats['total_images']} (placeholders 🍿)")
    print(f"\n💾 CSV guardado en:      {args.out.resolve()}")
    print(f"🌐 Visor actualizado en:  {args.viewer_out.resolve()}")
    print("=" * 50 + "\n")

    if args.open:
        webbrowser.open(args.viewer_out.resolve().as_uri())

if __name__ == "__main__":
    main()

