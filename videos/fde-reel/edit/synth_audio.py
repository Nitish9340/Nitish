"""Synthesize an original music bed and SFX for the FDE reel (no samples, no network).

Usage: python synth_audio.py <out_dir> <duration_seconds>
Writes music.wav and sfx-*.wav (48 kHz, 16-bit stereo).

Music: 120 BPM, Am-F-C-G, four-on-the-floor tech pulse. Arrangement follows the edit:
  0.00  hook groove (filtered)      2.68  full groove
  9.70  story breakdown (no kick)   12.8  riser -> gap -> 14.81 DROP on "FDE"
  26.26 stat section (busier hats)  29.24 outro groove, fade at the end
"""
import sys, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)  # seeded: re-running gives identical audio


def write(path, x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    peak = np.max(np.abs(x)) or 1.0
    x = x / peak * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def onepole(x, cutoff):
    """Time-varying one-pole lowpass. cutoff: scalar or per-sample array (Hz)."""
    c = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), x.shape)
    a = 1.0 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s); y[i] = s
    return y


def hp(x, cutoff):
    return x - onepole(x, cutoff)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def note_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 9):
        out += np.sin(2 * np.pi * f * k * t + phase * k) / k
    return out * 0.6


def place(buf, x, t):
    x = np.array(x, dtype=np.float64)
    f = min(len(x) // 4, int(0.006 * SR))  # de-click: 6 ms fade at both ends
    if f > 1:
        x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    i = int(round(t * SR))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i]


# ---------------------------------------------------------------- instruments
def kick():
    n = int(0.42 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env_exp(n, 0.13) + 0.15 * rng.standard_normal(n) * env_exp(n, 0.004)


def hat(open_=False):
    n = int((0.16 if open_ else 0.05) * SR)
    x = hp(rng.standard_normal(n), 7000)
    return x * env_exp(n, 0.05 if open_ else 0.012)


def clap():
    n = int(0.22 * SR)
    x = hp(onepole(rng.standard_normal(n), 3500), 900)
    e = env_exp(n, 0.06)
    for d in (0.0, 0.011, 0.022):  # three smeared hits
        e[int(d * SR):] += 0.5 * env_exp(n - int(d * SR), 0.008)
    return x * e * 0.7


def pluck(m, dur=0.22):
    n = int(dur * SR)
    x = saw(note_hz(m), n) * env_exp(n, 0.07)
    return onepole(x, 2600)


def bass_note(m, dur):
    n = int(dur * SR)
    x = saw(note_hz(m), n)
    e = np.minimum(1, np.arange(n) / (0.004 * SR)) * env_exp(n, 0.18)
    return onepole(x * e, 420)


def pad_chord(ms, dur):
    n = int(dur * SR); out = np.zeros(n)
    for m in ms:
        for det in (-0.12, 0.0, 0.11):
            out += saw(note_hz(m + det), n, phase=rng.uniform(0, 6.28))
    a = np.minimum(1, np.arange(n) / (0.35 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.3 * SR))
    return onepole(out * a, 1400) * 0.12


# ---------------------------------------------------------------- music
def music(total):
    n = int(total * SR)
    drums, bass, keys, pad = (np.zeros(n) for _ in range(4))
    beat = 0.5
    # Am, F, C, G  (root, chord tones) — two beats... one bar (2 s) each
    prog = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [55, 60, 64]), (43, [55, 59, 62])]
    K, H, HO, C = kick(), hat(), hat(True), clap()

    def section(t):
        if t < 2.68: return "hook"
        if t < 9.70: return "groove"
        if t < 14.81: return "story"
        if t < 26.26: return "drop"
        if t < 29.24: return "stat"
        return "outro"

    step = beat / 4
    for s in range(int(total / step)):
        t = s * step; sec = section(t)
        bar = int(t // 2.0); root, chord = prog[bar % 4]
        in_beat = s % 4; beat_i = (s // 4) % 4
        if in_beat == 0 and sec not in ("story",):
            place(drums, K * (0.8 if sec == "hook" else 1.0), t)
        if in_beat == 0 and sec == "story" and t >= 12.8 and beat_i % 2 == 0:
            place(drums, K * 0.55, t)  # half-time pulse into the riser
        if in_beat == 2 and sec != "hook":
            place(drums, (HO if sec in ("drop", "stat") and beat_i == 3 else H) * 0.35, t)
        if sec == "stat" and in_beat in (1, 3):
            place(drums, H * 0.18, t)
        if in_beat == 0 and beat_i in (1, 3) and sec in ("groove", "drop", "stat", "outro"):
            place(drums, C * 0.55, t)
        if in_beat in (0, 2) and sec != "story":
            place(bass, bass_note(root, step * 2 * 0.95), t)
        if sec != "hook" or t > 1.0:
            m = chord[(s // 1) % 3] + (12 if (s // 3) % 2 and sec in ("drop", "stat") else 0)
            place(keys, pluck(m) * (0.55 if sec == "story" else 0.42), t)
        if s % 16 == 0:
            place(pad, pad_chord(chord, 2.05), t)

    # sidechain: duck bass + pad + keys on each kick
    sc = np.ones(n)
    for b in range(int(total / beat)):
        t = b * beat
        if section(t) != "story":
            i = int(t * SR); L = int(0.25 * SR)
            seg = 1 - 0.55 * env_exp(L, 0.08)
            sc[i:i + L] = np.minimum(sc[i:i + L], seg[: max(0, min(L, n - i))])
    mix = drums * 0.9 + (bass * 0.75 + keys * 0.55 + pad * 1.0) * sc

    # riser 12.8 -> 14.62, then a short silence before the drop on "FDE" (14.81)
    rs, re_ = 12.8, 14.62
    L = int((re_ - rs) * SR); prog_ = np.linspace(0, 1, L)
    noise = onepole(rng.standard_normal(L), 300 + 9000 * prog_ ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * prog_ ** 2) / SR) * 0.25
    place(mix, (noise * 0.9 + tone) * prog_ ** 2 * 0.6, rs)
    gap = (np.arange(n) >= int(14.62 * SR)) & (np.arange(n) < int(14.81 * SR))
    mix[gap] *= 0.05

    # hook is low-passed (opens at 2.68)
    hook_end = int(2.68 * SR)
    mix[:hook_end] = onepole(mix[:hook_end], np.linspace(700, 6000, hook_end))

    # master fade-out over the last 0.8 s
    fo = int(0.8 * SR); mix[-fo:] *= np.linspace(1, 0, fo)
    # gentle stereo width: delayed copy of keys/pad on the right
    d = int(0.012 * SR)
    right = mix.copy(); right[d:] = 0.85 * mix[d:] + 0.15 * mix[:-d]
    return np.tanh(np.stack([mix, right], axis=1) * 1.2)


# ---------------------------------------------------------------- sfx
def sfx_whoosh(dur=0.55):
    n = int(dur * SR); p = np.linspace(0, 1, n)
    bell = np.sin(np.pi * p) ** 2
    x = onepole(rng.standard_normal(n), 400 + 5000 * np.sin(np.pi * p))
    pan = p
    return np.stack([x * bell * (1 - 0.6 * pan), x * bell * (0.4 + 0.6 * pan)], axis=1)


def sfx_impact():
    n = int(1.4 * SR); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(32 + 60 * np.exp(-t / 0.08)) / SR) * env_exp(n, 0.35)
    crack = onepole(rng.standard_normal(n), 2500) * env_exp(n, 0.05)
    tail = onepole(rng.standard_normal(n), 900) * env_exp(n, 0.45) * 0.25
    return np.tanh((sub * 1.2 + crack * 0.8 + tail) * 1.4)


def sfx_pop():
    n = int(0.09 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(500 + 900 * t / t[-1]) / SR) * env_exp(n, 0.025)


def sfx_click():
    n = int(0.03 * SR)
    return hp(rng.standard_normal(n), 2500) * env_exp(n, 0.004)


def sfx_ding():
    n = int(1.2 * SR); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1318.5, 1), (2637, 0.35), (3955, 0.12)))
    return x * env_exp(n, 0.35) * np.minimum(1, t / 0.002)


def sfx_scribble():
    n = int(0.32 * SR); t = np.arange(n) / SR
    wob = 0.5 + 0.5 * np.sin(2 * np.pi * 22 * t)
    return hp(onepole(rng.standard_normal(n), 4000), 1200) * wob * np.sin(np.pi * t / t[-1])


if __name__ == "__main__":
    out, total = sys.argv[1], float(sys.argv[2])
    write(f"{out}/music.wav", music(total))
    write(f"{out}/sfx-whoosh.wav", sfx_whoosh())
    write(f"{out}/sfx-impact.wav", sfx_impact())
    write(f"{out}/sfx-pop.wav", sfx_pop())
    write(f"{out}/sfx-click.wav", sfx_click())
    write(f"{out}/sfx-ding.wav", sfx_ding())
    write(f"{out}/sfx-scribble.wav", sfx_scribble())
    print("ok")
