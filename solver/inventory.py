"""Complete evidence-graded BIP39 word inventory for the BLM puzzle.
Grade 3 = the word is written as literal text in the image (strongest).
Grade 2 = the plain name of an unmistakable object, or a strongly marked concept.
Grade 1 = plausible but a naming choice, or buried in the whitepaper micrography.
"""
INV = [
 # ---- grade 3: literally written in the picture ----
 (3,"moon",     "written along a clock hand", "(381,882)"),
 (3,"tower",    "written along a clock hand", "(417,851)"),
 (3,"food",     "written down the Space Needle elevator shaft", "(1188-1212,653-679)"),
 (3,"real",     "'ONLY real BITCOIN', deliberately lower-case between capitals", "(98-231,1051-1062)"),
 (3,"black",    "'BLACK' - line 1 of the slogan block", "(1118-1138,194-289)"),
 (3,"police",   "'END POLICE BRUTALITY' - line 5", "(1232-1251,47-365)"),
 (3,"subject",  "underlined in the 13th Amendment engraving", "(1402-1447,896-906)"),
 (3,"matter",   "'MATTER' - line 3", "(1173-1196,204-337)"),
 (3,"peace",    "'NO JUSTICE NO PEACE' - line 4", "(1202-1223,120-417)"),
 (3,"end",      "'END POLICE BRUTALITY' - line 5", "(1232-1251,47-365)"),
 (3,"one",      "'NOT ONE MORE' - line 7", "(1291-1309,162-385)"),
 (3,"more",     "'NOT ONE MORE' - line 7", "(1291-1309,162-385)"),
 (3,"welcome",  "'WELCOME TO THE' micrography headline", "(524-922,408-462)"),
 (3,"brave",    "'BRAVE' micrography", "(524-958,468-592)"),
 (3,"world",    "'NEW WORLD' micrography", "(434-1065,592-700)"),
 (3,"order",    "'Order and stability', the camera's sight-line target", "(672-996,75-108)"),
 (3,"section",  "'Section 1', underlined, in the engraving", "(1424-1432,813-822)"),
 (3,"find",     "giant background headline", "(568-865,45-152)"),
 (3,"seed",     "giant background headline", "(552-870,200-285)"),
 (3,"phrase",   "giant background headline", "(552-868,300-390)"),
 (3,"this",     "giant background headline ('THE THIS' - doubled article)", "(527-900,375-412)"),
 (3,"picture",  "giant background headline", "(527-900,375-412)"),
 (3,"sing",     "typo for 'sign' in the O of WORLD (BIP39->BIP39)", "(845-858,615-632)"),
 (3,"creek",    "typo for 'check' in the E of BRAVE (BIP39->BIP39)", "(890-915,534-544)"),
 (3,"crime",    "13th Amendment text", "(1315-1460,855-866)"),
 (3,"party",    "13th Amendment text", "(1315-1460,866-876)"),
 (3,"exist",    "13th Amendment text", "(1315-1460,876-886)"),
 (3,"place",    "13th Amendment text ('or any place subject to')", "(1315-1460,896-906)"),
 # ---- grade 2: unmistakable object, or strongly marked ----
 (2,"camera",   "two CCTV cameras", "(1290-1520,60-220)"),
 (2,"mask",     "four masked faces", "(55-560,30-260)"),
 (2,"eye",      "eye-in-triangle on the junction box; the Great Seal's eye", "(1412-1436,190-212)"),
 (2,"pyramid",  "the Great Seal's uncapped pyramid", "(560-740,894-1022)"),
 (2,"glove",    "gloved hand holding the CVD19 vial", "(55-160,200-320)"),
 (2,"rifle",    "M16 aimed at China", "(802-900,700-780)"),
 (2,"flag",     "Pan-African/US flag, 44 stars + 13 stripes", "(155-400,180-470)"),
 (2,"liberty",  "the Statue of Liberty", "(90-280,520-1110)"),
 (2,"clock",    "the large dial", "(287-655,756-1124)"),
 (2,"gold",     "the 17-year gold price chart", "(0-560,240-460)"),
 (2,"vote",     "the election panel; '.VS.' = 12 under vertical flip", "(1021-1089,1055-1088)"),
 (2,"second",   "Leopold II, 'XX' on the head", "(1358-1428,440-475)"),
 (2,"power",    "the raised Black Power fist in the STOP roundel", "(70-147,460-517)"),
 (2,"future",   "'PAY FOR THE FUTURE.' on the pedestal", "(78-86,869-1025)"),
 (2,"predict",  "'THIS IS THE FIRST PREDICTION.'", "(94-108,833-1029)"),
 (2,"first",    "'THIS IS THE FIRST PREDICTION.'", "(94-108,833-1029)"),
 (2,"payment",  "'PAY FOR THE FUTURE.'", "(78-86,869-1025)"),
 (2,"green",    "the unique colour of slogan line 6 (the only serif, oversized line)", "(1257-1288,96-425)"),
 (2,"blue",     "the colour of slogan line 4", "(1202-1223,120-417)"),
 (2,"space",    "the Space Needle", "(1090-1300,330-1000)"),
 (2,"need",     "the Space Needle", "(1090-1300,330-1000)"),
 (2,"hand",     "the gloved hand; the raised fist", "(55-160,200-320)"),
 (2,"brick",    "the pyramid's 13 brick courses", "(560-740,894-1022)"),
 (2,"book",     "the book/block stack under the statue", "(98-231,1045-1157)"),
 # ---- grade 1: plausible naming, or whitepaper micrography ----
 (1,"gun",      "the rifle", "(802-900,700-780)"),
 (1,"weapon",   "the rifle", "(802-900,700-780)"),
 (1,"trade",    "the US-China trade-war motif", "(880-1120,695-812)"),
 (1,"deal",     "the trade-war motif", "(880-1120,695-812)"),
 (1,"life",     "'BLACK LIVES MATTER' (list has 'life', not 'lives')", "(1148-1168,215-303)"),
 (1,"security", "the surveillance motif", "(1290-1520,60-220)"),
 (1,"news",     "the COVID/5G graffiti", "(45-140,352-405)"),
 (1,"phone",    "the 5G claim", "(45-140,352-405)"),
 (1,"mobile",   "the 5G claim", "(45-140,352-405)"),
 (1,"debate",   "the Trump/Biden face-off", "(850-1250,780-1160)"),
 (1,"price",    "the chart", "(0-560,240-460)"),
 (1,"axis",     "the chart's y-axis", "(12-45,245-535)"),
 (1,"maximum",  "the chart's peak", "(0-560,240-460)"),
 (1,"minimum",  "the chart's trough", "(0-560,240-460)"),
 (1,"proof",    "whitepaper band, misspelled 'proot'", "(400-428,1148-1168)"),
 (1,"receive",  "whitepaper band", "(790-1010,1148-1168)"),
 (1,"major",    "whitepaper band ('the majority of nodes')", "(790-1010,1148-1168)"),
 (1,"agree",    "whitepaper micrography", "(420-1060,375-730)"),
 (1,"history",  "whitepaper micrography", "(892-922,408-462)"),
 (1,"trust",    "whitepaper micrography", "(420-1060,375-730)"),
 (1,"coin",     "whitepaper micrography", "(420-1060,375-730)"),
 (1,"double",   "whitepaper micrography", "(926-960,565-580)"),
 (1,"model",    "whitepaper micrography ('mint based model')", "(555-575,425-440)"),
 (1,"paper",    "the Bitcoin whitepaper itself", "(420-1060,375-730)"),
 (1,"verb",     "'proverb' - the pot-and-kettle Latin line", "(1045-1468,1166-1186)"),
 (1,"accuse",   "the pot calling the kettle black", "(1045-1468,1166-1186)"),
 (1,"fire",     "the pot/kettle motif", "(1045-1468,1166-1186)"),
 (1,"punch",    "the fist", "(70-147,460-517)"),
 (1,"twin",     "the two cameras are a matched pair", "(1290-1520,60-220)"),
 (1,"city",     "the Seattle skyline", "(1090-1300,330-1000)"),
 (1,"state",    "'within the United States'", "(1315-1460,886-896)"),
 (1,"unit",     "'the United States'", "(1315-1460,886-896)"),
 (1,"two",      "two cameras, two candidates, 'sum of two numbers'", "-"),
 (1,"number",   "'sum of two numbers' rune", "(266-440,1024-1039)"),
]
if __name__ == "__main__":
    import blm
    from collections import Counter
    bad=[w for _,w,_,_ in INV if w not in blm.WIDX]
    seen=Counter(w for _,w,_,_ in INV)
    print(f"inventory: {len(INV)} entries, {len(seen)} distinct words")
    print("NOT in BIP39 (must be removed):", bad or "none")
    dup=[w for w,c in seen.items() if c>1]
    print("duplicates:", dup or "none")
    for g in (3,2,1):
        ws=sorted({w for gg,w,_,_ in INV if gg==g})
        print(f"\ngrade {g} ({len(ws)}): {' '.join(ws)}")
