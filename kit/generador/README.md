# Generador (ejemplo: short_bola_gomas)

- `guion.txt`: lo que dice la voz, una frase por línea (con la pronunciación adaptada: «Clod Mur», «Guínes»).
- Voz: Piper (`pip install piper-tts`) con la voz `es-carlfm-x-low`, descargada de
  https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-es-carlfm-x-low.tar.gz (Hugging Face no se puede usar desde la nube).
  `python3 -m piper -m es-carlfm-x-low.onnx --length-scale 0.92 -f lN.wav` (una frase por archivo).
- `render.py <carpeta> video.mp4`: dibuja las escenas, el título y los subtítulos palabra a palabra (1080x1920, 30 fps).
  Las escenas y los subtítulos (`CAP`) van dentro del script: para un tema nuevo se cambian `CAP`, `TITLE` y `scene()`.
- `audio.py`: coloca las frases en su sitio y añade música y «pops» generados (sin derechos de autor).
- Mezcla final: `ffmpeg -i video.mp4 -i audio.wav -c:v copy -c:a aac -b:a 192k -ar 48000 -af "acompressor=threshold=-18dB:ratio=3,loudnorm=I=-14:TP=-1.5" short_X.mp4`
