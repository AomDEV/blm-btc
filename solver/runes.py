"""Rune cipher: build a glyph->Cyrillic key from the confirmed top-line crib,
then decode the other inscriptions."""
import numpy as np
from PIL import Image, ImageOps

SRC = "/Users/aom/Desktop/Workspace/claude/blm-btc/BLM_0.2BTC/pictures/n1x7g8ceaur51.png"
IM = Image.open(SRC).convert("L")

def binar(box, pad=3, thresh=None, upscale=6, rot=0):
    """Crop -> optional rotate -> normalise -> binary ink mask (True = ink)."""
    x0, y0, x1, y1 = box
    im = IM.crop((x0 - pad, y0 - pad, x1 + pad, y1 + pad))
    if rot: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    im = im.resize((im.width * upscale, im.height * upscale), Image.LANCZOS)
    a = np.asarray(ImageOps.autocontrast(im)).astype(np.float32)
    t = np.percentile(a, 35) if thresh is None else thresh
    return a < t

def segment(mask, min_gap=None, min_w=None):
    """Split an ink mask into glyph column-runs."""
    col = mask.sum(0)
    on = col > 0
    runs, s = [], None
    for i, v in enumerate(on):
        if v and s is None: s = i
        elif not v and s is not None:
            runs.append((s, i)); s = None
    if s is not None: runs.append((s, len(on)))
    if min_w:
        runs = [r for r in runs if r[1] - r[0] >= min_w]
    return runs

def glyph_imgs(mask, runs, H=28, W=22):
    """Normalise each column-run to a fixed-size bitmap for matching."""
    out = []
    for a, b in runs:
        sub = mask[:, a:b]
        rows = np.where(sub.any(1))[0]
        if len(rows) == 0: out.append(np.zeros((H, W), bool)); continue
        sub = sub[rows.min():rows.max() + 1]
        im = Image.fromarray((sub * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
        out.append(np.asarray(im) > 110)
    return out

def dist(a, b):
    return (a ^ b).mean()
