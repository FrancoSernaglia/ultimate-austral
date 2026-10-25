#!/usr/bin/env python3
"""Trae al repo las fotos y videos propios que el equipo deja en OneDrive.

Copia (nunca mueve ni borra) cada archivo nuevo de la carpeta de origen a media/propias/crudos/
y arma una vista previa en media/propias/previews/ para poder calificarlo. Crudos y previews
quedan fuera de git (el repo es publico); al repo van solo CATALOGO.md y media/propias/listas/.

  Origen/                 material sin permiso confirmado: se cataloga, no se publica
  Origen/con-permiso/     quienes aparecen dieron permiso: se puede preparar y publicar

Si un archivo ya importado aparece despues en con-permiso/, se detecta por su hash y se
actualiza el permiso sin copiarlo de nuevo. Imprime un JSON con lo nuevo y lo actualizado.

Requiere: pip install pillow imageio-ffmpeg

  python herramientas/importar_propias.py [--origen RUTA]
  python herramientas/importar_propias.py --detalle media/propias/crudos/x.mp4 12 24
  python herramientas/importar_propias.py --preparar-foto media/propias/crudos/x.jpg --out media/propias/listas/x.jpg

--detalle arma una hoja con un cuadro por segundo entre esos segundos, para elegir cortes.
--preparar-foto deja la foto derecha (EXIF) a 1440 px de ancho, como las del banco.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from armar_imagen import fuente  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROPIAS = ROOT / "media" / "propias"
CRUDOS = PROPIAS / "crudos"
PREVIEWS = PROPIAS / "previews"
INDICE = CRUDOS / "indice.json"
ORIGEN = Path.home() / "OneDrive" / "Austral Ultimate"
CARPETA_PERMISO = "con-permiso"
FOTO_EXT = (".jpg", ".jpeg", ".png", ".heic")
VIDEO_EXT = (".mp4", ".mov")
CUADROS_HOJA = 12


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def hash_archivo(ruta):
    h = hashlib.sha1()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def info_video(ruta):
    """Duracion y tamano ya rotado (los celulares guardan la rotacion aparte)."""
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(ruta)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    err = r.stderr
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    dur = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else 0.0
    v = re.search(r"Stream #.*Video:.*?(\d{2,5})x(\d{2,5})", err)
    w, h = (int(v.group(1)), int(v.group(2))) if v else (0, 0)
    rot = re.search(r"rotation of (-?[\d.]+)|rotate\s*:\s*(-?\d+)", err)
    if rot and abs(float(rot.group(1) or rot.group(2))) % 180 == 90:
        w, h = h, w
    fps = re.search(r"([\d.]+) fps", err)
    return {"duracion_s": round(dur, 1), "ancho": w, "alto": h, "fps": float(fps.group(1)) if fps else None,
            "audio": "Audio:" in err}


def cuadro(ruta, t):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(ruta),
                        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if r.returncode or not r.stdout:
        return None
    from io import BytesIO
    return Image.open(BytesIO(r.stdout)).convert("RGB")


def hoja(ruta, tiempos, out):
    """Cuadros en grilla de 4 columnas, cada uno con su segundo marcado arriba a la izquierda."""
    cuadros = [(t, c) for t in tiempos if (c := cuadro(ruta, t))]
    if not cuadros:
        return None
    for _, c in cuadros:
        c.thumbnail((360, 360))
    cw, ch = cuadros[0][1].size
    filas = (len(cuadros) + 3) // 4
    lienzo = Image.new("RGB", (cw * 4, ch * filas), (20, 20, 20))
    d = ImageDraw.Draw(lienzo)
    f = fuente(28)
    for i, (t, c) in enumerate(cuadros):
        x, y = (i % 4) * cw, (i // 4) * ch
        lienzo.paste(c, (x, y))
        etiqueta = f"{int(t // 60):02d}:{t % 60:04.1f}"
        d.rectangle([x, y, x + d.textlength(etiqueta, font=f) + 16, y + 38], fill=(0, 0, 0))
        d.text((x + 8, y + 4), etiqueta, font=f, fill=(255, 214, 10))
    out.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(out, "JPEG", quality=85)
    return out


def preview_foto(ruta, out):
    img = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    w, h = img.size
    img.thumbnail((1200, 1200))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=85)
    return {"ancho": w, "alto": h}


def destino_libre(nombre):
    dest = CRUDOS / nombre
    n = 2
    while dest.exists():
        dest = CRUDOS / f"{Path(nombre).stem}-{n}{Path(nombre).suffix}"
        n += 1
    return dest


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def importar(origen):
    indice = json.loads(INDICE.read_text(encoding="utf-8")) if INDICE.exists() else {}
    nuevos, actualizados = [], []
    for f in sorted(origen.rglob("*")):
        ext = f.suffix.lower()
        if not f.is_file() or ext not in FOTO_EXT + VIDEO_EXT:
            continue
        permiso = CARPETA_PERMISO in [p.lower() for p in f.relative_to(origen).parts[:-1]]
        h = hash_archivo(f)
        if h in indice:
            e = indice[h]
            if permiso and not e["permiso"]:
                e["permiso"] = True
                actualizados.append(e)
            e["origen"] = str(f)
            continue
        CRUDOS.mkdir(parents=True, exist_ok=True)
        dest = destino_libre(f.name)
        shutil.copy2(f, dest)
        e = {"archivo": dest.name, "crudo": rel(dest), "origen": str(f), "permiso": permiso,
             "importado": datetime.now().strftime("%Y-%m-%d"), "tipo": "video" if ext in VIDEO_EXT else "foto"}
        if e["tipo"] == "foto":
            prev = PREVIEWS / f"{dest.stem}.jpg"
            try:
                e.update(preview_foto(dest, prev))
                e["preview"] = rel(prev)
            except Exception as ex:  # HEIC u otro formato que Pillow no abre
                e["preview_error"] = str(ex)
        else:
            e.update(info_video(dest))
            dur = e["duracion_s"]
            tiempos = [dur * (i + 0.5) / CUADROS_HOJA for i in range(CUADROS_HOJA)]
            prev = hoja(dest, tiempos, PREVIEWS / f"{dest.stem}.jpg")
            if prev:
                e["preview"] = rel(prev)
        indice[h] = e
        nuevos.append(e)
    CRUDOS.mkdir(parents=True, exist_ok=True)
    INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"origen": str(origen), "nuevos": nuevos, "actualizados": actualizados, "total": len(indice)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--origen", default=str(ORIGEN))
    p.add_argument("--detalle", nargs=3, metavar=("VIDEO", "DESDE", "HASTA"))
    p.add_argument("--preparar-foto", metavar="FOTO")
    p.add_argument("--out")
    a = p.parse_args(argv)
    if a.detalle:
        video, desde, hasta = Path(a.detalle[0]), float(a.detalle[1]), float(a.detalle[2])
        tiempos = [desde + i for i in range(int(hasta - desde) + 1)]
        out = hoja(video, tiempos, PREVIEWS / f"{video.stem}-detalle-{int(desde)}-{int(hasta)}.jpg")
        print(out or "no pude sacar cuadros")
        return
    if a.preparar_foto:
        if not a.out:
            sys.exit("--preparar-foto necesita --out")
        img = ImageOps.exif_transpose(Image.open(a.preparar_foto)).convert("RGB")
        if img.width > 1440:
            img = img.resize((1440, round(img.height * 1440 / img.width)), Image.LANCZOS)
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, "JPEG", quality=88, optimize=True)
        print(f"{out}  {img.width}x{img.height}  {out.stat().st_size // 1024} KB")
        return
    origen = Path(a.origen)
    if not origen.is_dir():
        sys.exit(f"No existe la carpeta de origen: {origen}")
    print(json.dumps(importar(origen), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
