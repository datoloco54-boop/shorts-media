# Cómo ejecutar el kit y elegir temas (léelo antes de crear o proponer)

## Qué hacer según lo que pida el usuario
Manda siempre lo que diga el usuario. Si no dice algo, se usa lo de esta tabla:

| El usuario dice | Qué se hace |
|---|---|
| «ejecuta el kit» (sin más) | **1 vídeo**, tema elegido por Claude, directamente (sin preguntar) |
| «ejecuta el kit con X vídeos» | **X vídeos**, temas elegidos por Claude, directamente |
| «ejecuta el kit con X de actualidad / X aleatorios» | X vídeos de ese tipo |
| «ejecuta el kit sobre <tema>» | ese tema |
| «dime temas» / «propón temas» | se propone una lista, el usuario elige y **solo entonces** se crean |

## Tipos de tema
- **Aleatorio**: datos curiosos atemporales (lugares, animales, historia, ciencia, leyes raras…) en el estilo del canal.
- **Actualidad**: cualquier **noticia viral** de los **últimos 7 días**, de cualquier tema (no solo ciencia):
  EE. UU., España, Argentina, México y el resto de Latinoamérica, o noticias virales del mundo. Se busca en la web el mismo día
  y se cuenta el «dato loco» o el ángulo sorprendente de la noticia.
- Si el usuario no dice qué tipo, **ir variando**: alternar aleatorio y actualidad (en una tanda de varios, mezclar;
  en ejecuciones sueltas, mirar en `kit/temas_hechos.md` qué tipo fue el último y usar el otro).

## Reglas
1. **No repetir**: comprueba `kit/temas_hechos.md` y `pendientes/`, también si es el mismo tema con otro nombre
   (p. ej. Llívia se parece a Baarle: si es así, avisa del parecido).
2. **Actualidad**: comprueba el dato en un medio fiable o en la fuente original. Pon la fecha de la noticia y las fuentes en la descripción.
   En política, contar los hechos sin tomar partido. En noticias con víctimas, tratarlas con respeto, nunca en tono de broma.
3. Al crear cada short, añade su línea a `kit/temas_hechos.md` en el mismo commit, marcada con `[aleatorio]` o `[actualidad]`.
