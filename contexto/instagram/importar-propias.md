# Importar material propio (domingos 8:00, en la PC de Franco)

Corre como tarea programada local de la app de Claude, porque OneDrive solo está en esa PC. Tiene que terminar antes de las 14:00 ART, que es cuando la tarea local `austral-instagram-semana` arma la semana con lo que haya en `media/propias/listas/`.

Python: `"$LOCALAPPDATA/Microsoft/WindowsApps/python3.11.exe" -X utf8` (abajo, `PY`). Dependencias: `PY -m pip install -q pillow imageio-ffmpeg`.

## 1. Traer

1. `git pull --rebase` en `C:\Development\Ultimate Austral`. El archivo `PAUSA` no frena esta tarea (acá no se publica nada).
2. `PY herramientas/importar_propias.py`. Copia lo nuevo de `C:\Users\LENOVO\OneDrive\Austral Ultimate` a `media/propias/crudos/` y arma previews en `media/propias/previews/`. Imprime un JSON con `nuevos` y `actualizados` (archivos que pasaron a `con-permiso/`).
3. Si no hay nuevos ni actualizados, terminá con "Sin material nuevo".

Nunca borres ni muevas nada de OneDrive. Nunca agregues a git `crudos/` ni `previews/` (están en `.gitignore`; no uses `git add -f`).

## 2. Calificar

Por cada archivo nuevo, abrí su preview con Read. En los videos, la hoja tiene 12 cuadros con el segundo marcado. Para elegir cortes, pedí una hoja de un cuadro por segundo con `PY herramientas/importar_propias.py --detalle media/propias/crudos/<video> DESDE HASTA`.

Escribí la ficha en `media/propias/CATALOGO.md` con el mismo formato que las existentes: Tipo, Permiso, Puntaje (técnica y contenido, criterios al principio del catálogo), Qué muestra, Tramos buenos y Evitar (videos), Usos, Listas, Usado.
- En "Qué muestra" se describe la escena, nunca a una persona puntual. Sin nombres. Decí si se ven mujeres o solo varones.
- Marcá en "Evitar" los primeros planos de caras de gente que no está jugando, los tramos movidos y todo lo que muestre algo privado (patentes, pantallas, mochilas abiertas).
- Si un archivo es repetido, borroso o no sirve, igual lleva ficha: puntaje 1 y "Usos: ninguno".

En los actualizados (ahora con permiso) cambiá `Permiso` a `sí`.

## 3. Preparar (solo `Permiso: sí` y puntaje 3 o más, con Listas vacío)

- **Foto:** `PY herramientas/importar_propias.py --preparar-foto media/propias/crudos/<foto> --out media/propias/listas/<slug>.jpg`
- **Video:** de 1 a 3 clips limpios (sin texto) de 6 a 15 s con los tramos buenos:
  `PY herramientas/editar_clip.py media/propias/crudos/<video> --tramo A-B [--tramo C-D] --out media/propias/listas/<slug>.mp4`
  Sacá el audio (`--sin-audio`) si es solo viento o se escuchan conversaciones.
- Slug corto y descriptivo, sin nombres de personas: `atardecer-pases-1`, `primera-persona-atrapada`.
- Revisá cada clip con `--detalle` antes de darlo por bueno. Anotá en la ficha qué archivos quedaron en Listas y de qué tramos salen.

## 4. Subir

1. `PY publisher.py validate` y `PY -m unittest discover -s tests`.
2. `git add media/propias/CATALOGO.md media/propias/listas`, commit "Material propio DD/MM: N nuevos, M listos", `git pull --rebase`, `git push origin main`.
3. Resumen corto en español: qué entró, puntaje de cada uno, qué quedó listo para publicar y qué está esperando permiso (para que Franco lo pase a `con-permiso/` si corresponde).
