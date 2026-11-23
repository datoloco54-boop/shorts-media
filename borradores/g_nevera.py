# g_nevera.py — Manual irónico n.º 21 (24-nov-2026): «Modo Explorador de Nevera™». Tema de la lista del 23-nov-2026 (Jesús: «hazlos»).
# Costumbre: abrir la nevera una y otra vez «por si hay algo nuevo» y acabar comiéndote lo que había desde el principio.
# Le pasa a TODO el mundo (regla del 23-nov-2026).
# Dato real del cierre: estudio de hogares del Instituto Federal Alemán de Evaluación de Riesgos (BfR) y el Max Rubner-Institut
# («Answers to a cold case», primaria): apuntando cada apertura durante 24 h, la media fue de 11,9 aperturas al día por hogar;
# el máximo, 46. Otro estudio con sensores en 119 neveras domésticas (core.ac.uk) da unas 20 al día. En voz: «12» y «46».
# EVITADO: «22 veces al día» (sale en prensa atribuido a Cornell, sin fuente original).
# Deseos por grupo (apartado 0b): poder (el gancho: «tu nevera fabrica comida nueva»), juego (la luz mágica, los rayos de la
# nevera, el congelador que escupe hielo), pertenencia (a todos nos ha pasado: «¿cuántas veces abres tú la nevera?»).
# Decorado: tresd.cocina(dia=0, luz=0, nevera=False) de noche con tresd.nevera_abierta() (v1.9). Objeto-metáfora: el mismo
# queso de siempre en la balda del medio. Recursos nuevos: cocina a oscuras con la luz de la nevera como único foco, el contador
# de visitas, el congelador que escupe cubitos y el giro «te comes lo que había al principio».
import math, functools
from PIL import Image, ImageDraw
import tresd as T
import ui
from ui import clamp, eo, eb
from personaje import lolo

AMARILLO = {"CIERRA", "NUEVA", "EXPLORADOR", "ABRES", "MISMO", "CIERRAS", "CONGELADOR", "HIELO", "BUSCAS", "NADA", "PRINCIPIO", "REAL", "12", "46", "NUEVO"}
DICHO = {"«": "", "»": "", "12 veces": "doce veces", "46 veces": "cuarenta y seis veces"}
PRIMER_CORTE = lambda k: k.at(0, 5)                          # corte en «comida»
PREGUNTA = "¿Cuántas veces abres tú la nevera al día?"
MUSICA = 0.09
NEV = (2.4, 0, 2.55)
LOLO_N = (1.6, 0, 2.0)
FAM = dict(sudadera=(230, 90, 90), gorro=(60, 40, 30), pompon=False, pant=(60, 60, 70))
QUESO = (255, 205, 60)

def queso():
    o = T.caja(0.22, 0.1, 0.14, QUESO)
    for x, y in ((-0.05, 0.05), (0.04, 0.03), (0.07, 0.07)): o.une(T.esfera(0.018, (220, 170, 40), nu=6, nv=4), pos=(x, y, -0.071))
    return o

def yogur(): o = T.cilindro(0.04, 0.08, (250, 250, 252), n=10); o.une(T.cilindro(0.041, 0.006, (240, 120, 160), n=10), pos=(0, 0.08, 0)); return o

@functools.lru_cache(maxsize=1)
def _base():
    e = T.cocina(dia=0.05, luz=0.35, nevera=False)
    return e

def cocina(abre=1.0, luz=1.0, queso_on=True, lolo=True, lbr=1.0, cong=0.0):
    e = _base().copia()
    e.pon(T.nevera_abierta(abre, luz=luz), pos=NEV)
    cosas = [(1, 1, queso() if queso_on else None), (0, 0, yogur()), (2, 0, T.brik((60, 140, 230), h=0.22)), (3, 2, T.botella(liquido=0.6))]
    for i, f, o in cosas:
        if o is None: continue
        x, y, z = T.baldas_xy(i, f); e.pon(o, pos=(NEV[0] + x, y, NEV[2] + z))
    if abre > 0.1 and luz > 0: e.halo((NEV[0] - 0.2, 1.1, NEV[2] - 0.2), (200, 230, 255), 0.35, 0.22 * abre * luz)
    if lolo: e.pon(T.persona(brazo=lbr), pos=LOLO_N, yaw=math.pi / 2)
    for j in range(int(cong * 10)):                           # cubitos que salen disparados
        u = cong * 10 - j
        if 0 < u < 1.6: e.pon(T.caja(0.06, 0.06, 0.06, (200, 235, 255)), pos=(NEV[0] - 0.3 - 0.8 * u, 1.75 + 0.4 * math.sin(u * 2) - 0.6 * u * u, NEV[2] - 0.3 - 0.3 * j % 3 * 0.2))
    return e

CAMN = lambda t, D: T.cam_keys(t, [(0, (1.05, 1.7, -0.1), (2.4, 1.05, 2.45), 56), (D, (1.25, 1.65, 0.3), (2.4, 1.05, 2.45), 52)])

def rayos_luz(img, t, f=1.0, cx=820, cy=900):
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(9):
        a = -2.4 + i * 0.3 + 0.05 * math.sin(t * 3 + i)
        d.polygon([(cx, cy), (cx + 1400 * math.cos(a - 0.05), cy + 1400 * math.sin(a - 0.05)), (cx + 1400 * math.cos(a + 0.05), cy + 1400 * math.sin(a + 0.05))], fill=(255, 250, 220, int(18 * f)))

def nevera2d(t, txt="¿ALGO NUEVO?"):
    L, d = ui.capa(560, 900)
    d.rounded_rectangle([0, 0, 1119, 1799], 60, fill=(236, 240, 246), outline=ui.TINTA, width=10)
    d.rounded_rectangle([60, 60, 1059, 1739], 40, fill=(230, 244, 255))
    for y in (560, 1060, 1500): d.rectangle([60, y, 1059, y + 22], fill=(190, 214, 236))
    d.rounded_rectangle([420, 920, 700, 1060], 20, fill=QUESO, outline=(200, 150, 30), width=8)
    d.text((560, 300), txt, font=ui.fuente(120), fill=ui.TINTA, anchor="mm")
    for i in range(6):
        a = t * 2 + i; x, y = 560 + 400 * math.cos(a), 760 + 300 * math.sin(a * 1.3)
        d.text((x, y), "✦", font=ui.fuente(90), fill=(255, 205, 50), anchor="mm")
    return L

@functools.lru_cache(maxsize=4)
def fondo(osc=0.55, blur=16):
    return ui.oscurece(cocina().render(CAMN(0, 1)), osc, blur)

# ------------------------------------------------------------------ tomas
def t_gancho(t, k):
    tc = k.at(0, 5)
    if t < tc:                                                # desde el fotograma 0: la puerta se abre de golpe y la luz inunda la cocina
        ab = eo(t / 0.35)
        e = cocina(abre=ab, lbr=0.3 + 0.9 * eo(t / 0.3))
        cam = T.cam_keys(t, [(0, (0.0, 2.0, -1.2), (2.2, 1.1, 2.3), 62), (tc, (1.15, 1.65, 0.15), (2.4, 1.05, 2.45), 50)], suave=T.eo)
        img = T.vineta(e.render(cam))
        rayos_luz(img, t, ab)
        if t < 0.06: img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), 0.6)
        if t > 0.3: ui.texto(img, "¡AAAH!", 330, 760, 100, ui.AMAR)
        return img
    lt = t - tc
    img = fondo().copy(); rayos_luz(img, lt, 1.0, 540, 1000)
    ui.pega(img, nevera2d(lt), 505, 1040, esc=0.5 + 0.5 * eb(lt / 0.3))
    if lt > 0.6: ui.sello(img, "NUEVO\nCADA 5 MIN", 760, 1450, lt - 0.6, col=ui.VERDE, giro=8, size=56)
    return img

def t_nombre(t, k):
    img = ui.rayos(t, cols=((70, 120, 220), (30, 60, 150)), brillo=(230, 245, 255))
    ui.pedestal(img, 540, 1270, col=(60, 70, 130))
    ui.pega(img, nevera2d(t, ""), 540, 900 + 12 * math.sin(t * 2.4), esc=0.6 * (0.7 + 0.3 * eb(t / 0.3)), giro=4 * math.sin(t * 1.7))
    ui.placa(img, "MODO EXPLORADOR\nDE NEVERA™", 505, 1450, t - k.at(0, 3), size=64)
    return img

def _abre(k): return [k.at(0, 0), k.at(2, 4), k.at(4, 3)]

def t_tres(t, k):
    D = k.dur; a = _abre(k); n = len([x for x in a if x <= t])
    ult = a[n - 1] if n else 0
    ab = eo((t - ult) / 0.3) if n else 0.0
    if n and t > ult + 1.1 and n < 3: ab = 1 - eo((t - ult - 1.1) / 0.3)          # cierra antes de la siguiente
    cong = clamp((t - k.at(5, 0)) / 1.0) if t >= k.at(5, 0) else 0.0
    e = cocina(abre=ab, lbr=0.4 + 0.8 * ab, cong=cong)
    cam = CAMN(t, D)
    img = T.vineta(e.render(cam))
    rayos_luz(img, t, ab * 0.8)
    if n: ui.contador(img, f"VISITA {n}", 505, 650, t - ult, size=96, col=[ui.AMAR, (255, 150, 40), ui.ROJO][n - 1], giro=-3)
    for s in (1, 3):
        if t >= k.at(s, 0): ui.placa(img, "LO MISMO", 300 if s == 1 else 720, 1350 if s == 1 else 1250, t - k.at(s, 0), size=56, col=(255, 255, 255), giro=(-4, 4)[s // 3])
    if cong > 0: ui.sello(img, "HIELO", 505, 1450, t - k.at(5, 0), col=(110, 200, 255), giro=-5, size=80)
    return img

def t_nada(t, k):
    tf = k.at(1, 0); tt = min(t, tf)                          # se congela en «dices»
    e = cocina(abre=1.0, lbr=0.5)
    e.pon(T.persona(brazo=0.9, brazo2=0.9, **FAM), pos=(0.4, 0, 1.4), yaw=math.pi / 2 + 0.2)
    cam = T.cam_keys(tt, [(0, (-0.6, 1.7, -0.6), (1.4, 1.2, 1.9), 52), (tf, (-0.3, 1.65, -0.2), (1.4, 1.2, 1.9), 48)])
    img = T.vineta(e.render(cam))
    rayos_luz(img, tt, 0.6, 900, 820)
    if t >= k.at(0, 5): ui.texto(img, "¿QUÉ BUSCAS?", 380, 700, 84, ui.ROSA)
    if t >= tf:
        img = ui.congela(img, t - tf)
        ui.pega(img, lolo("serio", t), 330, 1340 + (1 - eb((t - tf) / 0.3)) * 500, esc=0.8)
        ui.placa(img, "BUSCANDO:\nNADA", 660, 1020, t - k.at(1, 1), size=64, giro=4)
    return img

def t_otro(t, k):
    e = cocina(abre=1.0, lolo=False)
    e.pon(T.persona(brazo=1.1, **FAM), pos=LOLO_N, yaw=math.pi / 2)
    cam = CAMN(t, k.dur)
    img = T.vineta(e.render(cam))
    rayos_luz(img, t, 0.8)
    tc = k.at(0, 7)                                           # «cierra»
    if t >= tc:
        ui.pega(img, lolo("enfado", t), 330, 1340 + (1 - eb((t - tc) / 0.3)) * 500, esc=0.78)
        ui.sello(img, "¡CIERRA!", 720, 1000, t - tc, col=ui.ROJO, giro=7, size=96)
    if t >= k.at(0, 10): ui.placa(img, "SE ESCAPA EL FRÍO", 505, 700, t - k.at(0, 10), size=60, col=(200, 235, 255), giro=-3)
    return img

def t_giro(t, k):
    tq = k.at(0, 4)                                           # «comes»: coge el queso
    cogido = t >= tq
    e = cocina(abre=1.0, queso_on=not cogido, lbr=1.4 if cogido else 0.6)
    if cogido:
        u = clamp((t - tq) / 0.5)
        x, y, z = T.baldas_xy(1, 1); p0 = (NEV[0] + x, y, NEV[2] + z); p1 = (LOLO_N[0] + 0.25, 1.6, LOLO_N[2] - 0.1)
        e.pon(queso(), pos=tuple(a + (b - a) * eo(u) for a, b in zip(p0, p1)), yaw=u)
    cam = T.cam_keys(t, [(0, (1.35, 1.6, 0.6), (2.2, 1.2, 2.3), 48), (k.dur, (1.45, 1.6, 0.9), (2.0, 1.4, 2.2), 44)])
    img = T.vineta(e.render(cam))
    rayos_luz(img, t, 0.7)
    if t >= tq + 0.4:
        ui.sello(img, "EL DE\nSIEMPRE", 740, 760, t - tq - 0.4, col=ui.AMAR, giro=7, size=72)
        ui.pega(img, lolo("feliz", t), 330, 1340 + (1 - eb((t - tq - 0.4) / 0.3)) * 500, esc=0.75)
    return img

def t_dato(t, k):
    img = fondo(0.74, 14).copy()
    ui.sello(img, "DATO REAL", 505, 520, t - k.at(0, 1), col=ui.TEAL, giro=-5, size=96)
    if t >= k.at(0, 6): ui.contador(img, "ALEMANIA", 505, 690, t - k.at(0, 6), size=84, col=ui.AMAR, giro=-3)
    t12 = k.at(0, 12)
    if t >= t12:
        v = int(12 * eo((t - t12) / 0.7))
        ui.contador(img, f"{v} VECES", 505, 930, (t - t12) % 0.1 if v < 12 else t - t12 - 0.7, size=170, col=ui.BLANCO, giro=-3)
        ui.texto(img, "AL DÍA, DE MEDIA, POR CASA", 505, 1080, 52, ui.AMAR)
    t46 = k.at(1, 5)
    if t >= t46:
        ui.sello(img, "RÉCORD:\n46 VECES", 505, 1290, t - t46, col=ui.ROJO, giro=-6, size=80)
    ui.fuente_chip(img, "Fuente: Instituto Federal Alemán de Evaluación de Riesgos (BfR)", t - k.at(0, 6), y=1515, size=30)
    return img

def t_cierre(t, k):
    e = cocina(abre=1.0, lolo=False)
    e.pon(queso(), pos=(1.6, 2.4 + 0.05 * math.sin(t * 3), 1.6), yaw=t * 1.3, esc=2.4)
    cam = T.cam_keys(t, [(0, (0.0, 1.8, -1.2), (1.8, 1.5, 2.2), 56), (k.dur, (0.2, 1.75, -0.8), (1.8, 1.5, 2.2), 54)])
    img = ui.oscurece(T.vineta(e.render(cam)), 0.15)
    rayos_luz(img, t, 0.6)
    tl = k.at(0, 7)
    g = "chulo" if t < tl else "feliz"
    ui.pega(img, lolo(g, t, banda="EXPLORADOR DE NEVERAS"), 505, 1300 + (1 - eb(t / 0.35)) * 700, esc=1.08)
    ui.placa(img, "EL QUE ABRE LA NEVERA\nCADA CINCO MINUTOS", 505, 820, t - k.at(0, 6), size=48, giro=-3)
    ui.pregunta(img, PREGUNTA, t, k, size=52)
    return img


TOMAS = [
    dict(sents=["¿Sabías que tu nevera fabrica comida nueva cada cinco minutos?"], dib=t_gancho, pausa=0.45, d3=lambda k: k.at(0, 5) / k.dur,
         sfx=[("whoosh", 0.0, 0.8), ("golpe", 0.05, 0.6), ("sube", 0.1, 0.4), ("tada", (0, 5), 0.4)]),
    dict(sents=["Es el Modo Explorador de Nevera."], dib=t_nombre, pausa=0.5, corte="whip", d3=0, sfx=[("ding", 0.05, 0.4), ("golpe", (0, 3), 0.6)]),
    dict(sents=["¿Abres?", "Lo mismo.", "¿Cierras y vuelves a abrir?", "Lo mismo.", "¿Pruebas con el congelador?", "Hielo."], dib=t_tres, pausa=0.5, gap=0.14, d3=1,
         sfx=[("whoosh", _abre, 0.5), ("error", lambda k: [k.at(1, 0), k.at(3, 0)], 0.4), ("pop", lambda k: [k.at(5, 0) + i * 0.1 for i in range(6)], 0.4)]),
    dict(sents=["Y si alguien te pregunta qué buscas,", "dices: «nada»."], dib=t_nada, pausa=0.55, corte="whip", d3=1,
         sfx=[("pop", (0, 5), 0.5), ("congela", (1, 0), 0.9), ("golpe", (1, 1), 0.6)]),
    dict(sents=["Pero si la abre otro, le gritas: «¡cierra, que se escapa el frío!»."], dib=t_otro, pausa=0.55, corte="whip", d3=1,
         sfx=[("whoosh", 0.05, 0.4), ("golpe", (0, 7), 0.8), ("error", (0, 10), 0.4)]),
    dict(sents=["Y al final te comes lo que había desde el principio."], dib=t_giro, pausa=0.55, d3=1,
         sfx=[("whoosh", (0, 4), 0.5), ("ding", lambda k: k.at(0, 4) + 0.4, 0.5)]),
    dict(sents=["El dato real: en un estudio alemán, cada casa abría la nevera 12 veces al día de media.", "Y una llegó a abrirla 46 veces."],
         dib=t_dato, pausa=0.4, corte="whip", d3=0, sfx=[("golpe", (0, 1), 0.8), ("pop", (0, 6), 0.6), ("sube", (0, 12), 0.4), ("golpe", (1, 5), 0.8)]),
    dict(sents=["Así que mándaselo a ese amigo que abre la nevera cada cinco minutos por si hay algo nuevo."], dib=t_cierre, pausa=1.9, d3=1,
         sfx=[("tada", 0.1, 0.5), ("pop", (0, 6), 0.6)]),
]
