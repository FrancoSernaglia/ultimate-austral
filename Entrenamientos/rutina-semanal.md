# Rutina semanal de entrenamientos

Corre los miércoles a las 20:00 como tarea programada local en la PC de Franco (`austral-entrenamientos-semana` en la app de Claude). Arma el plan del viernes y sábado de esa semana, renderiza los videos que falten, pushea a `main` y le manda el plan por mail a Franco. No pide aprobación.

## 0. Antes de nada

1. `git pull` en `C:\Development\Ultimate Austral`. Si existe `Entrenamientos/PAUSA`, no hagas nada y terminá.
2. Leé `CLAUDE.md`, `contexto/agenda.md`, `Entrenamientos/README.md`, `Entrenamientos/equipo.md`, `Entrenamientos/programa.md`, `Entrenamientos/feedback.md` y `Entrenamientos/historial.md`.
3. Fijate en la agenda el estado del viernes y del sábado de esta semana:
   - `confirmada`: se arma el plan normal.
   - `a confirmar`: se arma igual, avisando arriba del mail que la fecha no está confirmada.
   - `suspendida` o sin práctica: no se arma ese día. Si no hay ninguno de los dos, mandá un mail corto avisando que no hay práctica y terminá.

## 1. Elegir el foco

1. La semana del ciclo es la siguiente a la última fila de `historial.md` (después de la 8 vuelve a la 1, subiendo a las variantes "más difícil").
2. Leé `feedback.md` (lo más nuevo arriba). Si dice que algo costó o no funcionó, ajustá: repetí el foco con otros ejercicios o metelo como foco 2. Si dice cuántos vinieron, usá ese número en vez de 6.
3. Respetá `equipo.md` (gente, material, cancha). Nunca planifiques un ejercicio que pida más discos o conos de los que hay.

## 2. Armar el plan

1. Seguí la estructura fija de `programa.md` (120 min): calentamiento, lanzamientos en parejas, foco 1, agua + charla, foco 2 o posesión, partido (15 min condicionado + 25 libre) y vuelta a la calma. Siempre más de 40 minutos de partido.
2. Usá fichas de la biblioteca. No repitas el mismo ejercicio de foco en dos semanas seguidas, salvo que el feedback lo pida.
3. Si el foco necesita un ejercicio que no está en la biblioteca, creá la ficha nueva en la carpeta que corresponde siguiendo `plantilla-ejercicio.md` (con palabras propias; si te basaste en un manual de `fuentes.md`, citarlo en `fuente`) y sumala al README de esa carpeta.
4. Escribí `Entrenamientos/semanas/AAAA-MM-DD.md` (fecha del viernes) con el mismo formato que `semanas/2026-11-13.md`: tabla por día con minutos, ficha y video, "lo que Franco mira hoy", y qué hacer si vienen menos o más.

## 3. Videos

1. Para cada ejercicio de foco del plan que tenga `animacion: no`, si se puede mostrar con jugadores moviéndose, escribí el `.json` al lado de la ficha (formato en `Entrenamientos/README.md`), cambiá `animacion:` en la ficha y renderizá:
   `"$LOCALAPPDATA/Microsoft/WindowsApps/python3.11.exe" -X utf8 herramientas/animar_ejercicio.py Entrenamientos/<carpeta>/<ejercicio>.json`
2. Mirá el PNG que sale (Read) antes de seguir: jugadores dentro de la cancha, pases que salen del que tiene el disco, texto que se lee. Si algo está mal, corregí el JSON y volvé a renderizar.
3. Como máximo 2 videos nuevos por semana.

## 4. Publicar

1. Sumá la fila de la semana a `historial.md`.
2. `git add Entrenamientos herramientas/animar_ejercicio.py`, commit con mensaje "Entrenamientos semana <n>: <foco>" y `git push` a `main`. Si el push falla, seguí igual con el mail (avisá en el mail que los links de videos nuevos todavía no andan).

## 5. Mail

Mandalo con el conector de Gmail (`send_message`) a **fsernaglia01@gmail.com**, en `htmlBody` (y el mismo contenido en texto plano en `body`).

- Asunto: `Entrenamiento semana <n>: <foco> (vie DD/MM y sáb DD/MM)`.
- Arriba: foco de la semana en una línea, el objetivo y, si corresponde, aviso de fecha `a confirmar` o de cambios por feedback.
- Una tabla por día (minutos, qué, cómo en una línea). Debajo de cada tabla, "lo que mirás hoy".
- Sección "Videos para el grupo": por cada video, link al MP4 y al diagrama PNG:
  `https://raw.githubusercontent.com/FrancoSernaglia/ultimate-austral/main/Entrenamientos/<carpeta>/<ejercicio>.mp4` (y `.png`).
- Al final: link al plan completo en GitHub (`https://github.com/FrancoSernaglia/ultimate-austral/blob/main/Entrenamientos/semanas/AAAA-MM-DD.md`) y el recordatorio "Después de la práctica anotá 3 líneas en Entrenamientos/feedback.md".
- Estilo del repo: voseo, directo, sin rayas largas, sin "no es X, es Y".
- No adjuntes archivos (los videos van por link).

## Reglas

- No cambies `equipo.md`, `feedback.md` ni `programa.md` (son de Franco), salvo sumar ejercicios nuevos a los README de las carpetas.
- No toques `posts/` ni nada de la rutina de Instagram.
- No mandes mails a nadie más que a fsernaglia01@gmail.com.
