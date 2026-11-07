# Austral Ultimate

Proyecto de Franco: fundar y organizar un equipo mixto de ultimate frisbee en la Universidad Austral (Pilar). Este repo contiene el publicador de Instagram (`publisher.py`, `posts/`, `media/`) y `reglas/`: las reglas WFDF 2025-2028 explicadas en castellano por sección (con número de regla), más `reglas/contenido-redes.md` con ideas de posts. Para cualquier contenido que hable de reglas, partí de ahí.

Antes de trabajar leé el contexto en `contexto/` (memoria y diagnóstico son locales, no se suben porque el repo es público; si no están, seguí con el resto):
- `contexto/diagnostico-inicial.md`: situación al 26/09/2026, riesgos, norte y preguntas abiertas.
- `contexto/instagram-voice.md`: voz de marca para Instagram. Los `{{completar}}` los define Franco, no los inventes.
- `contexto/memoria.md`: datos de Franco y del equipo (horarios, objetivo) y preferencias de estilo.

Reglas de estilo:
- Español rioplatense informal (voseo), directo, con salidas concretas.
- Evitar "no es X, es Y" (decir directo "Es Y"), evitar "no es humo", y no usar guiones largos entre rayas (usar paréntesis o comas).
- No afirmar que es equipo oficial de la Universidad Austral hasta que haya reconocimiento formal con Deportes.

## Entrenamientos

`Entrenamientos/` tiene la biblioteca de ejercicios por habilidad (una ficha `.md` por ejercicio, con animación `.json` → `.mp4`/`.png` hecha con `herramientas/animar_ejercicio.py`) y el sistema semanal: cada miércoles 20:00 una tarea programada local (`austral-entrenamientos-semana`) sigue `Entrenamientos/rutina-semanal.md`, arma el plan de viernes y sábado en `Entrenamientos/semanas/`, pushea a `main` y se lo manda por Gmail a Franco (fsernaglia01@gmail.com). Franco controla con `Entrenamientos/equipo.md` (gente y material), `feedback.md` y `programa.md`; pausa con un archivo `Entrenamientos/PAUSA`.

## Skills de Instagram (`.claude/skills/ig-*`)

Instaladas desde github.com/Jakeschincariol/instagram-agent-skill (commit d03c56b, MIT). Las skills nombran rutas en `~/.claude/instagram/`; en este proyecto usá estas:
- `voice.md` → `contexto/instagram-voice.md`
- `log.md`, `plan.md`, `swipe.md` → `contexto/instagram/` (mismo nombre de archivo)

Python: no está en el PATH. Usá `"$LOCALAPPDATA/Microsoft/WindowsApps/python3.11.exe" -X utf8 <script>` (sin `-X utf8` los scripts rompen con emojis en la consola de Windows).

Los scripts (hookscore, detect, humanize) están calibrados en inglés: en español sirven para limpiar rayas y caracteres invisibles y para el lint de caption, pero el puntaje de hooks y la lista de "slop" no detectan patrones en castellano. Tomá esos números como orientación, no como veredicto.

## Publicación autónoma

Desde el 18/10/2026 Franco pidió que la cuenta se gestione sola, sin aprobación previa. Cada domingo a las 14:00 una tarea programada local (`austral-instagram-semana`, en la PC de Franco) sigue `contexto/instagram/rutina.md`: arma la semana en `posts/` (con imágenes de `herramientas/armar_imagen.py` en `media/piezas/`) y pushea a `main`; GitHub Actions publica cada pieza cuando llega su `fecha_utc`.
- `contexto/agenda.md` manda sobre fechas y horarios; solo se anuncia lo `confirmada`.
- Pausa: crear un archivo `PAUSA` en la raíz (frena la rutina) o poner `PUBLICAR_REAL=false` en el environment "Instagram Env" (frena Actions).
- Fotos: solo de `media/banco/` (stock, ver `CREDITOS.md`), `media/banco-cc/` (Creative Commons de Wikimedia Commons, ver su `CREDITOS.md`; **exigen atribución en el caption**: "Foto: autor / Wikimedia Commons / licencia") o material propio de `media/propias/listas/` (ver `media/propias/CATALOGO.md`). Infografías en `media/infografias/` (en inglés, rehacer en castellano citando la fuente). Videos y posts de terceros (`contexto/recursos-externos.md`): solo con permiso del autor, nunca descargados por la rutina.
- Material propio: Franco lo sube a OneDrive (`Austral Ultimate/`). Desde el 06/11/2026 todo lo propio del equipo está autorizado, con caras (autorización general de Franco para mostrar comunidad); `con-permiso/` ya no es requisito. Cada domingo a las 8:00 una tarea local sigue `contexto/instagram/importar-propias.md`: copia a `media/propias/crudos/` (fuera de git), califica en el catálogo y deja clips y fotos limpios en `listas/`.
