/*
 * blmc - BLM puzzle search engine in C.
 *
 * Per thread, over a contiguous partition of the template's combo space:
 *   enumerate -> BIP39 checksum (SHA-256) -> PBKDF2-HMAC-SHA512 (OpenSSL)
 *   -> BIP32 m/44'/0'/0'/0/i (HMAC-SHA512 + libsecp256k1) -> hash160 -> compare.
 * No queues, no coordinator: each thread owns [lo, hi) and just runs.
 *
 * Modes
 *   blmc --template FILE [--target HEX] [--naddr K] [--threads N]   search
 *   blmc --derive [--naddr K]        stdin: mnemonics; stdout: seed, master, hash160s
 *   blmc --template FILE --list      print every checksum-valid mnemonic (small spaces)
 *   blmc --template FILE --list-bin  the same as raw uint16 word indices, NW per survivor, to
 *                                    stdout - what cgpu.py feeds the GPU (no text round-trip)
 *   blmc --template FILE --count     print total and checksum-valid counts
 *   --passphrase STR                 BIP39 passphrase (salt = "mnemonic" || STR); default empty
 *   --passfile FILE                  sweep one passphrase per line against every survivor, in a
 *                                    SINGLE enumeration pass (vs one full re-run per passphrase)
 *   --part b/n | --part b..c/n       work only on parts b (to c) of the combo space split into n
 *                                    equal parts (cgpu.py gives the GPU some parts, the CPU the rest)
 *   --nochecksum                     derive EVERY combo, not only BIP39-checksum-valid ones (a wallet
 *                                    that imports a mnemonic without enforcing the checksum, e.g.
 *                                    Electrum's BIP39 import, accepts such phrases). 2^CS x the work.
 *   --compressed-only                default is to test the hash160 of BOTH the compressed (02/03)
 *                                    and the uncompressed (04) pubkey; a hit says key=uncompressed
 *   --paths std|ext                  std (default): m/44'/0'/0'/0/i, i < naddr. ext adds, per seed,
 *                                    m/44'/0'/0'/1/i, m/44'/0'/1'/0/i, m/0'/0/i, m/0/i, m, m/0'/0'/0'
 *                                    (~1.8x the per-seed cost; C engine only, the GPU kernel is std)
 *   blmc --selftest                  SHA-512 / PBKDF2 fast paths vs OpenSSL
 *   blmc --bench [--template T]      per-component cost on one core (PBKDF2 x1/x2/x4, EC, enumerator)
 *
 * Template syntax (same as solve.py): word | ? | {a|b|c}
 *
 * Build: see build.sh. Tested differentially against the Python reference
 * (test_blmc.py) on seed, master key, chain code, and every address.
 */
#include <stdio.h>
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdatomic.h>
#include <pthread.h>
#include <unistd.h>
#include <time.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <secp256k1.h>
#include "sha512_fast.h"
#include "sha256_fast.h"
#include <openssl/ripemd.h>

#define MAXW 24
#define NWORDS 2048
#define MAXLINE 256

static char wordlist[NWORDS][16];
static int  wordlen[NWORDS];

/* ------------------------------------------------------------------ util */
static void die(const char *m) { fprintf(stderr, "blmc: %s\n", m); exit(2); }

static int word_index(const char *w) {
    for (int i = 0; i < NWORDS; i++) if (strcmp(wordlist[i], w) == 0) return i;
    return -1;
}

static void load_wordlist(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) die("cannot open wordlist");
    char line[64]; int n = 0;
    while (n < NWORDS && fgets(line, sizeof line, f)) {
        size_t L = strcspn(line, "\r\n"); line[L] = 0;
        if (!L) continue;
        if (L > 15) die("wordlist word too long");
        strcpy(wordlist[n], line); wordlen[n] = (int)L; n++;
    }
    fclose(f);
    if (n != NWORDS) die("wordlist must have 2048 words");
}

static int hexval(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
static void parse_hex20(const char *s, uint8_t out[20]) {
    if (strlen(s) != 40) die("target must be 40 hex chars (hash160)");
    for (int i = 0; i < 20; i++) {
        int a = hexval(s[2*i]), b = hexval(s[2*i+1]);
        if (a < 0 || b < 0) die("bad hex in target");
        out[i] = (uint8_t)(a * 16 + b);
    }
}
static void hex(const uint8_t *b, int n, char *out) {
    static const char *h = "0123456789abcdef";
    for (int i = 0; i < n; i++) { out[2*i] = h[b[i] >> 4]; out[2*i+1] = h[b[i] & 15]; }
    out[2*n] = 0;
}

/* --------------------------------------------------------------- crypto */
static void hash160(const uint8_t *d, size_t n, uint8_t out[20]) {
    uint8_t s[32];
    if (n <= 55) sha256_short(d, n, s); else SHA256(d, n, s);   /* 33-byte pubkey: HW SHA-256 unit */
    RIPEMD160(s, 32, out);                                       /* legacy one-shot: no provider fetch */
}
static void hmac512(const uint8_t *key, size_t klen, const uint8_t *d, size_t n, uint8_t out[64]) {
    if (klen > 128 || n > 111) die("hmac512: unsupported size");
    hmac512_small(key, klen, d, n, out);
}
/* BIP39 seed: PBKDF2-HMAC-SHA512 with HMAC midstates on the ARMv8 SHA-512 unit (sha512_fast.h).
 * Keys > 128 bytes (21/24-word mnemonics) are pre-hashed per RFC 2104, same as OpenSSL. */
static void bip39_seed(const char *mnemonic, size_t mlen, uint8_t seed[64]) {
    const uint8_t *m = (const uint8_t *)mnemonic; uint8_t (*sd)[64] = (uint8_t (*)[64])seed;
    pbkdf2_bip39_x1(&m, &mlen, sd);
}
/* Interleave width. `--bench` on an M3 measures 43.5 ns/block at x2 and 44.1 at x4: the SHA-512
 * unit saturates at two streams, so 2 is the default (same rate, half the register pressure and
 * half the partial-batch waste). Override with -DNWAY=4 to re-measure on other silicon. */
#ifndef NWAY
#define NWAY 2
#endif
#define BLM_CAT_(a, b) a##b
#define BLM_CAT(a, b) BLM_CAT_(a, b)
#define pbkdf2_bip39_xN BLM_CAT(pbkdf2_bip39_x, NWAY)
#define pbkdf2_mid_xN   BLM_CAT(pbkdf2_mid_x, NWAY)

typedef struct { uint8_t k[32]; uint8_t c[32]; } xkey;

static void master_from_seed(const uint8_t seed[64], xkey *m) {
    uint8_t I[64];
    hmac512((const uint8_t *)"Bitcoin seed", 12, seed, 64, I);
    memcpy(m->k, I, 32); memcpy(m->c, I + 32, 32);
}
/* returns 0 on the (astronomically rare) invalid child; caller must skip */
static int ckd_hard(secp256k1_context *ctx, const xkey *p, uint32_t i, xkey *ch) {
    uint8_t data[37], I[64];
    data[0] = 0; memcpy(data + 1, p->k, 32);
    i |= 0x80000000u;
    data[33] = i >> 24; data[34] = i >> 16; data[35] = i >> 8; data[36] = i;
    hmac512(p->c, 32, data, 37, I);
    memcpy(ch->k, p->k, 32);
    if (!secp256k1_ec_seckey_tweak_add(ctx, ch->k, I)) return 0;
    memcpy(ch->c, I + 32, 32);
    return 1;
}
static int pubkey33(secp256k1_context *ctx, const uint8_t k[32], uint8_t out[33]) {
    secp256k1_pubkey pk; size_t L = 33;
    if (!secp256k1_ec_pubkey_create(ctx, &pk, k)) return 0;
    secp256k1_ec_pubkey_serialize(ctx, out, &L, &pk, SECP256K1_EC_COMPRESSED);
    return 1;
}
/* both serialisations of one pubkey: the EC mult is paid once, the 65-byte form is a copy */
static int pubkey_both(secp256k1_context *ctx, const uint8_t k[32], uint8_t c33[33], uint8_t u65[65]) {
    secp256k1_pubkey pk; size_t L = 33;
    if (!secp256k1_ec_pubkey_create(ctx, &pk, k)) return 0;
    secp256k1_ec_pubkey_serialize(ctx, c33, &L, &pk, SECP256K1_EC_COMPRESSED);
    L = 65; secp256k1_ec_pubkey_serialize(ctx, u65, &L, &pk, SECP256K1_EC_UNCOMPRESSED);
    return 1;
}
/* normal CKD from a parent whose serialized pubkey the caller already has. Every leaf under
 * m/44'/0'/0'/0 shares one parent pubkey, so hoisting it out saves NADDR-1 EC mults per seed. */
static int ckd_normal_pub(secp256k1_context *ctx, const xkey *p, const uint8_t ppub[33], uint32_t i, xkey *ch) {
    uint8_t data[37], I[64];
    memcpy(data, ppub, 33);
    data[33] = i >> 24; data[34] = i >> 16; data[35] = i >> 8; data[36] = i;
    hmac512(p->c, 32, data, 37, I);
    memcpy(ch->k, p->k, 32);
    if (!secp256k1_ec_seckey_tweak_add(ctx, ch->k, I)) return 0;
    memcpy(ch->c, I + 32, 32);
    return 1;
}
static int ckd_normal(secp256k1_context *ctx, const xkey *p, uint32_t i, xkey *ch) {
    uint8_t ppub[33];
    if (!pubkey33(ctx, p->k, ppub)) return 0;
    return ckd_normal_pub(ctx, p, ppub, i, ch);
}
/* derive m/44'/0'/0'/0; returns 0 if any step invalid */
static int account_chain(secp256k1_context *ctx, const uint8_t seed[64], xkey *out) {
    xkey a, b;
    master_from_seed(seed, &a);
    if (!ckd_hard(ctx, &a, 44, &b)) return 0;
    if (!ckd_hard(ctx, &b, 0, &a)) return 0;
    if (!ckd_hard(ctx, &a, 0, &b)) return 0;
    if (!ckd_normal(ctx, &b, 0, out)) return 0;
    return 1;
}

/* -------------------------------------------------------------- template */
typedef struct { int n; uint16_t *idx; } slot;
static slot slots[MAXW]; static int NW = 0;
static int freeslot[MAXW]; static int NFREE = 0;      /* indices of slots with n > 1 */
static int CS, ENTB;                                   /* checksum bits, entropy bytes */
static uint8_t fixedbuf[33];                           /* packed fixed words */

static void clr11(uint8_t *buf, int pos) {              /* clear 11 bits at bit position pos */
    uint32_t w = 0x7ffu << (32 - 11 - (pos & 7));
    int byte = pos >> 3;
    buf[byte] &= (uint8_t)~(w >> 24); buf[byte + 1] &= (uint8_t)~(w >> 16); buf[byte + 2] &= (uint8_t)~(w >> 8);
}
static void put11(uint8_t *buf, int pos, uint32_t v) {  /* OR 11 bits at bit position pos, MSB-first */
    uint32_t w = v << (32 - 11 - (pos & 7));            /* align within a 32-bit window */
    int byte = pos >> 3;
    buf[byte]     |= (uint8_t)(w >> 24);
    buf[byte + 1] |= (uint8_t)(w >> 16);
    buf[byte + 2] |= (uint8_t)(w >> 8);
}

static void parse_template(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) die("cannot open template");
    char *text = NULL; size_t cap = 0, len = 0; int ch;
    while ((ch = fgetc(f)) != EOF) { if (len + 2 > cap) { cap = cap ? cap * 2 : 4096; text = realloc(text, cap); } text[len++] = (char)ch; }
    fclose(f); if (!text) die("empty template"); text[len] = 0;
    char *save = NULL;
    for (char *tok = strtok_r(text, " \t\r\n", &save); tok; tok = strtok_r(NULL, " \t\r\n", &save)) {
        if (NW >= MAXW) die("too many words");
        slot *s = &slots[NW];
        if (strcmp(tok, "?") == 0) {
            s->n = NWORDS; s->idx = malloc(NWORDS * sizeof(uint16_t));
            for (int i = 0; i < NWORDS; i++) s->idx[i] = (uint16_t)i;
        } else if (tok[0] == '{') {
            size_t L = strlen(tok); if (tok[L-1] != '}') die("bad {..} slot"); tok[L-1] = 0;
            int cnt = 1; for (char *p = tok + 1; *p; p++) if (*p == '|') cnt++;
            s->idx = malloc(cnt * sizeof(uint16_t)); s->n = 0;
            char *sv2 = NULL;
            for (char *w = strtok_r(tok + 1, "|", &sv2); w; w = strtok_r(NULL, "|", &sv2)) {
                int k = word_index(w); if (k < 0) { fprintf(stderr, "not a BIP39 word: %s\n", w); exit(2); }
                s->idx[s->n++] = (uint16_t)k;
            }
        } else {
            int k = word_index(tok); if (k < 0) { fprintf(stderr, "not a BIP39 word: %s\n", tok); exit(2); }
            s->n = 1; s->idx = malloc(sizeof(uint16_t)); s->idx[0] = (uint16_t)k;
        }
        NW++;
    }
    free(text);
    if (NW % 3 || NW < 3 || NW > 24) die("word count must be 12/15/18/21/24");
    CS = NW * 11 / 33; ENTB = (NW * 11 - CS) / 8;
    memset(fixedbuf, 0, sizeof fixedbuf);
    for (int i = 0; i < NW; i++) {
        if (slots[i].n == 1) put11(fixedbuf, 11 * i, slots[i].idx[0]);
        else freeslot[NFREE++] = i;
    }
}

static uint64_t space_size(void) {
    uint64_t n = 1;
    for (int j = 0; j < NFREE; j++) {
        uint64_t m = n * (uint64_t)slots[freeslot[j]].n;
        if (m / (uint64_t)slots[freeslot[j]].n != n) die("combo space overflows 64 bits");
        n = m;
    }
    return n;
}

/* checksum test on a packed buffer; returns 1 if valid */
static int checksum_ok(const uint8_t *buf) {
    uint8_t h[32]; sha256_short(buf, ENTB, h);
    return (h[0] >> (8 - CS)) == (buf[ENTB] >> (8 - CS));
}

/* build "w1 w2 ... wN" from a packed buffer; returns length */
static size_t build_mnemonic(const uint8_t *buf, char *out) {
    size_t L = 0;
    for (int i = 0; i < NW; i++) {
        int pos = 11 * i, byte = pos >> 3, sh = pos & 7;
        uint32_t w = ((uint32_t)buf[byte] << 16 | (uint32_t)buf[byte+1] << 8 | buf[byte+2]) >> (24 - 11 - sh);
        w &= 2047;
        memcpy(out + L, wordlist[w], wordlen[w]); L += wordlen[w];
        out[L++] = ' ';
    }
    out[--L] = 0;
    return L;
}

/* ------------------------------------------------------------ passphrases
 * A sweep tests every checksum-valid mnemonic against every candidate passphrase. The passphrase
 * is PBKDF2's salt, not its key, so nothing about the 2048 rounds can be shared between two
 * passphrases - but the enumeration, the checksum and the HMAC key midstate of the mnemonic are
 * computed once and reused across the whole list instead of once per passphrase per full re-run.
 * The table is built before any thread starts and is read-only afterwards. */
#define MAXPASS 100000
static pb_salt *psalt = NULL;          /* one prepared salt per passphrase */
static char   **pname = NULL;          /* the passphrase text, for hit reporting */
static int      NPASS = 1;             /* 1 = the single --passphrase (default empty) */

static void load_passfile(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) die("cannot open passphrase file");
    size_t cap = 256; NPASS = 0;
    psalt = malloc(cap * sizeof *psalt); pname = malloc(cap * sizeof *pname);
    if (!psalt || !pname) die("out of memory");
    char line[512];
    while (fgets(line, sizeof line, f)) {
        size_t L = strcspn(line, "\r\n"); line[L] = 0;
        /* blank and whitespace-only lines are skipped: a trailing newline must not silently add
         * an empty-passphrase pass. The no-passfile run already covers the empty passphrase. */
        int blank = 1; for (size_t q = 0; q < L; q++) if (!isspace((unsigned char)line[q])) { blank = 0; break; }
        if (blank) continue;
        if (NPASS == MAXPASS) die("too many passphrases");
        if ((size_t)NPASS == cap) { cap *= 2;
            psalt = realloc(psalt, cap * sizeof *psalt); pname = realloc(pname, cap * sizeof *pname);
            if (!psalt || !pname) die("out of memory"); }
        pb_salt_init(&psalt[NPASS], line);
        pname[NPASS] = strdup(line); if (!pname[NPASS]) die("out of memory");
        NPASS++;
    }
    fclose(f);
    if (!NPASS) die("passphrase file is empty");
}

/* ---------------------------------------------------------------- search */
static uint8_t target[20];
static int NADDR = 2;
static int UNC = 1;      /* also test the hash160 of the UNCOMPRESSED pubkey (--compressed-only turns it off) */
static int NOCHK = 0;    /* --nochecksum: derive every combo, not only the BIP39-checksum-valid ones */
static atomic_ullong combos_done = 0, seeds_done = 0;
static atomic_int stop_flag = 0, hits = 0;
static pthread_mutex_t hit_mu = PTHREAD_MUTEX_INITIALIZER;
static int list_mode = 0;

/* Work is handed out in chunks from one atomic cursor instead of split statically: on a 4P+4E
 * Apple part an E-core thread is ~4x slower than a P-core one, so an equal split leaves the fast
 * threads idle at the tail. Chunks are sized for ~256 checksum-valid seeds each. */
static atomic_ullong next_chunk = 0;
static uint64_t CHUNK = 1 << 16, G_LO = 0, G_HI = 0;

static void report_hit(const char *mn, const char *path, const char *pw, int unc) {
    char tail[640] = "";
    size_t o = 0;
    if (unc) o += (size_t)snprintf(tail + o, sizeof tail - o, " key=uncompressed");
    if (pw && *pw) snprintf(tail + o, sizeof tail - o, " passphrase='%s'", pw);
    pthread_mutex_lock(&hit_mu);
    printf("\n*** HIT *** '%s' path=%s%s [blmc]\n", mn, path, tail); fflush(stdout);
    const char *hf = getenv("BLM_HIT_FILE");            /* tests redirect; default is cwd/HIT.txt */
    FILE *f = fopen(hf && *hf ? hf : "HIT.txt", "a");
    if (f) { fprintf(f, "*** HIT *** '%s' path=%s%s [blmc]\n", mn, path, tail); fclose(f); }
    atomic_fetch_add(&hits, 1);
    atomic_store(&stop_flag, 1);
    pthread_mutex_unlock(&hit_mu);
}

/* test one private key: hash160 of the compressed pubkey, then (UNC) of the uncompressed one.
 * pfx is the path text; i >= 0 is appended to it ("m/44h/0h/0h/0/" + 1), i < 0 means pfx is complete. */
static int test_key(secp256k1_context *ctx, const uint8_t k[32], const char *mn, const char *pw, const char *pfx, int i) {
    uint8_t pub[33], upub[65], h[20]; char path[64];
    if (!pubkey_both(ctx, k, pub, upub)) return 0;
    hash160(pub, 33, h);
    int unc = 0;
    if (memcmp(h, target, 20) != 0) {
        if (!UNC) return 0;
        hash160(upub, 65, h);                         /* same point, 04||x||y: one more hash160, no EC work */
        if (memcmp(h, target, 20) != 0) return 0;
        unc = 1;
    }
    if (i >= 0) snprintf(path, sizeof path, "%s%d", pfx, i); else snprintf(path, sizeof path, "%s", pfx);
    report_hit(mn, path, pw, unc);
    return 1;
}

/* The extra derivations of --paths ext (each leaf i < NADDR, compressed + uncompressed):
 *   m/44'/0'/0'/1/i   BIP44 change chain           m/44'/0'/1'/0/i   BIP44 account 1
 *   m/0'/0/i          BIP32 default (BRD, MultiBit HD, early Copay/Bitcoin Wallet)
 *   m/0/i             bare BIP32 root chain (bip32.org, some scripts)
 *   m                 the master key itself         m/0'/0'/0'        Bitcoin Core style hardened
 * Costs ~14 extra EC mults per seed on top of the default 4, so ~1.8x the per-seed time. */
static int EXT = 0;

/* derive m/44'/0'/0'/0/i for i < NADDR from one seed and compare with the target */
static void check_seed(secp256k1_context *ctx, const uint8_t seed[64], const char *mn, const char *pw) {
    xkey m, a, b, acct, chain, t, u; uint8_t cpub[33];
    master_from_seed(seed, &m);
    if (!ckd_hard(ctx, &m, 44, &a) || !ckd_hard(ctx, &a, 0, &b) || !ckd_hard(ctx, &b, 0, &acct)) return;
    if (!ckd_normal(ctx, &acct, 0, &chain)) return;
    if (!pubkey33(ctx, chain.k, cpub)) return;        /* once; every leaf reuses it */
    for (int i = 0; i < NADDR; i++) {
        xkey leaf;
        if (!ckd_normal_pub(ctx, &chain, cpub, (uint32_t)i, &leaf)) continue;
        if (test_key(ctx, leaf.k, mn, pw, "m/44h/0h/0h/0/", i)) return;
    }
    if (!EXT) return;
    if (ckd_normal(ctx, &acct, 1, &t) && pubkey33(ctx, t.k, cpub))                                   /* m/44'/0'/0'/1/i */
        for (int i = 0; i < NADDR; i++) if (ckd_normal_pub(ctx, &t, cpub, (uint32_t)i, &u) && test_key(ctx, u.k, mn, pw, "m/44h/0h/0h/1/", i)) return;
    if (ckd_hard(ctx, &b, 1, &t) && ckd_normal(ctx, &t, 0, &u) && pubkey33(ctx, u.k, cpub))          /* m/44'/0'/1'/0/i */
        for (int i = 0; i < NADDR; i++) if (ckd_normal_pub(ctx, &u, cpub, (uint32_t)i, &t) && test_key(ctx, t.k, mn, pw, "m/44h/0h/1h/0/", i)) return;
    if (ckd_hard(ctx, &m, 0, &t) && ckd_normal(ctx, &t, 0, &u) && pubkey33(ctx, u.k, cpub))          /* m/0'/0/i */
        for (int i = 0; i < NADDR; i++) if (ckd_normal_pub(ctx, &u, cpub, (uint32_t)i, &t) && test_key(ctx, t.k, mn, pw, "m/0h/0/", i)) return;
    if (ckd_normal(ctx, &m, 0, &t) && pubkey33(ctx, t.k, cpub))                                      /* m/0/i */
        for (int i = 0; i < NADDR; i++) if (ckd_normal_pub(ctx, &t, cpub, (uint32_t)i, &u) && test_key(ctx, u.k, mn, pw, "m/0/", i)) return;
    if (test_key(ctx, m.k, mn, pw, "m", -1)) return;                                                 /* m */
    if (ckd_hard(ctx, &m, 0, &t) && ckd_hard(ctx, &t, 0, &u) && ckd_hard(ctx, &u, 0, &t))            /* m/0'/0'/0' */
        if (test_key(ctx, t.k, mn, pw, "m/0h/0h/0h", -1)) return;
}

/* One lane = one (mnemonic, passphrase) pair. With no --passfile there is a single passphrase and
 * this degenerates to the old "NWAY mnemonics" batch. */
typedef struct {
    char     mn[NWAY][MAXLINE];
    hmac_mid mid[NWAY];                     /* HMAC key midstate: one per mnemonic, reused across passphrases */
    int      pw[NWAY];                      /* index into psalt/pname */
    int      n;
} wbatch;

/* run PBKDF2 on the buffered pairs (NWAY interleaved when full) and check each */
static void flush_batch(secp256k1_context *ctx, wbatch *b) {
    uint8_t seed[NWAY][64];
    const pb_salt *sa[NWAY];
    for (int j = 0; j < b->n; j++) sa[j] = psalt ? &psalt[b->pw[j]] : &PB_DEFAULT;
    if (b->n == NWAY) pbkdf2_mid_xN(b->mid, sa, seed);
    else for (int j = 0; j < b->n; j++) pbkdf2_mid_x1(&b->mid[j], &sa[j], &seed[j]);
    for (int j = 0; j < b->n; j++) check_seed(ctx, seed[j], b->mn[j], pname ? pname[b->pw[j]] : NULL);
    atomic_fetch_add(&seeds_done, (uint64_t)b->n);
    b->n = 0;
}

static void *worker(void *arg) {
    (void)arg;
    secp256k1_context *ctx = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
    int digit[MAXW];
    uint8_t buf[33]; char mn[MAXLINE];
    wbatch B; B.n = 0;
    uint64_t local = 0, valid = 0;
    for (;;) {
        uint64_t off = atomic_fetch_add(&next_chunk, CHUNK);
        if (off >= G_HI - G_LO || atomic_load(&stop_flag)) break;
        uint64_t c = G_LO + off, end = c + CHUNK; if (end > G_HI) end = G_HI;
        /* mixed-radix decode of the chunk start: least-significant digit = last free slot */
        uint64_t rem = c;
        for (int j = NFREE - 1; j >= 0; j--) { int n = slots[freeslot[j]].n; digit[j] = (int)(rem % n); rem /= n; }
        memcpy(buf, fixedbuf, 33);
        for (int j = 0; j < NFREE; j++) put11(buf, 11 * freeslot[j], slots[freeslot[j]].idx[digit[j]]);
        for (; c < end; c++) {
            if (NOCHK || checksum_ok(buf)) {
                if (list_mode == 1) { build_mnemonic(buf, mn); pthread_mutex_lock(&hit_mu); puts(mn); pthread_mutex_unlock(&hit_mu); valid++; }
                else if (list_mode == 2) valid++;
                else if (list_mode == 3) {       /* raw uint16 indices: no formatting, no parsing */
                    uint16_t w[MAXW];
                    for (int i = 0; i < NW; i++) {
                        int bp = 11 * i, by = bp >> 3, sh = bp & 7;
                        w[i] = (uint16_t)((((uint32_t)buf[by] << 16 | (uint32_t)buf[by+1] << 8 | buf[by+2])
                                           >> (24 - 11 - sh)) & 2047);
                    }
                    fwrite(w, sizeof(uint16_t), (size_t)NW, stdout); valid++;
                }
                else {
                    char mnb[MAXLINE]; size_t L = build_mnemonic(buf, mnb);
                    hmac_mid mid; hmac_mid_init(&mid, (const uint8_t *)mnb, L);   /* once per mnemonic */
                    for (int q = 0; q < NPASS; q++) {
                        memcpy(B.mn[B.n], mnb, L + 1); B.mid[B.n] = mid; B.pw[B.n] = q;
                        if (++B.n == NWAY) flush_batch(ctx, &B);
                    }
                }
            }
            /* odometer increment; only the slots whose digit changed are re-packed */
            for (int j = NFREE - 1; j >= 0; j--) {
                int pos = 11 * freeslot[j]; clr11(buf, pos);
                if (++digit[j] < slots[freeslot[j]].n) { put11(buf, pos, slots[freeslot[j]].idx[digit[j]]); break; }
                digit[j] = 0; put11(buf, pos, slots[freeslot[j]].idx[0]);
            }
            if (++local == 4096) { atomic_fetch_add(&combos_done, local); local = 0;
                                   if (valid) { atomic_fetch_add(&seeds_done, valid); valid = 0; }
                                   if (atomic_load(&stop_flag)) break; }
        }
    }
    if (B.n) flush_batch(ctx, &B);
    atomic_fetch_add(&combos_done, local);
    if (valid) atomic_fetch_add(&seeds_done, valid);
    secp256k1_context_destroy(ctx);
    return NULL;
}

/* ------------------------------------------------------------ selftest */
static int selftest(void) {
    int bad = 0; srand(12345);
    /* compression vs OpenSSL on random states/blocks */
    for (int t = 0; t < 1000; t++) {
        uint8_t blk[128]; uint64_t st[8]; SHA512_CTX c; memset(&c, 0, sizeof c);
        for (int i = 0; i < 128; i++) blk[i] = (uint8_t)rand();
        for (int i = 0; i < 8; i++) { st[i] = ((uint64_t)rand() << 40) ^ ((uint64_t)rand() << 20) ^ (uint64_t)rand(); c.h[i] = st[i]; }
        sha512_compress(st, blk); SHA512_Transform(&c, blk);
        for (int i = 0; i < 8; i++) bad += st[i] != c.h[i];
    }
    printf("sha512 compress vs OpenSSL: %s\n", bad ? "MISMATCH" : "ok"); if (bad) return 1;
    /* PBKDF2 x1/x2/x4 vs OpenSSL for key lengths crossing the 128-byte pre-hash boundary */
    for (int n = 1; n <= 260; n += 3) {
        uint8_t k[4][260]; const uint8_t *mn[4]; size_t ml[4]; uint8_t ref[4][64], out[4][64];
        for (int j = 0; j < 4; j++) {
            ml[j] = (size_t)n + j; if (ml[j] > 260) ml[j] = 260; mn[j] = k[j];
            for (size_t i = 0; i < ml[j]; i++) k[j][i] = (uint8_t)('a' + rand() % 26);
            if (!PKCS5_PBKDF2_HMAC((const char *)k[j], (int)ml[j], (const uint8_t *)"mnemonic", 8, 2048, EVP_sha512(), 64, ref[j])) return 1;
        }
        pbkdf2_bip39_x4(mn, ml, out); bad += memcmp(out, ref, sizeof out) != 0;
        memset(out, 0, sizeof out); pbkdf2_bip39_x2(mn, ml, out); pbkdf2_bip39_x2(mn + 2, ml + 2, out + 2); bad += memcmp(out, ref, sizeof out) != 0;
        memset(out, 0, sizeof out); for (int j = 0; j < 4; j++) pbkdf2_bip39_x1(mn + j, ml + j, out + j); bad += memcmp(out, ref, sizeof out) != 0;
    }
    printf("pbkdf2 x1/x2/x4 vs OpenSSL (key lengths 1..260): %s\n", bad ? "MISMATCH" : "ok");
    { const char *pp[3] = {"TUESDAY", "a passphrase that is long enough to need a second SHA-512 block, more than one hundred and ten characters in total, yes", "I can't BREATHE"};
      for (int q = 0; q < 3 && !bad; q++) {
        char salt[256]; snprintf(salt, sizeof salt, "mnemonic%s", pp[q]); pbkdf2_set_passphrase(pp[q]);
        const char *K[4] = {"a b c", "legal winner thank year wave sausage worth useful legal winner thank yellow", "zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo vote", "x"};
        const uint8_t *mn[4]; size_t ml[4]; uint8_t ref[4][64], out[4][64];
        for (int j = 0; j < 4; j++) { mn[j] = (const uint8_t *)K[j]; ml[j] = strlen(K[j]);
          if (!PKCS5_PBKDF2_HMAC(K[j], (int)ml[j], (const uint8_t *)salt, (int)strlen(salt), 2048, EVP_sha512(), 64, ref[j])) return 1; }
        pbkdf2_bip39_x4(mn, ml, out); bad += memcmp(out, ref, sizeof out) != 0;
        memset(out, 0, sizeof out); pbkdf2_bip39_x2(mn, ml, out); pbkdf2_bip39_x2(mn + 2, ml + 2, out + 2); bad += memcmp(out, ref, sizeof out) != 0;
        memset(out, 0, sizeof out); for (int j = 0; j < 4; j++) pbkdf2_bip39_x1(mn + j, ml + j, out + j); bad += memcmp(out, ref, sizeof out) != 0;
      }
      pbkdf2_set_passphrase("");
      printf("pbkdf2 with passphrase salts (short, >111-byte, spaces) vs OpenSSL: %s\n", bad ? "MISMATCH" : "ok"); }
    /* per-lane salts: four DIFFERENT passphrases in the four interleaved lanes at once. A sweep
     * packs lanes this way, and a single global salt would pass every test above while being
     * wrong here, so this is the check that actually covers --passfile. */
    { const char *P4[4] = {"", "TUESDAY",
                           "a passphrase long enough that the salt needs a second SHA-512 block, which is more than one hundred and eleven bytes all told",
                           "I can't BREATHE"};
      const char *K4[4] = {"a b c", "legal winner thank year wave sausage worth useful legal winner thank yellow",
                           "zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo vote", "x"};
      pb_salt S[4]; const pb_salt *sp[4]; hmac_mid M[4]; uint8_t ref[4][64], out[4][64];
      for (int rot = 0; rot < 4 && !bad; rot++) {          /* rotate so every salt visits every lane */
          for (int j = 0; j < 4; j++) {
              const char *pw = P4[(j + rot) & 3]; char salt[300];
              snprintf(salt, sizeof salt, "mnemonic%s", pw);
              pb_salt_init(&S[j], pw); sp[j] = &S[j];
              hmac_mid_init(&M[j], (const uint8_t *)K4[j], strlen(K4[j]));
              if (!PKCS5_PBKDF2_HMAC(K4[j], (int)strlen(K4[j]), (const uint8_t *)salt, (int)strlen(salt),
                                     2048, EVP_sha512(), 64, ref[j])) return 1;
          }
          memset(out, 0, sizeof out); pbkdf2_mid_x4(M, sp, out);          bad += memcmp(out, ref, sizeof out) != 0;
          memset(out, 0, sizeof out); pbkdf2_mid_x2(M, sp, out); pbkdf2_mid_x2(M + 2, sp + 2, out + 2);
                                                                          bad += memcmp(out, ref, sizeof out) != 0;
          memset(out, 0, sizeof out); for (int j = 0; j < 4; j++) pbkdf2_mid_x1(M + j, sp + j, out + j);
                                                                          bad += memcmp(out, ref, sizeof out) != 0;
      }
      printf("pbkdf2 with a DIFFERENT passphrase per lane (x1/x2/x4, 4 rotations) vs OpenSSL: %s\n", bad ? "MISMATCH" : "ok"); }
    for (int n = 0; n <= 55 && !bad; n++) for (int t = 0; t < 50; t++) {
        uint8_t d[64], a[32], b[32]; for (int i = 0; i < n; i++) d[i] = (uint8_t)rand();
        sha256_short(d, (size_t)n, a); SHA256(d, (size_t)n, b); bad += memcmp(a, b, 32) != 0;
    }
    printf("sha256 short-message vs OpenSSL (len 0..55): %s\n", bad ? "MISMATCH" : "ok");
    for (int t = 0; t < 500 && !bad; t++) {
        uint8_t k[128], d[111], a[64], b[64]; unsigned L = 64; size_t kl = 1 + rand() % 128, dl = rand() % 112;
        for (size_t i = 0; i < kl; i++) k[i] = (uint8_t)rand(); for (size_t i = 0; i < dl; i++) d[i] = (uint8_t)rand();
        hmac512_small(k, kl, d, dl, a); HMAC(EVP_sha512(), k, (int)kl, d, dl, b, &L); bad += memcmp(a, b, 64) != 0;
    }
    printf("hmac-sha512 small vs OpenSSL (key 1..128, data 0..111): %s\n", bad ? "MISMATCH" : "ok");
    printf("hardware paths: sha512 %s, sha256 %s\n", SHA512_HW ? "yes" : "no", SHA256_HW ? "yes" : "no");
    return bad ? 1 : 0;
}

/* --------------------------------------------------------------- bench
 * Per-component cost on ONE core, so an optimisation can be attributed instead of guessed.
 * Prints ns per SHA-512 block for each interleave width (the gate for going wider), us per
 * seed for the EC half, and combos/s for the enumerator. */
static double now_s(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec / 1e9; }

static void bench_mode(void) {
    const int REPS = 60;                       /* 60 x 4 = 240 PBKDF2s per width, ~0.1 s each */
    enum { BW = 4 };                           /* always 4 lanes here: x4 is benchmarked whatever NWAY is */
    char buf[BW][MAXLINE]; const uint8_t *mn[BW]; size_t ml[BW]; uint8_t seed[BW][64];
    for (int j = 0; j < BW; j++) {
        size_t L = 0;
        for (int i = 0; i < 21; i++) { int w = (i * 97 + j * 13) & 2047;
            memcpy(buf[j] + L, wordlist[w], wordlen[w]); L += wordlen[w]; buf[j][L++] = ' '; }
        buf[j][--L] = 0; mn[j] = (const uint8_t *)buf[j]; ml[j] = L;
    }
    printf("bench (1 core, 21-word mnemonics, %d blocks per PBKDF2; engine runs at x%d)\n", 4096, NWAY);
#if SHA512_HW
    /* raw compression with no PBKDF2 glue: the floor the SHA-512 unit imposes. If pbkdf2 xN is
     * close to this, the byte-swapping/padding between rounds is free and not worth optimising. */
    {   uint64_t rst[4][8]; uint8_t rblk[4][128]; static volatile uint64_t sink;
        for (int j = 0; j < 4; j++) { memcpy(rst[j], H512_INIT, 64); memset(rblk[j], (uint8_t)(j + 1), 128); }
        for (int w = 1; w <= 4; w <<= 1) {
            const int RB = 200000; double t = now_s();
            for (int r = 0; r < RB; r++) {
                if (w == 1) { for (int j = 0; j < 4; j++) sha512_compress_x1(rst + j, (const uint8_t (*)[128])(rblk + j)); }
                else if (w == 2) { sha512_compress_x2(rst, (const uint8_t (*)[128])rblk); sha512_compress_x2(rst + 2, (const uint8_t (*)[128])(rblk + 2)); }
                else sha512_compress_x4(rst, (const uint8_t (*)[128])rblk);
            }
            double rt = now_s() - t;
            for (int j = 0; j < 4; j++) sink ^= rst[j][0];        /* keep the loop alive */
            printf("  raw    x%d : %6.1f ns/block  (no pbkdf2 glue)\n", w, rt / RB / 4 * 1e9);
        }
    }
#endif
    double t1 = 0, tN = 0;
    for (int w = 1; w <= 4; w <<= 1) {
        double t = now_s(); int n = 0;
        for (int r = 0; r < REPS; r++) {
            if (w == 1) { for (int j = 0; j < 4; j++) { pbkdf2_bip39_x1(mn + j, ml + j, seed + j); n++; } }
            else if (w == 2) { pbkdf2_bip39_x2(mn, ml, seed); pbkdf2_bip39_x2(mn + 2, ml + 2, seed + 2); n += 4; }
            else { pbkdf2_bip39_x4(mn, ml, seed); n += 4; }
        }
        double el = now_s() - t;
        if (w == 1) t1 = el;
        if (w == NWAY) tN = el;
        printf("  pbkdf2 x%d : %8.1f seeds/s  %7.1f us/seed  %6.1f ns/block   %.2fx x1\n",
               w, n / el, el / n * 1e6, el / n / 4096 * 1e9, t1 / el);
    }
    /* EC half: account_chain + NADDR leaves, exactly what check_seed does */
    secp256k1_context *ctx = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
    uint8_t sd[64]; memcpy(sd, seed[0], 64);
    int EREPS = 3000; double t = now_s(); int live = 0;
    for (int r = 0; r < EREPS; r++) {
        sd[0] = (uint8_t)r; sd[1] = (uint8_t)(r >> 8);
        xkey chain; uint8_t cpub[33], pub[33], h[20];
        if (!account_chain(ctx, sd, &chain) || !pubkey33(ctx, chain.k, cpub)) continue;
        for (int i = 0; i < NADDR; i++) { xkey leaf;
            if (!ckd_normal_pub(ctx, &chain, cpub, (uint32_t)i, &leaf)) continue;
            if (!pubkey33(ctx, leaf.k, pub)) continue;
            hash160(pub, 33, h); live += h[0]; }
    }
    double ec = (now_s() - t) / EREPS;
    printf("  ec derive : %8.1f seeds/s  %7.1f us/seed  (naddr %d, %d pubkey mults)%s\n",
           1 / ec, ec * 1e6, NADDR, NADDR + 2, live ? "" : "");
    /* one pubkey mult alone */
    t = now_s(); uint8_t pk[33];
    for (int r = 0; r < EREPS; r++) { sd[2] = (uint8_t)r; sd[3] = (uint8_t)(r >> 8); pubkey33(ctx, sd, pk); }
    printf("  pubkey33  : %7.2f us each\n", (now_s() - t) / EREPS * 1e6);
    secp256k1_context_destroy(ctx);
    /* enumerator: odometer + SHA-256 checksum, no derivation */
    if (NW) {
        uint8_t b[33]; int digit[MAXW]; memset(digit, 0, sizeof digit);
        memcpy(b, fixedbuf, 33);
        for (int j = 0; j < NFREE; j++) put11(b, 11 * freeslot[j], slots[freeslot[j]].idx[0]);
        uint64_t lim = 20000000, ok = 0; t = now_s();
        for (uint64_t c = 0; c < lim; c++) {
            ok += checksum_ok(b);
            for (int j = NFREE - 1; j >= 0; j--) { int pos = 11 * freeslot[j]; clr11(b, pos);
                if (++digit[j] < slots[freeslot[j]].n) { put11(b, pos, slots[freeslot[j]].idx[digit[j]]); break; }
                digit[j] = 0; put11(b, pos, slots[freeslot[j]].idx[0]); }
        }
        double en = now_s() - t;
        printf("  enumerate : %8.2f M combos/s  (%llu of %llu checksum-valid)\n", lim / en / 1e6,
               (unsigned long long)ok, (unsigned long long)lim);
        double per_seed = tN / (REPS * 4) + ec;          /* PBKDF2 at the search's width, plus EC */
        printf("  -> at x%d a seed costs %.1f us (pbkdf2 %.1f + ec %.1f); enumeration is %.1f%% of a\n"
               "     search over this template (%.3f%% of combos survive the checksum)\n",
               NWAY, per_seed * 1e6, (tN / (REPS * 4)) * 1e6, ec * 1e6,
               100.0 * (en / lim) / ((en / lim) + (double)ok / lim * per_seed), 100.0 * ok / lim);
    }
}

/* -------------------------------------------------------------- derive */
static void derive_mode(void) {
    secp256k1_context *ctx = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
    char line[MAXLINE * 2]; char hx[130];
    while (fgets(line, sizeof line, stdin)) {
        size_t L = strcspn(line, "\r\n"); line[L] = 0; if (!L) continue;
        uint8_t seed[64]; bip39_seed(line, L, seed);
        hex(seed, 64, hx); printf("seed %s\n", hx);
        xkey m; master_from_seed(seed, &m);
        hex(m.k, 32, hx); printf("master_k %s\n", hx);
        hex(m.c, 32, hx); printf("master_c %s\n", hx);
        xkey chain;
        if (!account_chain(ctx, seed, &chain)) { printf("invalid\n"); continue; }
        uint8_t cpub[33];
        if (!pubkey33(ctx, chain.k, cpub)) { printf("invalid\n"); continue; }
        for (int i = 0; i < NADDR; i++) {
            xkey leaf; uint8_t pub[33], upub[65], h[20];
            if (!ckd_normal_pub(ctx, &chain, cpub, (uint32_t)i, &leaf) || !pubkey_both(ctx, leaf.k, pub, upub)) { printf("addr %d invalid\n", i); continue; }
            hash160(pub, 33, h); hex(h, 20, hx); printf("addr %d %s\n", i, hx);
            hash160(upub, 65, h); hex(h, 20, hx); printf("uaddr %d %s\n", i, hx);
        }
        if (EXT) {   /* the --paths ext derivations, for the differential test: "ext PATH chex uhex" */
            xkey a, b, acct, t, u; uint8_t pub[33], upub[65], h[20]; char hu[41];
            struct { const char *name; int ok; xkey k; } ex[16]; int ne = 0;
            if (ckd_hard(ctx, &m, 44, &a) && ckd_hard(ctx, &a, 0, &b) && ckd_hard(ctx, &b, 0, &acct)) {
                static char nm[64][32];
                if (ckd_normal(ctx, &acct, 1, &t)) for (int i = 0; i < NADDR && ne < 14; i++) if (ckd_normal(ctx, &t, (uint32_t)i, &u)) { snprintf(nm[ne], 32, "m/44h/0h/0h/1/%d", i); ex[ne].name = nm[ne]; ex[ne++].k = u; }
                if (ckd_hard(ctx, &b, 1, &t) && ckd_normal(ctx, &t, 0, &u)) for (int i = 0; i < NADDR && ne < 14; i++) if (ckd_normal(ctx, &u, (uint32_t)i, &t)) { snprintf(nm[ne], 32, "m/44h/0h/1h/0/%d", i); ex[ne].name = nm[ne]; ex[ne++].k = t; }
                if (ckd_hard(ctx, &m, 0, &t) && ckd_normal(ctx, &t, 0, &u)) for (int i = 0; i < NADDR && ne < 14; i++) if (ckd_normal(ctx, &u, (uint32_t)i, &t)) { snprintf(nm[ne], 32, "m/0h/0/%d", i); ex[ne].name = nm[ne]; ex[ne++].k = t; }
                if (ckd_normal(ctx, &m, 0, &t)) for (int i = 0; i < NADDR && ne < 14; i++) if (ckd_normal(ctx, &t, (uint32_t)i, &u)) { snprintf(nm[ne], 32, "m/0/%d", i); ex[ne].name = nm[ne]; ex[ne++].k = u; }
                ex[ne].name = "m"; ex[ne++].k = m;
                if (ckd_hard(ctx, &m, 0, &t) && ckd_hard(ctx, &t, 0, &u) && ckd_hard(ctx, &u, 0, &t)) { ex[ne].name = "m/0h/0h/0h"; ex[ne++].k = t; }
            }
            for (int e = 0; e < ne; e++) {
                if (!pubkey_both(ctx, ex[e].k.k, pub, upub)) continue;
                hash160(pub, 33, h); hex(h, 20, hx); hash160(upub, 65, h); hex(h, 20, hu);
                printf("ext %s %s %s\n", ex[e].name, hx, hu);
            }
        }
        printf("end\n");
    }
    secp256k1_context_destroy(ctx);
}

/* ------------------------------------------------------------------ main */
int main(int argc, char **argv) {
    const char *tmpl = NULL, *wl = "english.txt", *thex = "ccbd031e54cde2a3189fd59bc49f731367a1779e";
    int threads = (int)sysconf(_SC_NPROCESSORS_ONLN), derive = 0, count = 0, bench = 0;
    pbkdf2_set_passphrase("");   /* before the arg loop: --selftest returns from inside it */
    long part_b = 0, part_c = 0, part_n = 1; const char *passphrase = "", *passfile = NULL;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--template") && i + 1 < argc) tmpl = argv[++i];
        else if (!strcmp(argv[i], "--wordlist") && i + 1 < argc) wl = argv[++i];
        else if (!strcmp(argv[i], "--target") && i + 1 < argc) thex = argv[++i];
        else if (!strcmp(argv[i], "--naddr") && i + 1 < argc) NADDR = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--threads") && i + 1 < argc) threads = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--derive")) derive = 1;
        else if (!strcmp(argv[i], "--list")) list_mode = 1;
        else if (!strcmp(argv[i], "--list-bin")) list_mode = 3;
        else if (!strcmp(argv[i], "--count")) count = 1;
        else if (!strcmp(argv[i], "--passphrase") && i + 1 < argc) passphrase = argv[++i];
        else if (!strcmp(argv[i], "--passfile") && i + 1 < argc) passfile = argv[++i];
        else if (!strcmp(argv[i], "--compressed-only")) UNC = 0;
        else if (!strcmp(argv[i], "--paths") && i + 1 < argc) {
            const char *p = argv[++i];
            if (!strcmp(p, "ext")) EXT = 1; else if (!strcmp(p, "std")) EXT = 0; else die("--paths wants std or ext");
        }
        else if (!strcmp(argv[i], "--nochecksum")) NOCHK = 1;
        else if (!strcmp(argv[i], "--selftest")) return selftest();
        else if (!strcmp(argv[i], "--bench")) bench = 1;
        else if (!strcmp(argv[i], "--part") && i + 1 < argc) {
            const char *a = argv[++i];
            if (sscanf(a, "%ld..%ld/%ld", &part_b, &part_c, &part_n) != 3) {
                if (sscanf(a, "%ld/%ld", &part_b, &part_n) != 2) die("--part wants b/n or b..c/n");
                part_c = part_b;
            }
            if (part_n < 1 || part_b < 0 || part_c < part_b || part_c >= part_n) die("--part out of range");
        }
        else die("unknown argument");
    }
    if (NADDR < 1 || NADDR > 1000) die("naddr out of range");
    if (passfile && *passphrase) die("--passphrase and --passfile are mutually exclusive");
    pbkdf2_set_passphrase(passphrase);          /* write-once: every worker only reads it */
    if (passfile) load_passfile(passfile);
    if (threads < 1) threads = 1;
    load_wordlist(wl);
    parse_hex20(thex, target);
    if (derive) { derive_mode(); return 0; }
    if (bench) { if (tmpl) parse_template(tmpl); bench_mode(); return 0; }
    if (!tmpl) die("need --template or --derive");
    parse_template(tmpl);
    uint64_t N = space_size();
    if (count || list_mode) { threads = count ? threads : 1; }   /* --list/--list-bin: one ordered pass */
    if (!list_mode) fprintf(stderr, "blmc: %d words, %d free slots, %llu combos, checksum %d bits%s, %d threads, naddr %d, %s keys, paths %s\n",
                            NW, NFREE, (unsigned long long)N, CS, NOCHK ? " IGNORED (--nochecksum)" : "", threads, NADDR,
                            UNC ? "compressed+uncompressed" : "compressed-only", EXT ? "ext (m/44h/0h/0h/{0,1}/i, m/44h/0h/1h/0/i, m/0h/0/i, m/0/i, m, m/0h/0h/0h)" : "std (m/44h/0h/0h/0/i)");
    if (passfile && !list_mode) fprintf(stderr, "blmc: %d passphrases from %s - one enumeration pass, "
                                                "every survivor tested against all of them\n", NPASS, passfile);
    if (count) list_mode = 0;
    /* global range = parts b..c of n; threads split it evenly (last thread takes the remainder) */
    uint64_t glo = (uint64_t)((unsigned __int128)N * (uint64_t)part_b / (uint64_t)part_n);
    uint64_t ghi = (uint64_t)((unsigned __int128)N * (uint64_t)(part_c + 1) / (uint64_t)part_n);
    if (part_n > 1 && !list_mode) fprintf(stderr, "blmc: part %ld..%ld/%ld -> combos [%llu, %llu)\n",
                                          part_b, part_c, part_n, (unsigned long long)glo, (unsigned long long)ghi);
    N = ghi - glo;
    pthread_t th[256]; if (threads > 256) threads = 256;
    G_LO = glo; G_HI = ghi; atomic_store(&next_chunk, 0);
    /* ~256 checksum-valid seeds per chunk (survival is 2^-CS), but at least 16 chunks per thread
     * so the tail cannot leave a fast core idle, and never below 1024 combos of odometer work. */
    CHUNK = NOCHK ? 256 : (uint64_t)256 << CS;      /* with --nochecksum every combo survives */
    if (CHUNK < 1024) CHUNK = 1024;
    uint64_t maxc = N / ((uint64_t)threads * 16);
    if (maxc && CHUNK > maxc) CHUNK = maxc;
    if (CHUNK < 1) CHUNK = 1;
    if (list_mode) CHUNK = N ? N : 1;           /* --list/--list-bin are single-threaded: one ordered pass */
    int count_only = count;
    if (count_only) list_mode = 2;   /* 2 = count only: neither derive nor print */
    struct timespec t0; clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int t = 0; t < threads; t++) pthread_create(&th[t], NULL, worker, NULL);
    if (!list_mode) {
        /* poll at 250 ms so the reported wall time is the real one (it used to round up to the
         * next 2 s, which made every short A/B measurement unusable); still print every ~2 s. */
        double next_print = 0;
        for (;;) {
            struct timespec ts = {0, 250000000L}; nanosleep(&ts, NULL);
            unsigned long long cd = atomic_load(&combos_done), sd = atomic_load(&seeds_done);
            struct timespec t1; clock_gettime(CLOCK_MONOTONIC, &t1);
            double el = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
            int done = (cd >= N || atomic_load(&stop_flag));
            if (el >= next_print || done) {
                fprintf(stderr, "\rblmc: %llu/%llu combos  %llu seeds  %.0f seeds/s  hits %d   ",
                        cd, (unsigned long long)N, sd, sd / (el > 0 ? el : 1), atomic_load(&hits));
                next_print = el + 2.0;
            }
            if (done) break;
        }
    }
    for (int t = 0; t < threads; t++) pthread_join(th[t], NULL);
    struct timespec t1; clock_gettime(CLOCK_MONOTONIC, &t1);
    double el = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    unsigned long long sd = atomic_load(&seeds_done);
    if (list_mode == 3) fflush(stdout);
    if (count_only) { printf("total %llu valid %llu\n", (unsigned long long)N, sd); return 0; }
    if (!list_mode) {
        if (NPASS > 1) fprintf(stderr, "\nblmc: done in %.1fs: %llu combos, %llu seeds (%llu mnemonics x %d passphrases), %d hits, %.0f seeds/s\n",
                               el, (unsigned long long)N, sd, sd / (unsigned)NPASS, NPASS, atomic_load(&hits), sd / (el > 0 ? el : 1));
        else fprintf(stderr, "\nblmc: done in %.1fs: %llu combos, %llu seeds, %d hits, %.0f seeds/s\n",
                     el, (unsigned long long)N, sd, atomic_load(&hits), sd / (el > 0 ? el : 1));
    }
    return 0;
}
