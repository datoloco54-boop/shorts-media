# g_traguito.py — Manual irónico n.º 20 (23-nov-2026): «El Último Traguito™». Tema elegido por Jesús de una lista de 4 («los dos primeros»).
# Costumbre: dejar un traguito (de leche, de refresco, una cucharada de helado) y volver a guardar el envase en la nevera para no
# tirarlo ni reponerlo. Le pasa a TODO el mundo (regla del 23-nov-2026).
# Dato real del cierre: PNUMA / UNEP, «Food Waste Index Report 2024» (primaria, con WRAP; datos de 2022): los hogares tiran
# 79 kg de comida por persona al año (el 60 % de los 1.050 millones de toneladas que se desperdician), más de mil millones de
# platos al día. Prensa: Noticias ONU, IISD. MATIZ (descripción): son estimaciones; la cifra mezcla partes comestibles y no.
# Deseos por grupo (apartado 0b): poder (el gancho: «no tirar nunca un envase»), juego (envases que vuelan a la nevera, la
# nevera que se llena de vacíos), protección (el dato: lo que tiramos en casa), pertenencia («¿en tu casa quién deja el traguito?»).
# Decorado: tresd.cocina(nevera=False) con tresd.nevera_abierta() (nueva, v1.9), brik(), botella(), vaso(). Objeto-metáfora:
# el brik de leche con «1 %». Recursos nuevos: la nevera abierta con baldas, la gota que cae sola en el vaso, la nevera llena de vacíos.
import math, functools
from PIL import Image, ImageDraw
import tresd as T
import ui
from ui import clamp, eo, eb
from personaje import lolo

AMARILLO = {"TRUCO", "TRAGUITO", "LECHE", "GOTAS", "CUCHARADA", "ILUSIÓN", "GOTA", "VACÍOS", "REAL", "79", "PLATOS", "GUARDAR"}
DICHO = {"79 kilos": "setenta y nueve kilos"}
PRIMER_CORTE = lambda k: k.at(0, 4)                          # corte en «truco»
PREGUNTA = "¿En tu casa quién deja el traguito?"
MUSICA = 0.09
ORO = (255, 205, 50)
NEV = (2.4, 0, 2.55)
FAM = dict(sudadera=(0, 180, 150), gorro=(120, 80, 50), pompon=False, pant=(50, 54, 70))
LECHE, NARANJA = (60, 140, 230), (240, 140, 40)

def helado(col=(240, 150, 190)):
    o = T.cilindro(0.08, 0.1, (250, 250, 252), n=10, r1=0.09); o.une(T.cilindro(0.092, 0.015, col, n=10), pos=(0, 0.1, 0)); return o

def nevera(e, abre=1.0, cosas=(), vacios=0):
    e.pon(T.nevera_abierta(abre), pos=NEV)
    for (i, fila, o) in cosas:
        x, y, z = T.baldas_xy(i, fila); e.pon(o, pos=(NEV[0] + x, y, NEV[2] + z))
    for j in range(vacios):                                   # envases vacíos por todas partes
        i, fila = j % 4, (j // 4) % 3; x, y, z = T.baldas_xy(i, fila)
        e.pon(T.brik(LECHE if j % 3 == 0 else (NARANJA if j % 3 == 1 else (230, 70, 70)), h=0.22), pos=(NEV[0] + x + 0.03 * (j // 12), y, NEV[2] + z - 0.1 * (j // 12)))

def cocina(**k):
    e = T.cocina(dia=0.3, nevera=False); nevera(e, **k); return e

def gota(img, x, y, s=1.0):
    d = ImageDraw.Draw(img); r = 16 * s
    d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 250, 255), outline=ui.TINTA, width=4)
    d.polygon([(x - r * 0.8, y - r * 0.5), (x + r * 0.8, y - r * 0.5), (x, y - r * 2.4)], fill=(250, 250, 255))

def brik2d(nivel=0.01, t=0.0, txt=None):
    L, d = ui.capa(260, 520)
    d.polygon([(40, 140), (480, 140), (420, 20), (100, 20)], fill=(236, 236, 240), outline=ui.TINTA)
    d.rectangle([40, 140, 480, 1000], fill=(250, 250, 252), outline=ui.TINTA, width=8)
    d.rectangle([40, 420, 480, 700], fill=LECHE)
    d.text((260, 560), "LECHE", font=ui.fuente(110), fill=(255, 255, 255), anchor="mm")
    y = min(970, 990 - 840 * nivel)                                    # nivel por transparencia (ventana lateral)
    d.rectangle([380, 160, 460, 980], fill=(220, 220, 228)); d.rectangle([380, y, 460, 980], fill=(255, 255, 255), outline=(120, 120, 140), width=4)
    if txt: d.text((260, 860), txt, font=ui.fuente(120), fill=ui.ROJO, anchor="mm", stroke_width=6, stroke_fill=(255, 255, 255))
    return L

@functools.lru_cache(maxsize=4)
def fondo(osc=0.6, blur=16):
    e = cocina(cosas=[(0, 1, T.brik(LECHE)), (1, 1, T.botella(liquido=0.05)), (2, 2, helado())])
    return ui.oscurece(e.render(T.Cam((0.4, 1.7, -1.4), (2.3, 1.1, 2.4), 56)), osc, blur)

CAMN = lambda t, D: T.cam_keys(t, [(0, (1.05, 1.7, -0.1), (2.4, 1.0, 2.45), 56), (D, (1.25, 1.65, 0.3), (2.4, 1.0, 2.45), 52)])
LOLO_N = (1.6, 0, 2.0)

# ------------------------------------------------------------------ tomas
def t_gancho(t, k):
    tc = k.at(0, 4)
    if t < tc:                                                # desde el fotograma 0: el brik vuela a la nevera y la puerta se cierra de golpe
        u = clamp(t / 0.6); ab = 1.0 if t < 0.55 else 1.0 - eo((t - 0.55) / 0.35)
        e = cocina(abre=ab)
        e.pon(T.persona(brazo=1.6 - u), pos=LOLO_N, yaw=math.pi / 2)
        p = (1.9 + (NEV[0] - 0.1 - 1.9) * u, 1.4 + 0.5 * math.sin(u * math.pi) - 0.4 * u, 2.0 + (NEV[2] - 0.08 - 2.0) * u)
        e.pon(T.brik(LECHE), pos=p, yaw=u * 8)
        cam = T.cam_keys(t, [(0, (0.2, 2.0, -1.4), (2.2, 1.1, 2.3), 60), (tc, (1.15, 1.65, 0.1), (2.4, 1.0, 2.45), 50)], suave=T.eo)
        img = T.vineta(e.render(cam))
        if t < 0.05: img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), 0.5)
        if t > 0.8: ui.texto(img, "¡PUM!", 760, 760, 110, ui.AMAR)
        return img
    lt = t - tc
    img = fondo().copy()
    ui.pega(img, brik2d(0.01, lt, "1 %"), 505, 1050 + 10 * math.sin(lt * 3), esc=0.5 + 0.5 * eb(lt / 0.3), giro=-4)
    if lt > 0.5: ui.sello(img, "¡NO SE TIRA!", 505, 1470, lt - 0.5, col=ui.ROJO, giro=-6, size=66)
    return img

def t_nombre(t, k):
    img = ui.rayos(t, cols=((60, 150, 230), (30, 90, 170)), brillo=(230, 245, 255))
    ui.pedestal(img, 540, 1260, col=(60, 70, 130))
    ui.pega(img, brik2d(0.01, t, "1 %"), 540, 940 + 12 * math.sin(t * 2.4), esc=0.62 * (0.7 + 0.3 * eb(t / 0.3)), giro=5 * math.sin(t * 1.7))
    ui.placa(img, "EL ÚLTIMO\nTRAGUITO™", 505, 1450, t - k.at(0, 2), size=72)
    if t >= k.at(0, 10): ui.sello(img, "A LA\nNEVERA", 790, 640, t - k.at(0, 10), col=ui.TEAL, giro=8, size=60)
    return img

def _mete(k): return [k.at(1, 0), k.at(3, 0), k.at(5, 0)]

def t_tres(t, k):
    D = k.dur; m = _mete(k); n = len([x for x in m if x <= t])
    cosas = [(0, 1, T.brik(LECHE)), (1, 1, T.botella(liquido=0.03)), (2, 2, helado())][:n]
    e = cocina(cosas=cosas)
    br = 1.0 + 0.4 * math.sin(clamp((t - (m[n - 1] if n else 0)) / 0.4) * math.pi) if n else 0.4
    e.pon(T.persona(brazo=br), pos=LOLO_N, yaw=math.pi / 2)
    cam = CAMN(t, D)
    img = T.vineta(e.render(cam))
    lab = ["QUEDA: 1 %", "QUEDA: 3 GOTAS", "QUEDA: 1 CUCHARADA"]
    if n: ui.contador(img, lab[n - 1], 505, 650, t - m[n - 1], size=[84, 80, 72][n - 1], col=[ui.AMAR, (255, 150, 40), ui.ROSA][n - 1], giro=-3)
    if n >= 2 and t >= k.at(3, 3): ui.sello(img, "SIN GAS", 760, 1300, t - k.at(3, 3), col=ui.ROJO, giro=8, size=62)
    return img

def t_gota(t, k):
    tf = k.at(1, 0); tt = min(t, tf)                          # se congela en «y le cae»
    e = cocina(cosas=[(1, 1, T.botella(liquido=0.03)), (2, 2, helado())])
    e.pon(T.persona(brazo=1.1, brazo2=0.9, **FAM), pos=(1.35, 0, 1.5), yaw=math.pi / 2)
    u = clamp(tt / 0.8); tilt = u
    e.pon(T.mesa_comedor(0.7, 0.5), pos=(1.95, 0, 1.5)); e.pon(T.vaso(0.0, r=0.06, h=0.16), pos=(1.95, 0.775, 1.5))
    e.pon(T.brik(LECHE), pos=(1.9, 1.3 + 0.1 * tilt, 1.5), yaw=0.3)
    cam = T.cam_keys(tt, [(0, (2.7, 1.55, 0.2), (1.8, 1.05, 1.6), 48), (tf, (2.55, 1.45, 0.5), (1.85, 1.0, 1.55), 42)])
    img = T.vineta(e.render(cam))
    if tt > 0.6:
        x, y, z = cam.pantalla((1.95, 1.25 - 0.4 * clamp((tt - 0.6) / 0.5), 1.5))
        if z > 0.3: gota(img, x, y, 1.6)
    if t >= tf:
        img = ui.congela(img, t - tf)
        ui.pega(img, lolo("chulo", t), 330, 1340 + (1 - eb((t - tf) / 0.3)) * 500, esc=0.8)
        ui.placa(img, "TÉCNICAMENTE\nNO LA TERMINÉ", 650, 1020, t - k.at(1, 3), size=54, giro=4)
    return img

def t_vacios(t, k):
    n = int(clamp(t / max(1.0, k.at(0, 8))) * 24)
    e = cocina(vacios=n)
    e.pon(T.persona(brazo=0.2, brazo2=0.2), pos=LOLO_N, yaw=math.pi / 2)
    cam = T.cam_keys(t, [(0, (1.3, 1.5, 0.5), (2.4, 1.1, 2.5), 52), (k.dur, (1.5, 1.4, 0.9), (2.4, 1.05, 2.5), 46)])
    img = T.vineta(e.render(cam))
    if n: ui.contador(img, f"x{n} VACÍOS", 505, 650, (t % 0.2), size=96, col=ui.ROJO, giro=-3)
    if t >= k.at(0, 8): ui.pega(img, lolo("sorpresa", t), 330, 1360 + (1 - eb((t - k.at(0, 8)) / 0.3)) * 500, esc=0.72)
    return img

def t_dato(t, k):
    img = fondo(0.74, 14).copy()
    ui.sello(img, "DATO REAL", 505, 520, t - k.at(0, 1), col=ui.TEAL, giro=-5, size=96)
    if t >= k.at(0, 4): ui.contador(img, "ONU · 2024", 505, 700, t - k.at(0, 4), size=84, col=ui.AMAR, giro=-3)
    t79 = k.at(0, 9)
    if t >= t79:
        v = int(79 * eo((t - t79) / 0.9))
        ui.contador(img, f"{v} KG", 505, 980, (t - t79) % 0.12 if v < 79 else t - t79 - 0.9, size=220, col=ui.ROJO, giro=-4)
        ui.texto(img, "DE COMIDA A LA BASURA", 505, 1170, 58, ui.BLANCO)
        ui.texto(img, "POR PERSONA Y AÑO, EN CASA", 505, 1250, 50, ui.AMAR)
    ui.fuente_chip(img, "Fuente: ONU, Food Waste Index (2024)", t - k.at(0, 6), y=1515)
    return img

def t_platos(t, k):
    e = cocina(vacios=24)
    caen = int(t * 7)
    for i in range(min(caen, 18)):                            # platos que caen a una montaña
        a = i * 2.4; r = 0.05 * i
        e.pon(T.plato(1.0, comida=(230, 150, 60), r=0.12), pos=(0.2 + r * math.cos(a) * 0.6, 0.02 + 0.035 * i, 0.9 + r * math.sin(a) * 0.4), yaw=a)
    cam = T.cam_keys(t, [(0, (-0.6, 1.5, -1.0), (0.3, 0.4, 1.0), 52), (k.dur, (-0.4, 1.6, -0.6), (0.3, 0.5, 1.0), 48)])
    img = T.vineta(e.render(cam))
    ui.contador(img, "+1.000.000.000", 505, 660, t - k.at(0, 3), size=96, col=ui.AMAR, giro=-3)
    ui.texto(img, "PLATOS AL DÍA EN EL MUNDO", 505, 780, 54, ui.BLANCO)
    return img

def t_cierre(t, k):
    e = cocina(cosas=[(0, 1, T.brik(LECHE)), (1, 1, T.botella(liquido=0.03)), (2, 2, helado())])
    e.pon(T.brik(LECHE), pos=(1.6, 2.55 + 0.05 * math.sin(t * 3), 1.6), yaw=t * 1.3, esc=2.2)
    cam = T.cam_keys(t, [(0, (0.0, 1.8, -1.2), (1.8, 1.4, 2.2), 56), (k.dur, (0.2, 1.75, -0.8), (1.8, 1.4, 2.2), 54)])
    img = ui.oscurece(T.vineta(e.render(cam)), 0.2)
    tl = k.at(0, 7)
    g = "chulo" if t < tl else "feliz"
    ui.pega(img, lolo(g, t, banda="REY DEL TRAGUITO"), 505, 1300 + (1 - eb(t / 0.35)) * 700, esc=1.08)
    ui.placa(img, "EL QUE DEJA UN TRAGUITO\nY LO VUELVE A GUARDAR", 505, 820, t - k.at(0, 6), size=48, giro=-3)
    ui.pregunta(img, PREGUNTA, t, k, size=54)
    return img


TOMAS = [
    dict(sents=["¿Sabías que hay un truco para no tirar nunca un envase?"], dib=t_gancho, pausa=0.45, d3=lambda k: k.at(0, 4) / k.dur,
         sfx=[("whoosh", 0.0, 0.8), ("golpe", 0.85, 0.8), ("pop", (0, 4), 0.6), ("golpe", lambda k: k.at(0, 4) + 0.5, 0.6)]),
    dict(sents=["Dejas un traguito… y lo vuelves a meter en la nevera."], dib=t_nombre, pausa=0.5, corte="whip", d3=0,
         sfx=[("tada", 0.05, 0.5), ("golpe", (0, 10), 0.6)]),
    dict(sents=["¿Leche?", "Un traguito.", "¿Refresco?", "Tres gotas y sin gas.", "¿Helado?", "Una cucharada."], dib=t_tres, pausa=0.5, gap=0.14, d3=1,
         sfx=[("whoosh", _mete, 0.5), ("golpe", _mete, 0.4), ("error", (3, 3), 0.4)]),
    dict(sents=["Y el siguiente abre la nevera con ilusión…", "y le cae una gota."], dib=t_gota, pausa=0.55, corte="whip", d3=1,
         sfx=[("ding", lambda k: 1.0, 0.4), ("congela", (1, 0), 0.9), ("pop", (1, 3), 0.6)]),
    dict(sents=["Y como nadie lo tira, la nevera se llena de envases vacíos."], dib=t_vacios, pausa=0.55, d3=1,
         sfx=[("pop", lambda k: [0.2 + i * 0.12 for i in range(14)], 0.35), ("golpe", (0, 8), 0.7)]),
    dict(sents=["El dato real: según la ONU, en casa tiramos 79 kilos de comida por persona al año."],
         dib=t_dato, pausa=0.4, corte="whip", d3=0, sfx=[("golpe", (0, 1), 0.8), ("pop", (0, 4), 0.6), ("sube", (0, 9), 0.4), ("golpe", lambda k: k.at(0, 9) + 0.9, 0.6)]),
    dict(sents=["En el mundo, más de mil millones de platos al día."], dib=t_platos, pausa=0.55, d3=1,
         sfx=[("clic", lambda k: [i / 7 for i in range(18)], 0.35), ("golpe", (0, 1), 0.6)]),
    dict(sents=["Así que mándaselo a ese amigo que deja un traguito y lo vuelve a guardar."], dib=t_cierre, pausa=1.9, d3=1,
         sfx=[("tada", 0.1, 0.5), ("pop", (0, 6), 0.6)]),
]
