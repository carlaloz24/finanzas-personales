"""Animatic Bloque 404 – Ep.04 'Le hemos intentado entregar'.
Montaje: Ken Burns por plano + rótulos + sonido sintetizado -> MP4 vertical 1080x1920.
Uso: python3 build.py
"""
import os, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(D, "frames")
B = os.path.join(D, "build"); os.makedirs(B, exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_B = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
MUSTARD = (212, 160, 23)

# plano: imagen, duración, zoom inicio->fin, centro de encuadre (x,y en 0-1), rótulos
# rótulo: (texto, t_inicio, t_fin, estilo)  estilo: hook | sub | title
SHOTS = [
    ("s1", 4.0, (1.00, 1.10), (0.55, 0.40), [("9 horas esperando\nal repartidor", 0.0, 4.0, "hook")]),
    ("s2", 2.8, (1.05, 1.25), (0.52, 0.47), [("«Ausente. Le hemos\nintentado entregar.»", 0.5, 2.8, "sub")]),
    ("s3", 2.8, (1.00, 1.22), (0.54, 0.30), []),
    ("s4", 2.0, (1.10, 1.18), (0.50, 0.33), []),
    ("s5", 4.4, (1.18, 1.00), (0.50, 0.40), [("Política de empresa.", 1.4, 4.4, "sub")]),
    ("s6", 4.0, (1.00, 1.06), (0.50, 0.42), []),
    ("s7", 3.6, (1.08, 1.00), (0.50, 0.50), [("BLOQUE 404", 0.4, 3.6, "title")]),
]


def font(path, size):
    return ImageFont.truetype(path, size)


def overlay(text, style):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if style == "title":
        f = font(FONT_B, 130); f2 = font(FONT, 40)
        bb = d.textbbox((0, 0), text, font=f)
        x = (W - (bb[2] - bb[0])) // 2; y = 300
        d.rectangle([x - 40, y - 30, x + bb[2] - bb[0] + 40, y + bb[3] - bb[1] + 60], fill=(15, 15, 15, 215))
        d.text((x - bb[0], y - bb[1] + 5), text, font=f, fill=MUSTARD + (255,))
        s = "Ep. 04 · Aviso de entrega"
        bb2 = d.textbbox((0, 0), s, font=f2)
        d.text(((W - (bb2[2] - bb2[0])) // 2, y + bb[3] - bb[1] + 85), s, font=f2, fill=(240, 240, 240, 255),
               stroke_width=3, stroke_fill=(0, 0, 0, 255))
        return img
    size = 70 if style == "hook" else 56
    f = font(FONT, size)
    lines = text.split("\n")
    y = 260 if style == "hook" else 1330
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=f)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        x = (W - w) // 2
        bg = MUSTARD + (240,) if style == "hook" else (0, 0, 0, 205)
        fg = (15, 15, 15, 255) if style == "hook" else (255, 255, 255, 255)
        d.rectangle([x - 26, y - 18, x + w + 26, y + h + 22], fill=bg)
        d.text((x - bb[0], y - bb[1]), ln, font=f, fill=fg)
        y += h + 44
    return img


def render_shot(i, name, dur, zoom, center, texts):
    n = int(round(dur * FPS))
    z0, z1 = zoom; cx, cy = center
    src = Image.open(os.path.join(F, name + ".png")).convert("RGB").resize((W, H), Image.LANCZOS)
    ovs = [(overlay(t, s), a, b) for t, a, b, s in texts]
    out = os.path.join(B, f"shot{i}.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for k in range(n):
        t = k / FPS; u = k / max(n - 1, 1)
        u = u * u * (3 - 2 * u)  # ease in-out
        z = z0 + (z1 - z0) * u
        cw, ch = W / z, H / z
        x0 = min(max(cx * W - cw / 2, 0), W - cw); y0 = min(max(cy * H - ch / 2, 0), H - ch)
        fr = src.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC).convert("RGBA")
        for ov, a, b in ovs:
            if a <= t < b:
                fade = min(1.0, (t - a) / 0.15)
                o = ov if fade >= 1 else Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 0)), ov, fade)
                fr = Image.alpha_composite(fr, o)
        p.stdin.write(fr.convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    return out


# ---------------- sonido ----------------
def env(n, a=0.01, r=0.2):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e


def bandnoise(dur, lo, hi, seed=0):
    n = int(dur * SR); rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n)); fr = np.fft.rfftfreq(n, 1 / SR)
    spec[(fr < lo) | (fr > hi)] = 0
    x = np.fft.irfft(spec, n); return x / (np.abs(x).max() + 1e-9)


def sine(dur, f, decay=None):
    t = np.arange(int(dur * SR)) / SR; x = np.sin(2 * np.pi * f * t)
    return x * (np.exp(-t / decay) if decay else 1)


def build_audio(total, starts):
    mix = np.zeros(int(total * SR) + SR)
    def add(x, t, g):
        i = int(t * SR); mix[i:i + len(x)] += g * x[:len(mix) - i]
    s = starts
    # dron de tensión (planos 1-5), se corta en seco en la mirada 404
    dd = s[5]; t = np.arange(int(dd * SR)) / SR
    drone = (np.sin(2*np.pi*55*t) + .5*np.sin(2*np.pi*82.4*t) + .3*np.sin(2*np.pi*110.6*t)) * (0.6 + 0.4*np.sin(2*np.pi*0.25*t))
    drone *= np.minimum(1, t / 1.5); add(drone, 0, 0.10)
    add(bandnoise(dd, 80, 400, 1) * np.minimum(1, t / 1.5), 0, 0.03)
    # reloj de pared (plano 1)
    for k in range(4): add(bandnoise(0.03, 2000, 6000, 10 + k) * env(int(.03*SR), .001, .02), 0.3 + k, 0.25)
    # papel deslizándose (plano 2)
    sw = bandnoise(0.9, 1500, 7000, 2); add(sw * env(len(sw), .25, .4), s[1] + 0.2, 0.35)
    # puerta abriéndose + zumbido fluorescente (plano 3)
    wh = bandnoise(0.5, 200, 2500, 3); add(wh * env(len(wh), .02, .35), s[2], 0.5)
    hd = s[3] - s[2]; th = np.arange(int(hd * SR)) / SR
    hum = (np.sin(2*np.pi*100*th) + .4*np.sin(2*np.pi*200*th) + .2*np.sin(2*np.pi*300*th)) * env(len(th), .1, .2)
    add(hum, s[2], 0.06)
    # bolígrafo escribiendo (desde el final del plano 3 hasta el 5)
    rng = np.random.default_rng(7)
    tt = s[3] - 0.6
    while tt < s[5] - 0.3:
        L = rng.uniform(.06, .18); x = bandnoise(L, 2500, 9000, int(tt*100)); add(x * env(len(x), .01, .03), tt, 0.10)
        tt += L + rng.uniform(.03, .12)
    # golpe grave al girarse (plano 4)
    t2 = np.arange(int(.8*SR)) / SR; hit = np.sin(2*np.pi*(60*np.exp(-t2*3))*t2) * np.exp(-t2*4)
    add(hit, s[3] + 0.05, 0.6)
    # "plaf" del aviso en la frente (plano 6), luego silencio absoluto
    sl = bandnoise(0.12, 300, 3000, 5); add(sl * env(len(sl), .002, .1), s[5], 0.7)
    # ding desafinado de ascensor (plano 7) = sound logo
    ding = sine(2.5, 880, .7) + .6*sine(2.5, 1318.5*0.985, .6) + .3*sine(2.5, 1760*1.01, .4)
    add(ding * env(len(ding), .003, .3), s[6] + 0.35, 0.22)
    ding2 = sine(2.5, 659.3*0.97, .8) + .4*sine(2.5, 987.8, .6)
    add(ding2 * env(len(ding2), .003, .3), s[6] + 0.75, 0.2)
    mix = mix[:int(total * SR)]
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.85
    out = os.path.join(B, "audio.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return out


if __name__ == "__main__":
    clips, starts, t = [], [], 0.0
    for i, sh in enumerate(SHOTS):
        starts.append(t); t += sh[1]
        clips.append(render_shot(i + 1, *sh)); print("plano", i + 1, "ok")
    audio = build_audio(t, starts)
    lst = os.path.join(B, "list.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{c}'\n" for c in clips)
    final = os.path.join(D, "bloque404_ep04_aviso_de_entrega.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", audio,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("OK", final, round(t, 1), "s")
