#!/usr/bin/env python3
"""Arma el visor de entrenamientos (una pagina HTML) a partir de las fichas de Entrenamientos/.

Lee cada carpeta de habilidad (README + fichas .md con encabezado), los planes de semanas/ y programa.md,
y escribe Entrenamientos/visor/index.html con todo embebido como JSON. Los diagramas (.png) y videos (.mp4)
se referencian como media/<carpeta>/<archivo>; al publicar el artifact se suben con ese mismo camino.

  python herramientas/armar_visor.py            -> escribe el HTML y lista los archivos de media
  python herramientas/armar_visor.py --files    -> ademas imprime el mapa de archivos en JSON (para publicar)

Solo libreria estandar.
"""
import argparse
import html
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENT = RAIZ / "Entrenamientos"
SALIDA = ENT / "visor" / "index.html"
PLANTILLA = Path(__file__).resolve().parent / "visor_plantilla.html"


def frontmatter(texto):
    if not texto.startswith("---"):
        return {}, texto
    fin = texto.find("\n---", 3)
    meta = {}
    for linea in texto[3:fin].strip().splitlines():
        if ":" in linea:
            k, v = linea.split(":", 1)
            meta[k.strip()] = v.split("#")[0].strip() if " #" in v else v.strip()
    return meta, texto[fin + 4:].lstrip("\n")


def inline(t, ids):
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)

    def codigo(m):
        c = m.group(1)
        stem = Path(c).stem
        if stem in ids:
            return f'<a class="ref" href="#ej-{stem}">{html.escape(ids[stem])}</a>'
        if c.startswith("reglas/"):
            return f'<span class="regla">{c}</span>'
        return f"<code>{c}</code>"

    t = re.sub(r"`([^`]+)`", codigo, t)
    t = re.sub(r"&lt;(https?://[^&\s]+)&gt;", r'<a href="\1" target="_blank" rel="noopener">\1</a>', t)
    # nombres de video sueltos en tablas (ej. pivote-con-marca.mp4)
    t = re.sub(r"\b([a-z0-9-]+)\.mp4\b",
               lambda m: f'<a class="vid" href="#ej-{m.group(1)}">▶ video</a>' if m.group(1) in ids else m.group(0), t)
    return t


def md_a_html(texto, ids):
    out, lista, tabla = [], None, []

    def cerrar_lista():
        nonlocal lista
        if lista:
            out.append(f"</{lista}>")
            lista = None

    def cerrar_tabla():
        nonlocal tabla
        if not tabla:
            return
        filas = [f for f in tabla if not re.match(r"^\|[\s:|-]+\|$", f)]
        h = ['<div class="tabla"><table>']
        for i, f in enumerate(filas):
            celdas = [c.strip() for c in f.strip().strip("|").split("|")]
            tag = "th" if i == 0 else "td"
            h.append("<tr>" + "".join(f"<{tag}>{inline(c, ids)}</{tag}>" for c in celdas) + "</tr>")
        h.append("</table></div>")
        out.append("".join(h))
        tabla = []

    for linea in texto.splitlines():
        s = linea.rstrip()
        if s.startswith("<!--") or s.endswith("-->") and not s.startswith("|"):
            continue
        if s.startswith("|"):
            cerrar_lista()
            tabla.append(s)
            continue
        cerrar_tabla()
        if not s.strip():
            cerrar_lista()
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", s)
        if m:
            cerrar_lista()
            n = len(m.group(1)) + 1
            out.append(f"<h{n}>{inline(m.group(2), ids)}</h{n}>")
            continue
        m = re.match(r"^\s*(\d+)\.\s+(.*)", s)
        if m:
            if lista != "ol":
                cerrar_lista()
                out.append("<ol>")
                lista = "ol"
            out.append(f"<li>{inline(m.group(2), ids)}</li>")
            continue
        m = re.match(r"^\s*-\s+(.*)", s)
        if m:
            if lista != "ul":
                cerrar_lista()
                out.append("<ul>")
                lista = "ul"
            out.append(f"<li>{inline(m.group(1), ids)}</li>")
            continue
        cerrar_lista()
        out.append(f"<p>{inline(s, ids)}</p>")
    cerrar_lista()
    cerrar_tabla()
    return "\n".join(out)


def sin_titulo(cuerpo):
    return re.sub(r"^#\s+.*\n+", "", cuerpo, count=1)


def para_que(cuerpo):
    m = re.search(r"\*\*Para qué:\*\*\s*(.+)", cuerpo)
    return m.group(1).strip() if m else ""


def quitar_para_que(cuerpo):
    return re.sub(r"^\*\*Para qué:\*\*.*\n?", "", cuerpo, flags=re.M)


def intro_readme(cuerpo):
    """Texto del README sin el titulo y sin la tabla de ejercicios."""
    lineas = [l for l in sin_titulo(cuerpo).splitlines()]
    out, en_tabla = [], False
    for l in lineas:
        if l.startswith("|"):
            en_tabla = True
            continue
        out.append(l)
    return "\n".join(out).strip(), en_tabla


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", action="store_true", help="imprime el mapa de archivos para publicar")
    args = ap.parse_args()

    carpetas = sorted(p for p in ENT.iterdir() if p.is_dir() and re.match(r"\d\d-", p.name))
    # primera pasada: ids y nombres (para linkear referencias cruzadas)
    ids = {}
    for c in carpetas:
        for f in sorted(c.glob("*.md")):
            if f.name == "README.md":
                continue
            meta, _ = frontmatter(f.read_text(encoding="utf-8"))
            ids[f.stem] = meta.get("nombre", f.stem)

    habilidades, ejercicios, media = [], [], {}
    for c in carpetas:
        readme = (c / "README.md").read_text(encoding="utf-8") if (c / "README.md").exists() else ""
        titulo = re.search(r"^#\s+(.*)", readme, re.M)
        intro, _ = intro_readme(readme)
        # la tabla de reglas/charlas (carpeta sin fichas) se muestra entera
        fichas = [f for f in sorted(c.glob("*.md")) if f.name != "README.md"]
        cuerpo_hab = md_a_html(sin_titulo(readme) if not fichas else intro, ids)
        habilidades.append({"id": c.name[3:], "carpeta": c.name, "num": c.name[:2],
                            "nombre": titulo.group(1) if titulo else c.name, "html": cuerpo_hab})
        for f in fichas:
            meta, cuerpo = frontmatter(f.read_text(encoding="utf-8"))
            cuerpo = sin_titulo(cuerpo)
            png, mp4 = c / f"{f.stem}.png", c / f"{f.stem}.mp4"
            item = {
                "id": f.stem, "habilidad": c.name[3:], "nombre": meta.get("nombre", f.stem),
                "nivel": meta.get("nivel", ""), "jugadores": meta.get("jugadores", ""),
                "discos": meta.get("discos", ""), "conos": meta.get("conos", ""),
                "duracion": meta.get("duracion", ""), "intensidad": meta.get("intensidad", ""),
                "fuente": meta.get("fuente", ""), "para_que": para_que(cuerpo),
                "html": md_a_html(quitar_para_que(cuerpo), ids), "png": None, "mp4": None,
            }
            if png.exists():
                item["png"] = f"media/{c.name}/{png.name}"
                media[item["png"]] = str(png.relative_to(RAIZ)).replace("\\", "/")
            if mp4.exists():
                item["mp4"] = f"media/{c.name}/{mp4.name}"
                media[item["mp4"]] = str(mp4.relative_to(RAIZ)).replace("\\", "/")
            ejercicios.append(item)

    semanas = []
    for f in sorted((ENT / "semanas").glob("*.md"), reverse=True):
        txt = f.read_text(encoding="utf-8")
        t = re.search(r"^#\s+(.*)", txt, re.M)
        semanas.append({"id": f.stem, "titulo": t.group(1) if t else f.stem, "html": md_a_html(sin_titulo(txt), ids)})

    programa = md_a_html(sin_titulo((ENT / "programa.md").read_text(encoding="utf-8")), ids)
    equipo = md_a_html(sin_titulo((ENT / "equipo.md").read_text(encoding="utf-8")), ids)

    datos = {"habilidades": habilidades, "ejercicios": ejercicios, "semanas": semanas,
             "programa": programa, "equipo": equipo}
    js = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    pagina = PLANTILLA.read_text(encoding="utf-8").replace("/*__DATOS__*/null", js)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(pagina, encoding="utf-8")
    print(f"ok {SALIDA.relative_to(RAIZ)}: {len(habilidades)} habilidades, {len(ejercicios)} ejercicios, "
          f"{sum(1 for e in ejercicios if e['mp4'])} con video, {len(semanas)} semanas")
    if args.files:
        print(json.dumps(media, indent=1))


if __name__ == "__main__":
    main()
