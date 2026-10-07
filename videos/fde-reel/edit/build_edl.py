"""Build the jump-cut edit list + corrected caption words from the Vosk transcript.

Input : edit/raw_words.json   (Vosk word timings on raw.mp4)
Output: edit/edl.json         (segments: source in/out -> timeline start) and
        edit/captions.json    (corrected words on the *timeline* clock)
"""
import json, pathlib

HERE = pathlib.Path(__file__).parent
words = json.load(open(HERE / "raw_words.json"))

# Corrections of small-model mishearings, by word index. None = drop (time merged into previous).
FIX = {
    10: "title.", 11: "Big", 12: None, 14: "are", 15: "hiring", 19: "now.",
    26: "it.", 28: "no,", 31: "working", 33: "home.", 36: "opposite.",
    38: "an", 39: "army.", 41: "soldiers", 42: "stay at", 45: "base.",
    51: "front line.", 52: "That's", 54: "FDE.", 55: "Forward", 56: "Deployed", 57: "Engineer.",
    58: "You", 62: "client's", 63: "office,", 64: None, 69: "team,", 81: "spot.",
    82: "Engineers", 86: "build", 87: "the", 88: "product.", 89: "This", 97: "world.",
    98: "Postings", 102: "are", 104: "800%", 105: None, 106: None, 107: "Have", 112: "it?",
    113: "Comment", 114: "FDE", 121: "and", 127: "AI", 128: "stuff.",
    0: "The",
}

fixed = []
for i, w in enumerate(words):
    t = FIX.get(i, w["text"])
    if t is None:
        fixed[-1]["end"] = w["end"]
        continue
    fixed.append({"i": i, "text": t, "start": w["start"], "end": w["end"]})

# Cut any gap longer than GAP between consecutive words; keep small handles.
GAP, PRE, POST = 0.28, 0.06, 0.10
segs, cur = [], [fixed[0]]
for w in fixed[1:]:
    if w["start"] - cur[-1]["end"] > GAP:
        segs.append(cur); cur = [w]
    else:
        cur.append(w)
segs.append(cur)

SRC_END = 38.549
edl, caps, t = [], [], 0.0
for k, s in enumerate(segs):
    a = max(0.0, s[0]["start"] - PRE)
    b = min(SRC_END, s[-1]["end"] + POST)
    # never overlap the next segment's handle
    if k + 1 < len(segs):
        b = min(b, segs[k + 1][0]["start"] - PRE)
    a, b = round(a, 3), round(b, 3)
    edl.append({"id": f"seg{k:02d}", "src_in": a, "src_out": b, "start": round(t, 3),
                "dur": round(b - a, 3), "text": " ".join(w["text"] for w in s)})
    for w in s:
        caps.append({"text": w["text"], "start": round(t + w["start"] - a, 3),
                     "end": round(t + w["end"] - a, 3)})
    t += b - a

json.dump(edl, open(HERE / "edl.json", "w"), indent=1)
json.dump(caps, open(HERE / "captions.json", "w"), indent=1)
for e in edl:
    print(f"{e['id']} t={e['start']:6.2f} dur={e['dur']:5.2f} src={e['src_in']:6.2f}-{e['src_out']:6.2f}  {e['text']}")
print(f"timeline: {t:.2f}s (raw {SRC_END}s), {len(edl)} cuts, {len(caps)} caption words")
