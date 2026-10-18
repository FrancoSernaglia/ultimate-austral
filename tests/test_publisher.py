import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import publisher as P  # noqa: E402

TOKEN = "IGAAsecreto1234567890"


class Resp:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(code, body):
    return urllib.error.HTTPError("http://x", code, "err", {}, io.BytesIO(json.dumps(body).encode()))


def cliente():
    return P.Cliente(TOKEN, "123", sleep=lambda s: None, poll_intervalo=0)


def pieza(**kw):
    d = {"id": "p1", "fecha_utc": "2026-01-01T00:00:00Z", "tipo": "imagen", "caption": "hola",
         "medios": ["https://ejemplo.com/a.jpg"], "estado": "pendiente", "media_id_publicado": None}
    d.update(kw)
    return d


class Validacion(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(P.validar_pieza(pieza()), ([], []))

    def test_caption_largo(self):
        e, _ = P.validar_pieza(pieza(caption="x" * 2201))
        self.assertTrue(any("2201" in x for x in e))

    def test_hashtags_es_warning_no_error(self):
        e, a = P.validar_pieza(pieza(caption="#a #b #c #d #e #f"))
        self.assertEqual(e, [])
        self.assertTrue(any("hashtags" in x for x in a))

    def test_carrusel_cantidad(self):
        e, _ = P.validar_pieza(pieza(tipo="carrusel", medios=["https://e.com/a.jpg"]))
        self.assertTrue(e)
        ok, _ = P.validar_pieza(pieza(tipo="carrusel", medios=["https://e.com/a.jpg", "https://e.com/b.mp4"]))
        self.assertEqual(ok, [])

    def test_formatos(self):
        self.assertTrue(P.validar_pieza(pieza(medios=["https://e.com/a.png"]))[0])
        self.assertTrue(P.validar_pieza(pieza(tipo="reel", medios=["https://e.com/a.jpg"]))[0])

    def test_campos_tipo_y_fecha(self):
        self.assertTrue(P.validar_pieza({"id": "x"})[0])
        self.assertTrue(P.validar_pieza(pieza(tipo="gif"))[0])
        self.assertTrue(P.validar_pieza(pieza(fecha_utc="ayer"))[0])

    def test_medio_local_inexistente(self):
        with tempfile.TemporaryDirectory() as d:
            e, _ = P.validar_pieza(pieza(medios=["no.jpg"]), media_dir=d)
            self.assertTrue(any("no existe" in x for x in e))


class Plan(unittest.TestCase):
    def test_url_local_con_base(self):
        u = P.url_publica("a b.jpg", {"MEDIA_BASE_URL": "https://h/media/"})
        self.assertEqual(u, "https://h/media/a%20b.jpg")

    def test_url_local_sin_base(self):
        with self.assertRaises(P.PiezaError):
            P.url_publica("a.jpg", {})

    def test_tipos(self):
        self.assertEqual(P.plan_publicacion(pieza(tipo="story"))["padre"]["media_type"], "STORIES")
        reel = pieza(tipo="reel", medios=["https://e.com/a.mp4"])
        self.assertEqual(P.plan_publicacion(reel)["padre"]["media_type"], "REELS")
        c = P.plan_publicacion(pieza(tipo="carrusel", medios=["https://e.com/a.jpg", "https://e.com/b.mp4"]))
        self.assertEqual(len(c["hijos"]), 2)
        self.assertEqual(c["hijos"][1]["media_type"], "VIDEO")


class Api(unittest.TestCase):
    @mock.patch("urllib.request.urlopen")
    def test_publicar_imagen_flujo_y_estado(self, uo):
        uo.side_effect = [Resp({"id": "C1"}), Resp({"status_code": "IN_PROGRESS"}),
                          Resp({"status_code": "FINISHED"}), Resp({"id": "M1"})]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "p1.json"
            self.assertTrue(P.publicar_pieza(cliente(), path, pieza()))
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((saved["estado"], saved["media_id_publicado"]), ("publicado", "M1"))
            req = uo.call_args_list[0][0][0]
            self.assertEqual(req.get_header("Authorization"), f"Bearer {TOKEN}")
            self.assertIn("/v25.0/123/media", req.full_url)
            self.assertNotIn(TOKEN, req.full_url)

    @mock.patch("urllib.request.urlopen")
    def test_idempotente(self, uo):
        with tempfile.TemporaryDirectory() as d:
            data = pieza(estado="publicado", media_id_publicado="M9")
            self.assertFalse(P.publicar_pieza(cliente(), Path(d) / "p1.json", data))
            uo.assert_not_called()

    @mock.patch("urllib.request.urlopen")
    def test_container_error_marca_error(self, uo):
        uo.side_effect = [Resp({"id": "C1"}), Resp({"status_code": "ERROR"})]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "p1.json"
            with self.assertRaises(P.ApiError):
                P.publicar_pieza(cliente(), path, pieza())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["estado"], "error")

    @mock.patch("urllib.request.urlopen")
    def test_container_expired(self, uo):
        uo.side_effect = [Resp({"status_code": "EXPIRED"})]
        with self.assertRaisesRegex(P.ApiError, "EXPIRED"):
            cliente().esperar_finished("C1")

    @mock.patch("urllib.request.urlopen")
    def test_timeout_de_polling(self, uo):
        uo.return_value = Resp({"status_code": "IN_PROGRESS"})
        with self.assertRaisesRegex(P.ApiError, "no termino"):
            cliente().esperar_finished("C1")
        self.assertEqual(uo.call_count, 5)

    @mock.patch("urllib.request.urlopen")
    def test_carrusel(self, uo):
        uo.side_effect = [Resp({"id": "H1"}), Resp({"status_code": "FINISHED"}),
                          Resp({"id": "H2"}), Resp({"status_code": "FINISHED"}),
                          Resp({"id": "P"}), Resp({"status_code": "FINISHED"}), Resp({"id": "M2"})]
        with tempfile.TemporaryDirectory() as d:
            data = pieza(tipo="carrusel", medios=["https://e.com/a.jpg", "https://e.com/b.jpg"])
            P.publicar_pieza(cliente(), Path(d) / "p1.json", data)
            body = uo.call_args_list[4][0][0].data.decode()
            self.assertIn("children=H1%2CH2", body)
            self.assertIn("media_type=CAROUSEL", body)

    @mock.patch("urllib.request.urlopen")
    def test_error_api_sin_reintento_en_4xx(self, uo):
        uo.side_effect = http_error(400, {"error": {"message": "Invalid parameter", "code": 100}})
        with self.assertRaisesRegex(P.ApiError, "Invalid parameter"):
            cliente().post("123/media", {})
        self.assertEqual(uo.call_count, 1)

    @mock.patch("urllib.request.urlopen")
    def test_reintenta_5xx(self, uo):
        uo.side_effect = [http_error(500, {"error": {"message": "boom"}}), Resp({"id": "C1"})]
        self.assertEqual(cliente().crear_contenedor({"image_url": "x"}), "C1")
        self.assertEqual(uo.call_count, 2)

    @mock.patch("urllib.request.urlopen")
    def test_reintentos_acotados(self, uo):
        uo.side_effect = urllib.error.URLError("sin red")
        with self.assertRaises(P.ApiError):
            cliente().get("123")
        self.assertEqual(uo.call_count, P.REINTENTOS)

    @mock.patch("urllib.request.urlopen")
    def test_refresh_token(self, uo):
        uo.return_value = Resp({"access_token": "NUEVO_TOKEN_123456", "expires_in": 5184000})
        r = cliente().refrescar_token()
        req = uo.call_args[0][0]
        self.assertIn("grant_type=ig_refresh_token", req.full_url)
        self.assertIn("refresh_access_token", req.full_url)
        self.assertEqual(r["expires_in"], 5184000)

    @mock.patch("urllib.request.urlopen")
    def test_cupo(self, uo):
        uo.return_value = Resp({"data": [{"quota_usage": 5, "config": {"quota_total": 100}}]})
        self.assertTrue(P.verificar_cupo(cliente()))
        uo.return_value = Resp({"data": [{"quota_usage": 100, "config": {"quota_total": 100}}]})
        self.assertFalse(P.verificar_cupo(cliente()))


class Seguridad(unittest.TestCase):
    def test_enmascara(self):
        cliente()
        self.assertNotIn(TOKEN, P.enmascarar(f"fallo con {TOKEN}"))
        self.assertNotIn("abc123", P.enmascarar("http://x?access_token=abc123&a=1"))

    @mock.patch("urllib.request.urlopen")
    def test_error_no_filtra_token(self, uo):
        uo.side_effect = http_error(400, {"error": {"message": f"token {TOKEN} invalido"}})
        with self.assertRaises(P.ApiError) as cm:
            cliente().get("123")
        self.assertNotIn(TOKEN, str(cm.exception))


class CLI(unittest.TestCase):
    def test_publish_sin_confirmar(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("urllib.request.urlopen") as uo:
            self.assertEqual(P.main(["--posts-dir", d, "publish"]), 2)
            uo.assert_not_called()

    def test_default_dry_run_no_llama_api(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("urllib.request.urlopen") as uo:
            Path(d, "p1.json").write_text(json.dumps(pieza()), encoding="utf-8")
            self.assertEqual(P.main(["--posts-dir", d]), 0)
            uo.assert_not_called()

    def test_validate_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "p1.json").write_text(json.dumps(pieza(tipo="gif")), encoding="utf-8")
            self.assertEqual(P.main(["--posts-dir", d, "validate"]), 1)

    def test_seleccion_fecha_futura(self):
        piezas = [(Path("a"), pieza(fecha_utc="2999-01-01T00:00:00Z"))]
        self.assertEqual(P.seleccionar(piezas), [])
        self.assertEqual(len(P.seleccionar(piezas, ignorar_fecha=True)), 1)

    def test_guardar_token_env(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / ".env"
            f.write_text("INSTAGRAM_USER_ID=1\nINSTAGRAM_ACCESS_TOKEN=viejo\n", encoding="utf-8")
            P.guardar_token_en_env(f, "nuevo")
            txt = f.read_text()
            self.assertIn("INSTAGRAM_ACCESS_TOKEN=nuevo", txt)
            self.assertIn("INSTAGRAM_USER_ID=1", txt)


if __name__ == "__main__":
    unittest.main()
