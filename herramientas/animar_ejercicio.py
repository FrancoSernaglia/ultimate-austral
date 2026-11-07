#!/usr/bin/env python3
"""Anima un ejercicio de ultimate como pizarra vista desde arriba (MP4) y saca el diagrama fijo (PNG).

Lee una ficha JSON (ver Entrenamientos/README.md, seccion "Animaciones") con la cancha, los conos,
los jugadores y una lista de pasos. Un paso con "rastro": false (rotaciones, volver a la fila)
se anima pero no deja dibujado el recorrido. En cada paso los jugadores se mueven a su nueva posicion y,
si hay pase, el disco vuela del que lo tiene al receptor (llega cuando termina la corrida).

  - MP4 1080x1350 (4:5), 30 fps, H.264, sin audio: entra en WhatsApp, Instagram feed y mail.
  - PNG del mismo tamano con todos los recorridos (lineas punteadas = corridas, lineas llenas = pases).

Requiere: pip install pillow imageio-ffmpeg

Ej.: python herramientas/animar_ejercicio.py Entrenamientos/01-lanzamientos/go-to.json
     (deja go-to.mp4 y go-to.png al lado del JSON; --out-dir para cambiar la carpeta)
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from armar_imagen import AMARILLO, BLANCO, MARCA, VERDE, fuente, partir  # noqa: E402

W, H = 1080, 1350
FPS = 30
CABECERA, PIE, MARGEN = 170, 230, 50
PASTO = (34, 120, 70)
PASTO_OSCURO = (28, 104, 60)
LINEA = (235, 245, 235)
DEFENSA = (120, 190, 255)
NEUTRO = (255, 150, 60)
CONO = (255, 110, 20)
COLORES = {"ataque": AMARILLO, "defensa": DEFENSA, "neutro": NEUTRO}
PAUSA_INICIO, PAUSA_FIN = 1.2, 1.5


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Pizarra:
    def __init__(self, ficha):
        self.f = ficha
        c = ficha.get("cancha", {})
        self.ancho, self.largo = c.get("ancho", 20), c.get("largo", 30)
        area_h = H - CABECERA - PIE - 2 * MARGEN
        area_w = W - 2 * MARGEN
        self.esc = min(area_w / self.ancho, area_h / self.largo)
        self.ox = (W - self.ancho * self.esc) / 2
        self.oy = CABECERA + MARGEN + (area_h - self.largo * self.esc) / 2
        self.r = max(16, min(30, int(self.esc * 0.9)))
        self.f_titulo = fuente(54)
        self.f_marca = fuente(26)
        self.f_texto = fuente(40)
        self.f_label = fuente(int(self.r * 1.05))
        self.f_paso = fuente(28)

    def px(self, p):
        x, y = p
        # y crece hacia arriba (sentido de ataque); la pantalla crece hacia abajo
        return (self.ox + x * self.esc, self.oy + (self.largo - y) * self.esc)

    def fondo(self):
        im = Image.new("RGB", (W, H), VERDE)
        d = ImageDraw.Draw(im)
        x0, y0 = self.px((0, self.largo))
        x1, y1 = self.px((self.ancho, 0))
        franjas = 6
        for i in range(franjas):
            ya = y0 + (y1 - y0) * i / franjas
            yb = y0 + (y1 - y0) * (i + 1) / franjas
            d.rectangle([x0, ya, x1, yb], fill=PASTO if i % 2 == 0 else PASTO_OSCURO)
        d.rectangle([x0, y0, x1, y1], outline=LINEA, width=4)
        for linea in self.f.get("lineas", []):  # [[x,y],[x,y]] en metros
            d.line([self.px(linea[0]), self.px(linea[1])], fill=LINEA, width=4)
        for zona in self.f.get("zonas", []):  # {"desde": y, "hasta": y} zona de gol sombreada
            za, zb = self.px((0, zona["hasta"])), self.px((self.ancho, zona["desde"]))
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(capa).rectangle([za[0], za[1], zb[0], zb[1]], fill=(255, 255, 255, 28))
            im.paste(capa, (0, 0), capa)
        d = ImageDraw.Draw(im)
        for cono in self.f.get("conos", []):
            cx, cy = self.px(cono)
            s = max(10, self.r * 0.6)
            d.polygon([(cx, cy - s), (cx - s * 0.85, cy + s * 0.6), (cx + s * 0.85, cy + s * 0.6)], fill=CONO,
                      outline=(120, 40, 0))
        # cabecera
        d.text((MARGEN, 34), MARCA, font=self.f_marca, fill=AMARILLO)
        lineas = partir(d, self.f.get("titulo", ""), self.f_titulo, W - 2 * MARGEN)[:2]
        for i, l in enumerate(lineas):
            d.text((MARGEN, 72 + i * 58), l, font=self.f_titulo, fill=BLANCO)
        # flecha de ataque
        if self.f.get("flecha_ataque", True):
            fx, fy = W - MARGEN + 18, CABECERA + MARGEN + 40
            d.line([(fx, fy + 90), (fx, fy)], fill=AMARILLO, width=5)
            d.polygon([(fx - 12, fy + 10), (fx + 12, fy + 10), (fx, fy - 10)], fill=AMARILLO)
        return im

    def jugador(self, d, nombre, pos, info):
        x, y = self.px(pos)
        r = self.r
        color = COLORES.get(info.get("equipo", "ataque"), AMARILLO)
        d.ellipse([x - r, y - r, x + r, y + r], fill=color, outline=(20, 20, 20), width=3)
        label = info.get("label", nombre)
        tw = d.textlength(label, font=self.f_label)
        d.text((x - tw / 2, y - r * 0.62), label, font=self.f_label, fill=(20, 20, 20))

    def disco(self, d, pos, alto=0.0):
        x, y = self.px(pos)
        y -= alto
        r = max(9, self.r * 0.45) * (1 + alto / 220)
        d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=BLANCO, outline=(30, 30, 30), width=2)

    def pie(self, d, texto, n_paso, total):
        y0 = H - PIE
        d.rectangle([0, y0, W, H], fill=VERDE)
        if total:
            d.text((MARGEN, y0 + 22), f"PASO {n_paso}/{total}", font=self.f_paso, fill=AMARILLO)
        for i, l in enumerate(partir(d, texto or "", self.f_texto, W - 2 * MARGEN)[:3]):
            d.text((MARGEN, y0 + 62 + i * 48), l, font=self.f_texto, fill=BLANCO)


def flecha(d, a, b, color, ancho=4, punteada=False):
    if punteada:
        dist = math.dist(a, b)
        n = max(1, int(dist / 22))
        for i in range(0, n, 2):
            p = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            q = (a[0] + (b[0] - a[0]) * min(i + 1, n) / n, a[1] + (b[1] - a[1]) * min(i + 1, n) / n)
            d.line([p, q], fill=color, width=ancho)
    else:
        d.line([a, b], fill=color, width=ancho)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    s = 18
    d.polygon([b, (b[0] - s * math.cos(ang - 0.45), b[1] - s * math.sin(ang - 0.45)),
               (b[0] - s * math.cos(ang + 0.45), b[1] - s * math.sin(ang + 0.45))], fill=color)


def simular(ficha):
    """Devuelve la lista de pasos resueltos: posiciones de inicio y fin, y el pase si lo hay."""
    jug = ficha["jugadores"]
    pos = {k: tuple(v["pos"]) for k, v in jug.items()}
    tiene = ficha.get("disco", {}).get("en")
    disco_libre = tuple(ficha["disco"]["pos"]) if ficha.get("disco", {}).get("pos") else None
    pasos = []
    for p in ficha["pasos"]:
        ini = dict(pos)
        fin = dict(pos)
        for k, v in p.get("mover", {}).items():
            fin[k] = tuple(v)
        pase = None
        if "pase" in p:
            a = p["pase"]["a"]
            origen = ini[tiene] if tiene else disco_libre
            pase = {"de": tiene, "a": a, "origen": origen, "inicio": p["pase"].get("inicio", 0.35),
                    "curva": p["pase"].get("curva", 0)}
            tiene = a
        pasos.append({"dur": p.get("dur", 1.8), "texto": p.get("texto", ""), "ini": ini, "fin": fin,
                      "pase": pase, "tiene_fin": tiene, "rastro": p.get("rastro", True)})
        pos = fin
    return pasos


def punto_pase(pase, destino, t, curva):
    o, dd = pase["origen"], destino
    x = o[0] + (dd[0] - o[0]) * t
    y = o[1] + (dd[1] - o[1]) * t
    if curva:  # curva lateral en metros (forehand/backhand con angulo)
        nx, ny = -(dd[1] - o[1]), dd[0] - o[0]
        n = math.hypot(nx, ny) or 1
        k = math.sin(math.pi * t) * curva
        x, y = x + nx / n * k, y + ny / n * k
    return (x, y)


def render(ficha, salida_mp4, salida_png):
    piz = Pizarra(ficha)
    base = piz.fondo()
    jug = ficha["jugadores"]
    pasos = simular(ficha)
    total = len(pasos)
    tiene0 = ficha.get("disco", {}).get("en")

    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "23",
           "-movflags", "+faststart", str(salida_mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def con_rastro(k):  # la defensa no deja linea (ensucia el dibujo), salvo "rastro_defensa": true
        return jug[k].get("equipo", "ataque") != "defensa" or ficha.get("rastro_defensa", False)

    rastros = []  # (a, b, color, punteada) en px, se acumulan para que quede el dibujo

    def cuadro(posiciones, disco_pos, disco_alto, texto, n, extras=()):
        im = base.copy()
        d = ImageDraw.Draw(im)
        for a, b, color, punt in list(rastros) + list(extras):
            flecha(d, a, b, color, ancho=3, punteada=punt)
        for k, p in posiciones.items():
            piz.jugador(d, k, p, jug[k])
        if disco_pos:
            piz.disco(d, disco_pos, disco_alto)
        piz.pie(d, texto, n, total)
        proc.stdin.write(im.tobytes())

    def disco_en(posiciones, quien):
        if not quien:
            return tuple(ficha["disco"]["pos"]) if ficha.get("disco", {}).get("pos") else None
        p = posiciones[quien]
        return (p[0] + piz.r * 1.15 / piz.esc, p[1] + 0.1)

    ini0 = pasos[0]["ini"] if pasos else {k: tuple(v["pos"]) for k, v in jug.items()}
    for _ in range(int(PAUSA_INICIO * FPS)):
        cuadro(ini0, disco_en(ini0, tiene0), 0, ficha.get("intro", "Mirá el recorrido"), 0)

    tiene = tiene0
    for n, paso in enumerate(pasos, 1):
        frames = max(1, int(paso["dur"] * FPS))
        pase = paso["pase"]
        for i in range(frames + 1):
            t = i / frames
            posiciones = {}
            extras = []
            for k in paso["ini"]:
                a, b = paso["ini"][k], paso["fin"][k]
                e = suave(t)
                posiciones[k] = (a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e)
                if a != b and con_rastro(k):
                    extras.append((piz.px(a), piz.px(posiciones[k]), BLANCO, True))
            if pase:
                ti = pase["inicio"]
                if t < ti:
                    dp, alto = disco_en(posiciones, tiene), 0
                else:
                    u = (t - ti) / (1 - ti)
                    destino = paso["fin"][pase["a"]]
                    dp = punto_pase(pase, destino, u, pase["curva"])
                    alto = math.sin(math.pi * u) * 40
                    extras.append((piz.px(pase["origen"]), piz.px(dp), AMARILLO, False))
            else:
                dp, alto = disco_en(posiciones, tiene), 0
            cuadro(posiciones, dp, alto, paso["texto"], n, extras)
        for k in paso["ini"]:
            if paso["rastro"] and con_rastro(k) and paso["ini"][k] != paso["fin"][k]:
                rastros.append((piz.px(paso["ini"][k]), piz.px(paso["fin"][k]), BLANCO, True))
        if pase and paso["rastro"]:
            rastros.append((piz.px(pase["origen"]), piz.px(paso["fin"][pase["a"]]), AMARILLO, False))
        tiene = paso["tiene_fin"]
        # pausa corta para leer
        for _ in range(int(0.5 * FPS)):
            cuadro(paso["fin"], disco_en(paso["fin"], tiene), 0, paso["texto"], n)

    final = pasos[-1]["fin"] if pasos else ini0
    cierre = ficha.get("cierre", "Rotá y repetí")
    for _ in range(int(PAUSA_FIN * FPS)):
        cuadro(final, disco_en(final, tiene), 0, cierre, total)
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg fallo")

    # PNG: posicion inicial + todos los recorridos
    im = base.copy()
    d = ImageDraw.Draw(im)
    for a, b, color, punt in rastros:
        flecha(d, a, b, color, ancho=4, punteada=punt)
    for k, p in ini0.items():
        piz.jugador(d, k, p, jug[k])
    if disco_en(ini0, tiene0):
        piz.disco(d, disco_en(ini0, tiene0))
    piz.pie(d, ficha.get("resumen", cierre), 0, 0)
    im.save(salida_png, quality=92)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fichas", nargs="+", type=Path, help="uno o mas JSON de animacion")
    ap.add_argument("--out-dir", type=Path, help="carpeta de salida (por defecto, al lado del JSON)")
    args = ap.parse_args()
    for f in args.fichas:
        ficha = json.loads(f.read_text(encoding="utf-8"))
        carpeta = args.out_dir or f.parent
        carpeta.mkdir(parents=True, exist_ok=True)
        mp4, png = carpeta / f"{f.stem}.mp4", carpeta / f"{f.stem}.png"
        render(ficha, mp4, png)
        print(f"ok {mp4} ({mp4.stat().st_size // 1024} KB) + {png.name}")


if __name__ == "__main__":
    main()
