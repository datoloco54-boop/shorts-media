# g_claxon.py — Manual irónico n.º 18 (23-nov-2026): «Pitido Mágico del Verde™». Línea «al volante». Tema elegido por Claude
# (Jesús: «y haz otro»); estaba en la lista de pendientes del registro (pitar en cuanto el semáforo se pone verde).
# Costumbre: pitar en el semáforo: antes de que se ponga verde, al de delante que no arranca y medio segundo después del verde.
# Dato real del cierre (giro del último tercio): campaña «The Punishing Signal» de la Policía de Bombay (vídeo oficial del
# 31-ene-2020; pruebas en nov–dic de 2019 en cruces como CSMT, Marine Drive, Pedder Road, Hindmata y Bandra): conectaron
# medidores de ruido a los semáforos; si el ruido llegaba a 85 dB, la cuenta atrás del rojo volvía a empezar (90 s).
# Lema: «Honk more, wait more» («pita más, espera más»). Fuentes: NPR (transcripción, feb-2020), CNN (05-feb-2020), Free Press
# Journal y Business Standard (declaraciones del comisario adjunto de Tráfico, Madhukar Pandey).
# MATIZ (va en la descripción): fue una prueba de concienciación, no un sistema fijo en toda la ciudad. En voz: «probó».
# EVITADO: los estudios de «pitamos antes a los vehículos baratos» (Doob y Gross, 1968): las réplicas se contradicen.
# Deseos por grupo (apartado 0b): poder y control (el gancho: «tu claxon pone el semáforo en verde»), juego (la corneta dorada,
# los anillos de sonido y el vehículo de delante que da un salto), pertenencia (la pregunta final: «¿en tu ciudad se pita mucho?»).
# Decorado: tresd.calle() con cruce, semáforo y fila. Objeto-metáfora: la corneta dorada en el techo del vehículo de Lolo.
# Recursos nuevos: anillos de sonido 3D que viajan hasta el de delante, el vehículo que salta, la cuenta atrás que vuelve a 90
# y el sonido de claxon (sonido.py v1.1).
import math, functools
from PIL import Image, ImageDraw
import tresd as T
import ui
from ui import clamp, eo, eb
from personaje import lolo

AMARILLO = {"CLAXON", "MÁGICO", "SIGUE", "ARRANCA", "MEDIO", "CODO", "SALTO", "TI", "EMPEZAR", "REAL", "85", "ESPERA", "DESPUÉS"}
DICHO = {"85 decibelios": "ochenta y cinco decibelios"}
PRIMER_CORTE = lambda k: k.at(0, 6)                          # corte en «poder»
PREGUNTA = "¿En tu ciudad se pita mucho? ¿Sí o no?"
MUSICA = 0.09
W_, H_ = 1080, 1920
ORO = (255, 205, 50)
MORADO = (120, 78, 214)
X1 = 1.75
CRUCE = T.calle(semilla=4, largo=140, paso_z=0.0)
VZ, LZ = -5.8, -11.0                                         # vehículo de delante (la víctima) y el de Lolo
DETRAS = [(X1, -16.2, (230, 90, 90)), (X1, -21.4, (90, 140, 230)), (X1, -26.6, (250, 180, 60))]
SEM = (7.6, 0.16, 6.0)

def corneta(esc=1.0):
    """Corneta dorada (objeto-metáfora), la boca mira a +z."""
    o = T.cilindro(0.07, 0.62, ORO, n=14, r1=0.3, eje="z", emis=0.35, tapas=False)
    o.DS = [True] * len(o.DS); o._fin = None
    o.une(T.esfera(0.11, (200, 150, 20), nu=8, nv=5, emis=0.2), pos=(0, 0, 0))
    o.une(T.caja(0.1, 0.18, 0.1, (90, 90, 104)), pos=(0, -0.2, 0.05))
    return o

@functools.lru_cache(maxsize=2)
def coche_lolo(con_corneta=True):
    o = T.coche(MORADO)
    o.une(T.esfera(0.42, (255, 205, 40), nu=10, nv=5, v0=0, v1=0.5), pos=(0, 1.36, -0.3))     # su gorro, en el techo
    o.une(T.cilindro(0.43, 0.1, (224, 164, 20), n=10, tapas=False), pos=(0, 1.34, -0.3))
    o.une(T.esfera(0.12, (255, 255, 255), nu=6, nv=4), pos=(0, 1.86, -0.3))
    if con_corneta: o.une(corneta(), pos=(0, 1.75, 0.55))
    return o

@functools.lru_cache(maxsize=32)
def _coche(col, freno=True): return T.coche(col, freno=1.0 if freno else 0.0)

def anillo(e, u, z0=LZ + 1.4):
    """Anillo de sonido que sale de la corneta y viaja hasta el de delante (u 0..1)."""
    if not 0 < u < 1: return
    r = 0.25 + 1.0 * eo(u)
    o = T.cilindro(r, 0.06, (255, 214, 0), n=24, eje="z", tapas=False, emis=0.7, alfa=int(230 * (1 - u)))
    o.DS = [True] * len(o.DS); o._fin = None
    e.pon(o, pos=(X1, 1.95 - 0.5 * u, z0 + 4.2 * u))

def cruce(sem="rojo", vy=0.0, vdz=0.0, pitidos=(), t=0.0, corneta_on=True, detras=True):
    e = CRUCE.copia()
    e.pon(T.semaforo(sem, "rojo" if sem != "rojo" else "verde", 0), pos=SEM, yaw=math.pi)
    e.pon(_coche((0, 170, 150), True), pos=(X1, vy, VZ + vdz))
    e.pon(coche_lolo(corneta_on), pos=(X1, 0, LZ))
    if detras:
        for x, z, c in DETRAS: e.pon(_coche(c), pos=(x, 0, z))
    for p in pitidos: anillo(e, (t - p) / 0.6)
    return e

def cam_fila(t, D, x=X1 + 1.7):
    return T.cam_keys(t, [(0, (x, 3.8, -20.5), (X1, 1.2, -4.0), 52), (D, (x - 0.4, 3.4, -18.5), (X1, 1.2, -4.0), 50)])

def piii(img, cam, p, t, size_k=520):
    x, y, z = cam.pantalla(p)
    if z > 0.3: ui.texto(img, "¡PIII!", clamp(x, 220, 790), clamp(y - 120 - 30 * eo(t / 0.3), 520, 1450), max(50, min(110, size_k / z)), ui.ROSA)

def cuenta(img, n, t_golpe, cx=840, cy=640, col=ui.ROJO):
    """Cuenta atrás del semáforo (panel negro con dígitos rojos)."""
    k = 1.3 - 0.3 * eb(t_golpe / 0.18) if t_golpe >= 0 else 1.0
    L, d = ui.capa(230, 150)
    d.rounded_rectangle([0, 0, 459, 299], 40, fill=(12, 10, 22), outline=(80, 80, 96), width=8)
    d.text((230, 150), f"{n:02d}", font=ui.fuente(210), fill=col, anchor="mm")
    ui.pega(img, L, cx, cy, esc=k)

@functools.lru_cache(maxsize=4)
def fondo(osc=0.6, blur=16):
    e = cruce()
    return ui.oscurece(e.render(cam_fila(0, 1)), osc, blur)

# ------------------------------------------------------------------ el volante en primer plano (2D)
def volante(hund=0.0, t=0.0):
    L, d = ui.capa(760, 760); c = 760; P = lambda *v: [x * 2 for x in v]
    d.ellipse(P(20, 40, 740, 760), fill=(20, 18, 30))
    d.ellipse(P(20, 20, 740, 740), outline=(54, 52, 68), width=110)
    for a in (200, 340, 90):                                  # radios
        x, y = 380 + 300 * math.cos(math.radians(a)), 380 + 300 * math.sin(math.radians(a))
        d.line(P(380, 380, x, y), fill=(54, 52, 68), width=120)
    r = 175 * (1 - 0.06 * hund)
    d.ellipse(P(380 - r, 380 - r + 14, 380 + r, 380 + r + 14), fill=(30, 28, 40))
    d.ellipse(P(380 - r, 380 - r, 380 + r, 380 + r), fill=(76, 74, 92) if hund < 0.3 else (96, 90, 60), outline=ORO, width=10)
    # icono de corneta
    d.polygon([tuple(P(310, 350)), tuple(P(350, 350)), tuple(P(440, 300)), tuple(P(440, 460)), tuple(P(350, 410)), tuple(P(310, 410))], fill=ORO)
    return L

def mini_semaforo(img, estado, cx=840, cy=640, t=0.0):
    L, d = ui.capa(130, 330)
    d.rounded_rectangle([0, 0, 259, 659], 50, fill=(20, 20, 30), outline=(90, 90, 104), width=8)
    for i, (nom, c) in enumerate((("rojo", (255, 60, 50)), ("ambar", (255, 190, 40)), ("verde", (60, 240, 120)))):
        on = nom == estado; cc = c if on else tuple(int(v * 0.25) for v in c)
        d.ellipse([40, 30 + i * 210, 220, 210 + i * 210], fill=cc)
    ui.pega(img, L, cx, cy)

def _toques(k): a = k.at(0, 6); return [a + 0.1 + i * 0.22 for i in range(6)]

def plano_volante(t, toques, entra=1.0, verde_en=None):
    img = fondo().copy()
    hechos = [x for x in toques if x <= t]; n = len(hechos)
    lt = t - hechos[-1] if hechos else -1
    hund = math.sin(clamp(lt / 0.14) * math.pi) if lt >= 0 else 0.0
    ui.pega(img, volante(hund, t), 505, 1090, esc=1.05)
    ui.onda(img, 505, 1090, lt, col=ORO, r1=330, dur=0.4)
    if lt >= 0 and lt < 0.3: ui.texto(img, "¡PIII!", 505, 760, 120, ui.ROSA)
    ui.dedo(img, 515, 1100, pulsa=clamp(lt / 0.14) if lt >= 0 else 0, entra=entra, ang=-10)
    mini_semaforo(img, "verde" if verde_en is not None and t >= verde_en else "rojo", 860, 620)
    return img, n

def corneta2d(t):
    L, d = ui.capa(420, 300)
    d.polygon([(60, 250), (230, 250), (780, 40), (780, 560), (230, 350), (60, 350)], fill=ORO, outline=(150, 100, 10))
    d.ellipse([700, 40, 840, 560], fill=(230, 170, 30), outline=(150, 100, 10), width=8)
    d.ellipse([20, 230, 120, 370], fill=(200, 150, 20))
    return L

# ------------------------------------------------------------------ tomas
def t_gancho(t, k):
    tc = k.at(0, 6)
    if t < tc:                                                # desde el fotograma 0: pitidos, anillos y el de delante que da un respingo
        pit = [0.0, 0.35, 0.7, 1.05]
        vy = 0.12 * abs(math.sin(t * 9)) * max(0, 1 - t / 1.4)
        e = cruce(vy=vy, pitidos=pit, t=t)
        cam = T.cam_keys(t, [(0, (X1 + 3.0, 5.0, -24.0), (X1, 1.0, -5.0), 56), (tc, (X1 + 1.2, 2.6, -15.5), (X1, 1.4, -6.0), 48)], suave=T.eo)
        sh = 0.04 * math.sin(t * 50) * max(0, 1 - t / 0.8)
        cam = T.Cam(cam.pos + (sh, sh, 0), cam.mira, cam.fov)
        img = T.vineta(e.render(cam))
        if t < 0.05: img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), 0.5)
        for p in pit:
            if 0 <= t - p < 0.3: piii(img, cam, (X1, 2.4, LZ + 2.0), t - p)
        return img
    lt = t - tc
    img, n = plano_volante(lt, [x - tc for x in _toques(k)], entra=clamp(lt / 0.15), verde_en=k.at(0, 12) - tc)
    return img

def t_nombre(t, k):
    img = ui.rayos(t, cols=((230, 70, 110), (160, 40, 80)), brillo=(255, 230, 190))
    ui.pedestal(img, 540, 1250, col=(60, 70, 130))
    sc = 1 + 0.06 * math.sin(t * 22) * (t > k.at(0, 3))
    ui.pega(img, corneta2d(t), 540, 960 + 12 * math.sin(t * 2.4), esc=0.9 * sc * (0.7 + 0.3 * eb(t / 0.3)), giro=8 + 5 * math.sin(t * 1.7))
    ui.placa(img, "PITIDO MÁGICO\nDEL VERDE™", 505, 1440, t - k.at(0, 2), size=68)
    if t > k.at(0, 4): mini_semaforo(img, "verde", 820, 640)
    return img

def _pit(k): return [k.at(1, 0), k.at(3, 0)] + [k.at(5, 0) + i * 0.16 for i in range(8)]

def t_tres(t, k):
    D = k.dur; tv = k.at(4, 1)                                # se pone verde en «puso»
    p = [x for x in _pit(k) if x <= t + 0.6]
    e = cruce("verde" if t >= tv else "rojo", pitidos=p, t=t)
    cam = cam_fila(t, D)
    img = T.vineta(e.render(cam))
    for x in _pit(k):
        if 0 <= t - x < 0.3: piii(img, cam, (X1, 2.4, LZ + 2.0), t - x)
    g = [k.at(1, 0), k.at(3, 0), k.at(5, 0)]; n = len([x for x in g if x <= t])
    if n: ui.contador(img, ["PIII", "PIIIII", "PIIIIIIII"][n - 1], 505, 650, t - g[n - 1], size=[100, 120, 130][n - 1], col=[ui.AMAR, (255, 150, 40), ui.ROJO][n - 1])
    mini_semaforo(img, "verde" if t >= tv else "rojo", 870, 640)
    if t >= tv: ui.sello(img, "VERDE\nHACE 0,5 s", 700, 900, t - tv, col=ui.VERDE, giro=8, size=56)
    if n >= 3:
        ui.pega(img, lolo("esfuerzo", t), 300, 1330 + (1 - eb((t - g[2]) / 0.3)) * 500, esc=0.72)
        ui.placa(img, "MODO CODO", 300, 1500, t - g[2] - 0.15, size=50, giro=-4)
    return img

def t_salto(t, k):
    tf = k.at(1, 0); tt = min(t, tf)                          # se congela en «fue»
    tj = k.at(0, 6)                                           # «salto»
    u = clamp((tt - tj + 0.15) / 0.5)
    vy = 0.9 * math.sin(u * math.pi) if 0 < u < 1 else 0.0
    vdz = 3.5 * eo(clamp((tt - tj) / 1.2)) if tt > tj else 0.0
    e = cruce("verde", vy=vy, vdz=vdz, pitidos=[0.1, 0.4, tj - 0.3], t=tt)
    cam = T.cam_keys(tt, [(0, (X1 - 2.6, 1.7, -9.8), (X1 + 0.2, 1.0, -4.5), 50), (tf, (X1 - 2.4, 1.6, -8.8), (X1 + 0.2, 1.1, -3.5), 48)])
    img = T.vineta(e.render(cam))
    if tj - 0.1 <= tt < tj + 0.6: ui.texto(img, "¡AY!", 700, 820, 110, ui.AMAR)
    if t >= tf:
        img = ui.congela(img, t - tf)
        ui.pega(img, lolo("chulo", t), 330, 1340 + (1 - eb((t - tf) / 0.3)) * 500, esc=0.8)
        ui.placa(img, "TRÁFICO\nARREGLADO", 650, 1020, t - k.at(1, 2), size=56, giro=4)
    return img

def t_giro(t, k):
    tp = k.at(0, 3); tr = k.at(0, 7)                          # «pitas» · «vuelve»
    e = cruce("rojo", pitidos=[tp, tp + 0.3], t=t, detras=False)
    cam = T.cam_keys(t, [(0, (X1 + 2.2, 2.6, -13.5), (5.5, 3.6, 4.0), 50), (k.dur, (X1 + 2.6, 2.8, -11.5), (6.5, 4.2, 5.0), 44)])
    img = T.vineta(e.render(cam))
    if t < tr: n, tg = max(3, 12 - int(t * 4)), (t % 0.25)
    else: n, tg = 90 - int((t - tr) * 4), t - tr
    cuenta(img, n, tg, 760, 700, ui.ROJO)
    if 0 <= t - tp < 0.35: ui.texto(img, "¡PIII!", 330, 1000, 110, ui.ROSA)
    if t >= tr:
        ui.sello(img, "¡OTRA\nVEZ!", 760, 960, t - tr - 0.05, col=ui.ROJO, giro=8, size=70)
        ui.pega(img, lolo("sorpresa", t), 320, 1340 + (1 - eb((t - tr) / 0.3)) * 500, esc=0.78)
    return img

def t_dato(t, k):
    img = fondo(0.74, 14).copy()
    ui.sello(img, "DATO REAL", 505, 520, t - k.at(0, 1), col=ui.TEAL, giro=-5, size=96)
    if t >= k.at(0, 4): ui.contador(img, "BOMBAY · 2020", 505, 700, t - k.at(0, 4), size=84, col=ui.AMAR, giro=-3)
    t1 = k.at(0, 7)                                            # «medidores»
    t85 = k.at(1, 4); tr = k.at(1, 8)                          # «85» · «volvía»
    if t >= t1:
        db = 60 + 25 * clamp((t - t1) / max(0.5, t85 - t1)) + (2 * math.sin(t * 30) if t >= t85 else 0)
        d = ImageDraw.Draw(img); x0, x1, y = 150, 870, 930
        ui.texto(img, "RUIDO", x0, y - 66, 54, ui.BLANCO, ancla="lm")
        ui.texto(img, f"{int(db)} dB", x1, y - 66, 54, ui.ROJO if db >= 85 else ui.AMAR, ancla="rm")
        d.rounded_rectangle([x0, y - 28, x1, y + 28], 28, fill=(30, 26, 62))
        d.rounded_rectangle([x0, y - 28, x0 + max(56, (x1 - x0) * clamp((db - 40) / 55)), y + 28], 28, fill=ui.ROJO if db >= 85 else ui.AMAR)
        mx = x0 + (x1 - x0) * (45 / 55); d.line([mx, y - 44, mx, y + 44], fill=ui.BLANCO, width=8)
        ui.texto(img, "LÍMITE: 85 dB", mx, y + 80, 44, ui.BLANCO)
    if t >= tr:
        cuenta(img, 90 - int((t - tr) * 3), t - tr, 505, 1220); ui.texto(img, "OTRA VEZ 90 s DE ROJO", 505, 1360, 52, ui.AMAR)
    ui.fuente_chip(img, "Fuente: Policía de Bombay (2020), vía NPR y CNN", t - k.at(0, 6), y=1515)
    return img

def t_lema(t, k):
    pit = [0.05 + i * 0.22 for i in range(12)]
    e = cruce("rojo", pitidos=pit, t=t)
    cam = T.cam_keys(t, [(0, (X1 + 4.5, 6.5, -30.0), (X1, 1.0, -8.0), 50), (k.dur, (X1 + 4.0, 6.0, -26.0), (X1, 1.0, -8.0), 48)])
    img = ui.oscurece(T.vineta(e.render(cam)), 0.15)
    cuenta(img, 90 - int(t * 2), t, 830, 640)
    ui.placa(img, "PITA MÁS,\nESPERA MÁS", 505, 1150, t - k.at(0, 1), size=82, col=(255, 255, 255), giro=-3)
    return img

def t_cierre(t, k):
    e = cruce("verde", t=t)
    cam = T.cam_keys(t, [(0, (X1 - 2.8, 2.0, -15.0), (X1, 1.6, -9.0), 52), (k.dur, (X1 - 2.4, 1.9, -14.0), (X1, 1.6, -9.0), 50)])
    img = ui.oscurece(T.vineta(e.render(cam)), 0.2)
    tl = k.at(0, 7)
    g = "chulo" if t < tl else "feliz"
    ui.pega(img, lolo(g, t, banda="REY DEL CLAXON"), 505, 1300 + (1 - eb(t / 0.35)) * 700, esc=1.08)
    ui.placa(img, "EL QUE PITA MEDIO SEGUNDO\nDESPUÉS DEL VERDE", 505, 820, t - k.at(0, 6), size=46, giro=-3)
    ui.pregunta(img, PREGUNTA, t, k, size=50)
    return img


TOMAS = [
    dict(sents=["¿Sabías que tu claxon tiene el poder de poner el semáforo en verde?"], dib=t_gancho, pausa=0.45,
         d3=lambda k: k.at(0, 6) / k.dur,
         sfx=[("claxon", lambda k: [0.0, 0.35, 0.7, 1.05], 0.7), ("golpe", 0.02, 0.5), ("claxon", _toques, 0.55), ("ding", (0, 12), 0.5)]),
    dict(sents=["Presentamos: el Pitido Mágico del Verde."], dib=t_nombre, pausa=0.5, corte="whip", d3=0,
         sfx=[("tada", 0.05, 0.5), ("claxon_largo", (0, 3), 0.4)]),
    dict(sents=["¿Sigue en rojo?", "Pitas.", "¿El de delante no arranca?", "Pitas más.", "¿Se puso verde hace medio segundo?", "Pitas con el codo."],
         dib=t_tres, pausa=0.5, gap=0.14, d3=1,
         sfx=[("claxon", _pit, 0.55), ("ding", (4, 1), 0.4), ("golpe", lambda k: [k.at(1, 0), k.at(3, 0), k.at(5, 0)], 0.5)]),
    dict(sents=["Y si el de delante arranca de un salto,", "fue gracias a ti."], dib=t_salto, pausa=0.55, corte="whip", d3=1,
         sfx=[("claxon", lambda k: k.at(0, 6) - 0.3, 0.6), ("golpe", (0, 6), 0.7), ("congela", (1, 0), 0.9), ("tada", (1, 2), 0.4)]),
    dict(sents=["Pero un día pitas… y el rojo vuelve a empezar."], dib=t_giro, pausa=0.6, d3=1,
         sfx=[("claxon", lambda k: [k.at(0, 3), k.at(0, 3) + 0.3], 0.6), ("error", (0, 7), 0.6), ("golpe", (0, 7), 0.6)]),
    dict(sents=["El dato real: en Bombay, la policía conectó medidores de ruido a los semáforos.", "Si el ruido pasaba de 85 decibelios, el rojo volvía a empezar."],
         dib=t_dato, pausa=0.35, corte="whip", d3=0,
         sfx=[("golpe", (0, 1), 0.8), ("pop", (0, 4), 0.6), ("sube", (0, 7), 0.4), ("error", (1, 8), 0.5)]),
    dict(sents=["Su lema: pita más, espera más."], dib=t_lema, pausa=0.6, d3=1,
         sfx=[("claxon", lambda k: [0.05 + i * 0.22 for i in range(6)], 0.35), ("golpe", (0, 1), 0.7)]),
    dict(sents=["Así que mándaselo a ese amigo que pita medio segundo después del verde."], dib=t_cierre, pausa=1.9, d3=1,
         sfx=[("tada", 0.1, 0.5), ("pop", (0, 6), 0.6)]),
]
