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
 *   blmc --template FILE --count     print total and checksum-valid counts
 *   --passphrase STR                 BIP39 passphrase (salt = "mnemonic" || STR); default empty
 *   --part b/n | --part b..c/n       work only on parts b (to c) of the combo space split into n
 *                                    equal parts (cgpu.py gives the GPU some parts, the CPU the rest)
 *   blmc --selftest                  SHA-512 / PBKDF2 fast paths vs OpenSSL
 *
 * Template syntax (same as solve.py): word | ? | {a|b|c}
 *
 * Build: see build.sh. Tested differentially against the Python reference
 * (test_blmc.py) on seed, master key, chain code, and every address.
 */
#include <stdio.h>
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
    uint8_t s[32]; SHA256(d, n, s); RIPEMD160(s, 32, out);      /* legacy one-shots: no provider fetch */
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
#define NWAY 4
/* NWAY mnemonics at once, rounds interleaved: ~1.7x the single-stream rate on M1 */
static void bip39_seed_x4(const uint8_t *const mn[NWAY], const size_t mlen[NWAY], uint8_t seed[NWAY][64]) {
    pbkdf2_bip39_x4(mn, mlen, seed);
}

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
static int ckd_normal(secp256k1_context *ctx, const xkey *p, uint32_t i, xkey *ch) {
    uint8_t data[37], I[64];
    if (!pubkey33(ctx, p->k, data)) return 0;
    data[33] = i >> 24; data[34] = i >> 16; data[35] = i >> 8; data[36] = i;
    hmac512(p->c, 32, data, 37, I);
    memcpy(ch->k, p->k, 32);
    if (!secp256k1_ec_seckey_tweak_add(ctx, ch->k, I)) return 0;
    memcpy(ch->c, I + 32, 32);
    return 1;
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

/* ---------------------------------------------------------------- search */
static uint8_t target[20];
static int NADDR = 2;
static atomic_ullong combos_done = 0, seeds_done = 0;
static atomic_int stop_flag = 0, hits = 0;
static pthread_mutex_t hit_mu = PTHREAD_MUTEX_INITIALIZER;
static int list_mode = 0;

typedef struct { uint64_t lo, hi; int id; } job;

static void report_hit(const char *mn, int i) {
    pthread_mutex_lock(&hit_mu);
    printf("\n*** HIT *** '%s' path=m/44h/0h/0h/0/%d [blmc]\n", mn, i); fflush(stdout);
    FILE *f = fopen("HIT.txt", "a");
    if (f) { fprintf(f, "*** HIT *** '%s' path=m/44h/0h/0h/0/%d [blmc]\n", mn, i); fclose(f); }
    atomic_fetch_add(&hits, 1);
    atomic_store(&stop_flag, 1);
    pthread_mutex_unlock(&hit_mu);
}

/* derive m/44'/0'/0'/0/i for i < NADDR from one seed and compare with the target */
static void check_seed(secp256k1_context *ctx, const uint8_t seed[64], const char *mn) {
    xkey chain; uint8_t pub[33], h[20];
    if (!account_chain(ctx, seed, &chain)) return;
    for (int i = 0; i < NADDR; i++) {
        xkey leaf;
        if (!ckd_normal(ctx, &chain, (uint32_t)i, &leaf)) continue;
        if (!pubkey33(ctx, leaf.k, pub)) continue;
        hash160(pub, 33, h);
        if (memcmp(h, target, 20) == 0) { report_hit(mn, i); return; }
    }
}

typedef struct { char mn[NWAY][MAXLINE]; size_t len[NWAY]; int n; } wbatch;

/* run PBKDF2 on the buffered mnemonics (NWAY interleaved when full) and check each */
static void flush_batch(secp256k1_context *ctx, wbatch *b) {
    uint8_t seed[NWAY][64];
    if (b->n == NWAY) {
        const uint8_t *mn[NWAY]; for (int j = 0; j < NWAY; j++) mn[j] = (const uint8_t *)b->mn[j];
        bip39_seed_x4(mn, b->len, seed);
    } else {
        for (int j = 0; j < b->n; j++) bip39_seed(b->mn[j], b->len[j], seed[j]);
    }
    for (int j = 0; j < b->n; j++) check_seed(ctx, seed[j], b->mn[j]);
    atomic_fetch_add(&seeds_done, (uint64_t)b->n);
    b->n = 0;
}

static void *worker(void *arg) {
    job *J = arg;
    secp256k1_context *ctx = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
    int digit[MAXW]; uint64_t rem = J->lo;
    /* mixed-radix decode of lo: least-significant digit = last free slot */
    for (int j = NFREE - 1; j >= 0; j--) { int n = slots[freeslot[j]].n; digit[j] = (int)(rem % n); rem /= n; }
    uint8_t buf[33]; char mn[MAXLINE];
    wbatch B; B.n = 0;
    uint64_t local = 0;
    memcpy(buf, fixedbuf, 33);
    for (int j = 0; j < NFREE; j++) put11(buf, 11 * freeslot[j], slots[freeslot[j]].idx[digit[j]]);
    for (uint64_t c = J->lo; c < J->hi; c++) {
        if (checksum_ok(buf)) {
            if (list_mode == 1) { build_mnemonic(buf, mn); pthread_mutex_lock(&hit_mu); puts(mn); pthread_mutex_unlock(&hit_mu); atomic_fetch_add(&seeds_done, 1); }
            else if (list_mode == 2) { atomic_fetch_add(&seeds_done, 1); }
            else {
                B.len[B.n] = build_mnemonic(buf, B.mn[B.n]);
                if (++B.n == NWAY) flush_batch(ctx, &B);
            }
        }
        /* odometer increment; only the slots whose digit changed are re-packed */
        for (int j = NFREE - 1; j >= 0; j--) {
            int pos = 11 * freeslot[j]; clr11(buf, pos);
            if (++digit[j] < slots[freeslot[j]].n) { put11(buf, pos, slots[freeslot[j]].idx[digit[j]]); break; }
            digit[j] = 0; put11(buf, pos, slots[freeslot[j]].idx[0]);
        }
        if (++local == 4096) { atomic_fetch_add(&combos_done, local); local = 0; if (atomic_load(&stop_flag)) break; }
    }
    if (B.n) flush_batch(ctx, &B);
    atomic_fetch_add(&combos_done, local);
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
        for (int i = 0; i < NADDR; i++) {
            xkey leaf; uint8_t pub[33], h[20];
            if (!ckd_normal(ctx, &chain, (uint32_t)i, &leaf) || !pubkey33(ctx, leaf.k, pub)) { printf("addr %d invalid\n", i); continue; }
            hash160(pub, 33, h); hex(h, 20, hx); printf("addr %d %s\n", i, hx);
        }
        printf("end\n");
    }
    secp256k1_context_destroy(ctx);
}

/* ------------------------------------------------------------------ main */
int main(int argc, char **argv) {
    const char *tmpl = NULL, *wl = "english.txt", *thex = "ccbd031e54cde2a3189fd59bc49f731367a1779e";
    int threads = (int)sysconf(_SC_NPROCESSORS_ONLN), derive = 0, count = 0;
    long part_b = 0, part_c = 0, part_n = 1; const char *passphrase = "";
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--template") && i + 1 < argc) tmpl = argv[++i];
        else if (!strcmp(argv[i], "--wordlist") && i + 1 < argc) wl = argv[++i];
        else if (!strcmp(argv[i], "--target") && i + 1 < argc) thex = argv[++i];
        else if (!strcmp(argv[i], "--naddr") && i + 1 < argc) NADDR = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--threads") && i + 1 < argc) threads = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--derive")) derive = 1;
        else if (!strcmp(argv[i], "--list")) list_mode = 1;
        else if (!strcmp(argv[i], "--count")) count = 1;
        else if (!strcmp(argv[i], "--passphrase") && i + 1 < argc) passphrase = argv[++i];
        else if (!strcmp(argv[i], "--selftest")) return selftest();
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
    pbkdf2_set_passphrase(passphrase);
    if (threads < 1) threads = 1;
    load_wordlist(wl);
    parse_hex20(thex, target);
    if (derive) { derive_mode(); return 0; }
    if (!tmpl) die("need --template or --derive");
    parse_template(tmpl);
    uint64_t N = space_size();
    if (count || list_mode) { threads = count ? threads : 1; }
    if (!list_mode) fprintf(stderr, "blmc: %d words, %d free slots, %llu combos, checksum %d bits, %d threads, naddr %d\n",
                            NW, NFREE, (unsigned long long)N, CS, threads, NADDR);
    if (count) list_mode = 0;
    /* global range = parts b..c of n; threads split it evenly (last thread takes the remainder) */
    uint64_t glo = (uint64_t)((unsigned __int128)N * (uint64_t)part_b / (uint64_t)part_n);
    uint64_t ghi = (uint64_t)((unsigned __int128)N * (uint64_t)(part_c + 1) / (uint64_t)part_n);
    if (part_n > 1 && !list_mode) fprintf(stderr, "blmc: part %ld..%ld/%ld -> combos [%llu, %llu)\n",
                                          part_b, part_c, part_n, (unsigned long long)glo, (unsigned long long)ghi);
    N = ghi - glo;
    pthread_t th[256]; job jobs[256]; if (threads > 256) threads = 256;
    uint64_t per = N / threads;
    for (int t = 0; t < threads; t++) {
        jobs[t].id = t; jobs[t].lo = glo + per * t; jobs[t].hi = (t == threads - 1) ? ghi : glo + per * (t + 1);
    }
    int count_only = count;
    if (count_only) list_mode = 2;   /* 2 = count only: neither derive nor print */
    struct timespec t0; clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int t = 0; t < threads; t++) pthread_create(&th[t], NULL, worker, &jobs[t]);
    if (!list_mode) {
        for (;;) {
            struct timespec ts = {2, 0}; nanosleep(&ts, NULL);
            unsigned long long cd = atomic_load(&combos_done), sd = atomic_load(&seeds_done);
            struct timespec t1; clock_gettime(CLOCK_MONOTONIC, &t1);
            double el = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
            fprintf(stderr, "\rblmc: %llu/%llu combos  %llu seeds  %.0f seeds/s  hits %d   ",
                    cd, (unsigned long long)N, sd, sd / (el > 0 ? el : 1), atomic_load(&hits));
            if (cd >= N || atomic_load(&stop_flag)) break;
        }
    }
    for (int t = 0; t < threads; t++) pthread_join(th[t], NULL);
    struct timespec t1; clock_gettime(CLOCK_MONOTONIC, &t1);
    double el = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    unsigned long long sd = atomic_load(&seeds_done);
    if (count_only) { printf("total %llu valid %llu\n", (unsigned long long)N, sd); return 0; }
    if (!list_mode) fprintf(stderr, "\nblmc: done in %.1fs: %llu combos, %llu seeds, %d hits, %.0f seeds/s\n",
                            el, (unsigned long long)N, sd, atomic_load(&hits), sd / (el > 0 ? el : 1));
    return 0;
}
