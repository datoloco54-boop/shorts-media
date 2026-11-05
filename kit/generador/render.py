#!/usr/bin/env python3
"""Short: la bola de gomas más grande del mundo (1080x1920, 30 fps)."""
import json, math, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = sys.argv[1]
OUT = sys.argv[2]
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F = lambda s: ImageFont.truetype(FONT, s)

# ---------- guion: (texto subtítulo, archivo de voz) ----------
CAP = [
    "Esta bola pesa más que un elefante.",
    "Y no es de piedra ni de metal.",
    "Es solo de gomas elásticas.",
    "5.251 kilos.",
    "La hizo Claude\u00a0Moore, en Detroit, durante 11 años.",
    "De niño hacía bolitas de gomas en las visitas al médico.",
    "En 2015, sus compañeros le retaron a hacer una gigante.",
    "En agosto la pesaron delante de Guinness.",
    "Y batió el récord anterior por más de mil kilos.",
    "Pero ya hay una marca en Sudáfrica que quiere quitárselo en diciembre.",
    "¿Cuántas gomas crees que lleva?",
]
GAP = 0.22
LEAD = 0.25

def wav_dur(p):
    with wave.open(p) as w:
        return w.getnframes() / w.getframerate()

starts, ends, t = [], [], LEAD
for i in range(len(CAP)):
    d = wav_dur(f"{HERE}/l{i+1}.wav")
    starts.append(t); ends.append(t + d); t += d + GAP
TOTAL = t + 0.35
json.dump({"starts": starts, "ends": ends, "total": TOTAL}, open(f"{HERE}/tiempos.json", "w"))

# palabras con tiempos (reparto proporcional a las letras)
WORDS = []
for i, txt in enumerate(CAP):
    ws = txt.split(" ")
    lens = [max(2, len(w.strip(".,¿?"))) + 1.5 for w in ws]
    tot = sum(lens); s0, d = starts[i], ends[i] - starts[i]
    acc = 0
    for w, L in zip(ws, lens):
        WORDS.append((w, i, s0 + d * acc / tot, s0 + d * (acc + L) / tot))
        acc += L

def chunks_for_line(i):
    ws = [w for w in WORDS if w[1] == i]
    out, cur = [], []
    for w in ws:
        cur.append(w)
        if len(cur) >= 3 or w[0][-1] in ".,?" or sum(len(x[0]) + 1 for x in cur) > 15:
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out
CHUNKS = [c for i in range(len(CAP)) for c in chunks_for_line(i)]

# ---------- utilidades ----------
def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def pop(x):  # rebote al aparecer
    x = min(1, max(0, x)); return 1 + 0.25 * math.sin(x * math.pi) * (1 - x) if x < 1 else 1

def outline_text(d, xy, txt, font, fill, anchor="mm", stroke=10):
    d.text(xy, txt, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(15, 10, 30))

def tag(img, cx, cy, txt, size, bg, fg=(20, 15, 30), angle=0, scale=1.0):
    if scale <= 0.02: return
    f = F(int(size * scale))
    bb = f.getbbox(txt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = int(26 * scale)
    t = Image.new("RGBA", (tw + 2 * pad + 20, th + 2 * pad + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    d.rounded_rectangle((10, 10, 10 + tw + 2 * pad, 10 + th + 2 * pad), radius=int(16 * scale), fill=bg)
    d.text((10 + pad - bb[0], 10 + pad - bb[1]), txt, font=f, fill=fg)
    if angle: t = t.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(t, (int(cx - t.width / 2), int(cy - t.height / 2)))

# ---------- fondo (rayos + estrellas), una sola vez ----------
def make_bg():
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = W / 2, H * 0.55
    r = np.hypot(xx - cx, yy - cy) / H
    ang = np.arctan2(yy - cy, xx - cx)
    rays = (np.sin(ang * 14) > 0.55).astype(float) * 0.07
    base = np.stack([40 - 25 * r, 22 - 12 * r, 70 - 35 * r], -1)
    base += rays[..., None] * np.array([90, 60, 140])
    # nubes de color
    for (px, py, col) in [(0.15, 0.75, (120, 40, 60)), (0.85, 0.3, (40, 30, 120)), (0.7, 0.85, (90, 30, 110))]:
        g = np.exp(-(((xx / W - px) ** 2 + (yy / H - py) ** 2) / 0.03))
        base += g[..., None] * np.array(col) * 0.6
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    rnd = random.Random(3)
    for _ in range(140):
        x, y, s = rnd.randrange(W), rnd.randrange(H), rnd.choice([1, 1, 2, 3])
        d.ellipse((x, y, x + s, y + s), fill=(255, 255, 255, rnd.randrange(90, 220)))
    return img
BG = make_bg()

# ---------- la bola de gomas (imagen grande, se reescala) ----------
BAND_COLS = [(235, 70, 70), (250, 170, 40), (80, 190, 90), (60, 140, 235), (240, 120, 190),
             (250, 220, 70), (150, 90, 220), (40, 200, 200), (230, 100, 40)]
def make_ball(R=700, seed=1, n=520):
    S = 2 * R + 40
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    d.ellipse((c - R, c - R, c + R, c + R), fill=(150, 60, 60))
    rnd = random.Random(seed)
    for k in range(n):
        col = rnd.choice(BAND_COLS)
        shade = 0.75 + 0.35 * rnd.random()
        col = tuple(min(255, int(v * shade)) for v in col)
        # una goma = elipse inclinada que atraviesa la bola
        a = rnd.uniform(0, math.pi)
        rr = R * rnd.uniform(0.55, 1.0)
        off = rnd.uniform(-0.6, 0.6) * R
        band = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        e = rr * rnd.uniform(0.15, 0.5)
        bd.ellipse((c - rr, c - e + off * 0.3, c + rr, c + e + off * 0.3), outline=col + (255,), width=rnd.randint(10, 18))
        band = band.rotate(math.degrees(a), center=(c, c), resample=Image.BICUBIC)
        im.alpha_composite(band)
        if k % 60 == 59:  # recorta a la esfera cada cierto tiempo
            mask = Image.new("L", (S, S), 0)
            ImageDraw.Draw(mask).ellipse((c - R, c - R, c + R, c + R), fill=255)
            im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", (S, S), 0), mask))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((c - R, c - R, c + R, c + R), fill=255)
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", (S, S), 0), mask))
    # sombreado esférico
    yy, xx = np.mgrid[0:S, 0:S]
    dx, dy = (xx - c + R * 0.35) / R, (yy - c + R * 0.35) / R
    light = np.clip(1.15 - 0.55 * np.hypot(dx, dy), 0.35, 1.15)
    arr = np.array(im).astype(float)
    arr[..., :3] *= light[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
BALL = make_ball()
BALL2 = make_ball(seed=7, n=300)
_ball_cache = {}
def ball(size, which=0):
    size = max(8, int(size))
    k = (size, which)
    if k not in _ball_cache:
        _ball_cache[k] = (BALL if which == 0 else BALL2).resize((size, size), Image.LANCZOS)
        if len(_ball_cache) > 300: _ball_cache.pop(next(iter(_ball_cache)))
    return _ball_cache[k]
def put_ball(img, cx, cy, diam, which=0, rot=0):
    b = ball(diam, which)
    if rot: b = b.rotate(rot, resample=Image.BICUBIC)
    img.alpha_composite(b, (int(cx - b.width / 2), int(cy - b.height / 2)))

# ---------- piezas de dibujo ----------
INK = (25, 18, 40)
def elephant(d, x, y, s):  # (x,y) = pie del centro
    g = (150, 155, 170); g2 = (120, 125, 140)
    d.ellipse((x - 150 * s, y - 260 * s, x + 150 * s, y - 60 * s), fill=g)          # cuerpo
    for lx in (-110, -40, 40, 110):
        d.rounded_rectangle((x + (lx - 28) * s, y - 120 * s, x + (lx + 28) * s, y), radius=int(14 * s), fill=g2 if lx in (-40, 110) else g)
    d.ellipse((x - 250 * s, y - 300 * s, x - 90 * s, y - 150 * s), fill=g)           # cabeza
    d.ellipse((x - 215 * s, y - 330 * s, x - 95 * s, y - 180 * s), fill=g2)          # oreja
    d.line([(x - 240 * s, y - 210 * s), (x - 280 * s, y - 120 * s), (x - 250 * s, y - 60 * s)], fill=g, width=int(34 * s), joint="curve")
    d.ellipse((x - 215 * s, y - 255 * s, x - 199 * s, y - 239 * s), fill=INK)        # ojo
    d.line([(x + 150 * s, y - 200 * s), (x + 185 * s, y - 140 * s)], fill=g2, width=int(10 * s))

def stick(d, x, y, s, col=(25, 18, 40), arm=0, wave_=0):
    w = int(16 * s)
    d.ellipse((x - 34 * s, y - 300 * s, x + 34 * s, y - 232 * s), fill=col)
    d.line([(x, y - 232 * s), (x, y - 110 * s)], fill=col, width=w)
    d.line([(x, y - 110 * s), (x - 45 * s, y)], fill=col, width=w)
    d.line([(x, y - 110 * s), (x + 45 * s, y)], fill=col, width=w)
    d.line([(x, y - 200 * s), (x - 60 * s, y - 130 * s)], fill=col, width=w)
    ay = -130 - arm * 130 + wave_ * 25
    d.line([(x, y - 200 * s), (x + 60 * s, y + ay * s)], fill=col, width=w)
    return (x + 60 * s, y + ay * s)

def ground(img, y, col=(70, 140, 90), col2=(55, 115, 75)):
    d = ImageDraw.Draw(img)
    d.rectangle((0, y, W, y + 500), fill=col)
    d.rectangle((0, y, W, y + 14), fill=col2)

# ---------- panel de escena ----------
PANEL_Y0, PANEL_Y1 = 430, 1230
PH = PANEL_Y1 - PANEL_Y0

def sky(img, top=(130, 190, 240), bot=(225, 235, 245)):
    a = np.linspace(0, 1, PH)[:, None, None]
    arr = (np.array(top) * (1 - a) + np.array(bot) * a) * np.ones((1, W, 1))
    img.alpha_composite(Image.fromarray(arr.astype(np.uint8)).convert("RGBA"))

def scene(i, lt, gt):
    """i: frase, lt: segundos desde que empieza la frase, gt: tiempo global."""
    img = Image.new("RGBA", (W, PH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if i in (0, 10):
        sky(img); ground(img, 620)
        # balancín
        tilt = (0.9 if i == 10 else ease(lt / 1.2)) * 9
        cx, cy = W / 2, 600
        L = 380
        a = math.radians(tilt)
        p1 = (cx - L * math.cos(a), cy + L * math.sin(a))   # lado bola (baja)
        p2 = (cx + L * math.cos(a), cy - L * math.sin(a))   # lado elefante (sube)
        d.polygon([(cx, cy - 10), (cx - 60, 625), (cx + 60, 625)], fill=(110, 80, 60))
        d.line([p1, p2], fill=(140, 95, 60), width=30)
        drop = 0 if i == 10 else (1 - ease(lt / 0.6)) * -700
        put_ball(img, p1[0] + 40, p1[1] - 150 + drop, 300, rot=gt * 8)
        elephant(d, p2[0] - 40, p2[1] - 14, 0.62)
        tag(img, W / 2, 110, "5.251 KG", 70, (250, 210, 50), angle=-4, scale=pop(lt / 0.5) if i == 0 else 1)
    elif i == 1:
        sky(img, (90, 80, 140), (160, 140, 200))
        put_ball(img, W / 2, PH / 2 + 40, 430, rot=gt * 6)
        for k, (txt, x) in enumerate([("PIEDRA", 250), ("METAL", 830)]):
            s = pop((lt - 0.15 - k * 0.55) / 0.4)
            if lt > 0.15 + k * 0.55:
                tag(img, x, 170, txt, 60, (200, 200, 210), angle=(-6 if k == 0 else 6), scale=s)
                if lt > 0.45 + k * 0.55:
                    dd = ImageDraw.Draw(img)
                    dd.line([(x - 140, 110), (x + 140, 235)], fill=(230, 40, 40), width=22)
                    dd.line([(x - 140, 235), (x + 140, 110)], fill=(230, 40, 40), width=22)
    elif i == 2:
        sky(img, (60, 40, 90), (110, 60, 120))
        z = 1 + 1.4 * ease(lt / 1.6)
        put_ball(img, W / 2, PH / 2 + 30, 520 * z, rot=gt * 5)
        tag(img, W / 2, 110, "GOMAS ELÁSTICAS", 64, (250, 170, 40), angle=-3, scale=pop((lt - 0.4) / 0.4) if lt > 0.4 else 0)
    elif i == 3:
        sky(img, (40, 30, 70), (80, 50, 110))
        put_ball(img, 300, PH / 2 + 60, 420, rot=gt * 6)
        v = int(5251 * ease(lt / 1.5))
        num = f"{v:,}".replace(",", ".")
        dd = ImageDraw.Draw(img)
        outline_text(dd, (760, PH / 2 - 10), num, F(150), (250, 210, 50), stroke=12)
        outline_text(dd, (760, PH / 2 + 130), "KILOS", F(80), (255, 255, 255), stroke=10)
        # elefante pequeño de comparación
        outline_text(dd, (650, PH - 150), "≈", F(110), (255, 255, 255), stroke=8)
        elephant(dd, 860, PH - 70, 0.42)
    elif i == 4:
        sky(img, (250, 160, 110), (255, 220, 170))
        dd = ImageDraw.Draw(img)
        rnd = random.Random(5)
        x = 0
        while x < W:   # horizonte de ciudad
            bw = rnd.randint(70, 150); bh = rnd.randint(150, 420)
            dd.rectangle((x, 600 - bh, x + bw, 600), fill=(70, 55, 90))
            for wy in range(600 - bh + 25, 590, 50):
                for wx in range(x + 15, x + bw - 20, 35):
                    if rnd.random() < 0.5: dd.rectangle((wx, wy, wx + 14, wy + 20), fill=(250, 210, 120))
            x += bw + 8
        ground(img, 600, (80, 70, 100), (60, 50, 80))
        put_ball(img, W / 2, 520, 220 + 60 * ease(lt / 3), rot=gt * 6)
        tag(img, W / 2, 110, "DETROIT, EE. UU.", 62, (90, 200, 110), angle=-3, scale=pop(lt / 0.4))
        yr = 2015 + int(11 * ease(max(0, lt - 1.4) / 1.6))
        if lt > 1.2:
            tag(img, W / 2, 250, f"{yr}  ·  11 AÑOS" if yr == 2026 else str(yr), 54, (255, 255, 255), angle=2)
    elif i == 5:
        sky(img, (200, 225, 235), (235, 245, 245))
        dd = ImageDraw.Draw(img)
        dd.rectangle((0, 640, W, PH), fill=(190, 200, 210))
        # cruz de consulta
        dd.rounded_rectangle((760, 140, 940, 320), radius=20, fill=(255, 255, 255))
        dd.rectangle((825, 165, 875, 295), fill=(230, 60, 60)); dd.rectangle((785, 205, 915, 255), fill=(230, 60, 60))
        # silla y niño
        dd.rectangle((280, 520, 520, 545), fill=(120, 90, 70))
        dd.rectangle((290, 545, 310, 650), fill=(120, 90, 70)); dd.rectangle((490, 545, 510, 650), fill=(120, 90, 70))
        hand = stick(dd, 400, 650, 0.85, arm=0.35 + 0.05 * math.sin(gt * 5))
        put_ball(img, hand[0] + 30, hand[1] - 20, 40 + 50 * ease(lt / 2.5), rot=gt * 30)
        tag(img, 280, 140, "DE NIÑO", 62, (250, 210, 50), angle=-5, scale=pop(lt / 0.4))
    elif i == 6:
        sky(img, (170, 200, 230), (220, 230, 240))
        ground(img, 650, (150, 150, 165), (120, 120, 135))
        dd = ImageDraw.Draw(img)
        cols = [(25, 18, 40), (60, 40, 90), (40, 30, 70)]
        for k, x in enumerate([200, 380, 820]):
            stick(dd, x, 650, 0.85, col=cols[k], arm=(0.9 if k < 2 else 0.1), wave_=math.sin(gt * 8 + k))
        put_ball(img, 820 + 51, 650 - 0.85 * 130 - 20, 70, rot=gt * 20)
        if lt > 0.5:
            s = pop((lt - 0.5) / 0.4)
            tag(img, 330, 250, "¡HAZLA GIGANTE!", 56, (255, 255, 255), angle=-4, scale=s)
        tag(img, 820, 140, "2015", 70, (250, 170, 40), angle=5, scale=pop(lt / 0.4))
    elif i == 7:
        sky(img, (110, 180, 230), (210, 230, 245))
        ground(img, 640)
        dd = ImageDraw.Draw(img)
        dd.rounded_rectangle((200, 600, 880, 660), radius=10, fill=(90, 95, 110))      # báscula
        dd.rounded_rectangle((400, 670, 680, 760), radius=12, fill=(30, 30, 40))
        put_ball(img, W / 2, 370, 460, rot=gt * 4)
        v = 5251.69 * ease(lt / 1.4)
        dd.text((W / 2, 715), f"{v:,.2f} KG".replace(",", "X").replace(".", ",").replace("X", "."),
                font=F(50), fill=(120, 255, 140), anchor="mm")
        if lt > 1.0:
            tag(img, 830, 130, "RÉCORD MUNDIAL", 46, (250, 210, 50), angle=8, scale=pop((lt - 1.0) / 0.4))
    elif i == 8:
        sky(img, (40, 30, 70), (70, 45, 100))
        dd = ImageDraw.Draw(img)
        base = 690; maxh = 520
        for k, (lab, kg, col) in enumerate([("2008", 4097, (160, 160, 180)), ("2026", 5252, (250, 170, 40))]):
            x0 = 230 + k * 380
            g = ease((lt - k * 0.5) / 1.0)
            h = maxh * kg / 5252 * g
            dd.rounded_rectangle((x0, base - h, x0 + 240, base), radius=18, fill=col)
            outline_text(dd, (x0 + 120, base + 60), lab, F(60), (255, 255, 255), stroke=8)
            if g > 0.3:
                outline_text(dd, (x0 + 120, base - h - 50), f"{int(kg * g):,} KG".replace(",", "."), F(50), (255, 255, 255), stroke=8)
        if lt > 1.6:
            tag(img, W / 2, 80, "+1.155 KG", 66, (90, 200, 110), angle=-4, scale=pop((lt - 1.6) / 0.4))
    elif i == 9:
        sky(img, (250, 150, 80), (250, 210, 140))
        ground(img, 640, (200, 150, 80), (170, 125, 60))
        put_ball(img, 320, 470, 380, rot=gt * 5)
        g = ease(lt / 3.0)
        put_ball(img, 790, 640 - (120 + 260 * g) / 2, 120 + 260 * g, which=1, rot=-gt * 7)
        dd = ImageDraw.Draw(img)
        outline_text(dd, (790, 640 - 300 * g - 150), "?", F(140), (255, 255, 255), stroke=10)
        tag(img, W / 2, 100, "SUDÁFRICA · DICIEMBRE", 52, (250, 210, 50), angle=-3, scale=pop((lt - 0.8) / 0.4) if lt > 0.8 else 0)
    # bordes difuminados del panel
    m = np.ones((PH, W), float)
    fade = 90
    ramp = np.linspace(0, 1, fade)
    m[:fade] *= ramp[:, None]; m[-fade:] *= ramp[::-1][:, None]
    a = np.array(img.getchannel("A")).astype(float) * m
    img.putalpha(Image.fromarray(a.astype(np.uint8)))
    return img

# ---------- título y subtítulos ----------
TITLE = [("¿UNA BOLA MÁS", (255, 255, 255)), ("PESADA QUE UN", (255, 255, 255)), ("ELEFANTE?", (250, 210, 50))]
def draw_title(img):
    d = ImageDraw.Draw(img)
    f = F(86)
    for k, (txt, col) in enumerate(TITLE):
        outline_text(d, (W / 2, 200 + k * 92), txt, f, col, stroke=11)

HL = [(250, 210, 50), (250, 150, 40), (90, 205, 110), (250, 210, 50)]
def draw_caption(img, gt):
    cur = None
    for c in CHUNKS:
        if c[0][2] - 0.05 <= gt <= c[-1][3] + 0.15: cur = c
    if cur is None: return
    d = ImageDraw.Draw(img)
    f = F(88)
    words = [w[0].upper().replace("\u00a0", " ") for w in cur]
    space = 28
    widths = [d.textlength(w, font=f) for w in words]
    total = sum(widths) + space * (len(words) - 1)
    lines = [list(range(len(words)))]
    if total > W - 120:
        best = None
        for k in range(1, len(words)):
            l1 = sum(widths[:k]) + space * (k - 1); l2 = sum(widths[k:]) + space * (len(words) - k - 1)
            if best is None or max(l1, l2) < best[0]: best = (max(l1, l2), k)
        k = best[1]; lines = [list(range(k)), list(range(k, len(words)))]
    y0 = 1420 - (len(lines) - 1) * 55
    appear = ease((gt - cur[0][2] + 0.05) / 0.15)
    for li, idxs in enumerate(lines):
        lw = sum(widths[j] for j in idxs) + space * (len(idxs) - 1)
        x = W / 2 - lw / 2
        y = y0 + li * 112
        for j in idxs:
            w = cur[j]
            active = (w[2] <= gt < w[3]) or (w is cur[-1] and gt >= w[3])
            col = (255, 255, 255)
            if active:
                hc = HL[w[1] % len(HL)]
                d.rounded_rectangle((x - 14, y - 58, x + widths[j] + 14, y + 52), radius=16, fill=hc,
                                    outline=(15, 10, 30), width=6)
                col = (20, 15, 30)
                d.text((x, y), words[j], font=f, fill=col, anchor="lm")
            else:
                d.text((x, y + (1 - appear) * 20), words[j], font=f, fill=col, anchor="lm", stroke_width=10, stroke_fill=(15, 10, 30))
            x += widths[j] + space

# ---------- render ----------
def frame(n):
    gt = n / FPS
    i = 0
    for k in range(len(CAP)):
        if gt >= starts[k] - (GAP if k else 99): i = k
    lt = gt - starts[i]
    img = BG.copy()
    sc = scene(i, max(0, lt), gt)
    # pequeña transición: escala al entrar
    if 0 <= lt < 0.18 and i not in (0,):
        s = 0.94 + 0.06 * ease(lt / 0.18)
        sc = sc.resize((int(W * s), int(PH * s)), Image.BICUBIC)
        img.alpha_composite(sc, ((W - sc.width) // 2, PANEL_Y0 + (PH - sc.height) // 2))
    else:
        img.alpha_composite(sc, (0, PANEL_Y0))
    draw_title(img)
    draw_caption(img, gt)
    return img.convert("RGB")

if __name__ == "__main__":
    N = int(TOTAL * FPS)
    if len(sys.argv) > 3:   # modo prueba: guardar fotogramas sueltos
        for s in sys.argv[3].split(","):
            frame(int(float(s) * FPS)).save(f"{HERE}/prev_{s}.png")
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                          "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
    for n in range(N):
        p.stdin.write(frame(n).tobytes())
    p.stdin.close(); p.wait()
    print("frames", N, "dur", TOTAL)
