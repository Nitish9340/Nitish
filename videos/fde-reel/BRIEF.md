---
workflow: general-video
flow: automation
storyboard: no
message: "The FDE (Forward Deployed Engineer) is the hardest, least-known job in tech, and demand is up 800%"
destination: instagram-reels
aspect: 1080x1920
language: en
length: 35s
---

## Intent

Re-edit the user's raw talking-head clip about Forward Deployed Engineers in the editing style
and energy of their reference Instagram reel: fast jump cuts, rotating layouts, one-word captions,
kinetic sans + serif headlines, stat boxes, music bed and SFX. "Keep my content original, but make
the editing, motion and sound feel equally engaging and professional."

## Assets

- raw.mp4 — the user's raw talking-head take (1080×1920, 38.5 s); the only picture/voice source.
- edit/raw_words.json — Vosk word timings (small-en model); corrected in edit/build_edl.py.
- assets/audio/*.wav — original music bed + SFX synthesized by edit/synth_audio.py.

## Customizations

- Style decoded from the reference reel; see STYLE.md.
- Motion-graphic scenes replace the reference's stock B-roll (no stock footage available).

## Notes

- Transcript came from a small offline model; a few words were corrected from context
  ("normal title", "Big companies are hiring", "not working from home", "army").
- Built end to end from the request as given (no storyboard pause).
