# Publicador de Instagram – Ultimate Austral (@ultimate.austral)

Script en Python 3 (solo librería estándar) que publica en Instagram con la **API oficial**
(*Instagram API with Instagram Login*, `graph.instagram.com`). Sin herramientas de terceros ni APIs privadas.
Doc de referencia: <https://developers.facebook.com/docs/instagram-platform/content-publishing>

## Estructura

```
publisher.py          # el script (validate, dry-run, publish, check-limit, refresh-token)
posts/                # una pieza por archivo JSON
media/                # imágenes/videos locales (el repo debe ser público)
tests/                # unittest con mocks, sin red
.github/workflows/publish.yml
.env.example          # copiar a .env (ignorado por git)
```

## Formato de una pieza (`posts/<id>.json`)

| Campo | Detalle |
|---|---|
| `id` | igual al nombre del archivo |
| `fecha_utc` | ISO 8601 en **UTC**. 17:00 ART = `20:00:00Z` |
| `tipo` | `imagen`, `carrusel`, `reel` o `story` |
| `caption` | hasta 2200 caracteres (las stories lo ignoran) |
| `medios` | URLs https o rutas relativas a `media/`. Imagen/reel/story: 1. Carrusel: 2 a 10 |
| `estado` | `pendiente`, `publicado` o `error` |
| `media_id_publicado` | lo completa el script |

El script agrega solos `publicado_utc`, `creation_id` (contenedor en curso) y `error`.
Una pieza en `error` **no se reintenta sola**: revisá el mensaje, corregí y volvela a `pendiente`.

Formatos: imágenes JPEG (hasta 8 MB); videos MP4/MOV. Los medios deben ser públicos al momento de publicar.

## Uso

```bash
python publisher.py validate                 # valida piezas y formatos
python publisher.py                          # = dry-run: muestra qué publicaría, no publica
python publisher.py publish --confirmar      # publica (máx. 1 pieza por corrida; --max N para más)
python publisher.py publish --confirmar --id 001-story-prueba --ignorar-fecha
python publisher.py check-limit              # cupo de publicación (muestra el JSON crudo de la API)
python publisher.py refresh-token --guardar-env .env
python -m unittest discover -s tests -v      # tests
```

`publish` sin `--confirmar` no hace nada. Una pieza publicada nunca se vuelve a publicar.
Los logs enmascaran el token. Reintentos: 3 intentos con espera creciente solo ante errores de red/5xx;
el estado del contenedor se consulta 1 vez por minuto, hasta 5 veces.

## Configuración en Meta (paso a paso)

1. La cuenta @ultimate.austral tiene que ser **profesional** (Business o Creator): Instagram → Configuración → Tipo de cuenta.
2. Entrá a <https://developers.facebook.com/> con tu usuario de Facebook → **Mis apps → Crear app**.
3. Elegí el caso de uso/tipo que incluya **Instagram** (API con inicio de sesión de Instagram). Poné nombre (ej. "Ultimate Austral Publisher").
4. En el panel de la app: **Instagram → API setup with Instagram login**.
5. Agregá la cuenta: **App Roles → Roles → Instagram Testers → Add**, buscá `ultimate.austral`.
   Luego, desde Instagram (web) → Configuración → *Apps y sitios web* → **Invitaciones de tester** → aceptar.
6. En *API setup*, sección **Generate access tokens**, agregá la cuenta y generá el token. Marcá los permisos
   `instagram_business_basic` e `instagram_business_content_publish`.
7. Ahí mismo vas a ver el **ID de la cuenta de Instagram** (es el `INSTAGRAM_USER_ID`).
8. Guardá ambos valores:
   - Local: copiá `.env.example` a `.env` y completalos (el `.env` está en `.gitignore`).
   - GitHub: repo → Settings → Secrets and variables → Actions → **Secrets**: `INSTAGRAM_ACCESS_TOKEN` e `INSTAGRAM_USER_ID`.
9. Probá: `python publisher.py check-limit`. Si devuelve JSON, la conexión anda.

### Qué NO está confirmado en la doc oficial

- **Si el rol Instagram Tester alcanza para publicar en tu propia cuenta sin App Review.** La página de content-publishing no
  menciona roles ni App Review; solo dice que el *Standard Access* cubre cuentas propias agregadas a la app y que el *Advanced Access*
  hace falta para cuentas de terceros. Es lo esperable, pero se verifica en la práctica con la Story de prueba.
- **Duración del token:** la doc de Business Login dice que el token de larga duración dura **60 días** (`expires_in` ≈ 5.18 millones de segundos).
  El token generado en el panel ya es de larga duración; si usás uno corto, hay que canjearlo (`ig_exchange_token`, del lado servidor, con el app secret).
- **Límite de publicaciones:** la doc dice 100 posts/24 h en un lado y 50 en la sección de carruseles. No se hardcodea: el script consulta `content_publishing_limit` y corta si el cupo está agotado. Los nombres de campos (`quota_usage`, `config.quota_total`) vienen de otras fuentes, no de esa página; si no los reconoce, avisa y sigue.
- **Caption de 2200 caracteres, hashtags, relación de aspecto (4:5 a 1.91:1) y duración de reels:** no figuran en la página de publishing. El script valida el caption y avisa (warning) con más de 5 hashtags, según lo indicado.

## Renovar el token (cada < 60 días)

La API (`GET /refresh_access_token?grant_type=ig_refresh_token`) exige que el token tenga **al menos 24 h** y **no esté vencido**.
Un token que pasa 60 días sin renovarse muere y hay que generar otro desde el panel.

1. Local: `python publisher.py refresh-token --guardar-env .env` (no imprime el token).
2. Actualizá el secret en GitHub con el valor nuevo de tu `.env` (Settings → Secrets → `INSTAGRAM_ACCESS_TOKEN` → Update).
   `GITHUB_TOKEN` no puede modificar secrets, por eso la renovación en Actions no es automática.
3. Poné un recordatorio en el calendario cada 45 días.

## GitHub Actions

1. Repo **público** (Meta baja las imágenes por URL; las rutas de `media/` se convierten a `raw.githubusercontent.com`).
2. Corre cada hora (cron en **UTC**; Argentina es UTC-3) y también a mano desde *Actions → Run workflow*.
3. Siempre hace tests + validate + **dry-run**. Publica solo si existe la variable de repo
   `PUBLICAR_REAL=true` (Settings → Secrets and variables → Actions → **Variables**). En ejecución manual, además hay que tildar "publicar".
4. Tras publicar, hace commit del estado de `posts/`.

## Primera prueba: Story

1. Poné una imagen JPEG vertical (9:16 ideal) en `media/story_prueba.jpg` y subí el repo.
2. `python publisher.py validate` y `python publisher.py` (dry-run). Revisá el plan.
3. Cuando lo apruebes: `python publisher.py publish --confirmar --id 001-story-prueba --ignorar-fecha`.
4. La Story vence sola a las 24 h. La API no permite borrar posts: si probás con un post de feed, se borra a mano desde la app.
