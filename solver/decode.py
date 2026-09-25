import numpy as np
from PIL import Image, ImageOps

IM = Image.open("/Users/aom/Desktop/Workspace/claude/blm-btc/BLM_0.2BTC/pictures/n1x7g8ceaur51.png").convert("L")

def mask_of(box, rot=0, pct=42, up=1):
    x0,y0,x1,y1 = box
    im = IM.crop((x0,y0,x1,y1))
    if rot: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    if up > 1: im = im.resize((im.width*up, im.height*up), Image.LANCZOS)
    a = np.asarray(ImageOps.autocontrast(im)).astype(np.float32)
    return a < np.percentile(a, pct)

def runs_of(m):
    col = m.sum(0); on = col > 0
    out=[]; s=None
    for i,v in enumerate(on):
        if v and s is None: s=i
        elif not v and s is not None: out.append((s,i)); s=None
    if s is not None: out.append((s,len(on)))
    return out

def split_group(m, a, b, n):
    """Split columns [a,b) into exactly n glyphs at the n-1 lowest-ink columns."""
    if n == 1: return [(a,b)]
    col = m[:, a:b].sum(0).astype(float)
    W = b - a
    cuts=[]
    forbidden = np.zeros(W, bool)
    minsep = max(3, W // (n * 3))
    forbidden[:minsep] = True; forbidden[-minsep:] = True
    for _ in range(n - 1):
        c = np.where(forbidden, 1e9, col)
        k = int(np.argmin(c))
        cuts.append(k)
        lo, hi = max(0, k - minsep), min(W, k + minsep + 1)
        forbidden[lo:hi] = True
    cuts = sorted(cuts)
    bounds = [0] + cuts + [W]
    return [(a + bounds[i], a + bounds[i+1]) for i in range(n)]

def norm(m, a, b, H=26, W=20):
    sub = m[:, a:b]
    rows = np.where(sub.any(1))[0]
    if len(rows)==0: return np.zeros((H,W), bool)
    sub = sub[rows.min():rows.max()+1]
    cols = np.where(sub.any(0))[0]
    sub = sub[:, cols.min():cols.max()+1]
    im = Image.fromarray((sub*255).astype(np.uint8)).resize((W,H), Image.BILINEAR)
    return np.asarray(im) > 110

def d(a,b): return float((a ^ b).mean())
