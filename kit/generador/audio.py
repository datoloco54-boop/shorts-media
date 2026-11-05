import json, sys, wave, numpy as np, subprocess
T = json.load(open("tiempos.json")); SR = 48000
N = int(T["total"] * SR)
# voz: cada frase en su sitio
voz = np.zeros(N)
for i, st in enumerate(T["starts"]):
    raw = subprocess.run(["ffmpeg","-v","error","-i",f"l{i+1}.wav","-ar",str(SR),"-ac","1","-f","f32le","-"],capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(float)
    a = int(st * SR); voz[a:a+len(x)] += x[:N-a]
# música: acordes suaves + arpegio + pulso
t = np.arange(N) / SR
bpm = 112; beat = 60 / bpm
chords = [[57,60,64],[53,57,60],[48,52,55],[55,59,62]]   # Am F C G
mus = np.zeros(N)
f = lambda m: 440 * 2 ** ((m - 69) / 12)
for k in range(int(T["total"] / (beat * 4)) + 1):
    ch = chords[k % 4]; a0 = k * beat * 4
    for j in range(8):                                     # arpegio en corcheas
        s = a0 + j * beat / 2; e = s + beat / 2
        m = ch[j % 3] + 12 * (j // 3 % 2)
        sl = (t >= s) & (t < e + 0.3)
        tt = t[sl] - s
        mus[sl] += 0.16 * np.sin(2*np.pi*f(m)*tt) * np.exp(-tt * 6) * (1 + 0.3*np.sin(2*np.pi*f(m)*2*tt))
    sl = (t >= a0) & (t < a0 + beat * 4)
    tt = t[sl] - a0
    for m in ch:                                           # colchón
        mus[sl] += 0.05 * np.sin(2*np.pi*f(m-12)*tt) * np.minimum(1, tt*4) * np.minimum(1, (beat*4-tt)*4)
    for b in range(4):                                     # bombo suave
        s = a0 + b * beat; sl = (t >= s) & (t < s + 0.25); tt = t[sl] - s
        mus[sl] += 0.35 * np.sin(2*np.pi*(55 + 90*np.exp(-tt*30))*tt) * np.exp(-tt*14)
# "pop" en cada cambio de escena
for st in T["starts"][1:]:
    a = int((st - 0.05) * SR); n = int(0.12 * SR); tt = np.arange(n) / SR
    mus[a:a+n] += 0.25 * np.sin(2*np.pi*(900 - 3000*tt)*tt) * np.exp(-tt*35)
# fundido final
fade = int(0.5 * SR); mus[-fade:] *= np.linspace(1, 0, fade)
voz /= max(1e-9, np.abs(voz).max()); mus /= max(1e-9, np.abs(mus).max())
mix = 0.92 * voz + 0.16 * mus
mix /= np.abs(mix).max() / 0.89
with wave.open("audio.wav", "w") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("ok", N / SR)
