/*
 * sha512_fast.h - SHA-512 compression + PBKDF2-HMAC-SHA512 tuned for the BIP39 case.
 *
 *   sha512_compress(st, block)       one 128-byte block; ARMv8.2 SHA-512 instructions
 *                                    when __ARM_FEATURE_SHA512, else OpenSSL SHA512_Transform.
 *   pbkdf2_bip39(mn, len, seed)      PBKDF2-HMAC-SHA512(mn, "mnemonic", 2048, 64):
 *                                    HMAC ipad/opad midstates computed once, then each
 *                                    round is exactly two compressions on fixed-layout blocks.
 *   pbkdf2_bip39_xN(mn[], len[], seeds[])  N=1,2,4 mnemonics interleaved round by round
 *                                    (sha512_nway.h, generated) so the CPU overlaps the chains.
 * Differentially tested against OpenSSL PKCS5_PBKDF2_HMAC (blmc --selftest).
 */
#ifndef SHA512_FAST_H
#define SHA512_FAST_H
#define OPENSSL_SUPPRESS_DEPRECATED
#include <stdint.h>
#include <string.h>
#include <openssl/sha.h>

static const uint64_t K512[80] = {
0x428a2f98d728ae22ULL,0x7137449123ef65cdULL,0xb5c0fbcfec4d3b2fULL,0xe9b5dba58189dbbcULL,0x3956c25bf348b538ULL,0x59f111f1b605d019ULL,0x923f82a4af194f9bULL,0xab1c5ed5da6d8118ULL,
0xd807aa98a3030242ULL,0x12835b0145706fbeULL,0x243185be4ee4b28cULL,0x550c7dc3d5ffb4e2ULL,0x72be5d74f27b896fULL,0x80deb1fe3b1696b1ULL,0x9bdc06a725c71235ULL,0xc19bf174cf692694ULL,
0xe49b69c19ef14ad2ULL,0xefbe4786384f25e3ULL,0x0fc19dc68b8cd5b5ULL,0x240ca1cc77ac9c65ULL,0x2de92c6f592b0275ULL,0x4a7484aa6ea6e483ULL,0x5cb0a9dcbd41fbd4ULL,0x76f988da831153b5ULL,
0x983e5152ee66dfabULL,0xa831c66d2db43210ULL,0xb00327c898fb213fULL,0xbf597fc7beef0ee4ULL,0xc6e00bf33da88fc2ULL,0xd5a79147930aa725ULL,0x06ca6351e003826fULL,0x142929670a0e6e70ULL,
0x27b70a8546d22ffcULL,0x2e1b21385c26c926ULL,0x4d2c6dfc5ac42aedULL,0x53380d139d95b3dfULL,0x650a73548baf63deULL,0x766a0abb3c77b2a8ULL,0x81c2c92e47edaee6ULL,0x92722c851482353bULL,
0xa2bfe8a14cf10364ULL,0xa81a664bbc423001ULL,0xc24b8b70d0f89791ULL,0xc76c51a30654be30ULL,0xd192e819d6ef5218ULL,0xd69906245565a910ULL,0xf40e35855771202aULL,0x106aa07032bbd1b8ULL,
0x19a4c116b8d2d0c8ULL,0x1e376c085141ab53ULL,0x2748774cdf8eeb99ULL,0x34b0bcb5e19b48a8ULL,0x391c0cb3c5c95a63ULL,0x4ed8aa4ae3418acbULL,0x5b9cca4f7763e373ULL,0x682e6ff3d6b2b8a3ULL,
0x748f82ee5defb2fcULL,0x78a5636f43172f60ULL,0x84c87814a1f0ab72ULL,0x8cc702081a6439ecULL,0x90befffa23631e28ULL,0xa4506cebde82bde9ULL,0xbef9a3f7b2c67915ULL,0xc67178f2e372532bULL,
0xca273eceea26619cULL,0xd186b8c721c0c207ULL,0xeada7dd6cde0eb1eULL,0xf57d4f7fee6ed178ULL,0x06f067aa72176fbaULL,0x0a637dc5a2c898a6ULL,0x113f9804bef90daeULL,0x1b710b35131c471bULL,
0x28db77f523047d84ULL,0x32caab7b40c72493ULL,0x3c9ebe0a15c9bebcULL,0x431d67c49c100d4cULL,0x4cc5d4becb3e42b6ULL,0x597f299cfc657e2aULL,0x5fcb6fab3ad6faecULL,0x6c44198c4a475817ULL};

static const uint64_t H512_INIT[8] = {
0x6a09e667f3bcc908ULL,0xbb67ae8584caa73bULL,0x3c6ef372fe94f82bULL,0xa54ff53a5f1d36f1ULL,
0x510e527fade682d1ULL,0x9b05688c2b3e6c1fULL,0x1f83d9abfb41bd6bULL,0x5be0cd19137e2179ULL};

#if defined(__ARM_FEATURE_SHA512)
#include <arm_neon.h>
#define SHA512_HW 1
/* One block with the ARMv8.2 SHA-512 instructions. State held as 4 vectors {a,b},{c,d},{e,f},{g,h}.
 * The two-round step's operand layout was verified against a scalar reference (find.c):
 *   sum = rot(W+K) + gh;  T1 = SHA512H(sum, {f,g}, {d,e});  ef' = cd + T1;  ab' = SHA512H2(T1, cd, ab)
 * and the roles rotate: cd' = ab, gh' = ef. */
static inline void sha512_compress(uint64_t st[8], const uint8_t blk[128]) {
    uint64x2_t ab = vld1q_u64(st), cd = vld1q_u64(st + 2), ef = vld1q_u64(st + 4), gh = vld1q_u64(st + 6);
    const uint64x2_t ab0 = ab, cd0 = cd, ef0 = ef, gh0 = gh;
    uint64x2_t m0 = vreinterpretq_u64_u8(vrev64q_u8(vld1q_u8(blk +   0)));
    uint64x2_t m1 = vreinterpretq_u64_u8(vrev64q_u8(vld1q_u8(blk +  16)));
    uint64x2_t m2 = vreinterpretq_u64_u8(vrev64q_u8(vld1q_u8(blk +  32)));
    uint64x2_t m3 = vreinterpretq_u64_u8(vrev64q_u8(vld1q_u8(blk +  48)));
    uint64x2_t m4 = vreinterpretq_u64_u8(vrev64q_u8(vld1q_u8(blk +  64)));
    uint64x2_t m5 = vreinterpretq_u64_u8(vrev64q_u8(vld1q_u8(blk +  80)));
    uint64x2_t m6 = vreinterpretq_u64_u8(vrev64q_u8(vld1q_u8(blk +  96)));
    uint64x2_t m7 = vreinterpretq_u64_u8(vrev64q_u8(vld1q_u8(blk + 112)));
    uint64x2_t sum, t1, nab;
#define RND2(k, w)                                                                 \
    sum = vaddq_u64(w, vld1q_u64(K512 + (k)));                                    \
    sum = vaddq_u64(vextq_u64(sum, sum, 1), gh);                                  \
    t1  = vsha512hq_u64(sum, vextq_u64(ef, gh, 1), vextq_u64(cd, ef, 1));         \
    nab = vsha512h2q_u64(t1, cd, ab);                                             \
    gh = ef; ef = vaddq_u64(cd, t1); cd = ab; ab = nab;
#define SCHED(w0, w1, w4, w5, w7) w0 = vsha512su1q_u64(vsha512su0q_u64(w0, w1), w7, vextq_u64(w4, w5, 1));
#define EIGHT(k) RND2(k, m0) RND2(k + 2, m1) RND2(k + 4, m2) RND2(k + 6, m3) \
                 RND2(k + 8, m4) RND2(k + 10, m5) RND2(k + 12, m6) RND2(k + 14, m7)
#define NEXT() SCHED(m0, m1, m4, m5, m7) SCHED(m1, m2, m5, m6, m0) SCHED(m2, m3, m6, m7, m1) \
               SCHED(m3, m4, m7, m0, m2) SCHED(m4, m5, m0, m1, m3) SCHED(m5, m6, m1, m2, m4) \
               SCHED(m6, m7, m2, m3, m5) SCHED(m7, m0, m3, m4, m6)
    EIGHT(0) NEXT() EIGHT(16) NEXT() EIGHT(32) NEXT() EIGHT(48) NEXT() EIGHT(64)
#undef RND2
#undef SCHED
#undef EIGHT
#undef NEXT
    vst1q_u64(st,     vaddq_u64(ab, ab0)); vst1q_u64(st + 2, vaddq_u64(cd, cd0));
    vst1q_u64(st + 4, vaddq_u64(ef, ef0)); vst1q_u64(st + 6, vaddq_u64(gh, gh0));
}
#else
#define SHA512_HW 0
static inline void sha512_compress(uint64_t st[8], const uint8_t blk[128]) {
    SHA512_CTX c; memset(&c, 0, sizeof c);
    for (int i = 0; i < 8; i++) c.h[i] = st[i];
    SHA512_Transform(&c, blk);
    for (int i = 0; i < 8; i++) st[i] = c.h[i];
}
#endif

static inline void st_to_bytes(const uint64_t st[8], uint8_t out[64]) {
    for (int i = 0; i < 8; i++) { uint64_t v = st[i]; for (int j = 7; j >= 0; j--) { out[8*i + j] = (uint8_t)v; v >>= 8; } }
}
static inline void put_be64(uint8_t *p, uint64_t v) { for (int j = 7; j >= 0; j--) { p[j] = (uint8_t)v; v >>= 8; } }

/* Full SHA-512 of an arbitrary message (used for keys > 128 bytes) */
static void sha512_msg(const uint8_t *d, size_t n, uint8_t out[64]) {
    uint64_t st[8]; memcpy(st, H512_INIT, sizeof st);
    size_t i = 0;
    for (; i + 128 <= n; i += 128) sha512_compress(st, d + i);
    uint8_t blk[256]; memset(blk, 0, sizeof blk);
    size_t rem = n - i; memcpy(blk, d + i, rem); blk[rem] = 0x80;
    size_t nb = (rem + 1 + 16 <= 128) ? 1 : 2;
    put_be64(blk + nb * 128 - 8, (uint64_t)n * 8);
    sha512_compress(st, blk); if (nb == 2) sha512_compress(st, blk + 128);
    st_to_bytes(st, out);
}

typedef struct { uint64_t in[8], out[8]; } hmac_mid;

/* PBKDF2 salt = "mnemonic" || passphrase. The first HMAC message (salt || INT(1)) does not depend
 * on the mnemonic, so its padded SHA-512 block(s) are built once, per passphrase, into a pb_salt.
 * A sweep holds one pb_salt per candidate passphrase and hands a *different* one to each
 * interleaved lane, so the salt can never be a shared mutable global in the hot loop. */
typedef struct { uint8_t blk[2][128]; int nblk; } pb_salt;

static void pb_salt_init(pb_salt *s, const char *pass) {
    uint8_t msg[256]; size_t n = 0;
    memcpy(msg, "mnemonic", 8); n = 8;
    size_t pl = pass ? strlen(pass) : 0;
    if (pl > 200) { fprintf(stderr, "passphrase too long (max 200 bytes)\n"); exit(2); }
    memcpy(msg + n, pass ? pass : "", pl); n += pl;
    msg[n++] = 0; msg[n++] = 0; msg[n++] = 0; msg[n++] = 1;          /* INT(1) */
    memset(s->blk, 0, sizeof s->blk);
    uint64_t bits = (uint64_t)(128 + n) * 8;
    if (n <= 111) { memcpy(s->blk[0], msg, n); s->blk[0][n] = 0x80; put_be64(s->blk[0] + 120, bits); s->nblk = 1; }
    else { memcpy(s->blk[0], msg, 128); if (n > 128) memcpy(s->blk[1], msg + 128, n - 128); s->blk[1][n - 128] = 0x80;
           put_be64(s->blk[1] + 120, bits); s->nblk = 2; }
}

/* The default salt used when no per-lane salt is supplied. Written once by
 * pbkdf2_set_passphrase() before any worker thread starts, and read-only thereafter. */
static pb_salt PB_DEFAULT;
static void pbkdf2_set_passphrase(const char *pass) { pb_salt_init(&PB_DEFAULT, pass); }

/* HMAC-SHA512 midstates for key = mnemonic (pre-hashed if > 128 bytes, per RFC 2104) */
static void hmac_mid_init(hmac_mid *m, const uint8_t *key, size_t klen) {
    uint8_t k[128]; memset(k, 0, 128);
    if (klen > 128) sha512_msg(key, klen, k); else memcpy(k, key, klen);
    uint8_t blk[128];
    memcpy(m->in, H512_INIT, 64); memcpy(m->out, H512_INIT, 64);
    for (int i = 0; i < 128; i++) blk[i] = k[i] ^ 0x36; sha512_compress(m->in, blk);
    for (int i = 0; i < 128; i++) blk[i] = k[i] ^ 0x5c; sha512_compress(m->out, blk);
}

/* A 64-byte digest as a single padded SHA-512 block following a 128-byte prefix (len 192 B) */
static inline void pad64_block(uint8_t blk[128]) {
    memset(blk + 64, 0, 64); blk[64] = 0x80; put_be64(blk + 120, 192 * 8);
}

/* HMAC-SHA512 for key <= 128 bytes and data <= 111 bytes (BIP32 CKD: 4 compressions, no allocations) */
static inline void hmac512_small(const uint8_t *key, size_t klen, const uint8_t *d, size_t n, uint8_t out[64]) {
    uint8_t blk[128]; uint64_t st[8];
    memset(blk, 0x36, 128); for (size_t i = 0; i < klen; i++) blk[i] = key[i] ^ 0x36;
    memcpy(st, H512_INIT, 64); sha512_compress(st, blk);
    memset(blk, 0, 128); memcpy(blk, d, n); blk[n] = 0x80; put_be64(blk + 120, (uint64_t)(128 + n) * 8);
    sha512_compress(st, blk);
    st_to_bytes(st, blk); pad64_block(blk);                      /* inner digest as the outer message */
    uint8_t kb[128]; memset(kb, 0x5c, 128); for (size_t i = 0; i < klen; i++) kb[i] = key[i] ^ 0x5c;
    uint64_t so[8]; memcpy(so, H512_INIT, 64); sha512_compress(so, kb); sha512_compress(so, blk);
    st_to_bytes(so, out);
}

/* PBKDF2-HMAC-SHA512(mn, "mnemonic", 2048, dkLen 64) */
static void __attribute__((unused)) pbkdf2_bip39(const uint8_t *mn, size_t mlen, uint8_t seed[64]) {
    hmac_mid m; hmac_mid_init(&m, mn, mlen);
    uint64_t st[8]; uint8_t blk[128];
    /* U1 = HMAC(mn, salt || 0x00000001) with the precomputed salt block(s) */
    const pb_salt *S = &PB_DEFAULT;
    memcpy(st, m.in, 64); sha512_compress(st, S->blk[0]); if (S->nblk == 2) sha512_compress(st, S->blk[1]);
    st_to_bytes(st, blk); pad64_block(blk);
    memcpy(st, m.out, 64); sha512_compress(st, blk);
    uint64_t T[8]; memcpy(T, st, 64);
    for (int r = 1; r < 2048; r++) {
        st_to_bytes(st, blk); pad64_block(blk);          /* U_{r} as inner message */
        memcpy(st, m.in, 64); sha512_compress(st, blk);
        st_to_bytes(st, blk); pad64_block(blk);
        memcpy(st, m.out, 64); sha512_compress(st, blk);
        for (int i = 0; i < 8; i++) T[i] ^= st[i];
    }
    st_to_bytes(T, seed);
}

/* ---- N-way PBKDF2 (N = 1,2,4): seeds[j] = PBKDF2-HMAC-SHA512(mn[j], "mnemonic", 2048, 64) ---- */
#if SHA512_HW
#include "sha512_nway.h"
/* Core: N lanes, each with its own HMAC key midstate AND its own salt. A passphrase sweep reuses
 * one midstate per mnemonic across every candidate passphrase and varies only the salt; a plain
 * search passes the same salt in every lane. U1 is done lane by lane because lanes may disagree
 * on whether the salt needs one block or two - that is 1-2 blocks out of 4096, under 0.05%. */
#define PBKDF2_NWAY(N)                                                                             \
static void pbkdf2_mid_x##N(const hmac_mid *m, const pb_salt *const *sa, uint8_t (*seed)[64]) {    \
    uint64_t st[N][8], T[N][8]; uint8_t blk[N][128];                                               \
    for (int j = 0; j < N; j++) {                                                                  \
        uint64_t u[8]; memcpy(u, m[j].in, 64);                                                     \
        sha512_compress(u, sa[j]->blk[0]);                                                         \
        if (sa[j]->nblk == 2) sha512_compress(u, sa[j]->blk[1]);                                   \
        st_to_bytes(u, blk[j]); pad64_block(blk[j]); memcpy(st[j], m[j].out, 64);                  \
    }                                                                                              \
    sha512_compress_x##N(st, (const uint8_t (*)[128])blk);                                         \
    memcpy(T, st, sizeof T);                                                                       \
    for (int r = 1; r < 2048; r++) {                                                               \
        for (int j = 0; j < N; j++) { st_to_bytes(st[j], blk[j]); pad64_block(blk[j]); memcpy(st[j], m[j].in, 64); } \
        sha512_compress_x##N(st, (const uint8_t (*)[128])blk);                                     \
        for (int j = 0; j < N; j++) { st_to_bytes(st[j], blk[j]); pad64_block(blk[j]); memcpy(st[j], m[j].out, 64); } \
        sha512_compress_x##N(st, (const uint8_t (*)[128])blk);                                     \
        for (int j = 0; j < N; j++) for (int i = 0; i < 8; i++) T[j][i] ^= st[j][i];               \
    }                                                                                              \
    for (int j = 0; j < N; j++) st_to_bytes(T[j], seed[j]);                                        \
}                                                                                                  \
static void pbkdf2_bip39_x##N(const uint8_t *const *mn, const size_t *mlen, uint8_t (*seed)[64]) { \
    hmac_mid m[N]; const pb_salt *sa[N];                                                           \
    for (int j = 0; j < N; j++) { hmac_mid_init(&m[j], mn[j], mlen[j]); sa[j] = &PB_DEFAULT; }     \
    pbkdf2_mid_x##N(m, sa, seed);                                                                  \
}
PBKDF2_NWAY(1) PBKDF2_NWAY(2) PBKDF2_NWAY(4)
#else
/* portable fallback (no SHA-512 instructions): same interface, one stream at a time */
#define PBKDF2_NWAY_SEQ(N)                                                                         \
static void pbkdf2_mid_x##N(const hmac_mid *m, const pb_salt *const *sa, uint8_t (*seed)[64]) {    \
    for (int j = 0; j < N; j++) {                                                                  \
        uint64_t st[8], T[8]; uint8_t blk[128];                                                    \
        memcpy(st, m[j].in, 64); sha512_compress(st, sa[j]->blk[0]);                               \
        if (sa[j]->nblk == 2) sha512_compress(st, sa[j]->blk[1]);                                  \
        st_to_bytes(st, blk); pad64_block(blk);                                                    \
        memcpy(st, m[j].out, 64); sha512_compress(st, blk);                                        \
        memcpy(T, st, 64);                                                                         \
        for (int r = 1; r < 2048; r++) {                                                           \
            st_to_bytes(st, blk); pad64_block(blk);                                                \
            memcpy(st, m[j].in, 64); sha512_compress(st, blk);                                     \
            st_to_bytes(st, blk); pad64_block(blk);                                                \
            memcpy(st, m[j].out, 64); sha512_compress(st, blk);                                    \
            for (int i = 0; i < 8; i++) T[i] ^= st[i];                                             \
        }                                                                                          \
        st_to_bytes(T, seed[j]);                                                                   \
    }                                                                                              \
}                                                                                                  \
static void pbkdf2_bip39_x##N(const uint8_t *const *mn, const size_t *mlen, uint8_t (*seed)[64]) { \
    hmac_mid m[N]; const pb_salt *sa[N];                                                           \
    for (int j = 0; j < N; j++) { hmac_mid_init(&m[j], mn[j], mlen[j]); sa[j] = &PB_DEFAULT; }     \
    pbkdf2_mid_x##N(m, sa, seed);                                                                  \
}
PBKDF2_NWAY_SEQ(1) PBKDF2_NWAY_SEQ(2) PBKDF2_NWAY_SEQ(4)
#endif
#endif /* SHA512_FAST_H */
