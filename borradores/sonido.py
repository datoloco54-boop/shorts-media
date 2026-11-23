# sonido.py — efectos y música del kit de Manuales Irónicos (v1.0). Todo sintetizado con numpy: nada descargado.
#   fx(nombre) → array float32 a SR.   Nombres: pop, clic, whoosh, ding, golpe, tic, error, tada, sube, freno, congela, alarma, claxon, claxon_largo
#   musica(dur) → base suave tipo «anuncio» (va MUY baja: la voz manda y las pausas tras cada remate se notan).
import numpy as np
SR = 24000

def _t(d): return np.arange(int(SR * d)) / SR
def _env(n, a=0.005, r=0.1):
    e = np.ones(n); na, nr = max(1, int(SR * a)), max(1, int(SR * r))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e

def fx(nombre):
    rng = np.random.default_rng(abs(hash(nombre)) % 2 ** 31)
    if nombre == "pop":
        t = _t(0.12); return (np.sin(2 * np.pi * (520 + 900 * np.exp(-t * 40)) * t) * np.exp(-t * 34)).astype(np.float32)
    if nombre == "clic":                       # botón mecánico
        t = _t(0.07); x = rng.standard_normal(len(t)) * np.exp(-t * 160) * 0.7 + np.sin(2 * np.pi * 180 * t) * np.exp(-t * 60)
        return x.astype(np.float32)
    if nombre == "whoosh":
        t = _t(0.34); x = rng.standard_normal(len(t)); k = np.exp(-np.linspace(-2, 2, 400) ** 2); x = np.convolve(x, k / k.sum(), "same")
        x = np.diff(x, prepend=0) * 14
        return (x * np.sin(np.linspace(0, np.pi, len(t))) ** 2).astype(np.float32)
    if nombre == "ding":
        t = _t(0.9); return ((np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 2637 * t)) * np.exp(-t * 5) * 0.6).astype(np.float32)
    if nombre == "golpe":                      # sello que cae
        t = _t(0.3); x = np.sin(2 * np.pi * (110 * np.exp(-t * 14) + 46) * t) * np.exp(-t * 13) + rng.standard_normal(len(t)) * np.exp(-t * 70) * 0.5
        return x.astype(np.float32)
    if nombre == "tic":
        t = _t(0.04); return (np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 120) * 0.7).astype(np.float32)
    if nombre == "error":                      # zumbido de «incorrecto»
        t = _t(0.38); x = np.sign(np.sin(2 * np.pi * 150 * t)) * 0.35 + np.sign(np.sin(2 * np.pi * 113 * t)) * 0.25
        return (x * _env(len(t), 0.005, 0.08)).astype(np.float32)
    if nombre == "tada":
        out = np.zeros(int(SR * 1.1))
        for k, f in enumerate((523, 659, 784, 1047)):
            t = _t(0.7); s = int(k * 0.085 * SR); x = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 4.5)
            out[s:s + len(x)] += x[:len(out) - s] * 0.4
        return out.astype(np.float32)
    if nombre == "sube":                       # tono que sube (medidor que se llena)
        t = _t(1.0); f = 300 + 900 * t ** 1.5
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.05, 0.1) * 0.35).astype(np.float32)
    if nombre == "freno":                      # chirrido corto de frenada
        t = _t(0.5); f = 1500 - 500 * t
        x = np.sin(2 * np.pi * np.cumsum(f) / SR + 2.5 * np.sin(2 * np.pi * 37 * t)) * _env(len(t), 0.02, 0.3) * 0.22
        return x.astype(np.float32)
    if nombre == "congela":                    # disparo de cámara
        t = _t(0.16); x = rng.standard_normal(len(t)) * (np.exp(-t * 90) + 0.6 * np.exp(-((t - 0.09) ** 2) / 0.0002))
        return (x * 0.7).astype(np.float32)
    if nombre == "alarma":                     # pitido doble de despertador
        out = np.zeros(int(SR * 0.5))
        for k in range(2):
            t = _t(0.11); x = np.sign(np.sin(2 * np.pi * 1960 * t)) * 0.25 * _env(len(t), 0.004, 0.02); s0 = int(k * 0.2 * SR); out[s0:s0 + len(x)] += x
        return out.astype(np.float32)
    if nombre in ("claxon", "claxon_largo"):   # bocina de vehículo (dos tonos desafinados, con algo de saturación) — v1.1, 23-nov-2026
        t = _t(0.32 if nombre == "claxon" else 0.9)
        x = sum(np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * t) for f in (415, 494)) * 0.18
        k = np.exp(-np.linspace(-2, 2, 9) ** 2); x = np.convolve(x, k / k.sum(), "same")
        return (np.tanh(x * 2.2) * 0.4 * _env(len(t), 0.01, 0.05)).astype(np.float32)
    raise KeyError(nombre)


def musica(dur, bpm=104, semilla=1):
    """Base ligera: bajo con tresillo suave + acordes cortos. Cambia de tono con la semilla (un vídeo ≠ otro)."""
    n = int(SR * dur); out = np.zeros(n); beat = 60 / bpm
    raiz = [48, 50, 45, 52][semilla % 4]
    prog = [0, 5, 7, 3] if semilla % 2 else [0, 3, 5, 7]
    def nota(m): return 440 * 2 ** ((m - 69) / 12)
    def pon(t0, x, g):
        s = int(t0 * SR)
        if s < n: m = min(len(x), n - s); out[s:s + m] += x[:m] * g
    k = 0; t0 = 0.0
    while t0 < dur:
        ac = raiz + prog[(k // 8) % 4]
        t = _t(beat * 0.9)
        if k % 2 == 0: pon(t0, np.sin(2 * np.pi * nota(ac - 12) * t) * np.exp(-t * 5), 0.5)
        if k % 4 in (1, 3):
            ch = sum(np.sin(2 * np.pi * nota(ac + i + 12) * _t(0.22)) for i in (0, 4, 7)) * np.exp(-_t(0.22) * 16)
            pon(t0, ch, 0.14)
        if k % 2 == 1: pon(t0, np.random.default_rng(k).standard_normal(int(SR * 0.03)) * np.exp(-_t(0.03) * 150), 0.12)
        k += 1; t0 += beat / 2
    return (out / max(1e-6, np.abs(out).max())).astype(np.float32)
