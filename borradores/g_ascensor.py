# g_ascensor.py — Manual irónico n.º 17 (22-nov-2026): «Cierre Exprés Antivecinos™». Tema elegido por Claude (Jesús: «crea un short viral»).
# Costumbre: apretar el botón de cerrar puertas del ascensor una y otra vez, sobre todo cuando alguien viene corriendo.
# Por qué este tema (métricas, 22-nov-2026): el «botón inútil» del semáforo es el vídeo que mejor retiene del canal (97 % visto,
# 63 % llega al final); el formato rinde con temas propios y un giro en el último tercio. Aquí el giro es el propio dato.
# Dato real del cierre:
#  - Normas ADA de EE. UU. (Access Board, guía del cap. 4, §407.3.4 y §407.3.5, primaria): las puertas tienen que quedarse
#    abiertas un tiempo mínimo al llegar a un piso (mín. 3 s abiertas del todo, y un mínimo de 5 s entre el aviso de llegada
#    y el cierre) y ni el funcionamiento automático ni el botón de cerrar pueden acortarlo.
#  - The New York Times (oct-2016), citado por CBS News Boston y ABC7: Karen Penafiel (National Elevator Industry Inc.) dijo
#    que los botones de cerrar que funcionan se fueron retirando desde la ley ADA de 1990; bomberos y mantenimiento tienen
#    llaves o códigos con los que sí funcionan.
#  MATIZ (va en la descripción): pasado el tiempo mínimo, en muchos ascensores el botón sí cierra; fuera de EE. UU. depende
#  del país. Por eso la voz dice «no lo acorta» y «en muchos», no «no funciona nunca». EVITADO: «el 80 % no funcionan»
#  (lo dijo un técnico, sin más fuente).
# Deseos por grupo (apartado 0b): poder y control (el gancho: «que nadie más se suba contigo»), juego (la guerra de botones
# con las puertas que se abren y cierran solas), protección (el dato: la espera es para quien va en silla de ruedas) y
# pertenencia (la pregunta final: «¿cerrar o abrir?»).
# Decorado nuevo: tresd.ascensor() (rellano con puertas que se deslizan y cabina con botonera; pon_cabina / pon_rellano).
# Objeto-metáfora: el botón dorado de «cerrar» (tresd.boton_oro). Recursos nuevos: la guerra de botones (puertas que
# van y vienen), el marcador «LOLO 1 · VECINO 0» y el botón que salta de la botonera y deja ver el cable suelto.
import math, functools
from PIL import Image, ImageDraw
import tresd as T
import ui
from ui import clamp, eo, eb
from personaje import lolo

AMARILLO = {"BOTÓN", "ANTIVECINOS", "CORRE", "APRIETAS", "ESPERA", "FUERTE", "SALUDA", "DOS", "CARA", "GANASTE", "ABRIR", "GUERRA",
            "REAL", "RUEDAS", "ACORTA", "BOMBEROS", "CORRER"}
DICHO = {"«": "", "»": ""}
PRIMER_CORTE = lambda k: k.at(0, 6)                          # corte en «botón»
PREGUNTA = "¿Tú aprietas cerrar o abrir?"
W_, H_ = 1080, 1920
ORO = (255, 205, 50)
VEC = dict(sudadera=(0, 180, 150), gorro=(70, 46, 40), pompon=False, pant=(60, 60, 70))
LOLO3 = (0.1, 0, 0.8)

def vecino(paso=0.0, brazo=0.2, brazo2=0.2): return T.persona(paso=paso, brazo=brazo, brazo2=brazo2, **VEC)
def lolo3(brazo2=1.0, brazo=0.2): return T.persona(brazo=brazo, brazo2=brazo2)

def escena(abre, vz=None, vx=-0.4, vpaso=0.0, vbr=(0.2, 0.2), lbr=1.0, dentro=False, flecha=0.0, boton=None):
    e = T.ascensor(abre, dentro=dentro, flecha=flecha)
    T.pon_cabina(e, lolo3(lbr), LOLO3, yaw=math.pi)
    if vz is not None: T.pon_rellano(e, vecino(vpaso, *vbr), (vx, 0, vz))
    if boton is not None: T.pon_rellano(e, T.boton_oro(), boton[0], yaw=boton[1], esc=boton[2])
    return e

def rotulo(img, cam, p, txt, size_k=260, col=ui.AMAR, dy=0.0):
    x, y, z = cam.pantalla(p)
    y = max(y, 500 + dy)                                      # nunca encima de los subtítulos
    if z > 0.3 and 60 < x < 1000: ui.texto(img, txt, min(max(x, 300), 710), y - dy, max(40, min(110, size_k / z)), col)

@functools.lru_cache(maxsize=4)
def fondo(osc=0.6, blur=16):
    e = escena(0.6, vz=-2.0)
    return ui.oscurece(e.render(T.Cam((0.4, 1.6, -4.4), (0.0, 1.25, 0.5), 55)), osc, blur)

# ------------------------------------------------------------------ la botonera en primer plano (2D)
def triangulos(d, cx, cy, s, col, cerrar=True):
    """▶|◀ (cerrar) o ◀|▶ (abrir), centrado en (cx, cy), a escala de capa."""
    for sg in (-1, 1):
        if cerrar: pts = [(cx + sg * s * 1.1, cy - s * 0.6), (cx + sg * s * 0.18, cy), (cx + sg * s * 1.1, cy + s * 0.6)]
        else: pts = [(cx + sg * s * 0.25, cy - s * 0.6), (cx + sg * s * 1.15, cy), (cx + sg * s * 0.25, cy + s * 0.6)]
        d.polygon(pts, fill=col)
    d.rectangle([cx - s * 0.05, cy - s * 0.65, cx + s * 0.05, cy + s * 0.65], fill=col)

def botonera(hund=0.0, brillo=1.0, sin_boton=0.0, t=0.0):
    """Placa de acero con pisos y, abajo, abrir (verde) y CERRAR (dorado). sin_boton 0..1 = el dorado ya saltó (hueco y cable)."""
    L, d = ui.capa(560, 1100); P = lambda *v: [x * 2 for x in v]
    d.rounded_rectangle(P(10, 16, 560, 1100), 60, fill=(110, 114, 126))
    d.rounded_rectangle(P(0, 0, 548, 1084), 60, fill=(196, 200, 210), outline=(236, 238, 244), width=8)
    for i in range(8):
        x, y = (180 if i % 2 == 0 else 370), 150 + (i // 2) * 160
        d.ellipse(P(x - 62, y - 62, x + 62, y + 62), fill=(150, 154, 166)); d.ellipse(P(x - 54, y - 58, x + 54, y + 50), fill=(240, 240, 246))
        d.text((x * 2, (y - 4) * 2), str(8 - i), font=ui.fuente(130), fill=(60, 64, 80), anchor="mm")
    cy = 880
    d.ellipse(P(160 - 78, cy - 78, 160 + 78, cy + 78), fill=(150, 154, 166)); d.ellipse(P(160 - 68, cy - 70, 160 + 68, cy + 62), fill=(60, 200, 120))
    triangulos(d, 320, cy * 2 - 8, 46, (255, 255, 255), cerrar=False)
    if sin_boton < 0.5:
        r = 96 * (1 - 0.08 * hund)
        if brillo > 0: d.ellipse(P(390 - r - 30, cy - r - 30, 390 + r + 30, cy + r + 30), fill=(255, 220, 90, int(110 * brillo)))
        d.ellipse(P(390 - r, cy - r + 10, 390 + r, cy + r + 10), fill=(170, 120, 20))
        d.ellipse(P(390 - r, cy - r, 390 + r, cy + r), fill=ORO if hund < 0.3 else (230, 170, 30), outline=(255, 240, 170), width=8)
        triangulos(d, 780, cy * 2, 54 * (1 - 0.08 * hund), (60, 40, 10))
    else:                                                     # hueco con el cable suelto
        d.ellipse(P(390 - 90, cy - 90, 390 + 90, cy + 90), fill=(30, 26, 40))
        d.line(P(380, cy - 20, 410, cy + 30, 450, cy + 10, 470, cy + 60), fill=(230, 60, 60), width=18)
        d.line(P(470, cy + 60, 490, cy + 70), fill=(200, 140, 60), width=10)
        if int(t * 10) % 2: d.text((520 * 2, (cy + 40) * 2), "✶", font=ui.fuente(100), fill=(255, 230, 90), anchor="mm")
    return L

BX, BY, BE = 505, 980, 0.95                                    # dónde va la botonera y a qué escala
def boton_xy(): return BX + (390 - 280) * BE, BY + (880 - 550) * BE

def plano_boton(t, toques, entra=1.0):
    img = fondo().copy()
    hechos = [x for x in toques if x <= t]; n = len(hechos)
    lt = t - hechos[-1] if hechos else -1
    hund = math.sin(clamp(lt / 0.12) * math.pi) if lt >= 0 else 0.0
    ui.pega(img, botonera(hund, 0.6 + 0.4 * math.sin(t * 9)), BX, BY, esc=BE)
    bx, by = boton_xy()
    ui.onda(img, bx, by, lt, col=(255, 240, 160), r1=170)
    ui.dedo(img, bx + 8, by + 6, pulsa=clamp(lt / 0.12) if lt >= 0 else 0, entra=entra, ang=-10)
    return img, n

def boton_grande(t):
    L, d = ui.capa(300, 300)
    d.ellipse([20, 40, 580, 600], fill=(170, 120, 20)); d.ellipse([20, 20, 580, 580], fill=ORO, outline=(255, 240, 170), width=14)
    triangulos(d, 300, 300, 130, (60, 40, 10))
    return L

# ------------------------------------------------------------------ tomas
def _toques(k): a = k.at(0, 6); return [a + 0.12 + i * 0.16 for i in range(7)]

def t_gancho(t, k):
    tc = k.at(0, 6)
    if t < tc:                                                # desde el fotograma 0: el vecino corre y las puertas se cierran
        vz = -3.3 + 1.0 * t; ab = 1.0 - 0.45 * eo(t / max(0.5, tc))
        e = escena(ab, vz=vz, vx=-0.2, vpaso=t * 11, vbr=(1.7 + 0.2 * math.sin(t * 14), 0.3), lbr=1.0 + 0.15 * math.sin(t * 30))
        cam = T.cam_keys(t, [(0, (1.2, 1.9, -7.2), (-0.2, 1.3, 0.0), 60), (tc, (0.6, 1.65, -4.2), (0.0, 1.3, 0.4), 50)], suave=T.eo)
        sh = 0.03 * math.sin(t * 55) * max(0, 1 - t / 0.7)
        cam = T.Cam(cam.pos + (sh, sh * 0.5, 0), cam.mira, cam.fov)
        img = T.vineta(e.render(cam))
        if t < 0.05: img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), 0.5)
        if t > 0.15: rotulo(img, cam, (-0.2, 2.25, vz), "¡ESPEREN!", 320, ui.ROSA, dy=20 * eo((t - 0.15) / 0.3))
        return img
    img, n = plano_boton(t, _toques(k), entra=clamp((t - tc) / 0.15))
    if n: ui.contador(img, f"x{n}", 860, 640, t - _toques(k)[n - 1], size=150)
    return img

def t_nombre(t, k):
    img = ui.rayos(t, cols=((240, 180, 40), (180, 110, 20)), brillo=(255, 245, 200))
    ui.pedestal(img, 540, 1240, col=(60, 70, 130))
    ui.pega(img, boton_grande(t), 540, 980 + 14 * math.sin(t * 2.4), esc=0.95 * (0.7 + 0.3 * eb(t / 0.3)), giro=6 * math.sin(t * 1.7))
    ui.placa(img, "CIERRE EXPRÉS\nANTIVECINOS™", 505, 1440, t - k.at(0, 2), size=68)
    if t > k.at(0, 4): ui.sello(img, "SOLO\nPARA TI", 790, 640, t - k.at(0, 4), col=ui.ROJO, giro=8, size=58)
    return img

def _golpes(k): return [k.at(1, 0), k.at(3, 0), k.at(5, 0)]

def t_tres(t, k):
    D = k.dur; u = t / D
    vz = -3.0 + 1.7 * eo(u); vx = -2.5 + 2.0 * eo(u); ab = 0.9 - 0.5 * u
    saluda = t >= k.at(4, 0)
    vbr = (2.0 + 0.25 * math.sin(t * 16), 0.3) if saluda else (1.6, 0.4)
    g = _golpes(k); n = len([x for x in g if x <= t])
    lbr = 1.0 + (0.08 + 0.06 * n) * math.sin(t * (20 + 8 * n))
    e = escena(ab, vz=vz, vx=vx, vpaso=0 if saluda else t * 11, vbr=vbr, lbr=lbr)
    if n >= 3: T.pon_cabina(e, T.persona(brazo=lbr, brazo2=lbr), LOLO3, yaw=math.pi)   # con las dos manos
    cam = T.cam_keys(t, [(0, (1.9, 1.75, -5.0), (-0.7, 1.2, -0.6), 60), (D, (1.6, 1.65, -4.3), (-0.5, 1.2, -0.5), 56)])
    img = T.vineta(e.render(cam))
    if k.at(2, 2) <= t < k.at(4, 0): rotulo(img, cam, (vx, 2.3, vz), "¡ESPERAAA!", 300, ui.ROSA, dy=16 * eo((t - k.at(2, 2)) / 0.3))
    if saluda: rotulo(img, cam, (vx, 2.3, vz), "¡HOLA, VECINO!", 280, ui.BLANCO, dy=16 * eo((t - k.at(4, 0)) / 0.3))
    if n: ui.contador(img, ["x3", "x12", "x40"][n - 1], 830, 650, t - g[n - 1], size=[130, 160, 200][n - 1], col=[ui.AMAR, (255, 150, 40), ui.ROJO][n - 1])
    if n >= 3:
        ui.pega(img, lolo("esfuerzo", t), 300, 1330 + (1 - eb((t - g[2]) / 0.3)) * 500, esc=0.72)
        ui.placa(img, "2 MANOS", 300, 1500, t - g[2] - 0.15, size=50, giro=-4)
    return img

def t_cara(t, k):
    tf = k.at(1, 0); tt = min(t, tf)                          # se congela en «sientes»
    tz = k.at(0, 6)                                           # «cara»: las puertas acaban de cerrarse
    ab = 0.4 * (1 - eo(tt / max(0.3, tz)))
    e = escena(ab, vz=-0.85, vx=-0.1, vbr=(1.3, 0.3))
    cam = T.cam_keys(tt, [(0, (-1.4, 1.8, -4.2), (0.15, 1.3, 0.2), 52), (tf, (-1.2, 1.75, -3.6), (0.15, 1.35, 0.2), 48)])
    img = T.vineta(e.render(cam))
    if tt >= tz - 0.05: ui.texto(img, "¡CLAC!", 690, 900, 110 * (1.2 - 0.2 * eo((tt - tz) / 0.2)), ui.AMAR)
    if t >= tf:
        img = ui.congela(img, t - tf)
        ui.pega(img, lolo("chulo", t), 330, 1340 + (1 - eb((t - tf) / 0.3)) * 500, esc=0.8)
        ui.placa(img, "LOLO 1 · VECINO 0", 620, 1020, t - k.at(1, 2), size=56, giro=4)
    return img

def _guerra(t, t0):
    """Puertas de la guerra: desde t0 se abren y se cierran sin parar."""
    if t < t0: return 0.15 + 0.6 * eo(t / 0.8)
    return 0.5 + 0.45 * math.sin((t - t0) * 17)

def t_guerra(t, k):
    t0 = k.at(1, 0)
    ab = _guerra(t, t0)
    e = escena(ab, vz=-0.75, vx=0.85, vbr=(1.0 + 0.12 * math.sin(t * 24), 0.2), lbr=1.0 + 0.15 * math.sin(t * 24 + 1.5))
    sh = 0.02 * math.sin(t * 40) if t > t0 else 0
    cam = T.cam_keys(t, [(0, (-1.0, 1.65, -4.2), (0.45, 1.2, 0.0), 56), (k.dur, (-0.8, 1.6, -3.6), (0.45, 1.25, 0.0), 52)])
    cam = T.Cam(cam.pos + (sh, sh, 0), cam.mira, cam.fov)
    img = T.vineta(e.render(cam))
    if t >= k.at(0, 6): rotulo(img, cam, (0.85, 2.3, -0.75), "¡ABRIR!", 300, ui.VERDE)
    if t > t0:
        if int((t - t0) * 6) % 2: ui.texto(img, "¡CERRAR!", 330, 1250, 90, ui.AMAR)
        else: ui.texto(img, "¡ABRIR!", 720, 1250, 90, ui.VERDE)
        ui.sello(img, "GUERRA DE\nBOTONES", 505, 700, t - k.at(1, 2), col=ui.ROJO, giro=-6, size=80)
    return img

def t_dato(t, k):
    img = fondo(0.74, 14).copy()
    ui.sello(img, "DATO REAL", 505, 520, t - k.at(0, 1), col=ui.TEAL, giro=-5, size=96)
    if t >= k.at(0, 4): ui.contador(img, "LEY DE EE. UU.", 505, 700, t - k.at(0, 4), size=84, col=ui.AMAR, giro=-3)
    t1 = k.at(0, 11)
    if t >= t1:                                               # temporizador de puertas abiertas
        d = ImageDraw.Draw(img); x0, x1, y = 150, 870, 930
        p = clamp((t - t1) / 2.2)
        ui.texto(img, "PUERTAS ABIERTAS", x0, y - 66, 52, ui.BLANCO, ancla="lm")
        d.rounded_rectangle([x0, y - 28, x1, y + 28], 28, fill=(30, 26, 62))
        d.rounded_rectangle([x0, y - 28, x0 + max(56, (x1 - x0) * p), y + 28], 28, fill=ui.VERDE)
        ui.texto(img, "TIEMPO MÍNIMO" if p < 1 else "¡AHORA SÍ!", 505, y + 82, 50, ui.AMAR if p < 1 else ui.VERDE)
    ui.aviso(img, 505, 1270, "PARA QUE ENTRE", "QUIEN VA EN SILLA DE RUEDAS", t - k.at(1, 3), col=ui.TEAL, w=700)
    ui.fuente_chip(img, "Fuente: normas ADA de EE. UU. (Access Board)", t - k.at(0, 6), y=1515)
    return img

def llave(t):
    L, d = ui.capa(330, 140)
    d.ellipse([10, 30, 230, 250], fill=ORO, outline=(150, 100, 10), width=10); d.ellipse([80, 100, 160, 180], fill=(0, 0, 0, 0))
    d.rectangle([210, 120, 640, 160], fill=ORO)
    for x in (520, 590): d.rectangle([x, 160, x + 34, 230], fill=ORO)
    return L

def t_dato2(t, k):
    img = fondo(0.74, 14).copy()
    ui.sello(img, "DATO REAL", 505, 520, 5.0, col=ui.TEAL, giro=-5, size=96)
    ts = k.at(0, 5)                                           # «acorta»: el botón salta
    u = clamp((t - ts) / 0.6)
    ui.pega(img, botonera(0, 0.5, sin_boton=1.0 if t >= ts else 0.0, t=t), 330, 1060, esc=0.62)
    if t >= ts and u < 1:                                     # el botón sale volando
        bx, by = 330 + (390 - 280) * 0.62, 1060 + (880 - 550) * 0.62
        ui.pega(img, boton_grande(t), bx + 380 * u, by - 520 * math.sin(u * math.pi * 0.8) + 300 * u * u, esc=0.35, giro=u * 400)
    if t >= ts: ui.sello(img, "NO ACORTA\nNADA", 760, 760, t - ts - 0.1, col=ui.ROJO, giro=7, size=62)
    tb = k.at(1, 6)
    if t >= tb:
        ui.pega(img, llave(t), 760, 960 + (1 - eb((t - tb) / 0.3)) * 300, esc=0.7, giro=-15)
        ui.placa(img, "SOLO CON LLAVE\nDE BOMBEROS", 760, 1120, t - tb - 0.1, size=44, giro=3)
    if t >= ts + 0.3: ui.pega(img, lolo("sorpresa", t), 850, 1430 + (1 - eb((t - ts - 0.3) / 0.3)) * 400, esc=0.42)
    ui.fuente_chip(img, "Fuente: The New York Times (2016), vía CBS News", t - k.at(1, 0), y=1515)
    return img

def t_cierre(t, k):
    e = escena(1.0, vz=-1.4, vx=-0.9, vbr=(0.3, 0.3), boton=((-0.6, 2.1, -0.6), t * 1.3, 1.8))
    cam = T.cam_keys(t, [(0, (0.6, 1.7, -4.6), (0.0, 1.6, 0.3), 56), (k.dur, (0.4, 1.65, -4.0), (0.0, 1.65, 0.3), 54)])
    img = ui.oscurece(T.vineta(e.render(cam)), 0.2)
    tl = k.at(0, 7)
    g = "chulo" if t < tl else "feliz"
    ui.pega(img, lolo(g, t, banda="REY DEL CERRAR"), 505, 1300 + (1 - eb(t / 0.35)) * 700, esc=1.08)
    ui.placa(img, "EL QUE APRIETA CERRAR\nAL VER A ALGUIEN CORRER", 505, 820, t - k.at(0, 6), size=48, giro=-3)
    ui.pregunta(img, PREGUNTA, t, k, size=54)
    return img


TOMAS = [
    dict(sents=["¿Sabías que tu ascensor tiene un botón para que nadie más se suba contigo?"], dib=t_gancho, pausa=0.4,
         d3=lambda k: k.at(0, 6) / k.dur,
         sfx=[("whoosh", 0.0, 0.8), ("golpe", 0.02, 0.6), ("alarma", 0.3, 0.25), ("clic", _toques, 0.7), ("ding", lambda k: _toques(k)[-1] + 0.15, 0.4)]),
    dict(sents=["Es el Cierre Exprés Antivecinos."], dib=t_nombre, pausa=0.5, corte="whip", d3=0,
         sfx=[("tada", 0.05, 0.5), ("golpe", (0, 4), 0.6)]),
    dict(sents=["¿Alguien corre?", "Lo aprietas.", "¿Te grita «espera»?", "Más fuerte.", "¿Te saluda?", "Con las dos manos."], dib=t_tres,
         pausa=0.5, gap=0.14, d3=1,
         sfx=[("clic", lambda k: [k.at(1, 0) + i * 0.12 for i in range(3)], 0.6), ("clic", lambda k: [k.at(3, 0) + i * 0.08 for i in range(6)], 0.6),
              ("clic", lambda k: [k.at(5, 0) + i * 0.06 for i in range(10)], 0.6), ("golpe", _golpes, 0.6)]),
    dict(sents=["Y cuando se cierran en su cara,", "sientes que ganaste."], dib=t_cara, pausa=0.55, corte="whip", d3=1,
         sfx=[("golpe", (0, 6), 0.8), ("congela", (1, 0), 0.9), ("tada", (1, 2), 0.4)]),
    dict(sents=["Pero si el vecino aprieta abrir…", "empieza la guerra."], dib=t_guerra, pausa=0.6, d3=1,
         sfx=[("clic", (0, 5), 0.7), ("whoosh", lambda k: [k.at(1, 0) + i * 0.185 for i in range(9)], 0.35), ("golpe", (1, 2), 0.8)]),
    dict(sents=["El dato real: en Estados Unidos, la ley obliga a las puertas a esperar un mínimo,", "para que entre alguien en silla de ruedas."],
         dib=t_dato, pausa=0.35, corte="whip", d3=0, sfx=[("golpe", (0, 1), 0.8), ("pop", (0, 4), 0.6), ("sube", (0, 11), 0.4), ("ding", (1, 3), 0.5)]),
    dict(sents=["Y ese botón no lo acorta.", "En muchos, solo funciona con la llave de los bomberos."], dib=t_dato2, pausa=0.55, d3=0,
         sfx=[("pop", (0, 5), 0.8), ("error", lambda k: k.at(0, 5) + 0.3, 0.4), ("ding", (1, 6), 0.5)]),
    dict(sents=["Así que mándaselo a ese amigo que aprieta cerrar cuando ve a alguien correr."], dib=t_cierre, pausa=1.9, d3=1,
         sfx=[("tada", 0.1, 0.5), ("pop", (0, 6), 0.6)]),
]
