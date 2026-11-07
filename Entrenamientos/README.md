# Entrenamientos

Biblioteca de ejercicios de Austral Ultimate, ordenada por habilidad, y el sistema que cada miércoles arma el plan de viernes y sábado y se lo manda por mail a Franco.

## Cómo está armado

| Carpeta | Qué hay |
|---|---|
| `01-calentamiento/` | Activación, movilidad y prevención de lesiones (rodilla y tobillo) |
| `02-lanzamientos/` | Backhand, forehand, pivote, lanzar con marca, hammer |
| `03-recepcion/` | Atrapar con dos manos (sándwich), en carrera, en el aire |
| `04-cortes/` | Corte en V, timing, despejar, cortes profundos |
| `05-defensa-individual/` | Marca (stall count, forzar), marcar a un cortador |
| `06-ataque-en-equipo/` | Ataque para 3v3 y 4v4, vertical stack, flujo después del pase |
| `07-defensa-en-equipo/` | Forzar todos juntos, cambios, pull y transición |
| `08-juegos-y-partidos/` | Juegos reducidos y formatos de partido para 6 personas |
| `09-reglas-y-espiritu/` | Micro charlas de 5 minutos (se apoyan en `reglas/`) |
| `semanas/` | Un archivo por semana con el plan que se mandó |

Archivos de control (los edita Franco):

- `equipo.md`: cuántos son, nivel, material, cancha. **Si cambia algo, cambialo acá** y la rutina lo toma.
- `feedback.md`: qué salió bien o mal en la última práctica. La rutina lo lee antes de armar la semana siguiente.
- `programa.md`: el ciclo de 8 semanas (qué foco toca cada semana).
- `historial.md`: lo completa la rutina; qué se mandó y qué ejercicios se usaron.
- `rutina-semanal.md`: las instrucciones que sigue el agente cada miércoles.
- `fuentes.md`: manuales y material de referencia.

## Ficha de ejercicio

Cada ejercicio es un `.md` con encabezado fijo (ver `plantilla-ejercicio.md`). Si tiene animación, al lado va un `.json` con el mismo nombre y, una vez renderizado, el `.mp4` (video) y el `.png` (diagrama fijo).

## Animaciones

`herramientas/animar_ejercicio.py` dibuja la cancha vista desde arriba, mueve a los jugadores y hace volar el disco. Sale un MP4 1080x1350 de 10 a 20 s (entra en WhatsApp e Instagram) y un PNG con todos los recorridos.

```
"$LOCALAPPDATA/Microsoft/WindowsApps/python3.11.exe" -X utf8 herramientas/animar_ejercicio.py Entrenamientos/04-cortes/corte-en-v.json
```

Formato del JSON (metros; `x` es el ancho, `y` crece hacia donde se ataca):

```json
{
  "titulo": "Corte en V: amagá profundo, volvé al disco",
  "cancha": {"ancho": 20, "largo": 26},
  "conos": [[6, 4], [6, 22]],
  "lineas": [[[0, 20], [20, 20]]],
  "zonas": [{"desde": 20, "hasta": 26}],
  "jugadores": {
    "L": {"equipo": "ataque", "pos": [6, 5], "label": "L"},
    "D": {"equipo": "defensa", "pos": [7, 6], "label": "D"}
  },
  "disco": {"en": "L"},
  "intro": "Texto mientras arranca",
  "pasos": [
    {"dur": 1.4, "texto": "Lo que pasa en este paso", "mover": {"L": [8, 8]}},
    {"dur": 1.8, "texto": "Pase", "mover": {"C1": [14, 13]}, "pase": {"a": "C1", "inicio": 0.55, "curva": 1.2}},
    {"dur": 1.2, "texto": "Rotación", "mover": {"C1": [6, 5]}, "rastro": false}
  ],
  "cierre": "Texto final",
  "resumen": "Texto del pie en el PNG"
}
```

- `equipo`: `ataque` (amarillo), `defensa` (celeste) o `neutro` (naranja).
- `pase.inicio`: en qué momento del paso sale el disco (0 a 1). `pase.curva`: curva lateral en metros (positivo hacia la izquierda del lanzador, negativo hacia la derecha).
- `"rastro": false`: el paso se anima pero no queda dibujado (rotaciones, volver a la fila).
- `"disco": {"pos": [x, y]}` en vez de `"en"` si el disco arranca en el piso.

## Compartir con el equipo

Los videos quedan en el repo (público). Para mandarlos al grupo de WhatsApp: abrir el link del mail, descargar el MP4 y reenviarlo. También sirven como reel o story (son 4:5).
