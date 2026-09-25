"""Thematically-justified BIP39 candidate words for the BLM puzzle, by source element."""
SOURCES = {
 "clock":        ["moon", "tower", "clock", "hour", "time"],
 "13th_amend":   ["subject", "slave"[:0] or "crime", "punish"[:0] or "wall", "section"[:0] or "exist", "duty", "party", "unit", "place", "state"],
 "blm_slogans":  ["black", "police", "peace", "life", "one", "more"[:0] or "brother", "matter"[:0] or "mother"],
 "cameras":      ["camera", "twin", "eye", "video", "security", "picture"],
 "masked_people":["mask", "face", "crowd", "family", "four", "group"[:0] or "gather"],
 "liberty":      ["liberty", "crown", "torch"[:0] or "candle", "seven", "island", "real", "future", "payment", "predict", "first"],
 "pyramid_seal": ["pyramid", "eye", "brick", "order", "cause", "justice"[:0] or "judge", "world", "seal"[:0] or "stamp"],
 "gold_chart":   ["gold", "price", "axis", "maximum", "minimum", "chart"[:0] or "graph"[:0] or "curve", "stock", "market"],
 "covid":        ["news", "phone", "mobile", "hoax"[:0] or "false", "virus"[:0] or "disease", "five", "nineteen"[:0] or "hospital"],
 "vaccine":      ["glove", "hand", "vaccine"[:0] or "doctor", "five", "finger", "inject"[:0] or "surgery"],
 "election":     ["vote", "debate", "tuesday"[:0] or "election"[:0] or "president", "flag", "russia"[:0] or "country"],
 "trade_war":    ["rifle", "gun", "weapon", "trade", "deal", "china"[:0] or "target", "war"[:0] or "army"],
 "brave_new":    ["world", "welcome", "brave", "paper", "novel"[:0] or "book", "order", "stable"[:0] or "stability"[:0] or "table"],
 "george_floyd": ["life", "police", "security", "knee"[:0] or "kidney", "breath"[:0] or "bread", "may"[:0] or "march"],
 "leopold":      ["second", "king", "bust"[:0] or "busy", "blood", "congo"[:0] or "cover", "twenty"[:0] or "twist"],
 "black_power":  ["power", "punch", "black", "fist"[:0] or "first", "stop"[:0] or "step", "flag", "unity"[:0] or "unit"],
 "whitepaper":   ["order", "proof", "first", "agree", "major", "receive", "trust", "history", "node"[:0] or "notable", "chain"],
 "space_needle": ["food", "space", "need", "eye", "tower", "city", "fair"[:0] or "faith"],
 "pot_kettle":   ["black", "fire", "accuse", "verb", "kitchen", "cook"[:0] or "cool"],
 "gravity_falls":["cipher"[:0] or "circle", "demon"[:0] or "dentist", "triangle"[:0] or "trigger", "gravity"[:0] or "grass"],
 "juneteenth":   ["flag", "june"[:0] or "jungle", "free"[:0] or "freedom"[:0] or "friend", "star"[:0] or "state", "green", "red"[:0] or "reduce"],
 "misc_numbers": ["two", "three", "seven", "eleven"[:0] or "elevator", "twelve"[:0] or "twenty"[:0] or "twist", "zero", "one", "sum"[:0] or "summer", "number"],
 "bitcoin":      ["bitcoin"[:0] or "coin", "real", "seed", "phrase", "find", "wallet", "address", "total", "key"[:0] or "kid"],
}

def build():
    import blm
    out, bad = [], []
    for k, ws in SOURCES.items():
        for w in ws:
            if not w: continue
            (out if w in blm.WIDX else bad).append(w)
    seen = set(); pool = []
    for w in out:
        if w not in seen: seen.add(w); pool.append(w)
    return sorted(pool), sorted(set(bad))

if __name__ == "__main__":
    p, b = build()
    print(f"POOL ({len(p)}):"); print(" ".join(p))
    if b: print(f"\nDROPPED not-in-BIP39 ({len(b)}): {' '.join(b)}")
