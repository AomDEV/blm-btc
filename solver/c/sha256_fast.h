/*
 * sha256_fast.h - SHA-256 of one short message (<= 55 bytes, i.e. one padded block)
 * on the ARMv8 SHA-256 unit; falls back to OpenSSL's SHA256() elsewhere.
 * Used for the BIP39 checksum (entropy is 16..32 bytes). Verified in blmc --selftest.
 */
#ifndef SHA256_FAST_H
#define SHA256_FAST_H
#define OPENSSL_SUPPRESS_DEPRECATED
#include <stdint.h>
#include <string.h>
#include <openssl/sha.h>

#if defined(__ARM_FEATURE_SHA2)
#include <arm_neon.h>
#define SHA256_HW 1
static const uint32_t K256[64] = {
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};

static inline void sha256_short(const uint8_t *msg, size_t n, uint8_t out[32]) {
    uint8_t blk[64]; memset(blk, 0, 64); memcpy(blk, msg, n); blk[n] = 0x80;
    uint64_t bits = (uint64_t)n * 8; for (int i = 0; i < 8; i++) blk[63 - i] = (uint8_t)(bits >> (8 * i));
    uint32x4_t s0 = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a};
    uint32x4_t s1 = {0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    uint32x4_t m0 = vreinterpretq_u32_u8(vrev32q_u8(vld1q_u8(blk)));
    uint32x4_t m1 = vreinterpretq_u32_u8(vrev32q_u8(vld1q_u8(blk + 16)));
    uint32x4_t m2 = vreinterpretq_u32_u8(vrev32q_u8(vld1q_u8(blk + 32)));
    uint32x4_t m3 = vreinterpretq_u32_u8(vrev32q_u8(vld1q_u8(blk + 48)));
    uint32x4_t t, u;
#define R4(k, m) t = vaddq_u32(m, vld1q_u32(K256 + (k))); u = s0; \
                 s0 = vsha256hq_u32(s0, s1, t); s1 = vsha256h2q_u32(s1, u, t);
#define S4(a, b, c, d) a = vsha256su1q_u32(vsha256su0q_u32(a, b), c, d);
    R4(0, m0) R4(4, m1) R4(8, m2) R4(12, m3)
    S4(m0, m1, m2, m3) S4(m1, m2, m3, m0) S4(m2, m3, m0, m1) S4(m3, m0, m1, m2)
    R4(16, m0) R4(20, m1) R4(24, m2) R4(28, m3)
    S4(m0, m1, m2, m3) S4(m1, m2, m3, m0) S4(m2, m3, m0, m1) S4(m3, m0, m1, m2)
    R4(32, m0) R4(36, m1) R4(40, m2) R4(44, m3)
    S4(m0, m1, m2, m3) S4(m1, m2, m3, m0) S4(m2, m3, m0, m1) S4(m3, m0, m1, m2)
    R4(48, m0) R4(52, m1) R4(56, m2) R4(60, m3)
#undef R4
#undef S4
    s0 = vaddq_u32(s0, (uint32x4_t){0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a});
    s1 = vaddq_u32(s1, (uint32x4_t){0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19});
    vst1q_u8(out, vrev32q_u8(vreinterpretq_u8_u32(s0)));
    vst1q_u8(out + 16, vrev32q_u8(vreinterpretq_u8_u32(s1)));
}
#else
#define SHA256_HW 0
static inline void sha256_short(const uint8_t *msg, size_t n, uint8_t out[32]) { SHA256(msg, n, out); }
#endif
#endif /* SHA256_FAST_H */
