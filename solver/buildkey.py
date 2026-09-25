"""Build the full glyph->Cyrillic key from every CONFIRMED inscription,
then classify the one unknown glyph."""
import sys; sys.path.insert(0,'/Users/aom/Desktop/Workspace/claude/blm-btc/solver')
from decode import *
import numpy as np, pickle

TRAIN = []
# 1. top three lines (43 glyphs) - confirmed by 4 blind structural predictions
TRAIN += [((204,43,447,64),25,[((0,1),1,"Я"),((2,9),7,"надеюсь"),((10,12),3,"что"),((13,16),4,"сюда")]),
          ((195,68,386,88),25,[((0,4),5,"будут"),((5,14),9,"присылать")]),
          ((199,86,372,108),18,[((0,5),5,"много"),((6,15),9,"биткоинов")])]
# 2. clock rune (14 glyphs) - confirmed by internal repeat structure
TRAIN += [((264,1022,332,1041),25,[((0,99),5,"сумма")]),
          ((338,1022,387,1041),25,[((0,99),4,"двух")]),
          ((392,1022,442,1041),25,[((0,99),5,"чисел")])]

# 3. right-hand column groups 1-7 (41 glyphs) - plaintext now confirmed letter-by-letter.
#    Group 8 (the unknown X) is DELIBERATELY EXCLUDED from training.
COL = [(917,1014,"здесь"),(646,899,"зашифрованы"),(458,633,"биткоины"),(402,443,"на"),
       (253,389,"чёрный"),(154,239,"день"),(64,141,"номер")]

def build():
    key={}
    for box,pct,groups in TRAIN:
        m=mask_of(box,pct=pct,up=5); r=runs_of(m)
        for (i0,i1),n,letters in groups:
            a,b=(r[i0][0],r[i1-1][1]) if i1<=len(r) else (r[0][0],r[-1][1])
            for (pa,pb),ch in zip(split_group(m,a,b,n),letters):
                key.setdefault(ch.lower(),[]).append(norm(m,pa,pb))
    for y0,y1,word in COL:
        m=mask_of((1529,y0-1,1555,y1+1),rot=-90,pct=32,up=5); r=runs_of(m)
        a,b=r[0][0],r[-1][1]
        for (pa,pb),ch in zip(split_group(m,a,b,len(word)),word):
            key.setdefault(ch,[]).append(norm(m,pa,pb))
    return key

def classify(g,key):
    return sorted((min(d(g,t) for t in ts),ch) for ch,ts in key.items())

if __name__=="__main__":
    key=build()
    n=sum(len(v) for v in key.values())
    print(f"key built from {n} labelled glyphs, {len(key)} distinct letters:")
    print("  "+''.join(sorted(key)))
    print("  letters gained vs crib-only: " + ''.join(sorted(set(key)-set("Яабвгдеиклмнопрстухчыью".lower()))))
    pickle.dump(key,open('fullkey.pkl','wb'))
