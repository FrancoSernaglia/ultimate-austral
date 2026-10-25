#!/usr/bin/env python3
"""Corta y arma un clip vertical listo para Instagram (reel o story) a partir de un video propio.

  - Uno o mas tramos (--tramo 36-46 --tramo 13.5-19), pegados en ese orden.
  - 1080x1920 (9:16), 30 fps, H.264 + AAC, con un toque de saturacion y contraste.
  - Fundido de entrada y salida.
  - Texto opcional (--titulo / --subtitulo) arriba, con la paleta del flyer. Va arriba porque
    abajo y a la derecha Instagram pone la caption y los botones.

Sin --titulo sale el corte limpio: asi se preparan los clips de media/propias/listas/.
Instagram: reels hasta 90 s y stories hasta 60 s publicados por API.

Requiere: pip install pillow imageio-ffmpeg

Ej.: python herramientas/editar_clip.py media/propias/listas/viernes-atardecer.mp4 --tramo 0-9 \
        --titulo "Esto pasa los viernes" --subtitulo "17 hs, vení" --out media/piezas/012-reel-viernes.mp4
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from armar_imagen import AMARILLO, BLANCO, MARCA, VERDE, fuente, partir  # noqa: E402

W, H = 1080, 1920
FPS = 30
FUNDIDO = 0.4
MAX_S = {"reel": 90, "story": 60}


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def tiene_audio(video):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(video)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return "Audio:" in r.stderr


def parsear_tramo(texto):
    m = re.fullmatch(r"\s*([\d.]+)\s*-\s*([\d.]+)\s*", texto)
    if not m or float(m.group(2)) <= float(m.group(1)):
        raise argparse.ArgumentTypeError(f"tramo invalido '{texto}' (usar DESDE-HASTA en segundos, ej. 36-46)")
    return float(m.group(1)), float(m.group(2))


def capa_texto(titulo, subtitulo, out):
    """PNG transparente de 1080x1920 con la marca, el titulo y el subtitulo sobre un degradado arriba."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    margen, y0 = 80, 230
    ft, fs, fm = fuente(92), fuente(52), fuente(34)
    d = ImageDraw.Draw(img)
    lt = partir(d, titulo.upper(), ft, W - 2 * margen)
    ls = partir(d, subtitulo, fs, W - 2 * margen) if subtitulo else []
    fin = y0 + 60 + len(lt) * int(ft.size * 1.1) + (24 if ls else 0) + len(ls) * int(fs.size * 1.25)
    alto_degradado = fin + 220
    for y in range(alto_degradado):
        a = int(215 * min(1, (alto_degradado - y) / (alto_degradado * 0.45)))
        d.line([(0, y), (W, y)], fill=VERDE + (a,))
    d.text((margen, y0), MARCA, font=fm, fill=AMARILLO)
    y = y0 + 60
    for linea in lt:
        d.text((margen, y), linea, font=ft, fill=BLANCO)
        y += int(ft.size * 1.1)
    y += 24 if ls else 0
    for linea in ls:
        d.text((margen, y), linea, font=fs, fill=AMARILLO)
        y += int(fs.size * 1.25)
    img.save(out)


def comando(video, tramos, out, capa=None, audio=True):
    total = sum(b - a for a, b in tramos)
    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video)]
    if capa:
        cmd += ["-loop", "1", "-i", str(capa)]
    filtros, pegar = [], ""
    for i, (a, b) in enumerate(tramos):
        filtros.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,"
                       f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
                       f"eq=saturation=1.12:contrast=1.04,setsar=1[v{i}]")
        pegar += f"[v{i}]"
        if audio:
            filtros.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a{i}]")
            pegar += f"[a{i}]"
    filtros.append(f"{pegar}concat=n={len(tramos)}:v=1:a={int(audio)}[vc]" + ("[ac]" if audio else ""))
    fundido = f"fade=t=in:d={FUNDIDO},fade=t=out:st={max(0, total - FUNDIDO):.2f}:d={FUNDIDO}"
    if capa:
        filtros.append(f"[vc][1:v]overlay=0:0:shortest=1,{fundido},format=yuv420p[v]")
    else:
        filtros.append(f"[vc]{fundido},format=yuv420p[v]")
    mapas = ["-map", "[v]"]
    if audio:
        filtros.append(f"[ac]afade=t=in:d={FUNDIDO},afade=t=out:st={max(0, total - FUNDIDO):.2f}:d={FUNDIDO}[a]")
        mapas += ["-map", "[a]", "-c:a", "aac", "-b:a", "128k", "-ar", "48000"]
    return cmd + ["-filter_complex", ";".join(filtros)] + mapas + [
        # Tope de 5 Mbps (lo que recomienda Instagram): el pasto sin tope infla el archivo y va a git.
        "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-maxrate", "5M", "-bufsize", "10M",
        "-profile:v", "high",
        "-t", f"{total:.2f}", "-movflags", "+faststart", str(out)]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video")
    p.add_argument("--tramo", type=parsear_tramo, action="append", required=True)
    p.add_argument("--formato", choices=MAX_S, default="reel")
    p.add_argument("--titulo")
    p.add_argument("--subtitulo")
    p.add_argument("--sin-audio", action="store_true", help="saca el sonido ambiente")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    out = Path(a.out)
    if out.suffix.lower() != ".mp4":
        sys.exit("--out tiene que ser .mp4")
    if a.subtitulo and not a.titulo:
        sys.exit("--subtitulo necesita --titulo")
    total = sum(b - x for x, b in a.tramo)
    if total > MAX_S[a.formato]:
        sys.exit(f"el clip dura {total:.1f} s y un/a {a.formato} admite hasta {MAX_S[a.formato]} s")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        capa = None
        if a.titulo:
            capa = Path(tmp) / "texto.png"
            capa_texto(a.titulo, a.subtitulo, capa)
        r = subprocess.run(comando(a.video, a.tramo, out, capa, not a.sin_audio and tiene_audio(a.video)),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        sys.exit(f"ffmpeg fallo:\n{r.stderr[-2000:]}")
    print(f"{out}  {W}x{H}  {total:.1f} s  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
