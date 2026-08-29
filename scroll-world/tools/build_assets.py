# -*- coding: utf-8 -*-
"""
NA Beauty Scroll World - asset pipeline.

Synthesizes cinematic camera-move segments FROM the real reference stills
(zoompan dollies/pans + animated-crop tilts), crossfade-chains each scene's
segments, and appends a short "bridge" hold of the NEXT scene's opening still
so consecutive scenes share an identical frame (seams disappear).

Scene 0 uses the existing AI-generated footage (door approach + entrance
push-in). Nothing is invented anywhere.

Output: assets/scenes/scene-N/f_XXXX.webp @12fps + poster.jpg + manifest.json
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT.parent / "processed"
DOWNLOADS = Path(r"C:\Users\yasam\Downloads\nabeauty")
CLIPS = ROOT / "assets" / "clips"
SCENES_DIR = ROOT / "assets" / "scenes"
BUILD = ROOT / "build"

W, H, FPS = 1280, 720, 24
FADE = 0.6          # crossfade seconds between chained segments
EXTRACT_FPS = 12    # scroll-scrub playback rate
WEBP_Q = 82


def run(cmd):
    p = subprocess.run([str(c) for c in cmd], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n  "
                           + " ".join(str(c) for c in cmd) + "\n" + p.stderr[-2500:])


def probe_size(path):
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,duration", "-of", "json", str(path)],
        capture_output=True, text=True)
    info = json.loads(p.stdout)["streams"][0]
    return int(info["width"]), int(info["height"]), float(info.get("duration") or 0)


def resolve_folders():
    roles = {}
    for d in sorted(PROCESSED.iterdir()):
        if not d.is_dir():
            continue
        names = {f.name for f in d.iterdir()}
        if "page-002.png" in names and "page-029.png" in names:
            roles["br"] = d
        elif "page-049.png" in names:
            roles["f2"] = d
        else:
            roles["g"] = d
    if set(roles) != {"br", "g", "f2"}:
        raise SystemExit(f"folder resolution failed: {roles}")
    return roles


FOLDERS = resolve_folders()


def st(key, name):
    return str(FOLDERS[key] / name)


def even(x):
    return int(x) // 2 * 2


# ------------------------------------------------------------- segments

def slice_crop_filter(img_path, cy, big_w):
    """scale to big_w wide, then crop full-width 16:9 slice at focus_y."""
    iw, ih, _ = probe_size(img_path)
    sh = even(big_w * ih / iw)
    ch = even(big_w * 9 / 16)
    y_px = int(round(max(0.0, min(1.0, cy)) * (sh - ch)))
    return f"scale={even(big_w)}:-2,crop={even(big_w)}:{ch}:0:{y_px}"


def seg_zoompan(out_file, shot):
    img, dur, kind = shot["img"], float(shot["dur"]), shot["move"]
    n = int(round(dur * FPS))
    cy = shot.get("cy", 0.5)

    pre = slice_crop_filter(img, cy, 4500)

    z0 = z1 = 1.001
    if kind == "dolly_in":
        z0, z1 = shot.get("z0", 1.0), shot.get("z1", 1.2)
    elif kind == "dolly_out":
        z0, z1 = shot.get("z0", 1.2), shot.get("z1", 1.0)
    elif kind == "pan_r":
        z0 = z1 = shot.get("zoom", 1.15)
    elif kind == "pan_l":
        z0 = z1 = shot.get("zoom", 1.15)

    zf = f"{z0}+({z1}-{z0})*on/{n}"
    slack = 1 - 1 / z0
    if kind == "pan_r":
        xf = f"(iw-iw/zoom)*({slack}*on/{n})"
    elif kind == "pan_l":
        xf = f"(iw-iw/zoom)*({slack}-{slack}*on/{n})"
    else:
        xf = "(iw-iw/zoom)/2"
    yf = "(ih-ih/zoom)/2"

    vf = f"{pre},zoompan=z='{zf}':x='{xf}':y='{yf}':d={n}:s={W}x{H}:fps={FPS},format=yuv420p"
    run(["ffmpeg", "-y", "-i", img, "-vf", vf, "-frames:v", n,
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", out_file])


def seg_tilt(out_file, shot):
    """Tall portrait still -> animated vertical travel via moving crop."""
    img, dur = shot["img"], float(shot["dur"])
    n = int(round(dur * FPS))
    iw, ih, _ = probe_size(img)
    bw = even(iw * 4)
    sh = even(bw * ih / iw)
    ch = even(bw * 9 / 16)
    if shot["move"] == "tilt_up":     # bottom -> top
        yexpr = f"({sh}-{ch})*(1-t/{dur})"
    else:                             # tilt_down: top -> bottom
        yexpr = f"({sh}-{ch})*(t/{dur})"
    vf = (f"scale={bw}:-2,fps={FPS},crop={bw}:{ch}:0:'{yexpr}',"
          f"scale={W}:{H},format=yuv420p")
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", FPS, "-t", dur, "-i", img,
         "-vf", vf, "-frames:v", n,
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", out_file])


def make_segment(out_file, shot):
    if Path(out_file).exists():
        return False
    if shot["move"].startswith("tilt"):
        seg_tilt(out_file, shot)
    else:
        seg_zoompan(out_file, shot)
    return True


def chain(files, durs, out_file, fade=FADE):
    if len(files) == 1:
        Path(files[0]).replace(out_file)
        return
    inputs = []
    for f in files:
        inputs += ["-i", str(f)]
    fc, off = [], 0.0
    for i in range(len(files) - 1):
        off += durs[i] - fade
        a = "[0:v]" if i == 0 else f"[v{i}]"
        fc.append(f"{a}[{i + 1}:v]xfade=transition=fade:"
                  f"duration={fade}:offset={off:.3f}[v{i + 1}]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc),
         "-map", f"[v{len(files) - 1}]", "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", str(out_file)])


def extract(scene_id, clip):
    outdir = SCENES_DIR / f"scene-{scene_id}"
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("*.*"):
        old.unlink()
    run(["ffmpeg", "-y", "-i", str(clip), "-vf", f"fps={EXTRACT_FPS}",
         "-c:v", "libwebp", "-quality", WEBP_Q, "-compression_level", "5",
         str(outdir / "f_%04d.webp")])
    run(["ffmpeg", "-y", "-i", str(clip), "-vframes", "1", "-q:v", "4",
         str(outdir / "poster.jpg")])
    return len(list(outdir.glob("f_*.webp")))


# ------------------------------------------------------------- scenes

SCENES = [
    dict(id=1, shots=[
        dict(img=st("g", "page-005.png"), move="dolly_in", z0=1.0, z1=1.20, dur=6, cy=.52),
        dict(img=st("g", "page-017.png"), move="pan_r", zoom=1.15, dur=6),
        dict(img=st("g", "page-023.png"), move="dolly_in", z0=1.0, z1=1.15, dur=5),
    ], bridge=("g", "page-035.png")),
    dict(id=2, shots=[
        dict(img=st("g", "page-035.png"), move="dolly_in", z0=1.0, z1=1.22, dur=6),
        dict(img=st("g", "page-037.png"), move="pan_l", zoom=1.15, dur=5),
        dict(img=st("g", "page-042.png"), move="dolly_in", z0=1.0, z1=1.15, dur=5),
    ], bridge=("g", "page-044.png")),
    dict(id=3, shots=[
        dict(img=st("g", "page-044.png"), move="dolly_in", z0=1.0, z1=1.28, dur=8),
    ], bridge=("g", "page-011.png")),
    dict(id=4, shots=[
        dict(img=st("g", "page-011.png"), move="tilt_up", dur=6),
        dict(img=st("f2", "page-003.png"), move="tilt_down", dur=6),
        dict(img=st("f2", "page-004.png"), move="dolly_in", z0=1.0, z1=1.18, dur=5),
    ], bridge=("f2", "page-017.png")),
    dict(id=5, shots=[
        dict(img=st("f2", "page-017.png"), move="dolly_in", z0=1.0, z1=1.18, dur=5),
        dict(img=st("f2", "page-039.png"), move="pan_r", zoom=1.15, dur=5),
        dict(img=st("f2", "page-040.png"), move="dolly_in", z0=1.0, z1=1.15, dur=5),
    ], bridge=("f2", "page-031.png")),
    dict(id=6, shots=[
        dict(img=st("f2", "page-031.png"), move="dolly_in", z0=1.0, z1=1.20, dur=6),
        dict(img=st("f2", "page-032.png"), move="pan_l", zoom=1.15, dur=5),
        dict(img=st("f2", "page-041.png"), move="dolly_in", z0=1.0, z1=1.15, dur=5),
        dict(img=st("f2", "page-043.png"), move="dolly_in", z0=1.0, z1=1.22, dur=6),
    ], bridge=("br", "page-027.png")),
    dict(id=7, shots=[
        dict(img=st("br", "page-027.png"), move="dolly_in", z0=1.0, z1=1.15, dur=6),
        dict(img=st("br", "page-014.png"), move="dolly_in", z0=1.0, z1=1.08, dur=8),
    ], bridge=None),
]


def find_real_clips():
    clips = sorted(DOWNLOADS.glob("*.mp4"))
    if len(clips) < 2:
        raise SystemExit(f"expected 2 AI clips in {DOWNLOADS}, found {len(clips)}")
    # door clip first, then the entrance push-in (filename order works here)
    clips.sort(key=lambda p: (0 if "door" in p.name else 1, p.name))
    return clips[0], clips[1]


def build_scene(sc):
    sid = sc["id"]
    print(f"--- scene {sid}")
    segs, durs = [], []
    for i, shot in enumerate(sc["shots"]):
        f = BUILD / f"s{sid}_a{i}.mp4"
        made = make_segment(f, shot)
        print(f"    seg a{i}: {shot['move']} {shot['dur']}s {'(rendered)' if made else '(cached)'}")
        segs.append(f)
        durs.append(float(shot["dur"]))
    if sc["bridge"]:
        f = BUILD / f"s{sid}_bridge.mp4"
        made = make_segment(f, dict(img=st(*sc["bridge"]), move="hold", dur=1.6))
        print(f"    bridge -> {Path(st(*sc['bridge'])).name} {'(rendered)' if made else '(cached)'}")
        segs.append(f)
        durs.append(1.6)
    clip = CLIPS / f"scene-{sid}.mp4"
    chain(segs, durs, clip)
    frames = extract(sid, clip)
    total = sum(durs) - FADE * (len(segs) - 1)
    print(f"    => scene-{sid}.mp4 {total:.1f}s -> {frames} webp frames")


def build_scene0():
    print("--- scene 0 (real footage)")
    clip_a, clip_b = find_real_clips()
    _, _, da = probe_size(clip_a)
    _, _, db = probe_size(clip_b)
    bridge = BUILD / "s0_bridge.mp4"
    opener = SCENES[0]["shots"][0]["img"]
    make_segment(bridge, dict(img=opener, move="hold", dur=1.6))
    clip = CLIPS / "scene-0.mp4"
    chain([clip_a, clip_b, bridge], [da, db, 1.6], clip)
    frames = extract(0, clip)
    print(f"    => scene-0.mp4 ({da:.1f}s+{db:.1f}s footage + bridge) -> {frames} webp frames")


def write_manifest():
    scenes = []
    for d in sorted(SCENES_DIR.glob("scene-*")):
        frames = len(list(d.glob("f_*.webp")))
        if not frames:
            continue
        scenes.append({"id": int(d.name.split("-")[1]), "frames": frames,
                       "dur": round(frames / EXTRACT_FPS, 2)})
    manifest = {"fps": EXTRACT_FPS, "scenes": scenes}
    (SCENES_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    js = ("// generated by tools/build_assets.py -- do not edit\n"
          "window.NA_MANIFEST = " + json.dumps(manifest, indent=2) + ";")
    (ROOT / "src" / "data.js").write_text(js + "\n", "utf-8")
    print(f"manifest written: {len(scenes)} scenes, "
          f"{sum(s['frames'] for s in scenes)} frames")


if __name__ == "__main__":
    BUILD.mkdir(exist_ok=True)
    CLIPS.mkdir(parents=True, exist_ok=True)
    SCENES_DIR.mkdir(parents=True, exist_ok=True)

    only = None
    if "--only" in sys.argv:
        only = int(sys.argv[sys.argv.index("--only") + 1])

    if only in (None, 0):
        build_scene0()
    for sc in SCENES:
        if only is None or only == sc["id"]:
            build_scene(sc)
    write_manifest()
