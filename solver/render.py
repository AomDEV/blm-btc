"""Multi-mode forensic renderer for the BLM puzzle image."""
import numpy as np, os
from PIL import Image, ImageFilter, ImageOps

SRC = "/Users/aom/Desktop/Workspace/claude/blm-btc/BLM_0.2BTC/pictures/n1x7g8ceaur51.png"
OUT = "/Users/aom/Desktop/Workspace/claude/blm-btc/solver/forensics"
RGB = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
GRAY = RGB.mean(2)

def _blur(x, r):
    return np.asarray(Image.fromarray(np.clip(x, 0, 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(r))).astype(np.float32)

def mode_z(box, r=9):
    """Local z-score: pulls faint low-contrast strokes out of any background level."""
    x0, y0, x1, y1 = box
    g = GRAY[y0:y1, x0:x1]
    mu = _blur(g, r); d = g - mu
    sd = np.sqrt(np.maximum(_blur(d * d, r), 1.0))
    z = d / np.maximum(sd, 2.0)
    return np.clip(128 - z * 60, 0, 255).astype(np.uint8)

def mode_sat(box):
    """Saturation map: colour-coded text on grey reads as bright."""
    x0, y0, x1, y1 = box
    a = RGB[y0:y1, x0:x1]
    s = a.max(2) - a.min(2)
    s = s / max(s.max(), 1e-6) * 255
    return np.clip(255 - s * 2.2, 0, 255).astype(np.uint8)

def mode_hi(box):
    """Light-band level slice: near-white-on-white lettering."""
    x0, y0, x1, y1 = box
    g = GRAY[y0:y1, x0:x1]
    lo, hi = np.percentile(g, 62), np.percentile(g, 99.4)
    return np.clip(255 - (g - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)

def mode_edge(box):
    """Unsharp edge map: outlines faint shapes and counts."""
    x0, y0, x1, y1 = box
    g = GRAY[y0:y1, x0:x1]
    e = np.abs(g - _blur(g, 2.0))
    e = e / max(e.max(), 1e-6) * 255
    return np.clip(255 - e * 3.0, 0, 255).astype(np.uint8)

MODES = {"z": mode_z, "sat": mode_sat, "hi": mode_hi, "edge": mode_edge}

def render(name, box, modes=("z", "sat", "hi"), long_side=1400):
    x0, y0, x1, y1 = box
    sc = long_side / max(x1 - x0, y1 - y0)
    paths = []
    for m in modes:
        arr = MODES[m](box)
        im = Image.fromarray(arr)
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        p = os.path.join(OUT, f"{name}__{m}.png")
        im.save(p); paths.append(p)
    return paths

REGIONS = {
 "A_people_chart_covid":   (30,  25,  560, 430),
 "B_seedtext_flag_stop":   (300, 25,  900, 580),
 "C_floyd_blm_cameras":    (890, 25,  1400, 470),
 "D_runecol_leopold":      (1270,25,  1600, 1180),
 "E_bravenewworld":        (420, 375, 1060, 730),
 "F_liberty_address":      (25,  400, 400, 1185),
 "G_clock_seal":           (245, 685, 930, 1195),
 "H_trump_map_latin":      (790, 690, 1400, 1195),
}

if __name__ == "__main__":
    for n, b in REGIONS.items():
        ps = render(n, b)
        print(n, b, "->", len(ps), "files")
