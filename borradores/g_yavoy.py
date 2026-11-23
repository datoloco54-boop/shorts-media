# g_yavoy.py — Manual irónico n.º 19 (23-nov-2026): «El “Ya voy”™». Tema elegido por Jesús de una lista de 4 («los dos primeros»).
# Costumbre: decir «¡ya voy!» cuando te llaman (a comer) y tardar veinte minutos. Le pasa a TODO el mundo (regla del 23-nov-2026).
# Dato real del cierre: «falacia de la planificación». Buehler, Griffin y Ross (1994), «Exploring the "planning fallacy": Why people
# underestimate their task completion times», Journal of Personality and Social Psychology 67, 366–381 (primaria; 37 estudiantes
# de psicología): calcularon de media 33,9 días para acabar su trabajo de fin de carrera y tardaron 55,5. Divulgación: SPSP (blog),
# PMI. En voz se redondea a 34 y 56. EVITADO: «solo el 30 % acabó a tiempo» (solo lo da Wikipedia).
# Deseos por grupo (apartado 0b): poder (el gancho: «congelar el tiempo de los demás»), juego (el reloj que vuela, el bocadillo
# «¡YA VOY!» que crece), pertenencia (a todos nos han dicho «ya voy»: la pregunta «¿cuántos minutos dura tu ya voy?»).
# Decorado: tresd.salon() de noche con tresd.mesa_comedor(), plato() y vaso() (nuevos, v1.9) y la familia esperando.
# Objeto-metáfora: el bocadillo dorado «¡YA VOY!». Recursos nuevos: el vapor que se apaga, el reloj de pared que corre, la tortilla
# que se da la vuelta (Lolo esperando a otro).
import math, functools
from PIL import Image, ImageDraw
import tresd as T
import ui
from ui import clamp, eo, eb
from personaje import lolo

AMARILLO = {"PALABRAS", "VOY", "COMER", "SOPA", "PLATOS", "LLEGAS", "FRÍA", "TI", "RESPETO", "REAL", "56", "PLANIFICACIÓN", "VEINTE"}
DICHO = {"«": "", "»": "", "34 días": "treinta y cuatro días", "56": "cincuenta y seis"}
PRIMER_CORTE = lambda k: k.at(0, 4)                          # corte en «palabras»
PREGUNTA = "¿Cuántos minutos dura tu «ya voy»?"
MUSICA = 0.09
ORO = (255, 205, 50)
MESA = (1.3, 0, 0.1)
FAM = [dict(sudadera=(230, 90, 90), gorro=(60, 40, 30), pompon=False, pant=(60, 60, 70)),
       dict(sudadera=(0, 180, 150), gorro=(120, 80, 50), pompon=False, pant=(50, 54, 70))]
SOFA_L = (-0.6, 0, 2.05)

def comedor(e, vapor=1.0, comida=1.0, fam=(True, True), lolo_mesa=None, plato_lolo=1.0, brazos=0.3):
    e.pon(T.mesa_comedor(), pos=MESA)
    xs = (MESA[0] - 0.45, MESA[0] + 0.45)
    for i, (x, on) in enumerate(zip(xs, fam)):
        if on: e.pon(T.persona(sentado=True, brazo=brazos, brazo2=brazos, **FAM[i]), pos=(x, 0, MESA[2] + 0.75), yaw=math.pi)
        e.pon(T.plato(comida), pos=(x, 0.775, MESA[2] + 0.18))
    e.pon(T.plato(plato_lolo), pos=(MESA[0], 0.775, MESA[2] - 0.22))
    e.pon(T.vaso(0.6, (240, 140, 60)), pos=(MESA[0] + 0.2, 0.775, MESA[2] - 0.22))
    if lolo_mesa is not None: e.pon(T.persona(sentado=True, brazo=lolo_mesa, brazo2=0.3), pos=(MESA[0], 0, MESA[2] - 0.8), yaw=0)

def salon(hora=21.0, lolo_sofa=True, tel=1.0, otro_sofa=False):
    e = T.salon(dia=0.1, luz=1.0)
    e.pon(T.reloj_pared(hora, r=0.32), pos=(0.55, 2.45, 2.97))
    if lolo_sofa:
        e.pon(T.persona(sentado=True, brazo=1.1, brazo2=1.1), pos=SOFA_L, yaw=math.pi)
        e.pon(T.telefono(tel, (120, 190, 255)), pos=(SOFA_L[0], 1.05, SOFA_L[2] - 0.55))
    if otro_sofa:
        e.pon(T.persona(sentado=True, brazo=1.1, brazo2=1.1, **FAM[1]), pos=SOFA_L, yaw=math.pi)
        e.pon(T.telefono(1.0, (120, 190, 255)), pos=(SOFA_L[0], 1.05, SOFA_L[2] - 0.55))
    return e

def vapor(img, cam, p, t, f=1.0):
    if f <= 0.02: return
    d = ImageDraw.Draw(img, "RGBA")
    for j in range(3):
        x, y, z = cam.pantalla((p[0] + (j - 1) * 0.05, p[1], p[2]))
        if z < 0.3: continue
        s = 260 / z; pts = []
        for i in range(12):
            u = i / 11; pts.append((x + math.sin(u * 6 + t * 4 + j) * s * 0.08, y - u * s * 0.7))
        d.line(pts, fill=(255, 255, 255, int(170 * f)), width=max(3, int(s * 0.03)))

def globo(txt="¡YA VOY!", size=92, col=ORO):
    f = ui.fuente(size * 2); tw = f.getlength(txt)
    L, d = ui.capa(tw / 2 + 90, size * 1.5 + 60)
    w, h = L.width, L.height
    d.rounded_rectangle([10, 10, w - 10, h - 90], 70, fill=col, outline=ui.TINTA, width=12)
    d.polygon([(w * 0.3, h - 100), (w * 0.42, h - 100), (w * 0.26, h - 8)], fill=col, outline=ui.TINTA)
    d.polygon([(w * 0.3 + 8, h - 108), (w * 0.42 - 6, h - 108), (w * 0.27, h - 30)], fill=col)
    d.text((w / 2, (h - 80) / 2), txt, font=f, fill=ui.TINTA, anchor="mm")
    return L

def globo3d(img, cam, p, t, txt="¡YA VOY!", esc=1.0):
    if t < 0: return
    x, y, z = cam.pantalla(p)
    if z > 0.3: ui.pega(img, globo(txt, 70), clamp(x, 260, 760), clamp(y, 520, 1450), esc=esc * (0.4 + 0.6 * eb(t / 0.3)))

def reloj2d(h, m, t, cong=False):
    L, d = ui.capa(330, 330)
    d.ellipse([10, 20, 650, 660], fill=(40, 30, 60)); d.ellipse([10, 10, 650, 650], fill=(250, 250, 255), outline=(60, 50, 90), width=26)
    for i in range(12):
        a = i / 12 * 6.283; d.line([330 + 250 * math.sin(a), 330 - 250 * math.cos(a), 330 + 285 * math.sin(a), 330 - 285 * math.cos(a)], fill=(60, 50, 90), width=14)
    for ang, lg, wd, c in ((h / 12 * 6.283, 160, 26, (40, 30, 60)), (m / 60 * 6.283, 240, 16, ui.ROJO)):
        d.line([330, 330, 330 + lg * math.sin(ang), 330 - lg * math.cos(ang)], fill=c, width=wd)
    d.ellipse([310, 310, 350, 350], fill=(40, 30, 60))
    if cong: d.ellipse([10, 10, 650, 650], outline=(150, 220, 255), width=40)
    return L

@functools.lru_cache(maxsize=4)
def fondo(osc=0.6, blur=16):
    e = salon(); comedor(e)
    return ui.oscurece(e.render(T.Cam((0.2, 1.8, -3.6), (0.6, 1.0, 1.2), 56)), osc, blur)

CAM_G = lambda t, D: T.cam_keys(t, [(0, (-1.6, 2.1, -3.4), (0.5, 0.9, 1.3), 58), (D, (-1.3, 2.0, -2.9), (0.5, 0.9, 1.3), 56)])

# ------------------------------------------------------------------ tomas
def t_gancho(t, k):
    tc = k.at(0, 4)
    if t < tc:                                                # desde el fotograma 0: los platos caen en la mesa, vapor y «¡A COMER!»
        e = salon(); u = clamp(t / 0.35)
        e.pon(T.mesa_comedor(), pos=MESA)
        xs = (MESA[0] - 0.45, MESA[0] + 0.45, MESA[0])
        zs = (MESA[2] + 0.18, MESA[2] + 0.18, MESA[2] - 0.22)
        for i, (x, z) in enumerate(zip(xs, zs)):
            ui_ = clamp((t - 0.1 * i) / 0.3); y = 0.775 + 1.2 * (1 - eo(ui_)) ** 2
            e.pon(T.plato(1.0), pos=(x, y, z))
        e.pon(T.persona(brazo=2.0, brazo2=1.6, **FAM[0]), pos=(0.3, 0, 0.6), yaw=math.pi - 0.3)
        cam = T.cam_keys(t, [(0, (2.4, 2.3, -3.2), (0.7, 1.0, 0.5), 60), (tc, (1.9, 1.8, -2.0), (0.8, 1.0, 0.4), 52)], suave=T.eo)
        sh = 0.03 * math.sin(t * 50) * max(0, 1 - t / 0.6)
        cam = T.Cam(cam.pos + (sh, sh, 0), cam.mira, cam.fov)
        img = T.vineta(e.render(cam))
        if t > 0.3: vapor(img, cam, (xs[2], 0.8, zs[2]), t, clamp((t - 0.3) / 0.3))
        if t > 0.15: ui.texto(img, "¡A COMER!", 560, 640 - 20 * eo((t - 0.15) / 0.3), 120, ui.ROSA)
        return img
    lt = t - tc
    img = fondo().copy()
    ui.pega(img, reloj2d(9, 15, lt, cong=lt > 0.6), 505, 1180, esc=0.9)
    if lt > 0.6: ui.sello(img, "TIEMPO\nCONGELADO", 760, 1430, lt - 0.6, col=(110, 200, 255), giro=8, size=56)
    ui.pega(img, globo("¡YA VOY!", 110), 505, 760 + 10 * math.sin(lt * 3), esc=0.5 + 0.5 * eb(lt / 0.3))
    return img

def t_nombre(t, k):
    img = ui.rayos(t, cols=((240, 180, 40), (180, 110, 20)), brillo=(255, 245, 200))
    ui.pedestal(img, 540, 1250, col=(60, 70, 130))
    ui.pega(img, globo("¡YA VOY!", 110), 540, 980 + 14 * math.sin(t * 2.4), esc=0.9 * (0.7 + 0.3 * eb(t / 0.3)), giro=5 * math.sin(t * 1.7))
    ui.placa(img, "EL «YA VOY»™", 505, 1450, t - k.at(0, 2), size=78)
    return img

def _lineas(k): return [k.at(1, 0), k.at(3, 0), k.at(5, 0)]

def t_tres(t, k):
    D = k.dur; li = _lineas(k); n = len([x for x in li if x <= t])
    hora = 21.0 + [0, 0.08, 0.33, 0.75][n] + 0.05 * (t - (li[n - 1] if n else 0))
    lavan = t >= k.at(4, 0)
    e = salon(hora)
    comedor(e, vapor=1.0 if t < k.at(2, 0) else 0.0, comida=0.0 if lavan else (1.0 if n < 2 else 0.4), fam=(not lavan, True), plato_lolo=1.0)
    if lavan: e.pon(T.persona(brazo=1.0, **FAM[0]), pos=(MESA[0] + 0.9, 0, MESA[2] + 1.5), yaw=0.2)      # se lleva los platos
    cam = CAM_G(t, D)
    img = T.vineta(e.render(cam))
    if t < k.at(2, 0): vapor(img, cam, (MESA[0], 0.8, MESA[2] - 0.22), t)
    for i, x in enumerate(li):
        if x <= t < x + 1.0: globo3d(img, cam, (SOFA_L[0], 2.0, SOFA_L[2]), t - x, ["¡YA VOY!", "¡YA VOY!", "¡YA VOOOY!"][i], esc=[0.9, 1.0, 1.2][i])
    if n: ui.contador(img, ["+5 MIN", "+20 MIN", "+45 MIN"][n - 1], 800, 650, t - li[n - 1], size=[90, 100, 115][n - 1], col=[ui.AMAR, (255, 150, 40), ui.ROJO][n - 1])
    if t >= k.at(2, 2): ui.sello(img, "SOPA FRÍA", 330, 1380, t - k.at(2, 2), col=(110, 200, 255), giro=-6, size=62)
    return img

def t_fria(t, k):
    tf = k.at(1, 0); tt = min(t, tf)                          # se congela en «te quejas»
    e = salon(22.2, lolo_sofa=False)
    comedor(e, vapor=0, comida=0.0, fam=(False, False), plato_lolo=1.0)
    u = clamp(tt / max(0.4, tf - 0.2))
    if u < 1: e.pon(T.persona(paso=tt * 9), pos=(-0.2 + 1.5 * u, 0, 1.2 - 1.9 * u), yaw=math.pi * 0.75)
    else: e.pon(T.persona(sentado=True, brazo=1.0, brazo2=0.3), pos=(MESA[0], 0, MESA[2] - 0.8), yaw=0)
    cam = T.cam_keys(tt, [(0, (0.0, 1.9, -2.6), (1.0, 0.9, 0.4), 54), (tf, (0.4, 1.7, -2.2), (1.2, 0.85, 0.0), 50)])
    img = T.vineta(e.render(cam))
    if t >= tf:
        img = ui.congela(img, t - tf)
        ui.pega(img, lolo("enfado", t), 330, 1340 + (1 - eb((t - tf) / 0.3)) * 500, esc=0.8)
        ui.placa(img, "¿QUIÉN LA\nENFRIÓ?", 660, 1020, t - k.at(1, 3), size=62, giro=4)
    return img

def t_giro(t, k):
    tl = k.at(0, 5)                                           # «ya voy»
    e = salon(22.5, lolo_sofa=False, otro_sofa=True)
    comedor(e, vapor=1.0, comida=1.0, fam=(False, False), lolo_mesa=0.6 + 0.4 * abs(math.sin(t * 6)), plato_lolo=1.0)
    cam = T.cam_keys(t, [(0, (0.0, 2.3, -2.8), (-0.2, 1.0, 1.8), 58), (k.dur, (0.1, 2.2, -2.4), (-0.2, 1.0, 1.8), 55)])
    img = T.vineta(e.render(cam))
    if t >= tl: globo3d(img, cam, (SOFA_L[0], 2.0, SOFA_L[2]), t - tl, "¡YA VOY!", 0.8)
    if t >= tl + 0.3: ui.contador(img, f"ESPERANDO: {min(2, int((t - tl) * 1.2))} MIN", 505, 700, (t - tl) % 0.85, size=80, col=ui.AMAR, giro=-3)
    ts = k.at(1, 2)
    if t >= ts:
        ui.pega(img, lolo("enfado", t), 330, 1340 + (1 - eb((t - ts) / 0.3)) * 500, esc=0.75)
        ui.sello(img, "¡QUÉ FALTA\nDE RESPETO!", 700, 1100, t - ts - 0.1, col=ui.ROJO, giro=6, size=58)
    return img

def t_dato(t, k):
    img = fondo(0.74, 14).copy()
    ui.sello(img, "DATO REAL", 505, 520, t - k.at(0, 1), col=ui.TEAL, giro=-5, size=96)
    t1 = k.at(0, 8)
    if t >= t1:
        d = ImageDraw.Draw(img); x0, x1 = 150, 870
        for j, (et, y, v, col, ta) in enumerate((("CALCULARON", 860, 34, ui.VERDE, t1), ("TARDARON", 1080, 56, ui.ROJO, k.at(1, 0)))):
            if t < ta: continue
            p = eo((t - ta) / 0.8)
            ui.texto(img, et, x0, y - 62, 52, ui.BLANCO, ancla="lm")
            ui.texto(img, f"{int(v * p)} DÍAS", x1, y - 62, 52, col, ancla="rm")
            d.rounded_rectangle([x0, y - 28, x1, y + 28], 28, fill=(30, 26, 62))
            d.rounded_rectangle([x0, y - 28, x0 + max(56, (x1 - x0) * v / 60 * p), y + 28], 28, fill=col)
    if t >= k.at(1, 0) + 0.8: ui.texto(img, "¡CASI EL DOBLE!", 505, 1240, 70, ui.AMAR)
    ui.fuente_chip(img, "Fuente: Buehler, Griffin y Ross (1994)", t - k.at(0, 6), y=1515)
    return img

def t_nombre_real(t, k):
    e = salon(21.0 + t * 0.6)
    comedor(e, vapor=0, comida=0.0, fam=(False, False), plato_lolo=1.0)
    cam = T.cam_keys(t, [(0, (-0.4, 1.8, -1.6), (0.5, 2.0, 2.9), 50), (k.dur, (-0.2, 1.9, -1.0), (0.5, 2.2, 2.9), 44)])
    img = T.vineta(e.render(cam))
    ui.placa(img, "FALACIA DE LA\nPLANIFICACIÓN", 505, 1250, t - k.at(0, 2), size=66, col=(255, 255, 255), giro=-3)
    if t >= k.at(1, 0): ui.sello(img, "LE PASA\nA TODOS", 505, 760, t - k.at(1, 0), col=ui.TEAL, giro=5, size=70)
    return img

def t_cierre(t, k):
    e = salon(22.0, lolo_sofa=False); comedor(e, vapor=0, comida=0.6)
    cam = T.cam_keys(t, [(0, (-1.2, 1.9, -2.8), (0.6, 1.1, 1.0), 56), (k.dur, (-1.0, 1.85, -2.4), (0.6, 1.1, 1.0), 54)])
    img = ui.oscurece(T.vineta(e.render(cam)), 0.2)
    tl = k.at(0, 7)
    g = "chulo" if t < tl else "feliz"
    ui.pega(img, lolo(g, t, banda="REY DEL YA VOY"), 505, 1300 + (1 - eb(t / 0.35)) * 700, esc=1.08)
    ui.placa(img, "EL QUE DICE «YA VOY»\nY TARDA 20 MINUTOS", 505, 820, t - k.at(0, 6), size=50, giro=-3)
    ui.pregunta(img, PREGUNTA, t, k, size=54)
    return img


TOMAS = [
    dict(sents=["¿Sabías que hay dos palabras que congelan el tiempo de los demás?"], dib=t_gancho, pausa=0.45, d3=lambda k: k.at(0, 4) / k.dur,
         sfx=[("golpe", 0.0, 0.7), ("clic", lambda k: [0.3, 0.4, 0.5], 0.6), ("whoosh", (0, 4), 0.5), ("congela", lambda k: k.at(0, 4) + 0.6, 0.7)]),
    dict(sents=["Son estas: «ya voy»."], dib=t_nombre, pausa=0.5, corte="whip", d3=0, sfx=[("tada", 0.05, 0.5), ("golpe", (0, 2), 0.6)]),
    dict(sents=["¿Te llaman a comer?", "Ya voy.", "¿Se enfría la sopa?", "Ya voy.", "¿Ya están lavando los platos?", "Ya voooy."], dib=t_tres, pausa=0.5, gap=0.14, d3=1,
         sfx=[("pop", _lineas, 0.6), ("tic", lambda k: [k.at(1, 0) + i * 0.1 for i in range(6)] + [k.at(3, 0) + i * 0.07 for i in range(10)], 0.3), ("golpe", (2, 2), 0.5)]),
    dict(sents=["Y cuando por fin llegas,", "te quejas de que está fría."], dib=t_fria, pausa=0.55, corte="whip", d3=1,
         sfx=[("congela", (1, 0), 0.9), ("pop", (1, 3), 0.6)]),
    dict(sents=["Pero si alguien te dice «ya voy» a ti…", "es una falta de respeto."], dib=t_giro, pausa=0.55, corte="whip", d3=1,
         sfx=[("pop", (0, 5), 0.6), ("tic", lambda k: [k.at(0, 5) + 0.3 + i * 0.25 for i in range(6)], 0.3), ("golpe", (1, 2), 0.8)]),
    dict(sents=["El dato real: en un estudio, unos estudiantes calcularon que terminarían su trabajo en 34 días.", "Tardaron 56."],
         dib=t_dato, pausa=0.4, corte="whip", d3=0, sfx=[("golpe", (0, 1), 0.8), ("sube", (0, 8), 0.4), ("error", (1, 1), 0.5)]),
    dict(sents=["Tiene nombre: falacia de la planificación.", "Le pasa a casi todo el mundo."], dib=t_nombre_real, pausa=0.5, d3=1,
         sfx=[("whoosh", 0.1, 0.4), ("golpe", (0, 2), 0.6), ("pop", (1, 0), 0.5)]),
    dict(sents=["Así que mándaselo a ese amigo que dice «ya voy» y tarda veinte minutos."], dib=t_cierre, pausa=1.9, d3=1,
         sfx=[("tada", 0.1, 0.5), ("pop", (0, 6), 0.6)]),
]
