# Rutina semanal de Instagram (@ultimate.austral)

Corre los domingos a las 14:00 como tarea programada local en la PC de Franco (`austral-instagram-semana` en la app de Claude; la rutina de la nube quedó pausada el 27/10/2026 porque su cuenta de GitHub no puede pushear al repo). Deja programada la semana que arranca el lunes. Publica sin aprobación previa de Franco (lo pidió el 18/10/2026); el control es este archivo, la agenda y el botón de pausa.

## 0. Antes de nada

1. `git pull`. Si existe el archivo `PAUSA` en la raíz del repo, no hagas nada y terminá.
2. Leé `CLAUDE.md`, `contexto/agenda.md`, `contexto/instagram-voice.md`, `contexto/instagram/log.md`, `media/banco/CREDITOS.md`, `media/banco-cc/CREDITOS.md` y `media/propias/CATALOGO.md`.
3. Revisá `posts/`: piezas en `error` (anotá el mensaje en el log y no las toques) y piezas `pendiente` de la semana (no las dupliques).

## 1. Ritmo

| Día (hora ART) | Formato | Qué |
|---|---|---|
| Martes 19:00 | imagen feed | Enseñar: una cosa del ultimate (regla, jugada, Spirit of the Game, glosario: pull, layout, stack, huck, mark) |
| Jueves 19:00 | reel si hay un clip propio sin usar; si no, imagen feed (o carrusel cada 2 semanas) | Invitar: sin experiencia, mixto, mujeres explícitamente, gratis, horario |
| Viernes 10:00 | story (video propio si hay, si no imagen) | "Hoy entrenamos, 17 hs" (solo si la práctica está `confirmada`) |
| Sábado 10:00 | story | "Hoy hay práctica, 16 hs" (solo si está `confirmada`) |

- Horas en `fecha_utc`: ART = UTC-3. 19:00 ART = `22:00:00Z`, 10:00 ART = `13:00:00Z`.
- Si la práctica está `a confirmar` o `suspendida`, no hay story ese día. Si se suspende, el jueves se dice el día que sí hay.
- Si en la agenda aparece un evento `confirmada` en los próximos 14 días, el post del jueves lo anuncia.
- Máximo 2 posts de feed por semana. Menos es mejor que relleno.

## 2. Armar cada pieza

1. Elegí el material, en este orden:
   - **Propio:** un archivo de `media/propias/listas/` cuya ficha en `media/propias/CATALOGO.md` diga `Permiso: sí` y que no se haya usado en las últimas 4 semanas (campo `Usado` y log). Preferí puntaje 4 o 5 y respetá los `Usos` de la ficha.
   - **Stock:** si no hay propio que sirva, una foto de `media/banco/` que no se haya usado en las últimas 4 semanas.
   - **Creative Commons:** si el stock no alcanza, una foto de `media/banco-cc/` (mismo criterio de 4 semanas). El caption **debe** terminar con la atribución de su `CREDITOS.md`: "Foto: <autor> / Wikimedia Commons / <licencia>". Sin ese crédito no se usa.
   Lo que está en `media/propias/crudos/` o fuera de `listas/` no existe para vos (no está en el repo y no tiene permiso confirmado).
2. Imagen (foto del banco o de `listas/`): `pip install pillow` y
   `python herramientas/armar_imagen.py media/banco/<foto>.jpg --formato feed|story --titulo "..." --subtitulo "..." --out media/piezas/<id>.jpg`
   Título corto (máx. 5 palabras). Para carrusel, una imagen por slide (2 a 10) con `--formato feed`.
   Video (reel o story, solo de `listas/`): `pip install pillow imageio-ffmpeg` y
   `python herramientas/editar_clip.py media/propias/listas/<clip>.mp4 --tramo 0-9 --formato reel|story --titulo "..." --subtitulo "..." --out media/piezas/<id>.mp4`
   Reel de 7 a 15 s: lo mejor (disco en el aire, atrapada) en el primer segundo, título de máx. 5 palabras que funcione sin sonido, y el horario de la agenda en el subtítulo. Story de 5 a 10 s. En `posts/<id>.json` el `tipo` es `reel` o `story` y el medio `piezas/<id>.mp4`. El reel lleva caption como cualquier post de feed.
3. Caption (solo feed): seguí `.claude/skills/ig-caption/SKILL.md` (Job B: la primera línea es el hook) y la voz. Cierre siempre con el pedido exacto: `Comentá FRISBEE y te sumamos al grupo de wsp.` Hasta 3 hashtags al final.
4. Limpieza: `python -X utf8 .claude/skills/ig-human/humanize.py` sobre el caption (saca rayas y caracteres invisibles) y `caption.py --keywords "ultimate frisbee,Pilar"`. Los scripts están en inglés: ignorá el WARN de "no call to action".
5. `posts/<id>.json` con `estado: "pendiente"`, `media_id_publicado: null`, medios `piezas/<id>.jpg`. Id = número correlativo + slug (ej. `006-que-es-un-pull`).
6. `python publisher.py validate` y `python -m unittest discover -s tests`. Si algo falla, no pushees esa pieza.

## 3. Reglas duras (si una pieza no las cumple, no sale)

- Nunca decir que somos equipo oficial de la Universidad Austral, ni usar su logo. "En la Universidad Austral" o "en el Parque Empresarial Austral" para el lugar está bien.
- Las fotos de `media/banco/` y `media/banco-cc/` son de terceros: nunca "esta es nuestra práctica", "así entrenamos nosotros" ni nada que haga pasar a esas personas por el equipo.
- El material de `media/propias/listas/` sí es del equipo: ahí está bien "nuestra práctica", "así son los viernes". Pero nada de inventar sobre él: si la ficha no dice cuándo o dónde se filmó, no lo afirmes, y no digas cuánta gente vino ni quiénes son.
- Si en el material propio se ven solo varones (lo dice la ficha), el texto invita a mujeres en forma explícita.
- Nunca inventar números, nombres, resultados, torneos ni testimonios. Solo lo que está en la agenda o en la voz. Si falta un dato, cambiá el ángulo.
- Nunca nombrar ni etiquetar personas.
- Estilo de CLAUDE.md: voseo, humor cercano, sin puteadas, sin "no es X, es Y", sin "no es humo", sin rayas largas.
- Nada de comentar en otras cuentas, mandar DMs, seguir ni likear.
- Sin links en el caption.

## 4. Cerrar

1. Agregá al final de `contexto/instagram/log.md` una línea por pieza: fecha de publicación, id, formato, tema, foto o clip usado. Si usaste material propio, actualizá también el campo `Usado` de su ficha en `media/propias/CATALOGO.md` (fecha e id de la pieza).
2. `git add posts media/piezas media/propias/CATALOGO.md contexto/instagram/log.md`, commit "Semana DD/MM: N piezas programadas", `git pull --rebase`, `git push` a `main`.
3. Mandá un resumen corto: qué quedó programado y cuándo, qué se salteó y por qué, piezas en `error`, si el banco de fotos se está quedando corto (menos de 4 sin usar en el último mes), y cuánto material propio con permiso queda sin usar.
