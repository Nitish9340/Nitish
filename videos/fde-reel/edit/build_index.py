"""Generate index.html from edit/template.html + edl.json + captions.json.

Run after build_edl.py:  python3 edit/build_index.py
"""
import json, pathlib, html

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
edl = json.load(open(HERE / "edl.json"))
caps = json.load(open(HERE / "captions.json"))
DURATION = round(edl[-1]["start"] + edl[-1]["dur"], 3)

# ------------------------------------------------------------------ shots
# Extra framing cuts inside long takes (timeline seconds); source stays continuous.
EXTRA_CUTS = [30.55, 32.45]

# (from_t, layout, zoom) — layout per beat; zoom = punch-in level for the shot starting there.
LAYOUT = [
    (0.00, "split", 1.00), (2.68, "blur", 1.15), (4.97, "full", 1.00), (6.99, "split", 1.08),
    (9.70, "full", 1.38), (10.70, "full", 1.00), (12.81, "full", 1.10), (14.35, "full", 1.12),
    (16.74, "split", 1.00), (19.57, "split", 1.16), (22.04, "split", 1.06), (24.36, "full", 1.22),
    (26.26, "full", 1.00), (29.24, "full", 1.36), (30.55, "full", 1.00), (32.45, "full", 1.14),
]


def layout_at(t):
    cur = LAYOUT[0]
    for row in LAYOUT:
        if row[0] <= t + 0.01:
            cur = row
    return cur


shots = []
for seg in edl:
    a, b = seg["start"], seg["start"] + seg["dur"]
    cuts = [a] + [c for c in EXTRA_CUTS if a < c < b] + [b]
    for x, y in zip(cuts, cuts[1:]):
        shots.append({"start": round(x, 3), "end": round(y, 3),
                      "media": round(seg["src_in"] + (x - a), 3)})
for s in shots:  # durations from rounded edges, so neighbours meet exactly
    s["dur"] = round(s["end"] - s["start"], 3)

VOICE_CHAIN = {"version": 1, "nodes": [
    {"type": "highpass", "id": "n1", "label": "Remove Rumble", "params": {"frequency": 90, "q": 0.707, "poles": "2"}},
    {"type": "peaking", "id": "n2", "label": "Reduce Mud", "params": {"frequency": 320, "gain": -3, "q": 1.1}},
    {"type": "compressor", "id": "n3", "label": "Even Out Loudness", "params": {"threshold": -32, "ratio": 3.5, "attack": 8, "release": 140, "knee": 2.83, "makeup": 9, "mix": 1}},
    {"type": "peaking", "id": "n4", "label": "Add Clarity", "params": {"frequency": 3200, "gain": 3, "q": 0.9}},
    {"type": "highshelf", "id": "n5", "label": "Add Air", "params": {"frequency": 9000, "gain": 2}},
    {"type": "limiter", "id": "n6", "label": "Peak Ceiling", "params": {"limit": -1.5, "attack": 5, "release": 60, "level_out": 0}},
]}
chain_attr = html.escape(json.dumps(VOICE_CHAIN, separators=(",", ":")), quote=True)

videos, shot_js = [], []
for k, s in enumerate(shots):
    _, lay, z = layout_at(s["start"])
    sid = f"s{k:02d}"
    videos.append(
        f'      <div id="w-{sid}" class="shot {lay}" data-layout-allow-overflow>'
        f'<video id="v-{sid}" src="raw.mp4" data-start="{s["start"]}" data-duration="{s["dur"]}" '
        f'data-media-start="{s["media"]}" data-track-index="0" data-volume="1.5" '
        f'data-fx-chain="{chain_attr}" playsinline data-has-audio="true"></video></div>')
    if s["start"] == 14.35:  # FDE reveal: settle, then hard punch on "FDE"
        shot_js.append(f'      tl.fromTo("#w-{sid}", {{ scale: 1.2 }}, {{ scale: 1.12, duration: 0.25, ease: "power3.out" }}, {s["start"]});')
        shot_js.append(f'      tl.fromTo("#w-{sid}", {{ scale: 1.12 }}, {{ scale: 1.26, duration: 0.14, ease: "power4.out" }}, 14.81);')
        shot_js.append(f'      tl.to("#w-{sid}", {{ scale: 1.3, duration: {round(s["start"] + s["dur"] - 14.95, 3)}, ease: "none" }}, 14.95);')
        continue
    push = round(max(0.05, s["dur"] - 0.22), 3)
    shot_js.append(
        f'      tl.fromTo("#w-{sid}", {{ scale: {round(z * 1.07, 3)} }}, {{ scale: {z}, duration: 0.22, ease: "power3.out" }}, {s["start"]});'
        f' tl.to("#w-{sid}", {{ scale: {round(z * 1.035, 3)}, duration: {push}, ease: "none" }}, {round(s["start"] + 0.22, 3)});')

# ------------------------------------------------------------------ captions
# Big kinetic headlines already spell these words out; the reference shows no small caption under them.
NO_CAPS = [(9.70, 10.70), (14.35, 16.74), (24.36, 26.26), (29.24, 30.55), (32.45, 99.0)]
cap_html, cap_js = [], []
for k, c in enumerate(caps):
    if any(a <= c["start"] < b for a, b in NO_CAPS):
        continue
    nxt = caps[k + 1]["start"] if k + 1 < len(caps) else DURATION
    end = min(nxt, max(c["end"] + 0.25, c["start"] + 0.18), DURATION - 0.02)
    for a, b in NO_CAPS:
        if c["start"] < a < end:
            end = a
    # A word can outlive its shot: split it at every layout change so the caption moves with
    # the cut (seam position on split screens, chest position on full frame) and never lands on the face.
    edges = [c["start"]] + [t for t, _, _ in LAYOUT if c["start"] + 0.01 < t < end - 0.01] + [end]
    for j, (a, b) in enumerate(zip(edges, edges[1:])):
        if b - a < 0.07 and j > 0:
            continue
        cid = f"c{k:03d}" + ("" if j == 0 else f"-{j}")
        seam = " cap-seam" if layout_at(a)[1] == "split" else ""
        cap_html.append(f'      <div id="{cid}" class="cap{seam} clip" data-start="{round(a, 3)}" data-duration="{round(b - a, 3)}" data-track-index="20"><span id="{cid}-t">{html.escape(c["text"])}</span></div>')
        if j == 0:
            cap_js.append(f'tl.fromTo("#{cid}-t", {{ scale: 0.82 }}, {{ scale: 1, duration: 0.09, ease: "back.out(3)" }}, {c["start"]});')

# ------------------------------------------------------------------ audio
SFX = [  # (time, file, volume)
    (0.00, "whoosh", 0.55), (0.18, "pop", 0.35), (0.57, "pop", 0.45), (1.95, "scribble", 0.5), (2.22, "pop", 0.45),
    (2.62, "whoosh", 0.6), (3.05, "pop", 0.3), (3.72, "pop", 0.3), (4.30, "pop", 0.3), (4.60, "impact", 0.35),
    (4.93, "whoosh", 0.45), (6.30, "pop", 0.35),
    (6.95, "whoosh", 0.55), (7.56, "impact", 0.4), (8.70, "whoosh", 0.5), (9.06, "pop", 0.45),
    (9.66, "whoosh", 0.5), (10.28, "impact", 0.35),
    (10.66, "whoosh", 0.55), (11.05, "pop", 0.25), (12.86, "whoosh", 0.45), (13.74, "ding", 0.4),
    (14.81, "impact", 0.85), (15.45, "pop", 0.35), (15.84, "pop", 0.35), (16.17, "pop", 0.35),
    (16.70, "whoosh", 0.55), (18.30, "pop", 0.35), (19.50, "pop", 0.35), (20.80, "pop", 0.35), (21.58, "ding", 0.45),
    (22.00, "whoosh", 0.55), (23.42, "pop", 0.35), (24.32, "whoosh", 0.45), (24.80, "impact", 0.35),
    (26.22, "whoosh", 0.55), (26.30, "pop", 0.3), (28.18, "impact", 0.7), (28.20, "ding", 0.4),
    (29.20, "whoosh", 0.5), (29.80, "impact", 0.35),
    (30.57, "pop", 0.4), (31.07, "click", 0.6), (31.19, "click", 0.6), (31.31, "click", 0.6), (31.45, "pop", 0.4),
    (32.50, "pop", 0.45), (32.92, "click", 0.7), (33.00, "ding", 0.4), (33.78, "impact", 0.4),
]
SFX_LEN = {"whoosh": 0.55, "pop": 0.09, "scribble": 0.32, "impact": 1.4, "ding": 1.2, "click": 0.03}
audio = [f'      <audio id="music" src="assets/audio/music.wav" data-start="0" data-duration="{DURATION}" data-track-index="30" data-volume="0.7"></audio>']
SFX_TRIM_DB = {"impact": -12, "whoosh": -14, "pop": -16, "click": -16, "ding": -16, "scribble": -16}
SFX = [(t, name, round(vol * 10 ** (SFX_TRIM_DB[name] / 20), 4)) for t, name, vol in SFX]
lanes = []  # greedy lane packing so layered SFX never share a Studio lane
for k, (t, name, vol) in enumerate(SFX):
    d = round(min(SFX_LEN[name], DURATION - t - 0.01), 3)
    lane = next((i for i, end in enumerate(lanes) if end <= t), len(lanes))
    if lane == len(lanes):
        lanes.append(0)
    lanes[lane] = t + d
    audio.append(f'      <audio id="sfx{k:02d}-{name}" src="assets/audio/sfx-{name}.wav" data-start="{t}" data-duration="{d}" data-track-index="{31 + lane}" data-volume="{vol}"></audio>')

# ------------------------------------------------------------------ graphics bits
dots = []
k = 0
for r in range(3):
    for c in range(8):
        x, y = 290 + c * 66, 1095 + r * 70
        if (r, c) == (1, 4):
            continue  # the one who leaves is drawn as #b5-hero
        dots.append(f'          <div class="b5-dot" style="position: absolute; left: {x}px; top: {y}px; width: 40px; height: 40px; border-radius: 50%; background: #b9c8ff"></div>')
        k += 1

bars = []
heights = [60, 90, 140, 210, 330, 520]
for i, h in enumerate(heights):
    bars.append(f'          <div class="bar b10-bar" style="left: {150 + i * 140}px; top: {1280 - h}px; height: {h}px; bottom: auto"></div>')

ICON = {
    "BUILDING": '<svg width="56" height="56" viewBox="0 0 56 56"><rect x="10" y="8" width="36" height="42" rx="3" fill="none" stroke="#fff" stroke-width="5"/><path d="M19 18h6M31 18h6M19 28h6M31 28h6M24 50v-9h8v9" stroke="#fff" stroke-width="5" stroke-linecap="round"/></svg>',
    "TEAM": '<svg width="60" height="56" viewBox="0 0 60 56"><circle cx="20" cy="18" r="8" fill="#fff"/><circle cx="42" cy="18" r="8" fill="#fff"/><path d="M5 46c2-10 8-14 15-14s13 4 15 14M27 46c2-10 8-14 15-14s13 4 15 14" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/></svg>',
    "WARN": '<svg width="58" height="54" viewBox="0 0 58 54"><path d="M29 5 L54 49 H4 Z" fill="none" stroke="#ff4d5e" stroke-width="5" stroke-linejoin="round"/><path d="M29 21v13" stroke="#ff4d5e" stroke-width="5" stroke-linecap="round"/><circle cx="29" cy="41" r="3.5" fill="#ff4d5e"/></svg>',
    "WRENCH": '<svg width="56" height="56" viewBox="0 0 56 56"><path d="M36 8a12 12 0 0 0-11 16L9 40a5 5 0 0 0 7 7l16-16A12 12 0 0 0 48 20l-7 7-8-2-2-8 7-7a12 12 0 0 0-2-2z" fill="#2fd58b"/></svg>',
    "CHECK": '<svg width="44" height="44" viewBox="0 0 44 44"><path d="M9 23l9 9 18-19" fill="none" stroke="#052e1c" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "CUBE": '<svg width="200" height="200" viewBox="0 0 200 200"><path d="M100 20 L170 58 V142 L100 180 L30 142 V58 Z" fill="rgba(185,200,255,0.12)" stroke="#b9c8ff" stroke-width="9" stroke-linejoin="round"/><path d="M30 58 L100 96 L170 58 M100 96 V180" fill="none" stroke="#b9c8ff" stroke-width="9" stroke-linejoin="round"/></svg>',
    "GLOBE": '<svg width="200" height="200" viewBox="0 0 200 200"><circle cx="100" cy="100" r="78" fill="rgba(92,214,255,0.12)" stroke="#5cd6ff" stroke-width="9"/><ellipse cx="100" cy="100" rx="34" ry="78" fill="none" stroke="#5cd6ff" stroke-width="7"/><path d="M24 100h152M36 60h128M36 140h128" stroke="#5cd6ff" stroke-width="7"/></svg>',
    "SEND": '<svg width="46" height="46" viewBox="0 0 46 46"><path d="M6 22 L40 6 L28 40 L22 26 Z" fill="#fff"/></svg>',
}

out = (HERE / "template.html").read_text()
out = out.replace("__DURATION__", str(DURATION))
out = out.replace("__VIDEOS__", "\n".join(videos))
out = out.replace("__SHOT_JS__", "\n".join(shot_js))
out = out.replace("__CAPTIONS__", "\n".join(cap_html))
out = out.replace("__CAPTION_JS__", "      " + "\n      ".join(cap_js))
out = out.replace("__AUDIO__", "\n".join(audio))
out = out.replace("__DOTS__", "\n".join(dots))
out = out.replace("__BARS__", "\n".join(bars))
for name, svg in ICON.items():
    out = out.replace(f"__ICON_{name}__", svg)
assert "__" not in out.replace("window.__timelines", "").replace("__hf", ""), "unfilled placeholder"
(ROOT / "index.html").write_text(out)
print(f"index.html: {len(shots)} shots, {len(cap_html)} captions, {len(SFX)} sfx, duration {DURATION}s")
