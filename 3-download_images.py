#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flix2Flix - 3-download_images.py
Descarga y almacena en caché local todas las portadas de Netflix en ./imagenes/

Ventajas:
1. Sin riesgo de bloqueo o baneo por exceso de peticiones.
2. Inmune a la caducidad de tokens o eliminación de títulos en Netflix CDN.
3. Permite abrir y usar index.html 100% offline (en avión, sin wifi, etc.).
4. Carga ultrarrápida e instantánea en el navegador.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.request

from netflix_mylist_to_csv_and_viewer_spanish import (
    read_items_from_csv,
    write_viewer_html,
)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def build_image_map_from_sources() -> dict:
    """
    Escanea todos los CSV disponibles para obtener la mejor URL de portada para cada ID.
    """
    image_map = {}
    sources = [
        Path("netflix_mylist_actualizado.csv"),
        Path("netflix_mylist.csv"),
    ]
    backups = Path("BACKUPS")
    if backups.exists():
        sources.extend(sorted(backups.glob("*.csv"), reverse=True))

    for src in sources:
        if not src.exists():
            continue
        try:
            with src.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vid = str(row.get("id") or "").strip()
                    img = str(row.get("image_url") or row.get("image") or "").strip()
                    title = str(row.get("titulo") or row.get("title") or "").strip()
                    if vid and img and vid not in image_map:
                        image_map[vid] = {"url": img, "title": title}
        except Exception:
            continue
    return image_map

def download_single_image(vid: str, img_url: str, title: str, out_dir: Path, timeout: int = 10) -> tuple:
    """
    Descarga una imagen individual y la guarda como <out_dir>/<vid>.<ext>
    """
    # Si ya existe con cualquier extensión conocida, omitir
    for ext in (".jpg", ".webp", ".png", ".jpeg"):
        dest = out_dir / f"{vid}{ext}"
        if dest.exists() and dest.stat().st_size > 500:
            return vid, "already_exists", dest

    req = urllib.request.Request(
        img_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "",  # Sin referer para evitar 403 de Netflix CDN
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "").lower()
            if "webp" in content_type or ".webp" in img_url.lower():
                ext = ".webp"
            elif "png" in content_type or ".png" in img_url.lower():
                ext = ".png"
            else:
                ext = ".jpg"

            dest = out_dir / f"{vid}{ext}"
            data = resp.read()
            if len(data) < 200:
                return vid, "too_small", None

            dest.write_bytes(data)
            return vid, "downloaded", dest
    except urllib.error.HTTPError as e:
        return vid, f"http_{e.code}", None
    except Exception as e:
        return vid, f"error_{str(e)[:30]}", None

def main():
    parser = argparse.ArgumentParser(description="Flix2Flix: Descargar portadas de Netflix a ./imagenes/")
    parser.add_argument("--csv", type=Path, help="Ruta al CSV (default: netflix_mylist_actualizado.csv)")
    parser.add_argument("--out-dir", type=Path, default=Path("imagenes"), help="Carpeta de destino (default: ./imagenes)")
    parser.add_argument("--concurrency", type=int, default=6, help="Descargas simultáneas (default: 6)")
    parser.add_argument("--timeout", type=int, default=12, help="Timeout en segundos por descarga (default: 12)")
    parser.add_argument("--no-viewer-update", action="store_true", help="No regenerar index.html al finalizar")
    args = parser.parse_args()

    csv_path = args.csv
    if not csv_path:
        if Path("netflix_mylist_actualizado.csv").exists():
            csv_path = Path("netflix_mylist_actualizado.csv")
        elif Path("netflix_mylist.csv").exists():
            csv_path = Path("netflix_mylist.csv")
        else:
            sys.exit("❌ No se encontró ningún archivo CSV para procesar.")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🎬 Flix2Flix: Descargador de Portadas Offline")
    print(f"📂 Archivo CSV:    {csv_path}")
    print(f"📁 Carpeta destino: {args.out_dir.resolve()}")
    print("=" * 60)

    # Compilar mapa de imágenes cruzando todas las fuentes
    image_map = build_image_map_from_sources()
    items = read_items_from_csv(csv_path)

    to_download = []
    already_cached = 0
    missing_url = 0

    for it in items:
        vid = str(it.get("id") or "").strip()
        if not vid:
            continue

        # Verificar si ya existe en disco
        cached = False
        for ext in (".jpg", ".webp", ".png", ".jpeg"):
            dest = args.out_dir / f"{vid}{ext}"
            if dest.exists() and dest.stat().st_size > 500:
                already_cached += 1
                cached = True
                break
        if cached:
            continue

        # Obtener URL
        img_url = str(it.get("image_url") or it.get("image") or "").strip()
        title = str(it.get("titulo") or it.get("title") or "").strip()
        if not img_url and vid in image_map:
            img_url = image_map[vid]["url"]
            if not title:
                title = image_map[vid]["title"]

        if img_url:
            to_download.append((vid, img_url, title))
        else:
            missing_url += 1

    total_items = len(items)
    print(f"\n📊 Estado inicial:")
    print(f"- Total de títulos en tu lista: {total_items}")
    print(f"- Ya descargadas en caché:      {already_cached}")
    print(f"- Pendientes por descargar:     {len(to_download)}")
    if missing_url > 0:
        print(f"- Sin URL de portada:           {missing_url} (se mostrarán con póster temático 🍿)")

    if not to_download:
        print("\n✅ ¡Todas las imágenes disponibles ya están descargadas en ./imagenes/!")
    else:
        print(f"\n🚀 Iniciando descarga de {len(to_download)} portadas (concurrencia: {args.concurrency})...\n")

        downloaded = 0
        failed = 0
        lock = threading.Lock()
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = {
                executor.submit(download_single_image, vid, url, title, args.out_dir, args.timeout): (vid, title)
                for vid, url, title in to_download
            }

            for idx, future in enumerate(as_completed(futures), 1):
                vid, title = futures[future]
                try:
                    _, status, dest = future.result()
                    with lock:
                        pct = int((idx / len(to_download)) * 100)
                        if status == "downloaded":
                            downloaded += 1
                            display_title = (title[:30] + "..") if len(title) > 30 else title
                            print(f"[{idx}/{len(to_download)}] ({pct}%) ✅ {display_title}")
                        elif status == "already_exists":
                            already_cached += 1
                        else:
                            failed += 1
                            print(f"[{idx}/{len(to_download)}] ({pct}%) ⚠️ Error en {vid} ({title}): {status}")
                except Exception as e:
                    with lock:
                        failed += 1

        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print("🎉 ¡DESCARGA FINALIZADA!")
        print(f"- Portadas descargadas ahora: {downloaded}")
        print(f"- En caché previamente:       {already_cached}")
        print(f"- Fallidas / No disponibles:  {failed}")
        print(f"- Tiempo total transcurrido:  {elapsed:.1f} segundos")
        print("=" * 60)

    # Regenerar index.html para reflejar las portadas locales inmediatamente
    if not args.no_viewer_update:
        viewer_out = Path("index.html")
        write_viewer_html(items, viewer_out, page_title="Netflix My List – Viewer (Con Visto)")
        print(f"\n🌐 Visor actualizado con las imágenes locales en: {viewer_out.resolve()}")

if __name__ == "__main__":
    main()

