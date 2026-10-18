#!/usr/bin/env python3
"""Arma una imagen lista para Instagram a partir de una foto del banco.

  feed   1080x1350 (4:5). Las fotos verticales 2:3 se recortan; el feed no acepta menos de 4:5.
  story  1080x1920 (9:16).

Texto opcional (--titulo / --subtitulo) sobre una franja oscura abajo, con la paleta del flyer
(verde y amarillo). Requiere Pillow: pip install pillow

Ej.: python herramientas/armar_imagen.py media/banco/x.jpg --formato story \
        --titulo "Hoy entrenamos" --subtitulo "Viernes 17 hs" --out media/piezas/010-story.jpg
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

TAMANOS = {"feed": (1080, 1350), "story": (1080, 1920)}
VERDE = (11, 61, 46)
AMARILLO = (255, 214, 10)
BLANCO = (255, 255, 255)
MARCA = "ULTIMATE AUSTRAL"
FUENTES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "DejaVuSans-Bold.ttf",
]


def fuente(px):
    for f in FUENTES:
        try:
            return ImageFont.truetype(f, px)
        except OSError:
            continue
    return ImageFont.load_default(size=px)  # Pillow >= 10.1


def recortar(img, w, h):
    # Sesgo hacia arriba (0.4): en fotos deportivas la accion suele estar en el tercio superior.
    return ImageOps.fit(img, (w, h), method=Image.LANCZOS, centering=(0.5, 0.4))


def partir(draw, texto, font, ancho):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if draw.textlength(prueba, font=font) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def degradado(img, desde):
    """Oscurece de forma gradual desde la altura `desde` hasta abajo, para que el texto se lea."""
    w, h = img.size
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for y in range(desde, h):
        a = int(235 * min(1, (y - desde) / max(1, (h - desde) * 0.45)))
        d.line([(0, y), (w, y)], fill=VERDE + (a,))
    return Image.alpha_composite(img.convert("RGBA"), capa)


def armar(foto, formato, titulo=None, subtitulo=None):
    w, h = TAMANOS[formato]
    img = recortar(ImageOps.exif_transpose(Image.open(foto)).convert("RGB"), w, h)
    if not (titulo or subtitulo):
        return img
    margen = 80
    ft, fs, fm = fuente(96 if formato == "story" else 78), fuente(54 if formato == "story" else 46), fuente(34)
    d = ImageDraw.Draw(img)
    lt = partir(d, titulo.upper(), ft, w - 2 * margen) if titulo else []
    ls = partir(d, subtitulo, fs, w - 2 * margen) if subtitulo else []
    alto = len(lt) * int(ft.size * 1.1) + (24 if lt and ls else 0) + len(ls) * int(fs.size * 1.25)
    # En story se deja libre la barra de respuesta (abajo ~320 px); en feed basta un margen.
    piso = h - (320 if formato == "story" else 90)
    y = piso - alto
    img = degradado(img, max(0, y - 260))
    d = ImageDraw.Draw(img)
    d.text((margen, y - 70), MARCA, font=fm, fill=AMARILLO)
    for linea in lt:
        d.text((margen, y), linea, font=ft, fill=BLANCO)
        y += int(ft.size * 1.1)
    y += 24 if lt and ls else 0
    for linea in ls:
        d.text((margen, y), linea, font=fs, fill=AMARILLO)
        y += int(fs.size * 1.25)
    return img.convert("RGB")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("foto")
    p.add_argument("--formato", choices=TAMANOS, required=True)
    p.add_argument("--titulo")
    p.add_argument("--subtitulo")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    out = Path(a.out)
    if out.suffix.lower() not in (".jpg", ".jpeg"):
        sys.exit("--out tiene que ser .jpg (el publicador solo acepta JPEG)")
    out.parent.mkdir(parents=True, exist_ok=True)
    armar(a.foto, a.formato, a.titulo, a.subtitulo).save(out, "JPEG", quality=88, optimize=True)
    print(f"{out}  {TAMANOS[a.formato][0]}x{TAMANOS[a.formato][1]}  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
