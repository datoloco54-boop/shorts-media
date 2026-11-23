# g_momento.py — Manual irónico n.º 22 (24-nov-2026): «El “Solo un momento”™». Tema de la lista del 23-nov-2026 (Jesús: «hazlos»).
# Costumbre: mirar el teléfono «solo un momento» antes de dormir y acabar a las tres de la mañana. Le pasa a TODO el mundo.
# Dato real del cierre: Chang, Aeschbach, Duffy y Czeisler (2015), «Evening use of light-emitting eReaders negatively affects
# sleep, circadian timing, and next-morning alertness», PNAS 112(4), 1232–1237 (primaria; PubMed 25535358; Brigham and Women's
# Hospital / Harvard Medical School y Penn State): leer en una tablet (iPad) antes de dormir frente a un libro de papel →
# casi 10 min más en dormirse y la melatonina de la noche bajó un 55 % (± 20 %). Nota de prensa de Penn State; comentario de
# Van Gelder en PNAS. MATIZ (descripción): 12 adultos, 4 h de lectura en laboratorio; hay una carta (Zeitzer) que dice que en la
# vida real el efecto es menor. En voz: «casi diez minutos más» y «más de la mitad».
# Deseos por grupo (apartado 0b): poder (el gancho: «un botón para alargar la noche»), juego (el reloj que vuela, la cama que se
# ilumina de azul), protección (el dato: la pantalla retrasa el sueño), pertenencia («¿a qué hora sueltas tú el teléfono?»).
# Decorado: tresd.dormitorio() de noche (ocupada=False) con Lolo sentado en la cama y el resplandor azul del teléfono.
# Objeto-metáfora: el teléfono dorado. Recursos nuevos: el reloj digital que salta de hora en hora, el bucle «otra vez».
import math, functools
from PIL import Image, ImageDraw
import tresd as T
import ui
from ui import clamp, eo, eb
from personaje import lolo

AMARILLO = {"NOCHE", "MOMENTO", "VIDEO", "CIEN", "TRES", "ALARMA", "QUÉ", "OTRA", "REAL", "DIEZ", "MITAD", "DUERME"}
DICHO = {"«": "", "»": ""}
PRIMER_CORTE = lambda k: k.at(0, 6)                          # corte en «botón»
PREGUNTA = "¿A qué hora sueltas tú el teléfono?"
MUSICA = 0.09
ORO = (255, 205, 50)
CAMA = (-1.2, 0, 1.85)
AZUL = (120, 190, 255)

def cuarto(hora=23.5, dia=0.0, brillo=1.0, lolo3=True, tumbado=False, br=1.1):
    e = T.dormitorio(dia=dia, hora=hora, lampara=0.0, ocupada=tumbado)
    if lolo3 and not tumbado:
        e.pon(T.persona(sentado=True, brazo=br, brazo2=br), pos=(CAMA[0], 0.12, CAMA[2] + 0.35), yaw=math.pi)
        tel = T.telefono(brillo, AZUL); e.pon(tel, pos=(CAMA[0], 1.3, CAMA[2] - 0.25))
        if brillo > 0.05: e.halo((CAMA[0], 1.2, CAMA[2] - 0.3), AZUL, 0.25, 0.15 * brillo)
    return e

CAM_C = lambda t, D: T.cam_keys(t, [(0, (0.6, 1.9, -1.4), (-1.1, 1.2, 1.9), 54), (D, (0.4, 1.85, -1.0), (-1.1, 1.25, 1.9), 50)])

def hora_txt(h):
    h = h % 24; return f"{int(h):02d}:{int(round((h % 1) * 60)) % 60:02d}"

def digital(img, h, t_golpe, cx=800, cy=640, col=ui.ROJO):
    k = 1.3 - 0.3 * eb(t_golpe / 0.18) if t_golpe >= 0 else 1.0
    L, d = ui.capa(300, 140)
    d.rounded_rectangle([0, 0, 599, 279], 40, fill=(12, 10, 22), outline=(80, 80, 96), width=8)
    d.text((300, 140), hora_txt(h), font=ui.fuente(170), fill=col, anchor="mm")
    ui.pega(img, L, cx, cy, esc=k)

def movil2d(t, scroll=0.0, txt=None):
    """Teléfono en primer plano con un muro de tarjetas que sube."""
    L, d = ui.capa(520, 1000)
    d.rounded_rectangle([0, 0, 1039, 1999], 110, fill=(30, 30, 44)); d.rounded_rectangle([26, 26, 1013, 1973], 90, fill=(14, 12, 34))
    cols = [(230, 90, 120), (90, 160, 240), (255, 190, 60), (0, 190, 150), (200, 120, 220)]
    for i in range(-1, 6):
        y = 120 + i * 380 - (scroll * 380) % 380
        if -300 < y < 1900:
            d.rounded_rectangle([80, y, 960, y + 320], 40, fill=cols[(i + int(scroll)) % 5])
            d.rounded_rectangle([120, y + 230, 700, y + 270], 20, fill=(255, 255, 255))
            d.polygon([(480, y + 100), (480, y + 200), (570, y + 150)], fill=(255, 255, 255))
    if txt: d.text((520, 1850), txt, font=ui.fuente(90), fill=ORO, anchor="mm")
    return L

@functools.lru_cache(maxsize=4)
def fondo(osc=0.6, blur=16):
    return ui.oscurece(cuarto().render(CAM_C(0, 1)), osc, blur)

# ------------------------------------------------------------------ tomas
def _desliza(k): a = k.at(0, 6); return [a + 0.1 + i * 0.3 for i in range(8)]

def t_gancho(t, k):
    tc = k.at(0, 6)
    if t < tc:                                                # desde el fotograma 0: la pantalla se enciende de golpe y Lolo se incorpora
        br = eo(t / 0.15)
        e = cuarto(23.5, brillo=br, br=0.4 + 0.7 * eo(t / 0.4))
        cam = T.cam_keys(t, [(0, (1.6, 2.4, -2.6), (-1.0, 1.0, 1.9), 60), (tc, (0.3, 1.8, -0.8), (-1.1, 1.3, 1.9), 48)], suave=T.eo)
        sh = 0.03 * math.sin(t * 60) * max(0, 1 - t / 0.5)
        cam = T.Cam(cam.pos + (sh, sh, 0), cam.mira, cam.fov)
        img = T.vineta(e.render(cam))
        if t < 0.06: img = Image.blend(img, Image.new("RGB", img.size, AZUL), 0.6)
        if t > 0.1: ui.texto(img, "¡BZZZ!", 700, 760 - 20 * eo((t - 0.1) / 0.3), 110, AZUL)
        digital(img, 23.5, t, 820, 620, ui.VERDE)
        return img
    lt = t - tc; ds = [x - tc for x in _desliza(k)]
    n = len([x for x in ds if x <= lt]); lt0 = lt - ds[n - 1] if n else -1
    img = fondo().copy()
    ui.pega(img, movil2d(lt, n + eo(clamp(lt0 / 0.25)) if n else 0), 505, 1000, esc=0.95)
    ui.dedo(img, 560, 1250 - 260 * eo(clamp(lt0 / 0.25)) if lt0 >= 0 else 1250, pulsa=clamp(lt0 / 0.1) if lt0 >= 0 else 0, entra=clamp(lt / 0.15), ang=-8, esc=0.85)
    digital(img, 23.5 + lt * 0.5, (lt % 0.5), 820, 560, ui.AMAR)
    return img

def t_nombre(t, k):
    img = ui.rayos(t, cols=((60, 60, 160), (30, 30, 100)), brillo=(170, 210, 255))
    ui.pedestal(img, 540, 1270, col=(90, 60, 150))
    ui.pega(img, movil2d(t * 2, t * 2), 540, 880 + 12 * math.sin(t * 2.4), esc=0.55 * (0.7 + 0.3 * eb(t / 0.3)), giro=4 * math.sin(t * 1.7))
    ui.placa(img, "EL «SOLO UN\nMOMENTO»™", 505, 1450, t - k.at(0, 3), size=70)
    return img

def _saltos(k): return [k.at(1, 0), k.at(3, 0), k.at(5, 0)]

def t_tres(t, k):
    D = k.dur; s = _saltos(k); n = len([x for x in s if x <= t])
    h = [23.6, 0.5, 1.6, 3.0][n]
    e = cuarto(h, brillo=1.0)
    cam = CAM_C(t, D)
    img = T.vineta(e.render(cam))
    digital(img, h, t - s[n - 1] if n else -1, 800, 650, [ui.VERDE, ui.AMAR, (255, 150, 40), ui.ROJO][n])
    labs = ["+1 VIDEO", "+100 MENSAJES", "NOTICIAS DE TODO"]
    for i in range(n): ui.placa(img, labs[i], 600, 1150 + i * 120, t - s[i], size=50, col=(255, 255, 255), giro=(-3, 3, -2)[i])
    return img

def t_alarma(t, k):
    tf = k.at(1, 0); tt = min(t, tf)                          # se congela en «dices»
    e = T.dormitorio(dia=0.6, hora=7.0, lampara=0.0, ocupada=True)
    cam = T.cam_keys(tt, [(0, (0.4, 1.7, -0.6), (-1.0, 0.8, 2.0), 52), (tf, (0.2, 1.6, -0.2), (-1.0, 0.8, 2.0), 48)])
    sh = 0.02 * math.sin(tt * 70) if tt > 0.1 else 0
    cam = T.Cam(cam.pos + (sh, sh, 0), cam.mira, cam.fov)
    img = T.vineta(e.render(cam))
    if tt > 0.1 and int(tt * 6) % 2: ui.texto(img, "¡RIIIING!", 505, 760, 110, ui.ROJO)
    digital(img, 7.0, tt - 0.1, 800, 600, ui.ROJO)
    if t >= tf:
        img = ui.congela(img, t - tf)
        ui.pega(img, lolo("aburrido", t), 330, 1340 + (1 - eb((t - tf) / 0.3)) * 500, esc=0.8)
        ui.placa(img, "¿POR QUÉ\nSERÁ?", 660, 1020, t - k.at(1, 6), size=66, giro=4)
    return img

def t_otra(t, k):
    to = k.at(0, 3)                                           # «otra vez»
    e = cuarto(23.5, brillo=1.0 if t >= to - 0.2 else 0.0)
    cam = T.cam_keys(t, [(0, (-0.2, 1.7, -0.2), (-1.15, 1.35, 1.9), 46), (k.dur, (-0.4, 1.65, 0.2), (-1.15, 1.35, 1.9), 42)])
    img = T.vineta(e.render(cam))
    digital(img, 23.5, t - to, 820, 620, ui.VERDE)
    if t >= to:
        ui.sello(img, "OTRA VEZ", 505, 1000, t - to, col=ui.ROJO, giro=-6, size=96)
        ui.pega(img, lolo("chulo", t), 330, 1360 + (1 - eb((t - to) / 0.3)) * 500, esc=0.72)
    return img

def t_dato(t, k):
    img = fondo(0.74, 14).copy()
    ui.sello(img, "DATO REAL", 505, 520, t - k.at(0, 1), col=ui.TEAL, giro=-5, size=96)
    if t >= k.at(0, 7): ui.contador(img, "HARVARD", 505, 690, t - k.at(0, 7), size=84, col=ui.AMAR, giro=-3)
    t10 = k.at(0, 18)
    if t >= t10:
        ui.contador(img, "+10 MIN", 505, 920, t - t10, size=190, col=ui.BLANCO, giro=-3)
        ui.texto(img, "PARA QUEDARSE DORMIDO", 505, 1070, 54, ui.AMAR)
    ui.fuente_chip(img, "Fuente: Chang y otros, PNAS (2015)", t - k.at(0, 11), y=1515)
    return img

def t_dato2(t, k):
    img = fondo(0.74, 14).copy()
    ui.sello(img, "DATO REAL", 505, 520, 5.0, col=ui.TEAL, giro=-5, size=96)
    ui.contador(img, "+10 MIN", 505, 820, 5.0, size=150, col=ui.BLANCO, giro=-3)
    tm = k.at(0, 7)
    if t >= tm:
        d = ImageDraw.Draw(img); x0, x1, y = 150, 870, 1120
        p = 1 - 0.55 * eo((t - tm) / 0.9)
        ui.texto(img, "MELATONINA", x0, y - 62, 50, ui.BLANCO, ancla="lm")
        ui.texto(img, f"−{int(round((1 - p) * 100))} %", x1, y - 62, 50, ui.ROJO, ancla="rm")
        d.rounded_rectangle([x0, y - 28, x1, y + 28], 28, fill=(30, 26, 62))
        d.rounded_rectangle([x0, y - 28, x0 + max(56, (x1 - x0) * p), y + 28], 28, fill=(150, 120, 255))
    if t >= k.at(0, 7) + 1.0: ui.texto(img, "LA HORMONA DEL SUEÑO", 505, 1260, 52, ui.AMAR)
    ui.fuente_chip(img, "Fuente: Chang y otros, PNAS (2015)", 5.0, y=1515)
    return img

def t_cierre(t, k):
    e = cuarto(3.0, brillo=1.0, lolo3=True)
    tel = T.caja(0.3, 0.55, 0.04, ORO); tel.une(T.caja(0.26, 0.48, 0.01, AZUL), pos=(0, 0.035, -0.025)); tel.E = [0.4] * len(tel.E); tel._fin = None
    e.pon(tel, pos=(-0.75, 2.15 + 0.05 * math.sin(t * 3), 1.3), yaw=0.6 * math.sin(t * 1.3))
    cam = T.cam_keys(t, [(0, (0.8, 1.8, -1.8), (-0.7, 1.5, 1.8), 56), (k.dur, (0.6, 1.75, -1.4), (-0.7, 1.5, 1.8), 54)])
    img = ui.oscurece(T.vineta(e.render(cam)), 0.15)
    tl = k.at(0, 7)
    g = "chulo" if t < tl else "feliz"
    ui.pega(img, lolo(g, t, banda="REY DE LA MADRUGADA"), 505, 1300 + (1 - eb(t / 0.35)) * 700, esc=1.08)
    ui.placa(img, "EL QUE DICE «SOLO UN MOMENTO»\nY SE DUERME A LAS TRES", 505, 820, t - k.at(0, 6), size=44, giro=-3)
    ui.pregunta(img, PREGUNTA, t, k, size=54)
    return img


TOMAS = [
    dict(sents=["¿Sabías que tu teléfono tiene un botón para alargar la noche?"], dib=t_gancho, pausa=0.45, d3=lambda k: k.at(0, 6) / k.dur,
         sfx=[("alarma", 0.0, 0.5), ("golpe", 0.02, 0.6), ("whoosh", _desliza, 0.3)]),
    dict(sents=["Se activa diciendo: «solo un momento»."], dib=t_nombre, pausa=0.5, corte="whip", d3=0, sfx=[("tada", 0.05, 0.5), ("golpe", (0, 3), 0.6)]),
    dict(sents=["¿Un video?", "Y otro.", "¿Un mensaje?", "Y cien.", "¿Las noticias?", "Hasta las tres de la mañana."], dib=t_tres, pausa=0.5, gap=0.14, d3=1,
         sfx=[("pop", _saltos, 0.6), ("tic", lambda k: [k.at(5, 0) + i * 0.08 for i in range(10)], 0.3), ("golpe", (5, 2), 0.6)]),
    dict(sents=["Y cuando suena la alarma,", "dices que dormiste fatal… sin saber por qué."], dib=t_alarma, pausa=0.55, corte="whip", d3=1,
         sfx=[("alarma", lambda k: [0.1, 0.6, 1.1, 1.6], 0.6), ("congela", (1, 0), 0.9), ("pop", (1, 6), 0.6)]),
    dict(sents=["Y esa noche, otra vez:", "«solo un momento»."], dib=t_otra, pausa=0.55, d3=1,
         sfx=[("whoosh", 0.05, 0.4), ("golpe", (0, 3), 0.8)]),
    dict(sents=["El dato real: en un experimento en Harvard, leer en una tablet antes de dormir hizo tardar casi diez minutos más en dormirse.",
                ],
         dib=t_dato, pausa=0.35, corte="whip", d3=0, sfx=[("golpe", (0, 1), 0.8), ("pop", (0, 7), 0.6), ("golpe", (0, 18), 0.6)]),
    dict(sents=["Y la melatonina, la hormona del sueño, bajó más de la mitad."], dib=t_dato2, pausa=0.55, d3=0, sfx=[("sube", (0, 7), 0.4), ("error", lambda k: k.at(0, 7) + 0.9, 0.4)]),
    dict(sents=["Así que mándaselo a ese amigo que dice «solo un momento» y se duerme a las tres."], dib=t_cierre, pausa=1.9, d3=1,
         sfx=[("tada", 0.1, 0.5), ("pop", (0, 6), 0.6)]),
]
