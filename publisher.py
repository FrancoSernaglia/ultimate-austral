#!/usr/bin/env python3
"""Publicador de Instagram para Ultimate Austral.

Usa solo la libreria estandar y la API oficial "Instagram API with Instagram Login"
(graph.instagram.com). Doc: https://developers.facebook.com/docs/instagram-platform/content-publishing

Subcomandos: validate | dry-run (default) | publish --confirmar | check-limit | refresh-token
"""
import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
MEDIA_DIR = ROOT / "media"

API_HOST = "https://graph.instagram.com"
API_VERSION = os.environ.get("INSTAGRAM_API_VERSION", "v25.0")  # la doc usa v25.0 en sus ejemplos

TIPOS = ("imagen", "carrusel", "reel", "story")
ESTADOS = ("pendiente", "publicado", "error")
IMG_EXT = (".jpg", ".jpeg")  # la doc: solo JPEG
VID_EXT = (".mp4", ".mov")
CAPTION_MAX = 2200
HASHTAGS_AVISO = 5
CARRUSEL_MIN, CARRUSEL_MAX = 2, 10
POLL_INTERVALO_S = 60  # la doc: una vez por minuto
POLL_INTENTOS = 5  # ... durante no mas de 5 minutos
REINTENTOS = 3

log = logging.getLogger("publisher")
_SECRETOS = set()


class ApiError(Exception):
    def __init__(self, mensaje, code=None, status=None):
        super().__init__(mensaje)
        self.code = code
        self.status = status


class PiezaError(Exception):
    pass


# ---------------------------------------------------------------- logging seguro
def registrar_secreto(valor):
    if valor and len(valor) >= 8:
        _SECRETOS.add(valor)


def enmascarar(texto):
    texto = str(texto)
    for s in _SECRETOS:
        texto = texto.replace(s, "***TOKEN***")
    # por si el token aparece en una URL con query string
    return re.sub(r"(access_token=)[^&\s]+", r"\1***TOKEN***", texto)


class _MaskFilter(logging.Filter):
    def filter(self, record):
        record.msg = enmascarar(record.getMessage())
        record.args = ()
        return True


def configurar_logs(verbose=False):
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    h.addFilter(_MaskFilter())
    log.handlers[:] = [h]
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    log.propagate = False


# ---------------------------------------------------------------- cliente HTTP
class Cliente:
    def __init__(self, token, user_id, sleep=time.sleep, poll_intervalo=POLL_INTERVALO_S,
                 poll_intentos=POLL_INTENTOS):
        if not token or not user_id:
            raise ApiError("Faltan INSTAGRAM_ACCESS_TOKEN o INSTAGRAM_USER_ID en el entorno.")
        registrar_secreto(token)
        self.token = token
        self.user_id = user_id
        self.sleep = sleep
        self.poll_intervalo = poll_intervalo
        self.poll_intentos = poll_intentos

    def _request(self, method, url, params=None, bearer=True):
        params = params or {}
        data = None
        if method == "GET":
            if params:
                url += "?" + urllib.parse.urlencode(params)
        else:
            data = urllib.parse.urlencode(params).encode()
        headers = {"Authorization": f"Bearer {self.token}"} if bearer else {}
        ultimo = None
        for intento in range(1, REINTENTOS + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read().decode() or "{}")
            except urllib.error.HTTPError as e:
                cuerpo = e.read().decode(errors="replace")
                try:
                    err = json.loads(cuerpo).get("error", {})
                except ValueError:
                    err = {}
                msg = err.get("message") or cuerpo[:300]
                ultimo = ApiError(enmascarar(f"HTTP {e.code} de la API: {msg} (code={err.get('code')}, "
                                             f"subcode={err.get('error_subcode')})"),
                                  code=err.get("code"), status=e.code)
                transitorio = e.code >= 500 or err.get("is_transient") or err.get("code") in (1, 2, 4, 17)
                if not transitorio:
                    raise ultimo
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                ultimo = ApiError(enmascarar(f"Error de red: {e}"))
            log.warning("Intento %d/%d fallido: %s", intento, REINTENTOS, ultimo)
            if intento < REINTENTOS:
                self.sleep(2 ** intento)
        raise ultimo

    def post(self, path, params):
        return self._request("POST", f"{API_HOST}/{API_VERSION}/{path}", params)

    def get(self, path, params=None):
        return self._request("GET", f"{API_HOST}/{API_VERSION}/{path}", params)

    # --- operaciones de la API
    def crear_contenedor(self, params):
        r = self.post(f"{self.user_id}/media", params)
        if "id" not in r:
            raise ApiError(f"Respuesta inesperada al crear contenedor: {r}")
        return r["id"]

    def esperar_finished(self, container_id):
        estado = None
        for i in range(1, self.poll_intentos + 1):
            r = self.get(container_id, {"fields": "status_code"})
            estado = r.get("status_code")
            log.info("Contenedor %s: %s (%d/%d)", container_id, estado, i, self.poll_intentos)
            if estado in ("FINISHED", "PUBLISHED"):
                return estado
            if estado == "ERROR":
                raise ApiError(f"El contenedor {container_id} quedo en ERROR (Meta no pudo procesar el medio; "
                               "revisa formato, relacion de aspecto, tamano y que la URL sea publica).")
            if estado == "EXPIRED":
                raise ApiError(f"El contenedor {container_id} vencio (EXPIRED, pasaron 24 h).")
            if i < self.poll_intentos:
                self.sleep(self.poll_intervalo)
        raise ApiError(f"El contenedor {container_id} no termino en {self.poll_intentos} intentos "
                       f"(ultimo estado: {estado}).")

    def publicar(self, creation_id):
        r = self.post(f"{self.user_id}/media_publish", {"creation_id": creation_id})
        if "id" not in r:
            raise ApiError(f"Respuesta inesperada al publicar: {r}")
        return r["id"]

    def limite(self):
        return self.get(f"{self.user_id}/content_publishing_limit", {"fields": "quota_usage,config"})

    def refrescar_token(self):
        # Doc: GET graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=...
        url = f"{API_HOST}/refresh_access_token"
        return self._request("GET", url, {"grant_type": "ig_refresh_token", "access_token": self.token},
                             bearer=False)


# ---------------------------------------------------------------- piezas
def cargar_piezas(posts_dir=None):
    posts_dir = Path(posts_dir or POSTS_DIR)
    piezas = []
    for p in sorted(posts_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            raise PiezaError(f"{p.name}: JSON invalido ({e})")
        piezas.append((p, data))
    return piezas


def guardar_pieza(path, data):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def parsear_fecha(s):
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def es_url(m):
    return m.startswith("https://") or m.startswith("http://")


def extension(m):
    return Path(urllib.parse.urlparse(m).path).suffix.lower()


def validar_pieza(data, media_dir=None, nombre=""):
    """Devuelve (errores, avisos)."""
    media_dir = Path(media_dir or MEDIA_DIR)
    errores, avisos = [], []
    for campo in ("id", "fecha_utc", "tipo", "caption", "medios", "estado"):
        if campo not in data:
            errores.append(f"falta el campo '{campo}'")
    if errores:
        return errores, avisos
    if nombre and Path(nombre).stem != str(data["id"]):
        avisos.append(f"el id '{data['id']}' no coincide con el nombre del archivo")
    try:
        parsear_fecha(data["fecha_utc"])
    except ValueError:
        errores.append(f"fecha_utc invalida: {data['fecha_utc']!r} (usar ISO 8601, ej. 2026-10-23T20:00:00Z)")
    tipo, estado = data["tipo"], data["estado"]
    if tipo not in TIPOS:
        errores.append(f"tipo invalido '{tipo}' (validos: {', '.join(TIPOS)})")
    if estado not in ESTADOS:
        errores.append(f"estado invalido '{estado}' (validos: {', '.join(ESTADOS)})")
    if estado == "publicado" and not data.get("media_id_publicado"):
        errores.append("estado publicado sin media_id_publicado")
    caption = data["caption"]
    if not isinstance(caption, str):
        errores.append("caption debe ser texto")
        caption = ""
    if len(caption) > CAPTION_MAX:
        errores.append(f"caption de {len(caption)} caracteres (maximo {CAPTION_MAX})")
    n_hash = len(re.findall(r"(?<!\w)#\w+", caption))
    if n_hash > HASHTAGS_AVISO:
        avisos.append(f"{n_hash} hashtags (mas de {HASHTAGS_AVISO}): el limite cambio en dic. 2025 segun el "
                      "README de instagram-agent-skill; no figura en la doc oficial de publishing")
    medios = data["medios"]
    if not isinstance(medios, list) or not medios or not all(isinstance(m, str) for m in medios):
        errores.append("medios debe ser una lista no vacia de textos")
        return errores, avisos
    if tipo in ("imagen", "reel", "story") and len(medios) != 1:
        errores.append(f"un/a {tipo} lleva exactamente 1 medio (hay {len(medios)})")
    if tipo == "carrusel" and not CARRUSEL_MIN <= len(medios) <= CARRUSEL_MAX:
        errores.append(f"un carrusel lleva de {CARRUSEL_MIN} a {CARRUSEL_MAX} medios (hay {len(medios)})")
    if tipo == "story" and caption:
        avisos.append("las stories no muestran caption; se ignora")
    for m in medios:
        ext = extension(m)
        if tipo == "imagen" and ext not in IMG_EXT:
            errores.append(f"{m}: las imagenes deben ser JPEG (.jpg/.jpeg)")
        elif tipo == "reel" and ext not in VID_EXT:
            errores.append(f"{m}: los reels deben ser MP4 o MOV")
        elif tipo in ("carrusel", "story") and ext not in IMG_EXT + VID_EXT:
            errores.append(f"{m}: formato no soportado (JPEG, MP4 o MOV)")
        if es_url(m):
            if not m.startswith("https://"):
                avisos.append(f"{m}: conviene usar https")
        else:
            f = media_dir / m
            if not f.is_file():
                errores.append(f"{m}: no existe en media/")
            elif f.suffix.lower() in IMG_EXT and f.stat().st_size > 8 * 1024 * 1024:
                errores.append(f"{m}: pesa mas de 8 MB")
    return errores, avisos


def url_publica(m, env=None):
    """Convierte una ruta relativa a media/ en una URL publica que Meta pueda bajar."""
    env = env if env is not None else os.environ
    if es_url(m):
        return m
    base = env.get("MEDIA_BASE_URL")
    if not base and env.get("GITHUB_REPOSITORY"):
        rama = env.get("GITHUB_REF_NAME", "main")
        base = f"https://raw.githubusercontent.com/{env['GITHUB_REPOSITORY']}/{rama}/media"
    if not base:
        raise PiezaError(f"No puedo armar la URL publica de '{m}': defini MEDIA_BASE_URL "
                         "(ej. https://raw.githubusercontent.com/USUARIO/REPO/main/media) o usa URLs https.")
    return base.rstrip("/") + "/" + urllib.parse.quote(m)


def es_video(m):
    return extension(m) in VID_EXT


def plan_publicacion(data, env=None):
    """Describe los parametros que se mandarian a la API (sin llamar a nada)."""
    tipo, caption = data["tipo"], data["caption"]
    urls = [url_publica(m, env) for m in data["medios"]]
    if tipo == "imagen":
        return {"padre": {"image_url": urls[0], "caption": caption}, "hijos": []}
    if tipo == "reel":
        return {"padre": {"media_type": "REELS", "video_url": urls[0], "caption": caption}, "hijos": []}
    if tipo == "story":
        clave = "video_url" if es_video(data["medios"][0]) else "image_url"
        return {"padre": {"media_type": "STORIES", clave: urls[0]}, "hijos": []}
    hijos = []
    for m, u in zip(data["medios"], urls):
        if es_video(m):
            hijos.append({"media_type": "VIDEO", "video_url": u, "is_carousel_item": "true"})
        else:
            hijos.append({"image_url": u, "is_carousel_item": "true"})
    return {"padre": {"media_type": "CAROUSEL", "caption": caption}, "hijos": hijos}


def publicar_pieza(cliente, path, data, env=None):
    """Publica una pieza y persiste el estado. Idempotente."""
    if data.get("estado") == "publicado" or data.get("media_id_publicado"):
        log.info("[%s] ya publicada, se omite.", data["id"])
        return False
    plan = plan_publicacion(data, env)
    creation_id = data.get("creation_id")
    try:
        if creation_id:
            # contenedor de un intento anterior: reutilizarlo evita duplicados
            try:
                cliente.esperar_finished(creation_id)
            except ApiError:
                creation_id = None
        if not creation_id:
            if plan["hijos"]:
                ids = []
                for h in plan["hijos"]:
                    cid = cliente.crear_contenedor(h)
                    cliente.esperar_finished(cid)
                    ids.append(cid)
                plan["padre"]["children"] = ",".join(ids)
            creation_id = cliente.crear_contenedor(plan["padre"])
            data["creation_id"] = creation_id
            guardar_pieza(path, data)  # si algo falla despues, no se pierde el contenedor
            cliente.esperar_finished(creation_id)
        media_id = cliente.publicar(creation_id)
    except (ApiError, PiezaError) as e:
        data["estado"] = "error"
        data["error"] = enmascarar(str(e))
        guardar_pieza(path, data)
        raise
    data["estado"] = "publicado"
    data["media_id_publicado"] = media_id
    data["publicado_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data.pop("creation_id", None)
    data.pop("error", None)
    guardar_pieza(path, data)
    log.info("[%s] publicada. media_id=%s", data["id"], media_id)
    return True


# ---------------------------------------------------------------- comandos
def seleccionar(piezas, ids=None, ignorar_fecha=False, ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    out = []
    for path, data in piezas:
        if ids and data.get("id") not in ids:
            continue
        if data.get("estado") != "pendiente":
            continue
        if not ignorar_fecha and not ids and parsear_fecha(data["fecha_utc"]) > ahora:
            continue
        out.append((path, data))
    return out


def cmd_validate(args):
    hay_error = False
    piezas = cargar_piezas(args.posts_dir)
    if not piezas:
        log.warning("No hay piezas en posts/.")
    for path, data in piezas:
        errores, avisos = validar_pieza(data, nombre=path.name)
        for a in avisos:
            log.warning("%s: %s", path.name, a)
        for e in errores:
            log.error("%s: %s", path.name, e)
        hay_error |= bool(errores)
        if not errores:
            log.info("%s: OK", path.name)
    return 1 if hay_error else 0


def cmd_dry_run(args):
    piezas = cargar_piezas(args.posts_dir)
    sel = seleccionar(piezas, args.id, args.ignorar_fecha)
    if not sel:
        log.info("Nada para publicar (no hay piezas pendientes con fecha vencida).")
        return 0
    for path, data in sel[: args.max]:
        errores, avisos = validar_pieza(data, nombre=path.name)
        for a in avisos:
            log.warning("%s: %s", path.name, a)
        if errores:
            log.error("%s: no se publicaria, errores: %s", path.name, "; ".join(errores))
            continue
        try:
            plan = plan_publicacion(data)
        except PiezaError as e:
            log.error("%s: %s", path.name, e)
            continue
        print(f"[DRY-RUN] {data['id']} ({data['tipo']}) programada {data['fecha_utc']}")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    print("[DRY-RUN] No se llamo a la API de publicacion. Para publicar: publish --confirmar")
    return 0


def cmd_publish(args):
    if not args.confirmar:
        log.error("Falta --confirmar. Sin ese flag no se publica nada (usa dry-run para ver el plan).")
        return 2
    cliente = Cliente(os.environ.get("INSTAGRAM_ACCESS_TOKEN"), os.environ.get("INSTAGRAM_USER_ID"))
    piezas = cargar_piezas(args.posts_dir)
    sel = seleccionar(piezas, args.id, args.ignorar_fecha)[: args.max]
    if not sel:
        log.info("Nada para publicar.")
        return 0
    cupo_ok = verificar_cupo(cliente)
    if not cupo_ok:
        return 1
    fallos = 0
    for path, data in sel:
        errores, avisos = validar_pieza(data, nombre=path.name)
        for a in avisos:
            log.warning("%s: %s", path.name, a)
        if errores:
            log.error("%s: no se publica, errores: %s", path.name, "; ".join(errores))
            fallos += 1
            continue
        try:
            publicar_pieza(cliente, path, data)
        except (ApiError, PiezaError) as e:
            log.error("[%s] fallo: %s", data["id"], e)
            fallos += 1
    return 1 if fallos else 0


def verificar_cupo(cliente):
    """True si hay cupo. Si la respuesta no trae los campos esperados, avisa y sigue."""
    try:
        r = cliente.limite()
    except ApiError as e:
        log.warning("No pude consultar el cupo (%s); sigo igual.", e)
        return True
    try:
        item = r["data"][0]
        usado = item["quota_usage"]
        total = item.get("config", {}).get("quota_total")
        if total is not None and usado >= total:
            log.error("Cupo agotado: %s de %s en la ventana movil de 24 h.", usado, total)
            return False
    except (KeyError, IndexError, TypeError):
        log.warning("Formato de content_publishing_limit no reconocido: %s", r)
    return True


def cmd_check_limit(args):
    cliente = Cliente(os.environ.get("INSTAGRAM_ACCESS_TOKEN"), os.environ.get("INSTAGRAM_USER_ID"))
    print(json.dumps(cliente.limite(), indent=2))
    return 0


def guardar_token_en_env(archivo, nuevo):
    archivo = Path(archivo)
    lineas = archivo.read_text(encoding="utf-8").splitlines() if archivo.exists() else []
    hecho = False
    for i, l in enumerate(lineas):
        if l.startswith("INSTAGRAM_ACCESS_TOKEN="):
            lineas[i] = f"INSTAGRAM_ACCESS_TOKEN={nuevo}"
            hecho = True
    if not hecho:
        lineas.append(f"INSTAGRAM_ACCESS_TOKEN={nuevo}")
    archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def cmd_refresh_token(args):
    cliente = Cliente(os.environ.get("INSTAGRAM_ACCESS_TOKEN"), os.environ.get("INSTAGRAM_USER_ID"))
    r = cliente.refrescar_token()
    nuevo = r.get("access_token")
    if not nuevo:
        log.error("La respuesta no trae access_token: %s", enmascarar(json.dumps(r)))
        return 1
    registrar_secreto(nuevo)
    dias = round(r.get("expires_in", 0) / 86400, 1)
    log.info("Token renovado. Vence en ~%s dias (%s s).", dias, r.get("expires_in"))
    if args.guardar_env:
        guardar_token_en_env(args.guardar_env, nuevo)
        log.info("Nuevo token guardado en %s. Actualiza tambien el secret de GitHub.", args.guardar_env)
    else:
        log.warning("El token nuevo NO se guardo ni se imprimio. Reintenta con --guardar-env .env")
    return 0


# ---------------------------------------------------------------- CLI
def cargar_dotenv(path):
    p = Path(path)
    if not p.is_file():
        return
    for linea in p.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def armar_parser():
    p = argparse.ArgumentParser(description="Publicador de Instagram (API oficial).")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--posts-dir", default=None, help="carpeta de piezas (default: posts/)")
    sub = p.add_subparsers(dest="cmd")

    def comun(sp):
        sp.add_argument("--id", action="append", help="publicar solo estas piezas (repetible)")
        sp.add_argument("--max", type=int, default=1, help="maximo de piezas por corrida (default 1)")
        sp.add_argument("--ignorar-fecha", action="store_true", help="no exigir fecha_utc vencida")

    sub.add_parser("validate", help="valida piezas y formatos")
    comun(sub.add_parser("dry-run", help="muestra que se publicaria (default)"))
    sp = sub.add_parser("publish", help="publica de verdad (requiere --confirmar)")
    comun(sp)
    sp.add_argument("--confirmar", action="store_true")
    sub.add_parser("check-limit", help="consulta el cupo de publicacion")
    sp = sub.add_parser("refresh-token", help="renueva el token de 60 dias")
    sp.add_argument("--guardar-env", metavar="ARCHIVO", help="escribe el token nuevo en este .env")
    return p


def main(argv=None):
    parser = armar_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(argv)
    if args.cmd is None:  # sin subcomando: dry-run
        args = parser.parse_args(argv + ["dry-run"])
    configurar_logs(args.verbose)
    cargar_dotenv(ROOT / ".env")
    comandos = {"validate": cmd_validate, "dry-run": cmd_dry_run, "publish": cmd_publish,
                "check-limit": cmd_check_limit, "refresh-token": cmd_refresh_token}
    try:
        return comandos[args.cmd](args)
    except (ApiError, PiezaError) as e:
        log.error("%s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
