# tresd.py — motor 3D «low-poly» del kit de Manuales Irónicos (v1.0, 14-nov-2026).
# Solo numpy + PIL: sin Blender ni GPU, para que funcione igual en cualquier sesión de Claude Code.
#
# Ideas básicas
#   · Ejes: x = derecha, y = arriba, z = fondo. Unidades en metros.
#   · Un objeto (`Obj`) es una malla de caras planas con color, alfa, emisión (luz propia) y `bias`
#     (las calcomanías —ventanas, faros— se pintan después de la pared que las lleva).
#   · `Escena.render(cam)` proyecta, descarta caras traseras, recorta contra el plano cercano, ordena
#     (capa → objeto de lejos a cerca → cara de lejos a cerca), ilumina (sol + ambiente), aplica niebla
#     por distancia y añade resplandor (bloom) a todo lo emisivo. Devuelve un PIL RGB de 1080x1920.
#   · La cámara se anima con `cam_keys(t, claves)`: posición, punto al que mira y campo de visión.
#
# Piezas: caja(), tcaja() (caja con techo más pequeño), cilindro(), esfera(), suelo(), franja(),
#         coche(), edificio(), farola(), semaforo(), arbol(), corona(), persona(), cupula().
# Decorados completos: calle() (avenida al atardecer) y dormitorio() (interior con ventana día/noche, puerta,
#         reloj de pared, cama(), mesilla(), telefono(), reloj_arena()) y cocina() (encimera, nevera, ventana,
#         lámpara; piezas galleta(), bacteria(), cronometro()) y salon() (sofa(), planta(), lampara_pie(),
#         tarjeta(), escoba(); persona(sentado=True) para sentar a alguien) y oficina(frio) (escritorio(), silla(),
#         aire(), pinguino(), copo(); frio 0..1 congela la sala) y metro(t) (vagón con bancos, barras, ventanas
#         con las luces del túnel pasando y pasajeros sentados; piezas microfono(), burbuja_audio(), sitio_pasajero()) y supermercado()
#         (caja con cajera, estanterías y una fila: fila_pos(i), cliente(i), carrito(), estanteria()).
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
SS = 1.5                      # supermuestreo (1.5 = bordes suaves sin triplicar el tiempo)


def v3(*a): return np.array(a, float)
def _n(a):
    a = np.asarray(a, float); return a / max(1e-9, np.linalg.norm(a))
def clamp(t, a=0.0, b=1.0): return max(a, min(b, t))
def eo(t): t = clamp(t); return 1 - (1 - t) ** 3
def eio(t): t = clamp(t); return t * t * (3 - 2 * t)
def lerp(a, b, u): return a + (b - a) * u


# ------------------------------------------------------------------ mallas
class Obj:
    def __init__(self, capa=2):
        self.V, self.F, self.C, self.A, self.E, self.B, self.DS = [], [], [], [], [], [], []
        self.capa = capa
        self._fin = None

    def cara(self, pts, col, alfa=255, emis=0.0, bias=0, ds=False):
        i0 = len(self.V); self.V.extend([tuple(map(float, p)) for p in pts])
        self.F.append(tuple(range(i0, i0 + len(pts))))
        self.C.append(col[:3]); self.A.append(alfa); self.E.append(emis); self.B.append(bias); self.DS.append(ds)
        self._fin = None
        return self

    def une(self, o, pos=(0, 0, 0), yaw=0.0, esc=1.0):
        """Añade otra malla (ya colocada) a esta."""
        Vn = o.mundo(pos, yaw, esc)[0]
        i0 = len(self.V); self.V.extend(map(tuple, Vn))
        self.F.extend(tuple(i + i0 for i in f) for f in o.F)
        self.C.extend(o.C); self.A.extend(o.A); self.E.extend(o.E); self.B.extend(o.B); self.DS.extend(o.DS)
        self._fin = None
        return self

    def orienta(self, centro=None):
        """Pone todas las caras mirando hacia fuera de `centro` (para sólidos convexos)."""
        V = np.array(self.V); c = V.mean(0) if centro is None else np.array(centro, float)
        for k, f in enumerate(self.F):
            p = V[list(f)]; n = np.cross(p[1] - p[0], p[2] - p[0])
            if np.dot(n, p.mean(0) - c) < 0: self.F[k] = tuple(reversed(f))
        return self

    def fin(self):
        if self._fin is None:
            V = np.array(self.V, float)
            i3 = np.array([f[:3] for f in self.F])
            cen = np.array([V[list(f)].mean(0) for f in self.F])
            nor = np.cross(V[i3[:, 1]] - V[i3[:, 0]], V[i3[:, 2]] - V[i3[:, 0]])
            nor /= np.maximum(1e-9, np.linalg.norm(nor, axis=1))[:, None]
            self._fin = (V, cen, nor, np.array(self.C, float), np.array(self.A, float), np.array(self.E, float),
                         np.array(self.B, float), np.array(self.DS, bool))
        return self._fin

    def mundo(self, pos=(0, 0, 0), yaw=0.0, esc=1.0):
        V, cen, nor = self.fin()[:3]
        c, s = math.cos(yaw), math.sin(yaw)
        R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        p = np.array(pos, float)
        return (V * esc) @ R.T + p, (cen * esc) @ R.T + p, nor @ R.T


class Pieza:
    """Un objeto colocado en la escena."""
    def __init__(self, obj, pos=(0, 0, 0), yaw=0.0, esc=1.0, capa=None, tinte=None, orden=None):
        self.obj, self.pos, self.yaw, self.esc = obj, pos, yaw, esc
        self.capa = obj.capa if capa is None else capa
        self.tinte = tinte          # multiplica el color (p. ej. gris al «congelar»)
        self.orden = orden          # distancia forzada para ordenar (None = la del centro)


def caja(w, h, d, col, y0=0.0, cols=None):
    """Caja centrada en x,z con base en y0. cols = dict opcional con color por cara: top, bottom, front(+z), back, left, right."""
    o = Obj(); x, z = w / 2, d / 2; y1 = y0 + h; cols = cols or {}
    P = lambda a, b, c: (a, b, c)
    caras = dict(top=[P(-x, y1, -z), P(-x, y1, z), P(x, y1, z), P(x, y1, -z)], bottom=[P(-x, y0, -z), P(x, y0, -z), P(x, y0, z), P(-x, y0, z)],
                 front=[P(-x, y0, z), P(x, y0, z), P(x, y1, z), P(-x, y1, z)], back=[P(-x, y0, -z), P(-x, y1, -z), P(x, y1, -z), P(x, y0, -z)],
                 left=[P(-x, y0, -z), P(-x, y0, z), P(-x, y1, z), P(-x, y1, -z)], right=[P(x, y0, -z), P(x, y1, -z), P(x, y1, z), P(x, y0, z)])
    for k, pts in caras.items(): o.cara(pts, cols.get(k, col))
    return o.orienta((0, y0 + h / 2, 0))


def tcaja(w0, d0, w1, d1, h, col, y0=0.0, dz=0.0):
    """Caja con la tapa más pequeña (cabina de coche, tejado). dz desplaza la tapa en z."""
    o = Obj(); a, b, c, e = w0 / 2, d0 / 2, w1 / 2, d1 / 2; y1 = y0 + h
    lo = [(-a, y0, -b), (a, y0, -b), (a, y0, b), (-a, y0, b)]
    hi = [(-c, y1, -e + dz), (c, y1, -e + dz), (c, y1, e + dz), (-c, y1, e + dz)]
    o.cara(hi, col)
    for k in range(4): o.cara([lo[k], lo[(k + 1) % 4], hi[(k + 1) % 4], hi[k]], col)
    return o.orienta((0, y0 + h / 2, 0))


def cilindro(r, h, col, n=10, y0=0.0, r1=None, eje="y", tapas=True, emis=0.0, alfa=255):
    r1 = r if r1 is None else r1
    o = Obj(); A = [k / n * 2 * math.pi for k in range(n)]
    lo = [(r * math.cos(a), y0, r * math.sin(a)) for a in A]; hi = [(r1 * math.cos(a), y0 + h, r1 * math.sin(a)) for a in A]
    for k in range(n): o.cara([lo[k], lo[(k + 1) % n], hi[(k + 1) % n], hi[k]], col, alfa, emis)
    if tapas:
        if r1 > 1e-6: o.cara(hi, col, alfa, emis)
        o.cara(lo, col, alfa, emis)
    o.orienta((0, y0 + h / 2, 0))
    if eje == "x": o.V = [(y, x, z) for x, y, z in o.V]; o.orienta((y0 + h / 2, 0, 0))
    if eje == "z": o.V = [(x, z, y) for x, y, z in o.V]; o.orienta((0, 0, y0 + h / 2))
    return o


def esfera(r, col, nu=10, nv=7, cy=0.0, v0=0.0, v1=1.0, emis=0.0, alfa=255, ds=False):
    """Esfera facetada. v0..v1 recorta en vertical (0 = polo norte, 1 = polo sur): media esfera = v1=0.5."""
    o = Obj()
    def p(i, j):
        th = i / nu * 2 * math.pi; ph = (v0 + (v1 - v0) * j / nv) * math.pi
        return (r * math.sin(ph) * math.cos(th), cy + r * math.cos(ph), r * math.sin(ph) * math.sin(th))
    for j in range(nv):
        for i in range(nu):
            q = [p(i, j), p(i + 1, j), p(i + 1, j + 1), p(i, j + 1)]
            if j == 0 and v0 == 0: q = [q[0], q[2], q[3]]
            elif j == nv - 1 and v1 == 1: q = [q[0], q[1], q[2]]
            o.cara(q, col, alfa, emis, ds=ds)
    return o.orienta((0, cy, 0))


def suelo(x0, x1, z0, z1, col, paso=6.0, y=0.0, capa=0, col2=None):
    """Plano en baldosas (cada una recibe su niebla). col2 alterna un poco el tono."""
    o = Obj(capa); nz = max(1, int(round((z1 - z0) / paso))); nx = max(1, int(round((x1 - x0) / paso)))
    for i in range(nx):
        for j in range(nz):
            a, b = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
            c, e = z0 + (z1 - z0) * j / nz, z0 + (z1 - z0) * (j + 1) / nz
            o.cara([(a, y, c), (a, y, e), (b, y, e), (b, y, c)], col2 if (col2 and (i + j) % 2) else col)
    return o


def franja(x0, z0, x1, z1, ancho, col, y=0.02, capa=1, emis=0.0, alfa=255):
    """Rectángulo pintado en el suelo de (x0,z0) a (x1,z1) con un ancho (líneas de carril, paso de peatones)."""
    o = Obj(capa); d = _n((x1 - x0, 0, z1 - z0)); n = np.array([-d[2], 0, d[0]]) * ancho / 2
    a, b = np.array([x0, y, z0]), np.array([x1, y, z1])
    o.cara([a - n, a + n, b + n, b - n], col, alfa, emis, ds=True)
    return o


# ------------------------------------------------------------------ piezas de ciudad
PINTURAS = [(214, 60, 70), (240, 240, 235), (60, 120, 220), (250, 190, 40), (70, 180, 120), (150, 90, 200), (235, 130, 60), (60, 70, 90)]

def coche(col, luces=1.0, freno=0.0, taxi=False):
    """Coche de ~4,2 m mirando a +z. luces = faros encendidos (0..1); freno = luces de freno."""
    o = Obj(); osc = tuple(int(c * 0.55) for c in col)
    o.une(caja(1.8, 0.55, 4.2, col, y0=0.32, cols=dict(bottom=osc)))
    o.une(tcaja(1.7, 2.3, 1.35, 1.5, 0.52, tuple(int(c * 0.9) for c in col), y0=0.87, dz=-0.05), pos=(0, 0, -0.25))
    vid = (40, 54, 84)
    for sx in (-1, 1):                                   # ventanillas laterales
        o.cara([(sx * 0.86, 0.93, -1.25), (sx * 0.86, 0.93, 0.75), (sx * 0.71, 1.33, 0.4), (sx * 0.71, 1.33, -0.95)], vid, bias=1, ds=True)
    o.cara([(-0.7, 0.93, 0.92), (0.7, 0.93, 0.92), (0.58, 1.33, 0.53), (-0.58, 1.33, 0.53)], (70, 96, 140), bias=1, ds=True)      # parabrisas
    o.cara([(-0.7, 0.93, -1.42), (0.7, 0.93, -1.42), (0.58, 1.33, -1.05), (-0.58, 1.33, -1.05)], vid, bias=1, ds=True)           # luna trasera
    for sx in (-1, 1):
        for sz in (-1.3, 1.3):
            o.une(cilindro(0.34, 0.24, (24, 24, 30), n=8, eje="x"), pos=(sx * 0.92 - 0.12, 0.34, sz))
        o.cara([(sx * 0.45, 0.55, 2.11), (sx * 0.8, 0.55, 2.11), (sx * 0.8, 0.75, 2.11), (sx * 0.45, 0.75, 2.11)],
               (255, 244, 200), emis=1.6 * luces, bias=2, ds=True)
        r = 0.5 + 1.4 * freno
        o.cara([(sx * 0.45, 0.6, -2.11), (sx * 0.82, 0.6, -2.11), (sx * 0.82, 0.76, -2.11), (sx * 0.45, 0.76, -2.11)],
               (255, 40, 40), emis=r, bias=2, ds=True)
    if taxi: o.une(caja(0.5, 0.16, 0.25, (255, 230, 90)), pos=(0, 1.39, -0.3)); o.E[-6:] = [1.0] * 6
    return o


def edificio(w, h, d, col, rng, vent=(255, 214, 140), lados=("front", "left", "right", "back"), lit=0.45):
    """Bloque con ventanas (unas encendidas y otras no) en los lados indicados."""
    o = caja(w, h, d, col, cols=dict(top=tuple(int(c * 0.7) for c in col)))
    pisos = int((h - 2.5) / 3.1); apag = tuple(int(c * 0.42) for c in col)
    def fila(lado):
        ancho = w if lado in ("front", "back") else d
        n = max(2, int(ancho / 2.6)); m = ancho / n
        for p in range(pisos):
            y0 = 3.0 + p * 3.1
            for k in range(n):
                a = -ancho / 2 + k * m + m * 0.22; b = a + m * 0.56
                on = rng.random() < lit
                c = tuple(int(x * rng.uniform(0.8, 1.0)) for x in vent) if on else apag
                e = rng.uniform(0.3, 0.55) if on else 0.0
                if lado == "front": q = [(a, y0, d / 2 + .03), (b, y0, d / 2 + .03), (b, y0 + 1.7, d / 2 + .03), (a, y0 + 1.7, d / 2 + .03)]
                elif lado == "back": q = [(b, y0, -d / 2 - .03), (a, y0, -d / 2 - .03), (a, y0 + 1.7, -d / 2 - .03), (b, y0 + 1.7, -d / 2 - .03)]
                elif lado == "left": q = [(-w / 2 - .03, y0, b), (-w / 2 - .03, y0, a), (-w / 2 - .03, y0 + 1.7, a), (-w / 2 - .03, y0 + 1.7, b)]
                else: q = [(w / 2 + .03, y0, a), (w / 2 + .03, y0, b), (w / 2 + .03, y0 + 1.7, b), (w / 2 + .03, y0 + 1.7, a)]
                o.cara(q, c, emis=e, bias=1)
    for l in lados: fila(l)
    # las ventanas heredan la orientación de su pared: se recalcula con el centro
    V = np.array(o.V)
    for k, f in enumerate(o.F[6:], 6):
        p = V[list(f)]; n = np.cross(p[1] - p[0], p[2] - p[0]); c = p.mean(0) - (0, p.mean(0)[1], 0)
        if np.dot(n, c) < 0: o.F[k] = tuple(reversed(f))
    return o


def farola(h=7.0, brazo=1.6, on=1.0):
    o = Obj(); g = (60, 64, 80)
    o.une(cilindro(0.11, h, g, n=6))
    o.une(caja(brazo, 0.12, 0.12, g), pos=(brazo / 2, h - 0.1, 0))
    o.une(caja(0.7, 0.14, 0.36, (255, 226, 160)), pos=(brazo - 0.2, h - 0.26, 0)); o.E[-6:] = [1.8 * on] * 6
    return o


def semaforo(estado="rojo", peaton="rojo", boton=0.0):
    """Poste con semáforo de vehículos (arriba), figura para peatones y la caja del botón.
    estado: rojo | ambar | verde (vehículos). peaton: rojo | verde. boton 0..1 = anillo encendido."""
    o = Obj(); g = (52, 56, 70)
    o.une(cilindro(0.1, 5.4, g, n=8))
    o.une(caja(0.62, 1.7, 0.5, (30, 32, 42)), pos=(0, 3.7, 0))
    luces = [("rojo", (255, 60, 50), 4.95), ("ambar", (255, 190, 40), 4.42), ("verde", (60, 240, 120), 3.9)]
    for nom, c, y in luces:
        on = estado == nom
        cc = c if on else tuple(int(x * 0.22) for x in c)
        o.cara([(-0.2, y - 0.2, 0.26), (0.2, y - 0.2, 0.26), (0.2, y + 0.2, 0.26), (-0.2, y + 0.2, 0.26)], cc, emis=2.2 if on else 0, bias=2, ds=True)
    o.une(caja(0.5, 0.95, 0.4, (30, 32, 42)), pos=(0, 2.35, 0))                          # cabeza de peatones (mira a +x)
    for nom, c, y in (("rojo", (255, 60, 50), 3.0), ("verde", (60, 240, 120), 2.58)):
        on = peaton == nom; cc = c if on else tuple(int(x * 0.22) for x in c)
        o.cara([(0.26, y - 0.16, -0.14), (0.26, y - 0.16, 0.14), (0.26, y + 0.16, 0.14), (0.26, y + 0.16, -0.14)], cc, emis=2.0 if on else 0, bias=2, ds=True)
    o.une(caja(0.3, 0.42, 0.26, (250, 196, 30)), pos=(0.2, 1.05, 0))                      # caja del botón
    c = (255, 70, 60) if boton > 0.02 else (190, 190, 200)
    o.cara([(0.36, 1.2, -0.07), (0.36, 1.2, 0.07), (0.36, 1.34, 0.07), (0.36, 1.34, -0.07)], c, emis=2.2 * boton, bias=2, ds=True)
    return o


def arbol(h=5.0, col=(60, 150, 110)):
    o = Obj(); o.une(cilindro(0.16, h * 0.4, (90, 62, 50), n=6))
    o.une(esfera(h * 0.3, col, nu=7, nv=5, cy=h * 0.62)); return o


def corona(r=0.3, col=(255, 205, 50), n=8, emis=0.9):
    """Corona dorada (el objeto-metáfora del vídeo de muestra)."""
    o = Obj()
    for k in range(n):
        a0, a1 = k / n * 2 * math.pi, (k + 1) / n * 2 * math.pi; am = (a0 + a1) / 2
        p0, p1 = (r * math.cos(a0), 0, r * math.sin(a0)), (r * math.cos(a1), 0, r * math.sin(a1))
        q0, q1 = (r * math.cos(a0), r * 0.5, r * math.sin(a0)), (r * math.cos(a1), r * 0.5, r * math.sin(a1))
        c = col if k % 2 else tuple(int(x * 0.85) for x in col)
        o.cara([p0, p1, q1, q0], c, emis=emis, ds=True)
        o.cara([q0, q1, (r * 1.08 * math.cos(am), r * 1.15, r * 1.08 * math.sin(am))], c, emis=emis, ds=True)
    return o


def cupula(r, col=(255, 210, 90), nu=14, nv=5, alfa=46, emis=0.5):
    """Media esfera translúcida (aura, campo de fuerza)."""
    return esfera(r, col, nu=nu, nv=nv, v0=0, v1=0.5, alfa=alfa, emis=emis, ds=True)


def persona(sudadera=(120, 78, 214), gorro=(255, 205, 40), piel=(233, 178, 128), pant=(44, 50, 78),
            paso=0.0, brazo=0.0, brazo2=0.0, gorro_on=True, pompon=True, sentado=False):
    """Figura low-poly de 1,75 m mirando a +z. paso = fase de andar (rad); brazo / brazo2 = 0 (bajado) .. 1 (al frente) .. 2 (arriba).
    sentado=True: muslos hacia delante y asiento a 0,45 m (para sofás y sillas; origen = suelo, bajo la cadera)."""
    o = Obj()
    for sx, ph in ((-1, 0.0), (1, math.pi)):
        if sentado:
            o.une(caja(0.2, 0.2, 0.5, pant, y0=0.45), pos=(sx * 0.13, 0, 0.2))
            o.une(caja(0.2, 0.47, 0.2, pant), pos=(sx * 0.13, 0.04, 0.4))
            o.une(caja(0.22, 0.1, 0.34, (245, 245, 245)), pos=(sx * 0.13, 0, 0.45))
            continue
        sw = math.sin(paso + ph) * 0.32 if paso else 0.0
        pier = caja(0.2, 0.8, 0.22, pant); V = np.array(pier.V); V[:, 2] += (0.8 - V[:, 1]) * sw; pier.V = [tuple(p) for p in V]; pier._fin = None
        o.une(pier, pos=(sx * 0.13, 0.04, 0))
        o.une(caja(0.22, 0.1, 0.34, (245, 245, 245)), pos=(sx * 0.13, 0, sw * 0.8 + 0.05))
    up = Obj()
    up.une(tcaja(0.56, 0.34, 0.5, 0.3, 0.62, sudadera, y0=0.82))
    for sx, lv in ((-1, brazo2), (1, brazo)):
        a = lv * math.pi / 2
        br = caja(0.15, 0.56, 0.15, sudadera); V = np.array(br.V) - (0, 0.56, 0)       # cuelga del hombro
        y, z = V[:, 1] * math.cos(a) - V[:, 2] * math.sin(a), -V[:, 1] * math.sin(a) + V[:, 2] * math.cos(a)
        V[:, 1], V[:, 2] = y, z; br.V = [tuple(p) for p in V]; br._fin = None; br.orienta()
        up.une(br, pos=(sx * 0.36, 1.4, 0))
        up.une(esfera(0.085, piel, nu=6, nv=4), pos=(sx * 0.36, 1.4 - 0.6 * math.cos(a), 0.6 * math.sin(a)))
    up.une(cilindro(0.08, 0.1, piel, n=6), pos=(0, 1.42, 0))
    up.une(esfera(0.23, piel, nu=10, nv=7), pos=(0, 1.7, 0))
    for sx in (-1, 1):                                       # ojos
        q = [(sx * 0.05, 1.7, 0.232), (sx * 0.12, 1.7, 0.21), (sx * 0.12, 1.77, 0.2), (sx * 0.05, 1.77, 0.222)]
        up.cara(q if sx > 0 else q[::-1], (30, 26, 40), bias=3)                       # sin doble cara: de espaldas no se ven (v1.7, 19-nov)
    if gorro_on:
        up.une(esfera(0.25, gorro, nu=10, nv=4, v0=0, v1=0.5), pos=(0, 1.74, -0.01))
        up.une(cilindro(0.255, 0.07, tuple(int(c * 0.85) for c in gorro), n=10, tapas=False), pos=(0, 1.72, -0.01))
        if pompon: up.une(esfera(0.07, (255, 255, 255), nu=6, nv=4), pos=(0, 2.02, -0.01))
    o.une(up, pos=(0, -0.2 if sentado else 0, 0))
    return o


# ------------------------------------------------------------------ cámara
class Cam:
    def __init__(self, pos, mira, fov=50.0, giro=0.0):
        self.pos = np.array(pos, float); self.mira = np.array(mira, float); self.fov = fov
        f = _n(self.mira - self.pos); r = _n(np.cross((0, 1, 0), f)); u = np.cross(f, r)
        if giro:
            c, s = math.cos(giro), math.sin(giro); r, u = r * c + u * s, -r * s + u * c
        self.R = np.stack([r, u, f]); self.foc = (H / 2) / math.tan(math.radians(fov) / 2)

    def a_cam(self, P): return (np.asarray(P, float) - self.pos) @ self.R.T

    def pantalla(self, p):
        """Punto del mundo → (x, y, z) en píxeles de 1080x1920 (z = profundidad; < 0.1 = detrás)."""
        c = self.a_cam(p); z = max(1e-6, c[2])
        return W / 2 + c[0] / z * self.foc, H / 2 - c[1] / z * self.foc, c[2]


def cam_keys(t, claves, suave=eio):
    """claves = [(t, pos, mira, fov), ...] → Cam interpolada (con suavizado entre claves)."""
    if t <= claves[0][0]: k = claves[0]; return Cam(k[1], k[2], k[3])
    for a, b in zip(claves, claves[1:]):
        if t <= b[0]:
            u = suave((t - a[0]) / max(1e-6, b[0] - a[0]))
            return Cam(lerp(np.array(a[1], float), np.array(b[1], float), u), lerp(np.array(a[2], float), np.array(b[2], float), u), lerp(a[3], b[3], u))
    k = claves[-1]; return Cam(k[1], k[2], k[3])


# ------------------------------------------------------------------ render
def cielo(arriba=(26, 20, 64), medio=(120, 60, 150), abajo=(255, 150, 90), horizonte=0.52, sol=None):
    """Degradado de cielo (atardecer por defecto). sol = (x, y, radio, color) opcional."""
    y = np.linspace(0, 1, H)[:, None]
    u = np.clip(y / horizonte, 0, 1)
    a, m, b = (np.array(c, float) for c in (arriba, medio, abajo))
    col = np.where(u < 0.6, a + (m - a) * (u / 0.6), m + (b - m) * ((u - 0.6) / 0.4))
    img = Image.fromarray(np.repeat(col[:, None, :], W, 1).astype(np.uint8))
    if sol:
        x, yy, r, c = sol; g = Image.new("RGB", (W, H), (0, 0, 0)); d = ImageDraw.Draw(g)
        d.ellipse([x - r, yy - r, x + r, yy + r], fill=c)
        g2 = g.filter(ImageFilter.GaussianBlur(r * 0.9))
        img = Image.fromarray(np.clip(np.asarray(img, np.int16) + np.asarray(g2, np.int16) + np.asarray(g, np.int16) // 2, 0, 255).astype(np.uint8))
    return img


class Escena:
    def __init__(self, fondo=None, luz=(-0.45, 0.8, -0.35), amb=(0.50, 0.46, 0.66), dif=(0.78, 0.66, 0.50),
                 niebla=(150, 84, 140), dens=0.011, bloom=1.0):
        self.piezas = []; self.puntos = []          # puntos = luces sueltas (halo): (pos, color, radio en m, fuerza)
        self.fondo = fondo if fondo is not None else cielo()
        self.luz = _n(luz); self.amb = np.array(amb); self.dif = np.array(dif)
        self.niebla = np.array(niebla, float); self.dens = dens; self.bloom = bloom

    def pon(self, obj, pos=(0, 0, 0), yaw=0.0, esc=1.0, **k):
        self.piezas.append(Pieza(obj, pos, yaw, esc, **k)); return self

    def halo(self, pos, col, radio=0.6, fuerza=1.0): self.puntos.append((pos, col, radio, fuerza)); return self

    def copia(self):
        e = Escena(self.fondo, self.luz, self.amb, self.dif, self.niebla, self.dens, self.bloom)
        e.piezas = list(self.piezas); e.puntos = list(self.puntos); return e

    def render(self, cam, gris=0.0):
        sw, sh = int(W * SS), int(H * SS)
        img = self.fondo.resize((sw, sh), Image.BILINEAR).copy()
        d = ImageDraw.Draw(img, "RGBA")
        gw, gh = W // 3, H // 3
        glow = Image.new("RGB", (gw, gh), (0, 0, 0)); gd = ImageDraw.Draw(glow)
        near = 0.25; foc = cam.foc
        orden = []
        for pz in self.piezas:
            Vw, cen, nor = pz.obj.mundo(pz.pos, pz.yaw, pz.esc)
            dist = pz.orden if pz.orden is not None else float(np.linalg.norm(cen.mean(0) - cam.pos))
            orden.append((pz.capa, -dist, id(pz), pz, Vw, cen, nor))
        orden.sort(key=lambda x: (x[0], x[1]))
        for capa, _, _, pz, Vw, cen, nor in orden:
            _, _, _, C, A, E, B, DS = pz.obj.fin()
            Vc = cam.a_cam(Vw); cc = cam.a_cam(cen)
            mira = np.einsum("ij,ij->i", nor, cen - cam.pos)            # < 0 = la cara mira a la cámara
            vis = (mira < 0) | DS
            ndl = nor @ self.luz
            ndl = np.where(mira > 0, -ndl, ndl)                           # caras de doble lado: normal hacia la cámara
            lum = self.amb[None, :] + self.dif[None, :] * np.clip(ndl, 0, 1)[:, None]
            col = np.clip(C * lum, 0, 255)
            if pz.tinte is not None: col = col * np.array(pz.tinte)
            zc = cc[:, 2]
            f = np.exp(-self.dens * np.clip(zc, 0, None))[:, None]
            lit = np.clip(E, 0, 1)[:, None]
            col = col * (1 - lit) + C * lit                               # lo emisivo no se oscurece
            col = col * f + self.niebla[None, :] * (1 - f) * (1 - 0.6 * lit)
            idx = np.where(vis & (zc > -2))[0]
            idx = idx[np.argsort(-(zc[idx]) + B[idx] * 1e3)] if len(idx) else idx
            idx = sorted(idx, key=lambda k: (B[k], -zc[k]))
            F = pz.obj.F
            for k in idx:
                p = Vc[list(F[k])]
                if (p[:, 2] < near).all(): continue
                if (p[:, 2] < near).any(): p = _recorta(p, near)
                if len(p) < 3: continue
                xs = (W / 2 + p[:, 0] / p[:, 2] * foc); ys = (H / 2 - p[:, 1] / p[:, 2] * foc)
                if xs.max() < -50 or xs.min() > W + 50 or ys.max() < -50 or ys.min() > H + 50: continue
                c = col[k]
                if gris: g = c.mean(); c = c * (1 - gris) + g * gris
                d.polygon(list(zip((xs * SS).tolist(), (ys * SS).tolist())), fill=(int(c[0]), int(c[1]), int(c[2]), int(A[k])))
                if E[k] > 0.05:
                    e = min(1.6, E[k]) * float(f[k, 0]) * (A[k] / 255 if A[k] < 255 else 1)
                    gc = C[k] * e * (1 - gris * 0.7)
                    gd.polygon(list(zip((xs / 3).tolist(), (ys / 3).tolist())), fill=(int(min(255, gc[0])), int(min(255, gc[1])), int(min(255, gc[2]))))
        for pos, c, radio, fz in self.puntos:
            x, y, z = cam.pantalla(pos)
            if z < near: continue
            r = radio / z * foc / 3; ff = math.exp(-self.dens * z) * fz * (1 - gris * 0.7)
            if r < 0.3 or x < -200 or x > W + 200: continue
            gd.ellipse([x / 3 - r, y / 3 - r, x / 3 + r, y / 3 + r], fill=tuple(int(min(255, v * ff)) for v in c))
        out = img.resize((W, H), Image.LANCZOS if SS > 1 else Image.NEAREST)
        if self.bloom > 0:
            g1 = glow.filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BILINEAR)
            g2 = glow.filter(ImageFilter.GaussianBlur(16)).resize((W, H), Image.BILINEAR)
            a = np.asarray(out, np.float32) + (np.asarray(g1, np.float32) * 0.55 + np.asarray(g2, np.float32) * 0.9) * self.bloom
            out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        return out


def _recorta(p, near):
    """Recorta un polígono (en espacio de cámara) contra el plano z = near."""
    out = []
    for a, b in zip(p, np.roll(p, -1, axis=0)):
        ia, ib = a[2] >= near, b[2] >= near
        if ia: out.append(a)
        if ia != ib:
            u = (near - a[2]) / (b[2] - a[2]); out.append(a + (b - a) * u)
    return np.array(out) if out else np.zeros((0, 3))


def vineta(img, fuerza=0.55):
    """Oscurece las esquinas (acabado «de cine»)."""
    global _VIN
    try: _VIN
    except NameError:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        _VIN = np.clip((r - 0.45) / 0.75, 0, 1)[:, :, None]
    a = np.asarray(img, np.float32) * (1 - _VIN * fuerza)
    return Image.fromarray(a.astype(np.uint8))


# ------------------------------------------------------------------ ciudad lista para usar
def calle(semilla=7, largo=160, ancho=14.0, acera=4.5, edificios=True, farolas=True, arboles=True, paso_z=0.0, carriles=4):
    """Calle recta a lo largo de z (de -largo/2 a +largo/2) con aceras, líneas, paso de peatones en z = paso_z,
    edificios, farolas y árboles. Devuelve una Escena (añádele coches, semáforo y personajes)."""
    rng = random.Random(semilla); e = Escena()
    L = largo / 2; a2 = ancho / 2
    e.pon(suelo(-a2, a2, -L, L, (58, 58, 76), paso=7))
    for sx in (-1, 1):
        x0, x1 = sorted((sx * a2, sx * (a2 + acera)))
        e.pon(suelo(x0, x1, -L, L, (150, 142, 160), paso=6, y=0.16, col2=(140, 132, 152)), capa=1)
        bord = Obj(1); z = -L
        while z < L:                                         # bordillo (cara vertical entre calzada y acera)
            bord.cara([(sx * a2, 0, z), (sx * a2, 0, z + 8), (sx * a2, 0.17, z + 8), (sx * a2, 0.17, z)], (176, 170, 190), ds=True); z += 8
        e.pon(bord)
        e.pon(suelo(*sorted((sx * (a2 + acera), sx * (a2 + acera + 40))), -L, L, (74, 62, 96), paso=20, y=0.1), capa=0)
    for k in range(1, carriles):
        x = -a2 + ancho * k / carriles
        if k == carriles // 2 and carriles % 2 == 0:
            e.pon(franja(x, -L, x, paso_z - 6, 0.2, (250, 214, 90))); e.pon(franja(x, paso_z + 6, x, L, 0.2, (250, 214, 90)))
        else:
            o = Obj(1); z = -L
            while z < L:
                if abs(z + 1.5 - paso_z) > 6: o.une(franja(x, z, x, z + 3, 0.16, (230, 230, 236)))
                z += 8
            e.pon(o)
    o = Obj(1); n = int(ancho / 1.1)
    for k in range(n):
        x = -a2 + 0.45 + k * (ancho - 0.9) / (n - 1) if n > 1 else 0
        o.une(franja(x, paso_z - 2.0, x, paso_z + 2.0, 0.6, (236, 236, 242)))
    e.pon(o)
    for sz in (-1, 1): e.pon(franja(-a2, paso_z + sz * 3.4, a2, paso_z + sz * 3.4, 0.4, (236, 236, 242)))
    if edificios:
        tonos = [(126, 92, 150), (150, 100, 120), (96, 96, 150), (170, 120, 110), (110, 120, 160), (140, 110, 170)]
        for sx in (-1, 1):
            z = -L
            while z < L:
                w = rng.uniform(11, 20); h = rng.uniform(14, 46); dp = rng.uniform(12, 18)
                lados = ("right",) if sx < 0 else ("left",)
                o = edificio(dp, h, w - 0.8, rng.choice(tonos), rng, lados=lados + ("front", "back"))
                e.pon(o, pos=(sx * (a2 + acera + dp / 2 + 0.5), 0, z + w / 2))
                z += w
    if farolas:
        for z in range(int(-L) + 9, int(L), 22):
            for sx in (-1, 1):
                if abs(z - paso_z) < 4: continue
                e.pon(farola(), pos=(sx * (a2 + 0.9), 0.16, z), yaw=0 if sx < 0 else math.pi)
                e.halo((sx * (a2 + 0.9 - 1.4), 6.6, z), (255, 214, 140), 0.9, 0.55)
    if arboles:
        for z in range(int(-L) + 20, int(L), 22):
            for sx in (-1, 1):
                if abs(z - paso_z) < 6: continue
                e.pon(arbol(rng.uniform(4.2, 5.6), rng.choice([(60, 150, 120), (80, 160, 110), (50, 130, 130)])), pos=(sx * (a2 + 2.6), 0.16, z))
    return e



# ------------------------------------------------------------------ interior: dormitorio (v1.1, 14-nov-2026)
def reloj_arena(h=0.5, col=(255, 205, 50), emis=0.5):
    """Reloj de arena dorado (objeto-metáfora del vídeo «posponer»). Centrado en su mitad."""
    o = Obj(); r = h * 0.3
    o.une(cilindro(r, h / 2, (255, 236, 170), n=8, y0=-h / 2, r1=0.02, tapas=False, emis=emis))
    o.une(cilindro(0.02, h / 2, (255, 236, 170), n=8, y0=0, r1=r, tapas=False, emis=emis))
    for y in (-h / 2 - 0.04, h / 2): o.une(cilindro(r * 1.2, 0.04, col, n=8, y0=y, emis=emis))
    for f in o.F: pass
    o.DS = [True] * len(o.DS); o._fin = None
    return o

def telefono(on=1.0, col=(255, 150, 60)):
    """Teléfono tumbado (pantalla hacia arriba) de 8 x 16 cm."""
    o = caja(0.085, 0.012, 0.165, (24, 24, 32))
    o.cara([(-0.036, 0.0125, -0.075), (-0.036, 0.0125, 0.075), (0.036, 0.0125, 0.075), (0.036, 0.0125, -0.075)], col, emis=1.4 * on, bias=2, ds=True)
    return o

def cama(col_manta=(120, 78, 214), ocupada=True, gorro=(255, 205, 40), piel=(233, 178, 128)):
    """Cama individual con el cabecero en +z (origen = centro de la cama, en el suelo). ocupada = alguien durmiendo."""
    o = Obj(); mad = (120, 80, 58)
    o.une(caja(1.7, 0.3, 2.2, mad)); o.une(caja(1.6, 0.22, 2.1, (240, 238, 248), y0=0.3))
    o.une(caja(1.7, 1.15, 0.1, mad), pos=(0, 0, 1.08))
    o.une(caja(0.85, 0.14, 0.45, (255, 255, 255), y0=0.52), pos=(0, 0, 0.62))
    o.une(caja(1.64, 0.16, 1.45, col_manta, y0=0.5), pos=(0, 0, -0.3))
    o.une(caja(1.64, 0.05, 0.28, (255, 255, 255), y0=0.62), pos=(0, 0, 0.3))
    if ocupada:
        o.une(tcaja(0.62, 1.35, 0.4, 1.15, 0.2, col_manta, y0=0.66), pos=(0, 0, -0.3))
        o.une(esfera(0.2, piel, nu=10, nv=7), pos=(0, 0.8, 0.52))
        o.une(esfera(0.215, gorro, nu=10, nv=7), pos=(0, 0.82, 0.62))
        o.une(esfera(0.07, (255, 255, 255), nu=6, nv=4), pos=(0, 0.84, 0.86))
    return o

def mesilla(lampara=1.0, tel=1.0):
    """Mesilla con flexo y teléfono. lampara / tel = encendidos (0..1)."""
    o = caja(0.5, 0.55, 0.45, (140, 96, 70)); o.une(caja(0.4, 0.02, 0.02, (90, 60, 44)), pos=(0, 0.36, -0.235))
    o.une(cilindro(0.07, 0.03, (60, 60, 76), n=8), pos=(0.12, 0.55, 0.1)); o.une(cilindro(0.015, 0.26, (60, 60, 76), n=6), pos=(0.12, 0.58, 0.1))
    p = cilindro(0.16, 0.18, (255, 226, 160), n=8, r1=0.09, emis=1.2 * lampara); o.une(p, pos=(0.12, 0.82, 0.1))
    o.une(telefono(tel), pos=(-0.1, 0.55, -0.05), yaw=0.3)
    return o

def reloj_pared(hora=7.0, r=0.3, tarde=False):
    """Reloj redondo colgado en una pared que mira a -z. hora en decimales (9.5 = 9:30)."""
    o = Obj(1); n = 14; cara_c = (255, 220, 214) if tarde else (250, 250, 255)
    o.cara([(r * 1.12 * math.cos(k / n * 6.2832), r * 1.12 * math.sin(k / n * 6.2832), 0) for k in range(n)], (60, 50, 90), ds=True)
    o.cara([(r * math.cos(k / n * 6.2832), r * math.sin(k / n * 6.2832), -0.01) for k in range(n)], cara_c, emis=0.35, bias=1, ds=True)
    def aguja(ang, largo, ancho, col, b):
        dx, dy = -math.sin(ang), math.cos(ang); nx, ny = dy * ancho, -dx * ancho      # visto desde -z, +x queda a la izquierda
        o.cara([(-nx, -ny, -0.02), (nx, ny, -0.02), (nx + dx * largo, ny + dy * largo, -0.02), (-nx + dx * largo, -ny + dy * largo, -0.02)], col, bias=b, ds=True)
    aguja(-(hora % 12) / 12 * 6.2832, r * 0.5, r * 0.07, (40, 30, 60), 2)
    aguja(-(hora % 1) * 6.2832, r * 0.82, r * 0.045, (235, 60, 60) if tarde else (40, 30, 60), 3)
    return o

def dormitorio(dia=0.0, puerta=0.0, hora=6.0, tarde=False, luz=0.0, ocupada=True, lampara=1.0, manta=(120, 78, 214)):
    """Dormitorio de 6 x 6 m visto desde -z. dia 0 (noche) .. 0.5 (amanecer) .. 1 (pleno día): cambia el cielo de la
    ventana, la altura del sol y la luz de la habitación. puerta 0..1 = abierta (entra luz del pasillo). luz = lámpara del techo."""
    u = clamp(dia)
    def mez(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
    noche, alba, cielo_d = (34, 32, 86), (255, 150, 90), (140, 200, 255)
    cie = mez(noche, alba, u * 2) if u < 0.5 else mez(alba, cielo_d, u * 2 - 1)
    k = clamp(u * 0.9 + luz * 0.6 + puerta * 0.15)
    e = Escena(fondo=Image.new("RGB", (W, H), (16, 12, 34)), luz=(0.35, 0.8, -0.5), amb=mez((0.34, 0.31, 0.56), (0.62, 0.60, 0.66), k),
               dif=mez((0.28, 0.24, 0.34), (0.55, 0.50, 0.42), k), niebla=(24, 18, 50), dens=0.02 * (1 - k * 0.7), bloom=1.0)
    pared = (150, 128, 196); pared2 = (132, 110, 180)
    e.pon(suelo(-3, 3, -5, 3, (168, 128, 96), paso=1.0, col2=(158, 118, 88)))
    p = Obj(0)
    p.cara([(-3, 0, 3), (3, 0, 3), (3, 3.2, 3), (-3, 3.2, 3)], pared, ds=True)
    p.cara([(-3, 0, -5), (-3, 0, 3), (-3, 3.2, 3), (-3, 3.2, -5)], pared2, ds=True)
    p.cara([(3, 0, -5), (3, 0, 3), (3, 3.2, 3), (3, 3.2, -5)], pared2, ds=True)
    e.pon(p)
    d = Obj(1)                                                        # alfombra, ventana y puerta
    d.cara([(-0.2, 0.01, -1.6), (2.2, 0.01, -1.6), (2.2, 0.01, 0.4), (-0.2, 0.01, 0.4)], (0, 170, 150), ds=True)
    d.cara([(0.0, 0.012, -1.4), (2.0, 0.012, -1.4), (2.0, 0.012, 0.2), (0.0, 0.012, 0.2)], (0, 200, 170), bias=1, ds=True)
    vx0, vx1, vy0, vy1 = 1.05, 2.55, 1.0, 2.4
    d.cara([(vx0 - .08, vy0 - .08, 2.99), (vx1 + .08, vy0 - .08, 2.99), (vx1 + .08, vy1 + .08, 2.99), (vx0 - .08, vy1 + .08, 2.99)], (250, 250, 255), ds=True)
    d.cara([(vx0, vy0, 2.98), (vx1, vy0, 2.98), (vx1, vy1, 2.98), (vx0, vy1, 2.98)], cie, emis=0.6 - 0.25 * u, bias=1, ds=True)
    sy = vy0 - 0.3 + 1.5 * u; sx = 1.5 + 0.5 * u
    if vy0 + 0.16 < sy < vy1 - 0.16:
        d.cara([(sx + 0.15 * math.cos(a * 0.7854), sy + 0.15 * math.sin(a * 0.7854), 2.97) for a in range(8)], (255, 236, 150), emis=1.6, bias=2, ds=True)
    for q in ([(1.77, vy0, 2.96), (1.83, vy0, 2.96), (1.83, vy1, 2.96), (1.77, vy1, 2.96)], [(vx0, 1.67, 2.96), (vx1, 1.67, 2.96), (vx1, 1.73, 2.96), (vx0, 1.73, 2.96)]):
        d.cara(q, (250, 250, 255), bias=3, ds=True)
    pz0, pz1 = -1.3, -0.3                                              # puerta en la pared derecha
    d.cara([(2.99, 0, pz0 - .08), (2.99, 0, pz1 + .08), (2.99, 2.2, pz1 + .08), (2.99, 2.2, pz0 - .08)], (250, 250, 255), ds=True)
    if puerta > 0.02:
        d.cara([(2.98, 0, pz0), (2.98, 0, pz1), (2.98, 2.12, pz1), (2.98, 2.12, pz0)], (255, 236, 180), emis=1.2 * puerta, bias=1, ds=True)
        a = puerta * 1.25; hx, hz = 2.98 - math.sin(a) * 1.0, pz0 + math.cos(a) * 1.0
        d.cara([(2.98, 0, pz0), (hx, 0, hz), (hx, 2.12, hz), (2.98, 2.12, pz0)], (176, 124, 90), bias=2, ds=True)
    else:
        d.cara([(2.98, 0, pz0), (2.98, 0, pz1), (2.98, 2.12, pz1), (2.98, 2.12, pz0)], (176, 124, 90), bias=1, ds=True)
    e.pon(d)
    e.pon(reloj_pared(hora, tarde=tarde), pos=(-1.2, 2.45, 2.98))
    e.pon(cama(manta, ocupada), pos=(-1.2, 0, 1.85))
    e.pon(mesilla(lampara), pos=(0.1, 0, 2.65))
    if lampara > 0.05: e.halo((0.22, 0.95, 2.6), (255, 200, 120), 0.5, 0.5 * lampara * (1 - 0.6 * u))
    return e


# ------------------------------------------------------------------ interior: cocina (v1.2, 15-nov-2026)
def galleta(r=0.07, col=(214, 160, 90), chips=(70, 42, 30)):
    """Galleta con pepitas de chocolate, tumbada (origen = centro de la base)."""
    o = cilindro(r, 0.016, col, n=10)
    for k, (a, d) in enumerate(((0.3, 0.45), (2.0, 0.55), (3.6, 0.35), (4.9, 0.6), (1.2, 0.0))):
        x, z = math.cos(a) * r * d, math.sin(a) * r * d
        o.cara([(x - 0.009, 0.0165, z - 0.009), (x - 0.009, 0.0165, z + 0.009), (x + 0.009, 0.0165, z + 0.009), (x + 0.009, 0.0165, z - 0.009)], chips, bias=2, ds=True)
    return o

def bacteria(col=(110, 220, 90), r=0.05, enfado=False):
    """Bacteria simpática: bola verde con ojos (mira a -z, hacia la cámara). Origen = suelo."""
    o = esfera(r, col, nu=8, nv=6, cy=r)
    for sx in (-1, 1):
        x = sx * r * 0.36
        o.cara([(x - r * 0.18, r * 1.05, -r * 0.93), (x + r * 0.18, r * 1.05, -r * 0.93), (x + r * 0.18, r * 1.4, -r * 0.86), (x - r * 0.18, r * 1.4, -r * 0.86)], (255, 255, 255), bias=3, ds=True)
        o.cara([(x - r * 0.08, r * 1.1, -r * 0.95), (x + r * 0.08, r * 1.1, -r * 0.95), (x + r * 0.08, r * 1.28, -r * 0.92), (x - r * 0.08, r * 1.28, -r * 0.92)], (20, 20, 30), bias=4, ds=True)
        if enfado:
            o.cara([(x - r * 0.22, r * 1.5 + sx * r * 0.08, -r * 0.84), (x + r * 0.22, r * 1.5 - sx * r * 0.08, -r * 0.84), (x + r * 0.22, r * 1.58 - sx * r * 0.08, -r * 0.8), (x - r * 0.22, r * 1.58 + sx * r * 0.08, -r * 0.8)], (30, 60, 30), bias=4, ds=True)
    for k in range(5):                                   # pelitos
        a = k / 5 * 6.2832
        o.une(cilindro(0.006, r * 0.5, tuple(int(c * 0.8) for c in col), n=4), pos=(math.cos(a) * r * 0.5, r * 1.7, math.sin(a) * r * 0.5))
    return o

def cronometro(r=0.16, col=(255, 205, 50), emis=0.6):
    """Cronómetro dorado de bolsillo (objeto-metáfora del vídeo de la regla de los 5 segundos). Esfera mirando a -z."""
    o = cilindro(r, 0.06, col, n=14, eje="z", y0=-0.03, emis=emis)
    o.une(cilindro(r * 0.86, 0.01, (255, 250, 236), n=14, eje="z", y0=-0.045, emis=0.5))
    o.une(cilindro(0.035, 0.06, col, n=8, emis=emis), pos=(0, r, 0))
    o.une(cilindro(0.05, 0.02, col, n=8, emis=emis), pos=(0, r + 0.06, 0))
    o.DS = [True] * len(o.DS); o._fin = None
    return o

def cocina(dia=0.8, puerta=0.0, luz=1.0, suelo_col=((238, 232, 220), (60, 150, 160)), nevera=True):
    """Cocina de 6 x 6 m vista desde -z (misma planta que dormitorio()): suelo de baldosas a cuadros, encimera con
    muebles al fondo, ventana, nevera a la derecha, lámpara colgante y puerta en la pared derecha (puerta 0..1)."""
    u = clamp(dia)
    def mez(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
    k = clamp(0.4 + u * 0.5 + puerta * 0.1)
    e = Escena(fondo=Image.new("RGB", (W, H), (20, 16, 38)), luz=(0.4, 0.85, -0.45), amb=mez((0.42, 0.40, 0.58), (0.66, 0.64, 0.68), k),
               dif=mez((0.30, 0.26, 0.34), (0.52, 0.48, 0.40), k), niebla=(30, 24, 54), dens=0.012, bloom=1.0)
    pared = (238, 170, 120); pared2 = (226, 152, 104)
    e.pon(suelo(-3, 3, -5, 3, suelo_col[0], paso=0.5, col2=suelo_col[1]))
    p = Obj(0)
    p.cara([(-3, 0, 3), (3, 0, 3), (3, 3.2, 3), (-3, 3.2, 3)], pared, ds=True)
    p.cara([(-3, 0, -5), (-3, 0, 3), (-3, 3.2, 3), (-3, 3.2, -5)], pared2, ds=True)
    p.cara([(3, 0, -5), (3, 0, 3), (3, 3.2, 3), (3, 3.2, -5)], pared2, ds=True)
    e.pon(p)
    d = Obj(1)                                                           # azulejos detrás de la encimera, ventana y puerta
    d.cara([(-3, 0.9, 2.99), (1.4, 0.9, 2.99), (1.4, 1.5, 2.99), (-3, 1.5, 2.99)], (250, 246, 236), ds=True)
    for x in [-3 + 0.3 * i for i in range(15)]:
        d.cara([(x, 0.9, 2.985), (x + 0.012, 0.9, 2.985), (x + 0.012, 1.5, 2.985), (x, 1.5, 2.985)], (210, 200, 196), bias=1, ds=True)
    cie = mez((255, 170, 110), (150, 210, 255), u)
    vx0, vx1, vy0, vy1 = -2.3, -0.9, 1.65, 2.6
    d.cara([(vx0 - .08, vy0 - .08, 2.99), (vx1 + .08, vy0 - .08, 2.99), (vx1 + .08, vy1 + .08, 2.99), (vx0 - .08, vy1 + .08, 2.99)], (255, 255, 255), ds=True)
    d.cara([(vx0, vy0, 2.98), (vx1, vy0, 2.98), (vx1, vy1, 2.98), (vx0, vy1, 2.98)], cie, emis=0.45, bias=1, ds=True)
    d.cara([(-1.63, vy0, 2.97), (-1.57, vy0, 2.97), (-1.57, vy1, 2.97), (-1.63, vy1, 2.97)], (255, 255, 255), bias=2, ds=True)
    pz0, pz1 = -1.3, -0.3
    d.cara([(2.99, 0, pz0 - .08), (2.99, 0, pz1 + .08), (2.99, 2.2, pz1 + .08), (2.99, 2.2, pz0 - .08)], (255, 255, 255), ds=True)
    if puerta > 0.02:
        d.cara([(2.98, 0, pz0), (2.98, 0, pz1), (2.98, 2.12, pz1), (2.98, 2.12, pz0)], (255, 236, 180), emis=1.2 * puerta, bias=1, ds=True)
        a = puerta * 1.25; hx, hz = 2.98 - math.sin(a) * 1.0, pz0 + math.cos(a) * 1.0
        d.cara([(2.98, 0, pz0), (hx, 0, hz), (hx, 2.12, hz), (2.98, 2.12, pz0)], (120, 170, 160), bias=2, ds=True)
    else:
        d.cara([(2.98, 0, pz0), (2.98, 0, pz1), (2.98, 2.12, pz1), (2.98, 2.12, pz0)], (120, 170, 160), bias=1, ds=True)
    e.pon(d)
    mueble, tapa = (70, 150, 160), (246, 240, 230)                        # encimera con puertas y tiradores
    enc = caja(4.4, 0.86, 0.65, mueble, cols=dict(top=tapa)); enc.une(caja(4.5, 0.05, 0.7, tapa, y0=0.86))
    for i in range(6):
        x = -2.2 + 0.37 + i * 0.73
        enc.cara([(x - 0.3, 0.1, -0.33), (x + 0.3, 0.1, -0.33), (x + 0.3, 0.78, -0.33), (x - 0.3, 0.78, -0.33)], (84, 168, 178), bias=1, ds=True)
        enc.cara([(x + 0.2, 0.6, -0.34), (x + 0.24, 0.6, -0.34), (x + 0.24, 0.72, -0.34), (x + 0.2, 0.72, -0.34)], (220, 220, 230), bias=2, ds=True)
    e.pon(enc, pos=(-0.8, 0, 2.67))
    alto = caja(1.8, 0.75, 0.38, mueble); e.pon(alto, pos=(0.5, 1.95, 2.8))
    e.pon(caja(0.6, 0.02, 0.4, (40, 40, 50)), pos=(-0.2, 0.912, 2.66))                     # placa de cocina
    nev = caja(0.9, 2.0, 0.75, (236, 240, 246), cols=dict(top=(210, 214, 222)))
    nev.cara([(-0.43, 1.25, -0.38), (0.43, 1.25, -0.38), (0.43, 1.27, -0.38), (-0.43, 1.27, -0.38)], (170, 176, 190), bias=1, ds=True)
    for y0, y1 in ((0.5, 1.1), (1.4, 1.8)): nev.cara([(0.3, y0, -0.385), (0.34, y0, -0.385), (0.34, y1, -0.385), (0.3, y1, -0.385)], (150, 156, 170), bias=2, ds=True)
    if nevera: e.pon(nev, pos=(2.4, 0, 2.55))              # nevera=False para poner nevera_abierta() en su sitio
    e.pon(cilindro(0.01, 0.7, (40, 40, 50), n=4), pos=(-0.3, 2.5, 0.9))                       # lámpara colgante
    e.pon(cilindro(0.3, 0.25, (255, 214, 120), n=10, r1=0.08, emis=1.0 * luz), pos=(-0.3, 2.3, 0.9))
    if luz > 0.05: e.halo((-0.3, 2.3, 0.9), (255, 210, 130), 0.5, 0.45 * luz)
    return e


# ------------------------------------------------------------------ interior: salón (v1.3, 16-nov-2026)
def sofa(col=(214, 80, 90), ancho=2.2):
    """Sofá mirando a -z (hacia la cámara); origen = centro, en el suelo. Asiento a 0,45 m."""
    o = Obj(); osc = tuple(int(c * 0.82) for c in col)
    o.une(caja(ancho, 0.3, 0.9, osc, y0=0.08)); o.une(caja(ancho, 0.95, 0.25, col), pos=(0, 0.08, 0.4))
    for sx in (-1, 1): o.une(caja(0.22, 0.62, 0.95, col, y0=0.08), pos=(sx * (ancho / 2 + 0.1), 0, 0))
    n = 2
    for i in range(n): o.une(caja(ancho / n - 0.06, 0.12, 0.62, tuple(min(255, int(c * 1.1)) for c in col), y0=0.36), pos=(-ancho / 2 + ancho / n * (i + 0.5), 0, -0.1))
    return o

def planta(h=1.3):
    o = cilindro(0.2, 0.32, (200, 110, 70), n=8, r1=0.25)
    o.une(cilindro(0.03, h * 0.5, (70, 110, 60), n=5), pos=(0, 0.3, 0))
    for i, (dx, dz, r) in enumerate(((0, 0, 0.3), (0.18, 0.05, 0.22), (-0.16, -0.06, 0.24), (0.03, 0.12, 0.2))):
        o.une(esfera(r, (70 + 12 * i, 170 - 8 * i, 100), nu=7, nv=5), pos=(dx, h * 0.72 + 0.12 * i, dz))
    return o

def lampara_pie(on=1.0):
    o = cilindro(0.16, 0.04, (60, 60, 76), n=8); o.une(cilindro(0.02, 1.5, (60, 60, 76), n=6))
    o.une(cilindro(0.24, 0.3, (255, 226, 160), n=10, r1=0.14, emis=0.9 * on), pos=(0, 1.45, 0)); return o

def tarjeta(col=(60, 140, 240), icono=0):
    """Tarjeta de aplicación (30 x 42 cm, para que se vea): cara de color con un icono genérico blanco. Mira a -z."""
    o = caja(0.3, 0.42, 0.02, col)
    q = {0: [(-0.07, 0.14), (0.07, 0.14), (0.07, 0.28), (-0.07, 0.28)], 1: [(-0.08, 0.14), (0.08, 0.14), (0.0, 0.29)],
         2: [(0.08 * math.cos(a * 0.7854), 0.21 + 0.08 * math.sin(a * 0.7854)) for a in range(8)], 3: [(-0.09, 0.19), (0.09, 0.19), (0.09, 0.24), (-0.09, 0.24)]}[icono % 4]
    o.cara([(x, y, -0.011) for x, y in q], (255, 255, 255), emis=0.3, bias=2, ds=True)
    return o

def escoba(col=(255, 205, 50), emis=0.3):
    """Escoba dorada (objeto-metáfora de «limpiar» aplicaciones). Origen = punta de las cerdas."""
    o = tcaja(0.34, 0.08, 0.2, 0.06, 0.24, (240, 170, 30), emis and 0.0)
    o.une(cilindro(0.02, 1.0, col, n=6, emis=emis), pos=(0, 0.24, 0))
    o.E = [emis] * len(o.E); o.DS = [True] * len(o.DS); o._fin = None
    return o

def salon(dia=0.8, luz=1.0, tele=0.0, pared=(244, 214, 150)):
    """Salón de 6 x 6 m visto desde -z: sofá al fondo, cuadro, ventana, planta, lámpara de pie, alfombra y mesa baja."""
    u = clamp(dia)
    def mez(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
    k = clamp(0.35 + u * 0.55)
    e = Escena(fondo=Image.new("RGB", (W, H), (22, 16, 36)), luz=(0.4, 0.85, -0.45), amb=mez((0.40, 0.38, 0.56), (0.66, 0.64, 0.66), k),
               dif=mez((0.30, 0.26, 0.34), (0.50, 0.46, 0.40), k), niebla=(34, 26, 50), dens=0.012, bloom=1.0)
    pared2 = tuple(int(c * 0.9) for c in pared)
    e.pon(suelo(-3, 3, -5, 3, (176, 126, 90), paso=0.75, col2=(166, 116, 82)))
    p = Obj(0)
    p.cara([(-3, 0, 3), (3, 0, 3), (3, 3.2, 3), (-3, 3.2, 3)], pared, ds=True)
    p.cara([(-3, 0, -5), (-3, 0, 3), (-3, 3.2, 3), (-3, 3.2, -5)], pared2, ds=True)
    p.cara([(3, 0, -5), (3, 0, 3), (3, 3.2, 3), (3, 3.2, -5)], pared2, ds=True)
    e.pon(p)
    d = Obj(1)
    d.cara([(-1.6, 0.01, -1.4), (1.6, 0.01, -1.4), (1.6, 0.01, 1.3), (-1.6, 0.01, 1.3)], (70, 90, 170), ds=True)          # alfombra
    d.cara([(-1.4, 0.012, -1.2), (1.4, 0.012, -1.2), (1.4, 0.012, 1.1), (-1.4, 0.012, 1.1)], (90, 112, 196), bias=1, ds=True)
    cie = mez((255, 170, 110), (150, 210, 255), u)
    vx0, vx1, vy0, vy1 = 1.3, 2.6, 1.1, 2.5                                                                              # ventana (abierta: por ahí salen cosas)
    d.cara([(vx0 - .08, vy0 - .08, 2.99), (vx1 + .08, vy0 - .08, 2.99), (vx1 + .08, vy1 + .08, 2.99), (vx0 - .08, vy1 + .08, 2.99)], (255, 255, 255), ds=True)
    d.cara([(vx0, vy0, 2.98), (vx1, vy0, 2.98), (vx1, vy1, 2.98), (vx0, vy1, 2.98)], cie, emis=0.45, bias=1, ds=True)
    cx0, cx1, cy0, cy1 = -1.5, -0.3, 1.6, 2.4                                                                            # cuadro sobre el sofá
    d.cara([(cx0 - .06, cy0 - .06, 2.99), (cx1 + .06, cy0 - .06, 2.99), (cx1 + .06, cy1 + .06, 2.99), (cx0 - .06, cy1 + .06, 2.99)], (110, 76, 56), ds=True)
    d.cara([(cx0, cy0, 2.98), (cx1, cy0, 2.98), (cx1, cy1, 2.98), (cx0, cy1, 2.98)], (120, 200, 190), bias=1, ds=True)
    d.cara([(cx0, cy0, 2.97), (cx0 + 0.5, cy0 + 0.5, 2.97), (cx0 + 0.8, cy0 + 0.25, 2.97), (cx1, cy0 + 0.55, 2.97), (cx1, cy0, 2.97)], (90, 150, 110), bias=2, ds=True)
    d.cara([(cx1 - 0.3 + 0.1 * math.cos(a * 0.7854), cy1 - 0.2 + 0.1 * math.sin(a * 0.7854), 2.97) for a in range(8)], (255, 220, 120), bias=2, ds=True)
    e.pon(d)
    e.pon(sofa(), pos=(-0.6, 0, 2.3))
    e.pon(planta(), pos=(2.5, 0, 2.5)); e.pon(lampara_pie(luz), pos=(-2.5, 0, 2.5))
    if luz > 0.05: e.halo((-2.5, 1.6, 2.5), (255, 210, 130), 0.45, 0.4 * luz)
    e.pon(caja(1.0, 0.36, 0.55, (130, 90, 64), cols=dict(top=(150, 106, 76))), pos=(-0.6, 0, 0.9))                      # mesa baja
    return e


# ------------------------------------------------------------------ interior: oficina (v1.4, 16-nov-2026)
def escritorio(col=(214, 190, 150), pantalla=(120, 190, 255), on=1.0):
    """Mesa de oficina con monitor y teclado; quien se sienta lo hace en el lado -z, de espaldas a la cámara, y la pantalla mira hacia él."""
    o = caja(1.3, 0.05, 0.7, col, y0=0.72)
    for sx in (-1, 1):
        for sz in (-1, 1): o.une(caja(0.05, 0.72, 0.05, (90, 90, 104)), pos=(sx * 0.6, 0, sz * 0.3))
    o.une(caja(0.08, 0.2, 0.08, (50, 50, 62)), pos=(0, 0.77, 0.2)); o.une(caja(0.62, 0.38, 0.04, (40, 40, 52)), pos=(0, 0.95, 0.2))
    o.cara([(-0.28, 0.98, 0.178), (0.28, 0.98, 0.178), (0.28, 1.3, 0.178), (-0.28, 1.3, 0.178)], pantalla, emis=0.3 * on, bias=2, ds=True)
    o.une(caja(0.42, 0.02, 0.14, (60, 60, 74)), pos=(0, 0.77, -0.12))
    return o

def silla(col=(60, 70, 110)):
    o = caja(0.46, 0.07, 0.46, col, y0=0.42); o.une(caja(0.46, 0.5, 0.07, col), pos=(0, 0.5, 0.22))
    o.une(cilindro(0.03, 0.42, (70, 70, 84), n=6)); o.une(cilindro(0.26, 0.03, (70, 70, 84), n=8)); return o

def aire(on=1.0, frio=0.0):
    """Aparato de aire acondicionado de pared (mira a -z). on = piloto encendido; frio 0..1 = sale más aire (carámbanos)."""
    o = caja(1.1, 0.34, 0.26, (244, 246, 250), cols=dict(bottom=(200, 206, 216)))
    o.cara([(-0.48, 0.05, -0.132), (0.48, 0.05, -0.132), (0.48, 0.11, -0.132), (-0.48, 0.11, -0.132)], (70, 80, 100), bias=1, ds=True)
    o.cara([(0.36, 0.22, -0.132), (0.44, 0.22, -0.132), (0.44, 0.27, -0.132), (0.36, 0.27, -0.132)], (90, 220, 255), emis=1.6 * on, bias=2, ds=True)
    for i in range(int(7 * frio)):                               # carámbanos
        x = -0.45 + i * 0.15; h = 0.12 + 0.1 * ((i * 37) % 5) / 5
        c = cilindro(0.03, h, (190, 232, 255), n=5, r1=0.001, tapas=False, emis=0.3); c.V = [(a, -b, cc) for a, b, cc in c.V]; c.DS = [True] * len(c.DS); c._fin = None
        o.une(c, pos=(x, 0, -0.05))
    return o

def pinguino():
    """Pingüino low-poly de 60 cm mirando a -z (hacia la cámara). Origen = suelo."""
    o = Obj()
    o.une(esfera(0.2, (36, 40, 58), nu=8, nv=6, cy=0.26)); o.une(esfera(0.15, (36, 40, 58), nu=8, nv=6, cy=0.52))
    o.une(esfera(0.15, (250, 250, 255), nu=8, nv=6, cy=0.25), pos=(0, 0, -0.08))
    for sx in (-1, 1):
        o.cara([(sx * 0.045, 0.54, -0.145), (sx * 0.085, 0.54, -0.13), (sx * 0.085, 0.58, -0.125), (sx * 0.045, 0.58, -0.14)], (255, 255, 255), bias=3, ds=True)
        o.une(caja(0.05, 0.26, 0.12, (36, 40, 58)), pos=(sx * 0.21, 0.16, 0)); o.une(caja(0.12, 0.03, 0.16, (255, 160, 40)), pos=(sx * 0.09, 0, -0.06))
    pico = cilindro(0.04, 0.1, (255, 160, 40), n=5, r1=0.001, eje="z"); pico.V = [(a, b, -c) for a, b, c in pico.V]; pico.orienta((0, 0, -0.05))
    o.une(pico, pos=(0, 0.5, -0.13))
    return o

def copo(r=0.2, col=(255, 215, 80), emis=0.3):
    """Copo de nieve dorado (objeto-metáfora del vídeo del aire acondicionado). Plano, mirando a -z."""
    o = Obj()
    for k in range(3):
        a = k * math.pi / 3; dx, dy = math.cos(a) * r, math.sin(a) * r; nx, ny = -math.sin(a) * r * 0.09, math.cos(a) * r * 0.09
        o.cara([(-dx - nx, -dy - ny, 0), (dx - nx, dy - ny, 0), (dx + nx, dy + ny, 0), (-dx + nx, -dy + ny, 0)], col, emis=emis, ds=True)
        for sg in (-1, 1):
            cx, cy = sg * dx * 0.62, sg * dy * 0.62
            for b in (a + 1.0, a - 1.0):
                ex, ey = cx + sg * math.cos(b) * r * 0.3, cy + sg * math.sin(b) * r * 0.3
                o.cara([(cx - nx * .6, cy - ny * .6, 0), (ex - nx * .6, ey - ny * .6, 0), (ex + nx * .6, ey + ny * .6, 0), (cx + nx * .6, cy + ny * .6, 0)], col, emis=emis, ds=True)
    return o

def oficina(frio=0.0, dia=0.9, aire_on=1.0):
    """Oficina de 6 x 6 m vista desde -z: dos mesas con monitor y silla, aire acondicionado en la pared del fondo, ventana,
    planta y reloj. frio 0..1 congela el sitio: todo se tiñe de azul, salen carámbanos y escarcha en el suelo."""
    f = clamp(frio)
    def mez(a, b, k): return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
    hielo = lambda c: mez(c, (150, 200, 240), 0.55 * f)
    e = Escena(fondo=Image.new("RGB", (W, H), tuple(int(v) for v in mez((22, 18, 38), (14, 26, 50), f))), luz=(0.4, 0.85, -0.45),
               amb=mez((0.64, 0.62, 0.66), (0.50, 0.62, 0.82), f), dif=mez((0.48, 0.44, 0.40), (0.36, 0.44, 0.56), f),
               niebla=mez((34, 30, 54), (150, 200, 240), f), dens=0.012 + 0.03 * f, bloom=1.0)
    pared, pared2 = hielo((196, 214, 232)), hielo((178, 198, 220))
    e.pon(suelo(-3, 3, -5, 3, hielo((92, 104, 140)), paso=0.75, col2=hielo((84, 96, 130))))
    p = Obj(0)
    p.cara([(-3, 0, 3), (3, 0, 3), (3, 3.2, 3), (-3, 3.2, 3)], pared, ds=True)
    p.cara([(-3, 0, -5), (-3, 0, 3), (-3, 3.2, 3), (-3, 3.2, -5)], pared2, ds=True)
    p.cara([(3, 0, -5), (3, 0, 3), (3, 3.2, 3), (3, 3.2, -5)], pared2, ds=True)
    e.pon(p)
    d = Obj(1)
    cie = mez((150, 210, 255), (225, 240, 255), f)
    vx0, vx1, vy0, vy1 = -2.6, -1.2, 1.1, 2.4
    d.cara([(vx0 - .08, vy0 - .08, 2.99), (vx1 + .08, vy0 - .08, 2.99), (vx1 + .08, vy1 + .08, 2.99), (vx0 - .08, vy1 + .08, 2.99)], (255, 255, 255), ds=True)
    d.cara([(vx0, vy0, 2.98), (vx1, vy0, 2.98), (vx1, vy1, 2.98), (vx0, vy1, 2.98)], cie, emis=0.4, bias=1, ds=True)
    d.cara([(-1.93, vy0, 2.97), (-1.87, vy0, 2.97), (-1.87, vy1, 2.97), (-1.93, vy1, 2.97)], (255, 255, 255), bias=2, ds=True)
    if f > 0.3:                                                   # escarcha en el suelo
        rr = random.Random(6)
        for i in range(int(14 * f)):
            x, z, r = rr.uniform(-2.6, 2.6), rr.uniform(-2.5, 2.4), rr.uniform(0.25, 0.6)
            d.cara([(x + r * math.cos(a * 0.7854), 0.012, z + r * 0.6 * math.sin(a * 0.7854)) for a in range(8)], (225, 242, 255), alfa=150, ds=True)
    e.pon(d)
    e.pon(aire(aire_on, f), pos=(0.6, 2.45, 2.86))
    e.pon(reloj_pared(10.2), pos=(2.2, 2.4, 2.98))
    for x in (-1.3, 0.9):
        e.pon(escritorio(hielo((214, 190, 150))), pos=(x, 0, 1.3)); e.pon(silla(hielo((60, 70, 110))), pos=(x, 0, 0.55), yaw=0)
    e.pon(planta(), pos=(2.55, 0, 2.45))
    return e


# ------------------------------------------------------------------ interior: vagón de metro (v1.5, 17-nov-2026)
def microfono(col=(255, 205, 50), emis=0.3):
    """Micrófono dorado (objeto-metáfora del vídeo de los audios). Origen = base del mango."""
    o = cilindro(0.035, 0.22, col, n=8, r1=0.045, emis=emis)
    o.une(esfera(0.085, col, nu=8, nv=6, emis=emis), pos=(0, 0.29, 0))
    o.une(cilindro(0.088, 0.02, (200, 150, 20), n=8, emis=emis), pos=(0, 0.28, 0))
    o.DS = [True] * len(o.DS); o._fin = None
    return o

def burbuja_audio(col=(0, 170, 150), ancho=0.62):
    """Burbuja de mensaje de voz en 3D (triángulo de «reproducir» + onda). Mira a -z. Origen = centro."""
    o = caja(ancho, 0.2, 0.04, col, y0=-0.1)
    z = -0.022; x0 = -ancho / 2
    o.cara([(x0 + 0.05, -0.05, z), (x0 + 0.05, 0.05, z), (x0 + 0.13, 0.0, z)], (255, 255, 255), emis=0.3, bias=2, ds=True)
    for i in range(9):
        h = 0.02 + 0.05 * abs(math.sin(i * 1.9)); x = x0 + 0.18 + i * 0.045
        o.cara([(x, -h, z), (x + 0.02, -h, z), (x + 0.02, h, z), (x, h, z)], (220, 255, 248), emis=0.2, bias=2, ds=True)
    return o

def sitio_pasajero(i, a=1.4):
    """Posición (x, z) del pasajero i de metro() (para ponerle cosas encima)."""
    sx = -1 if i % 2 == 0 else 1
    return sx * (a - 0.42), -1.5 + 1.25 * (i // 2) * 2 + (0.6 if sx > 0 else 0)

PASAJEROS = [((230, 90, 90), (60, 40, 30)), ((0, 180, 150), (70, 46, 40)), ((250, 180, 60), (30, 30, 40)), ((90, 140, 230), (120, 80, 50)), ((200, 120, 200), (40, 30, 30)), ((120, 200, 120), (90, 60, 40))]

def metro(t=0.0, vel=14.0, pasajeros=6, largo=14.0):
    """Vagón de metro visto por dentro, a lo largo de z (de -largo/2 a +largo/2): bancos a los dos lados, barras amarillas,
    ventanas con las luces del túnel pasando (t y vel las mueven), luces en el techo y pasajeros sentados.
    Deja libre el pasillo central (x entre -0.6 y 0.6) para quien va de pie."""
    L = largo / 2; a = 1.4
    e = Escena(fondo=Image.new("RGB", (W, H), (10, 10, 22)), luz=(0.2, 0.9, -0.35), amb=(0.60, 0.60, 0.68), dif=(0.42, 0.40, 0.38),
               niebla=(26, 26, 44), dens=0.02, bloom=1.0)
    e.pon(suelo(-a, a, -L, L, (96, 100, 118), paso=1.0, col2=(88, 92, 110)))
    p = Obj(0)
    for sx in (-1, 1):
        p.cara([(sx * a, 0, -L), (sx * a, 0, L), (sx * a, 2.3, L), (sx * a, 2.3, -L)], (214, 220, 232), ds=True)
    p.cara([(-a, 0, L), (a, 0, L), (a, 2.3, L), (-a, 2.3, L)], (196, 202, 216), ds=True)
    p.cara([(-a, 2.3, -L), (a, 2.3, -L), (a, 2.3, L), (-a, 2.3, L)], (232, 236, 244), ds=True)
    e.pon(p)
    d = Obj(1)
    d.cara([(-0.06, 0.012, -L), (0.06, 0.012, -L), (0.06, 0.012, L), (-0.06, 0.012, L)], (250, 200, 40), ds=True)
    d.cara([(-0.45, 0, L - .01), (0.45, 0, L - .01), (0.45, 2.0, L - .01), (-0.45, 2.0, L - .01)], (150, 158, 176), ds=True)      # puerta del fondo
    d.cara([(-0.3, 1.1, L - .02), (0.3, 1.1, L - .02), (0.3, 1.8, L - .02), (-0.3, 1.8, L - .02)], (20, 22, 40), bias=1, ds=True)
    for sx in (-1, 1):
        x = sx * (a - 0.01)
        z = -L + 0.5
        while z < L - 1.6:                                           # ventanas
            d.cara([(x, 1.0, z), (x, 1.0, z + 1.5), (x, 1.85, z + 1.5), (x, 1.85, z)], (16, 18, 36), ds=True)
            z += 2.0
        for k in range(8):                                           # luces del túnel que pasan por detrás de los cristales
            zz = ((k * 3.7 + t * vel + (1.3 if sx > 0 else 0)) % (2 * L)) - L
            if any(-L + 0.5 + 2.0 * i <= zz <= -L + 0.5 + 2.0 * i + 1.2 for i in range(int(largo / 2))):
                d.cara([(sx * (a - 0.02), 1.3, zz), (sx * (a - 0.02), 1.3, zz + 0.3), (sx * (a - 0.02), 1.5, zz + 0.3), (sx * (a - 0.02), 1.5, zz)], (255, 220, 150), emis=0.45, bias=1, ds=True)
    for z in [-L + 1.0 + 2.0 * i for i in range(int(largo / 2))]:    # luces del techo
        d.cara([(-0.25, 2.29, z), (0.25, 2.29, z), (0.25, 2.29, z + 1.0), (-0.25, 2.29, z + 1.0)], (226, 228, 236), emis=0.2, ds=True)
    e.pon(d)
    banco = (60, 110, 200)
    for sx in (-1, 1):
        for j in range(int(largo - 1)):                              # banco en tramos de 1 m (se ordena bien con los pasajeros)
            zc = -L + 1.0 + j
            e.pon(caja(0.5, 0.45, 1.0, banco, cols=dict(top=(80, 130, 220))), pos=(sx * (a - 0.25), 0, zc), orden=None)
            e.pon(caja(0.08, 0.5, 1.0, (70, 120, 210)), pos=(sx * (a - 0.04), 0.45, zc))
    z = -L + 1.5
    while z < L - 0.5:
        for sx in (-1, 1): e.pon(cilindro(0.025, 2.3, (250, 200, 40), n=6), pos=(sx * 0.85, 0, z))
        z += 2.5
    rng = random.Random(12)
    for i in range(pasajeros):
        sx = -1 if i % 2 == 0 else 1; z = -1.5 + 1.25 * (i // 2) * 2 + (0.6 if sx > 0 else 0)
        sud, pelo = PASAJEROS[i % len(PASAJEROS)]
        e.pon(persona(sentado=True, sudadera=sud, gorro=pelo, pompon=False, pant=(50, 54, 70), brazo=0.4, brazo2=0.4), pos=(sx * (a - 0.42), 0, z), yaw=-sx * math.pi / 2)
    return e


# ------------------------------------------------------------------ interior: supermercado con fila (v1.6, 17-nov-2026)
def carrito(col=(200, 206, 220)):
    """Carrito de la compra mirando a +z. Origen = suelo."""
    o = Obj()
    o.une(tcaja(0.5, 0.75, 0.56, 0.85, 0.4, col, y0=0.5))
    o.une(caja(0.5, 0.04, 0.04, (220, 60, 70)), pos=(0, 1.0, -0.47))
    for sx in (-1, 1):
        o.une(caja(0.03, 0.5, 0.03, (150, 156, 170)), pos=(sx * 0.22, 0.0, -0.3))
        o.une(caja(0.03, 0.5, 0.03, (150, 156, 170)), pos=(sx * 0.22, 0.0, 0.3))
        for sz in (-0.3, 0.3): o.une(cilindro(0.06, 0.04, (40, 40, 50), n=6, eje="x"), pos=(sx * 0.22 - 0.02, 0.06, sz))
    return o

def estanteria(largo=6.0, col=(214, 218, 230), semilla=1):
    """Estantería de supermercado a lo largo de z, con productos de colores. La cara llena mira a +x."""
    o = caja(0.5, 2.0, largo, col); rng = random.Random(semilla)
    for b in range(4):
        y = 0.25 + b * 0.45
        o.une(caja(0.55, 0.03, largo, (170, 176, 190)), pos=(0.03, y, 0))
        z = -largo / 2 + 0.1
        while z < largo / 2 - 0.25:
            w = rng.uniform(0.12, 0.3); h = rng.uniform(0.18, 0.36)
            c = rng.choice([(230, 70, 70), (250, 190, 40), (60, 150, 230), (70, 190, 120), (240, 130, 60), (160, 100, 220), (245, 245, 245)])
            o.une(caja(0.16, h, w, c), pos=(0.2, y + 0.03, z + w / 2)); z += w + 0.03
    return o

FILA_X, FILA_Z0, FILA_PASO = 0.0, 4.3, 0.95
def fila_pos(i):
    """Posición del puesto i de la fila (0 = el que está pagando)."""
    return (FILA_X, 0, FILA_Z0 - i * FILA_PASO)

ROPAS = [((230, 90, 90), (60, 40, 30)), ((0, 180, 150), (70, 46, 40)), ((250, 180, 60), (30, 30, 40)), ((90, 140, 230), (120, 80, 50)),
         ((200, 120, 200), (40, 30, 30)), ((120, 200, 120), (90, 60, 40)), ((240, 150, 90), (50, 40, 40)), ((110, 110, 130), (150, 110, 70))]

def cliente(i, yaw=0.0, brazo=0.0, brazo2=0.0):
    sud, pelo = ROPAS[i % len(ROPAS)]
    return persona(sudadera=sud, gorro=pelo, pompon=False, pant=(50, 54, 70), brazo=brazo, brazo2=brazo2)

def supermercado(fila=8, giran=0.0, sin=()):
    """Supermercado visto desde -z: caja al fondo (z ≈ 5,5) con cajera, cinta y pantalla, estanterías a los lados,
    luces en el techo y una fila de `fila` clientes mirando a la caja (puestos fila_pos(i); `sin` = puestos vacíos).
    giran 0..1 = todos se giran a mirar hacia atrás (a quien se cuela)."""
    e = Escena(fondo=Image.new("RGB", (W, H), (230, 232, 240)), luz=(0.3, 0.9, -0.3), amb=(0.70, 0.70, 0.74), dif=(0.40, 0.38, 0.36),
               niebla=(220, 224, 236), dens=0.02, bloom=0.8)
    e.pon(suelo(-4, 4, -10, 8, (232, 234, 240), paso=0.6, col2=(214, 218, 228)))
    p = Obj(0)
    p.cara([(-4, 0, 8), (4, 0, 8), (4, 3.4, 8), (-4, 3.4, 8)], (240, 236, 226), ds=True)
    for sx in (-1, 1): p.cara([(sx * 4, 0, -10), (sx * 4, 0, 8), (sx * 4, 3.4, 8), (sx * 4, 3.4, -10)], (226, 230, 238), ds=True)
    p.cara([(-4, 3.4, -10), (4, 3.4, -10), (4, 3.4, 8), (-4, 3.4, 8)], (246, 246, 250), ds=True)
    e.pon(p)
    d = Obj(1)
    for z in range(-8, 8, 2):
        d.cara([(-0.6, 3.39, z), (0.6, 3.39, z), (0.6, 3.39, z + 0.8), (-0.6, 3.39, z + 0.8)], (255, 255, 250), emis=0.25, ds=True)
    d.cara([(-3.9, 2.4, 7.99), (-1.5, 2.4, 7.99), (-1.5, 3.0, 7.99), (-3.9, 3.0, 7.99)], (220, 60, 70), ds=True)              # cartel rojo
    d.cara([(1.5, 2.4, 7.99), (3.9, 2.4, 7.99), (3.9, 3.0, 7.99), (1.5, 3.0, 7.99)], (60, 150, 230), ds=True)
    e.pon(d)
    for sx in (-1, 1):
        e.pon(estanteria(7.0, semilla=3 + sx), pos=(sx * 3.3, 0, -3.5), yaw=0 if sx < 0 else math.pi)
    caja_ = caja(0.8, 0.85, 2.4, (60, 70, 110), cols=dict(top=(40, 40, 50)))                                               # caja con cinta
    caja_.une(caja(0.5, 0.04, 2.2, (30, 30, 36)), pos=(-0.05, 0.86, 0))
    e.pon(caja_, pos=(1.05, 0, 5.4))
    e.pon(caja(0.08, 0.5, 0.4, (40, 40, 52)), pos=(1.5, 0.86, 5.9))
    e.pon(caja(0.04, 0.3, 0.36, (40, 40, 52)), pos=(1.38, 1.0, 5.9))
    e.pon(persona(sudadera=(220, 60, 70), gorro=(60, 40, 30), pompon=False, brazo=0.6, brazo2=0.6), pos=(1.95, 0, 5.7), yaw=-math.pi / 2)
    e.pon(cilindro(0.04, 1.0, (200, 160, 40), n=6), pos=(-0.55, 0, 3.5)); e.pon(cilindro(0.04, 1.0, (200, 160, 40), n=6), pos=(-0.55, 0, -4.5))
    e.pon(franja(-0.55, 3.5, -0.55, -4.5, 0.05, (220, 40, 60), y=0.95))                                                       # cordón de la fila
    for i in range(fila):
        if i in sin: continue
        x, y, z = fila_pos(i)
        e.pon(cliente(i, brazo=0.2, brazo2=0.2), pos=(x, y, z), yaw=giran * math.pi)
        if i % 3 == 1: e.pon(carrito(), pos=(x + 0.05, 0, z + 0.45), esc=0.75)
    return e

if __name__ == "__main__":      # prueba rápida: python3 tresd.py  → prueba_3d.png
    import time
    e = calle(); rng = random.Random(3)
    for k in range(10):
        e.pon(coche(rng.choice(PINTURAS), freno=1), pos=(rng.choice([-5.2, -1.75]), 0, 8 + k * 7.5), yaw=math.pi)
        e.pon(coche(rng.choice(PINTURAS)), pos=(rng.choice([1.75, 5.2]), 0, -8 - k * 7.5))
    e.pon(semaforo("rojo", "verde", 1.0), pos=(-7.6, 0.16, -3.0))
    e.pon(persona(brazo=1.0), pos=(-7.9, 0.16, -1.2), yaw=math.pi / 2)
    e.pon(corona(), pos=(-7.9, 2.35, -1.2))
    t0 = time.time(); im = vineta(e.render(Cam((-2.5, 3.2, -9), (-7.5, 1.4, -1.5), 46))); print("render", round(time.time() - t0, 2), "s")
    im.save("prueba_3d.png")
    vineta(e.render(Cam((4, 34, -40), (0, 0, 6), 50))).save("prueba_3d_b.png")


# ------------------------------------------------------------------ interior: rellano con ascensor (v1.8, 22-nov-2026)
# Ascensor de puertas centrales en la pared z = 0 de un rellano (z < 0); la cabina va detrás (0 < z < 1,7).
# El orden de pintado se fuerza con `orden` (pintor): fuera (cámara en el rellano) cabina → lo de dentro → puertas → pared;
# dentro (cámara en la cabina) rellano → puertas → cabina. Para meter cosas usa pon_cabina() y pon_rellano().
ASC_HUECO, ASC_ALTO, ASC_ANCHO, ASC_FONDO = 0.55, 2.15, 0.9, 1.7

def boton_oro(r=0.09, emis=0.6):
    """Botón dorado de «cerrar puertas» (▶|◀), objeto-metáfora del vídeo del ascensor. Mira a -z; origen = centro."""
    o = cilindro(r * 1.25, 0.03, (150, 150, 165), n=16, eje="z")
    o.une(cilindro(r, 0.05, (255, 205, 50), n=16, eje="z", emis=emis), pos=(0, 0, -0.05))
    for sg in (-1, 1):                                        # dos triángulos que se miran
        o.cara([(sg * r * 0.75, -r * 0.4, -0.056), (sg * r * 0.12, 0, -0.056), (sg * r * 0.75, r * 0.4, -0.056)][::sg], (40, 30, 10), bias=3, ds=True)
    return o

def panel_botones(n=8, cerrar=1.0):
    """Botonera de pared (mira a -z): pisos en dos columnas y abajo «abrir» (verde) y «cerrar» (dorado, emis = cerrar)."""
    o = caja(0.3, 0.75, 0.03, (190, 194, 204))
    for i in range(n):
        x, y = (-0.065 if i % 2 == 0 else 0.065), 0.66 - (i // 2) * 0.1
        o.une(cilindro(0.032, 0.02, (235, 235, 240), n=10, eje="z"), pos=(x, y, -0.03))
    o.une(cilindro(0.04, 0.02, (60, 200, 120), n=10, eje="z", emis=0.3), pos=(-0.07, 0.13, -0.03))
    o.une(cilindro(0.04, 0.02, (255, 205, 50), n=10, eje="z", emis=0.7 * cerrar), pos=(0.07, 0.13, -0.03))
    return o

def _cara_z(o, x0, x1, y0, y1, z, col, hacia=-1, **k):
    q = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    o.cara(q if hacia > 0 else q[::-1], col, **k)

def ascensor(abre=1.0, dentro=False, piso=3, flecha=0.0, luz=1.0):
    """Rellano de 6 m con un ascensor. abre 0..1 = puertas; dentro = cámara en la cabina; piso = número del indicador;
    flecha 1 = la flecha de «subiendo» encendida. Devuelve una Escena."""
    a = clamp(abre)
    e = Escena(fondo=Image.new("RGB", (W, H), (24, 20, 40)), luz=(0.35, 0.85, -0.5), amb=(0.62, 0.6, 0.66), dif=(0.5, 0.46, 0.42),
               niebla=(36, 30, 56), dens=0.02, bloom=1.0)
    fu = lambda o: 10.0 if not dentro else 120.0               # pared del rellano
    # rellano: suelo, paredes laterales, techo
    e.pon(suelo(-3, 3, -7, 0, (196, 186, 170), paso=0.8, col2=(176, 166, 152)), orden=200)
    r = Obj(0)
    for sx in (-1, 1): r.cara([(sx * 3, 0, -7), (sx * 3, 0, 0), (sx * 3, 3, 0), (sx * 3, 3, -7)], (226, 214, 196), ds=True)
    r.cara([(-3, 3, -7), (3, 3, -7), (3, 3, 0), (-3, 3, 0)], (236, 232, 226), ds=True)
    for z in (-1.5, -4.5): r.cara([(-0.5, 2.99, z - 0.5), (0.5, 2.99, z - 0.5), (0.5, 2.99, z + 0.5), (-0.5, 2.99, z + 0.5)], (255, 250, 230), emis=0.6 * luz, bias=1, ds=True)
    e.pon(r, orden=150)
    # pared del ascensor (mira a -z) con hueco, marco de acero, indicador de piso y botón de llamada
    h, H2 = ASC_HUECO, ASC_ALTO; pw = Obj(0); col = (214, 198, 176)
    _cara_z(pw, -3, -h, 0, 3, 0, col); _cara_z(pw, h, 3, 0, 3, 0, col); _cara_z(pw, -h, h, H2, 3, 0, col)
    acero = (170, 176, 188)
    _cara_z(pw, -h - 0.09, -h, 0, H2 + 0.09, -0.01, acero, bias=1); _cara_z(pw, h, h + 0.09, 0, H2 + 0.09, -0.01, acero, bias=1)
    _cara_z(pw, -h - 0.09, h + 0.09, H2, H2 + 0.09, -0.01, acero, bias=1)
    _cara_z(pw, -0.32, 0.32, 2.36, 2.62, -0.01, (20, 16, 30), bias=1)                         # indicador
    for k in range(3 if piso >= 10 else 2):
        pass
    _cara_z(pw, -0.06, 0.06, 2.42, 2.56, -0.02, (255, 120, 60), emis=1.2 * luz, bias=2)        # número (bloque luminoso)
    _cara_z(pw, 0.14, 0.24, 2.43, 2.55, -0.02, (90, 230, 140) if flecha else (60, 70, 80), emis=1.2 * flecha, bias=2)
    _cara_z(pw, h + 0.25, h + 0.4, 1.0, 1.3, -0.01, acero, bias=1)                             # botón de llamada
    _cara_z(pw, h + 0.29, h + 0.36, 1.12, 1.19, -0.02, (255, 214, 120), emis=0.8, bias=2)
    e.pon(pw, orden=fu(pw))
    # puertas (de doble cara)
    pu = Obj(0); pc = (196, 202, 214)
    for sx in (-1, 1):
        x0 = sx * (h * a); x1 = sx * (h + h * a)
        x0, x1 = (min(x0, x1), max(x0, x1))
        pu.cara([(x0, 0, 0.04), (x1, 0, 0.04), (x1, H2, 0.04), (x0, H2, 0.04)], pc, ds=True)
        xm = (x0 + x1) / 2
        pu.cara([(xm - 0.006, 0.05, 0.035), (xm + 0.006, 0.05, 0.035), (xm + 0.006, H2 - 0.05, 0.035), (xm - 0.006, H2 - 0.05, 0.035)], (226, 230, 238), bias=1, ds=True)
    e.pon(pu, orden=50)
    # cabina: suelo, fondo con espejo, laterales, techo luminoso, jambas interiores (miran a +z), barra y botonera
    cb = Obj(0); w2, F = ASC_ANCHO, ASC_FONDO; mad = (150, 104, 70)
    cb.cara([(-w2, 0.005, 0.06), (-w2, 0.005, F), (w2, 0.005, F), (w2, 0.005, 0.06)], (70, 66, 80), ds=True)
    cb.cara([(-w2, 0, F), (w2, 0, F), (w2, 2.4, F), (-w2, 2.4, F)], mad, ds=True)
    cb.cara([(-0.55, 0.9, F - 0.01), (0.55, 0.9, F - 0.01), (0.55, 2.1, F - 0.01), (-0.55, 2.1, F - 0.01)], (176, 196, 214), bias=1, ds=True)   # espejo
    for sx in (-1, 1): cb.cara([(sx * w2, 0, 0.06), (sx * w2, 0, F), (sx * w2, 2.4, F), (sx * w2, 2.4, 0.06)], (162, 114, 78), ds=True)
    cb.cara([(-w2, 2.4, 0.06), (w2, 2.4, 0.06), (w2, 2.4, F), (-w2, 2.4, F)], (230, 226, 220), ds=True)
    cb.cara([(-0.5, 2.39, 0.4), (0.5, 2.39, 0.4), (0.5, 2.39, 1.4), (-0.5, 2.39, 1.4)], (255, 248, 225), emis=0.7 * luz, bias=1, ds=True)
    _cara_z(cb, -w2, -h, 0, 2.4, 0.06, acero, hacia=1); _cara_z(cb, h, w2, 0, 2.4, 0.06, acero, hacia=1); _cara_z(cb, -h, h, H2, 2.4, 0.06, acero, hacia=1)
    cb.une(caja(1.5, 0.05, 0.05, (210, 214, 224)), pos=(0, 0.95, F - 0.08))
    pb = panel_botones(); cb.une(pb, pos=(w2 - 0.02, 0.85, 0.4), yaw=-math.pi / 2)
    e.pon(cb, orden=100 if not dentro else 20)
    e.dentro = dentro
    return e

def pon_cabina(e, obj, pos, yaw=0.0, esc=1.0):
    """Mete algo dentro de la cabina con el orden correcto según la cámara."""
    if getattr(e, "dentro", False): e.pon(obj, pos=pos, yaw=yaw, esc=esc)
    else: e.pon(obj, pos=pos, yaw=yaw, esc=esc, capa=0, orden=70)

def pon_rellano(e, obj, pos, yaw=0.0, esc=1.0):
    """Mete algo en el rellano con el orden correcto según la cámara."""
    if getattr(e, "dentro", False): e.pon(obj, pos=pos, yaw=yaw, esc=esc, capa=0, orden=90)
    else: e.pon(obj, pos=pos, yaw=yaw, esc=esc)


# ------------------------------------------------------------------ comedor y nevera (v1.9, 23-nov-2026)
def mesa_comedor(w=1.6, d=0.9, col=(176, 124, 84), mantel=(240, 236, 226)):
    """Mesa de comedor (tapa a 0,75 m) con mantel. Origen = centro, en el suelo."""
    o = caja(w, 0.05, d, col, y0=0.72)
    for sx in (-1, 1):
        for sz in (-1, 1): o.une(caja(0.07, 0.72, 0.07, tuple(int(c * 0.8) for c in col)), pos=(sx * (w / 2 - 0.08), 0, sz * (d / 2 - 0.08)))
    o.cara([(-w / 2 + 0.1, 0.772, -d / 2 + 0.05), (-w / 2 + 0.1, 0.772, d / 2 - 0.05), (w / 2 - 0.1, 0.772, d / 2 - 0.05), (w / 2 - 0.1, 0.772, -d / 2 + 0.05)], mantel, bias=1, ds=True)
    return o

def plato(lleno=1.0, comida=(230, 150, 60), r=0.13):
    """Plato hondo; lleno 0..1 = cuánta comida queda (0 = vacío)."""
    o = cilindro(r, 0.03, (250, 250, 252), n=12, r1=r * 1.25)
    if lleno > 0.02: o.une(cilindro(r * 0.95 * (0.5 + 0.5 * lleno), 0.012, comida, n=12), pos=(0, 0.024, 0))
    return o

def vaso(lleno=0.0, col=(250, 250, 250), r=0.04, h=0.12):
    o = cilindro(r, h, (200, 220, 240), n=10, r1=r * 1.15, alfa=110, tapas=False); o.DS = [True] * len(o.DS); o._fin = None
    if lleno > 0.01: o.une(cilindro(r * 0.95, h * lleno, col, n=10, r1=r * (0.95 + 0.15 * lleno)), pos=(0, 0.003, 0))
    return o

def brik(col=(60, 140, 230), h=0.25, w=0.09):
    """Envase de cartón (leche) con tejadillo. Origen = base."""
    o = caja(w, h, w, (248, 248, 250), cols=dict(front=col, back=col))
    o.une(tcaja(w, w, w, 0.01, 0.05, (236, 236, 240), y0=h))
    o.cara([(-w / 2, h * 0.35, -w / 2 - 0.002), (w / 2, h * 0.35, -w / 2 - 0.002), (w / 2, h * 0.7, -w / 2 - 0.002), (-w / 2, h * 0.7, -w / 2 - 0.002)], col, bias=1, ds=True)
    return o

def botella(col=(220, 60, 60), h=0.3, r=0.045, liquido=0.0):
    """Botella de refresco (PET) con etiqueta; liquido 0..1."""
    o = cilindro(r, h * 0.7, (180, 200, 190), n=10, alfa=150, tapas=False); o.DS = [True] * len(o.DS); o._fin = None
    o.une(cilindro(r, h * 0.25, (180, 200, 190), n=10, r1=r * 0.35, y0=h * 0.7, alfa=150, tapas=False))
    o.une(cilindro(r * 1.01, h * 0.18, col, n=10, tapas=False), pos=(0, h * 0.3, 0))
    o.une(cilindro(r * 0.4, 0.03, (240, 240, 245), n=8), pos=(0, h * 0.95, 0))
    if liquido > 0.01: o.une(cilindro(r * 0.92, h * 0.7 * liquido, (90, 50, 30), n=10), pos=(0, 0.004, 0))
    return o

def nevera_abierta(abre=1.0, col=(236, 240, 246), luz=1.0):
    """Nevera de 0,9 x 2,0 m mirando a -z con la puerta (bisagra a la derecha) abierta abre 0..1 (1 = 100°).
    Por dentro: hueco iluminado con tres baldas (y = 0,55 / 1,0 / 1,45) y balda en la puerta. Pon cosas con baldas_xy()."""
    o = Obj(); w, h, d = 0.9, 2.0, 0.75; t = 0.05
    for sx in (-1, 1): o.une(caja(t, h, d, col), pos=(sx * (w / 2 - t / 2), 0, 0))
    o.une(caja(w, t, d, col), pos=(0, h - t, 0)); o.une(caja(w, 0.12, d, col), pos=(0, 0, 0)); o.une(caja(w, h, t, col), pos=(0, 0, d / 2 - t / 2))
    o.cara([(-w / 2 + t, 0.12, d / 2 - t - 0.001), (w / 2 - t, 0.12, d / 2 - t - 0.001), (w / 2 - t, h - t, d / 2 - t - 0.001), (-w / 2 + t, h - t, d / 2 - t - 0.001)][::-1],
           (200, 222, 240), emis=0.12 * luz)
    for y in (0.55, 1.0, 1.45):
        o.une(caja(w - 2 * t, 0.02, d - t - 0.02, (210, 230, 245)), pos=(0, y, -0.01))
    a = clamp(abre) * math.radians(100); hx, hz = w / 2, -d / 2
    pu = caja(w, h - 0.02, 0.07, col); pu.une(caja(w - 0.12, 0.03, 0.12, (210, 230, 245)), pos=(0, 0.6, 0.09)); pu.une(caja(w - 0.12, 0.03, 0.12, (210, 230, 245)), pos=(0, 1.2, 0.09))
    pu.une(caja(0.04, 0.5, 0.04, (170, 176, 190)), pos=(-w / 2 + 0.08, 0.8, -0.05))
    V = np.array(pu.V); V[:, 0] -= w / 2                         # bisagra en x = +w/2 (lado derecho visto desde -z)
    c, s = math.cos(a), math.sin(a); x2 = V[:, 0] * c - V[:, 2] * s; z2 = V[:, 0] * s + V[:, 2] * c
    pu.V = [tuple(p) for p in np.stack([x2 + hx, V[:, 1] + 0.01, z2 + hz - 0.035], 1)]; pu._fin = None
    o.une(pu)
    return o

def baldas_xy(i, fila):
    """Posición (x, y, z) relativa a la nevera para el objeto i (0..3) de la balda fila (0 abajo .. 2 arriba)."""
    return (-0.28 + 0.19 * i, (0.57, 1.02, 1.47)[fila], -0.08)
