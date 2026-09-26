// BLM puzzle GPU kernels. Appended after the 11 base files from bip39-solver-gpu
// (common, ripemd, sha2, mnemonic_constants, secp256k1_*, address).
//
// Both kernels take NW ushort word-indices per work-item (any BIP39 length), the padded PBKDF2
// salt block,
// a real target hash160 and a canary hash160, and write result[gid]:
//     p+1              real hit at path-id p
//     0x80000000|(p+1) canary hit at path-id p   (proves the launch ran)
//     0                nothing
//
// blm_check      : narrow  - m/44'/0'/0'/0/i, i < n_addr           (path-id = i)
// blm_check_wide : wide    - the same 101 paths as the CPU's WIDE_TREE (ids below)

// --- PBKDF2-HMAC-SHA512 with HMAC midstates -------------------------------------------------
// The original kernel called sha512(joined, 192) four times per round, and each of those calls
// re-compressed the 128-byte ipad/opad block from the initial state: 4 block compressions per
// round where 2 are needed. Computing the ipad/opad midstates once per work-item halves the
// kernel's SHA-512 work. This is the same structure the C engine uses (sha512_fast.h).
//
// The salt block is handed in as 16 big-endian words already padded for a 128+saltlen byte
// message, so the passphrase costs one 128-byte read per work-item and NOTHING in the kernel
// depends on its length: the program is built once and reused for every passphrase in a sweep.
// (Passing the salt *length* as an argument instead measured 35% slower - the Apple compiler
// then stops specialising sha512() at its call sites. One fixed-size block avoids that.)

__constant ulong H512_0[8] = {
  0x6a09e667f3bcc908UL, 0xbb67ae8584caa73bUL, 0x3c6ef372fe94f82bUL, 0xa54ff53a5f1d36f1UL,
  0x510e527fade682d1UL, 0x9b05688c2b3e6c1fUL, 0x1f83d9abfb41bd6bUL, 0x5be0cd19137e2179UL };

// sha2.cl #undefs F0/F1 at its end; ROUND_STEP_SHA512 still needs them. Same definitions.
#define F1(x,y,z) (bitselect(z,y,x))
#define F0(x,y,z) (bitselect (x, y, ((x) ^ (z))))

// One 128-byte block from an arbitrary state. Win holds the 16 message words already in
// big-endian order (i.e. what sha512() would produce with SWAP512), so no byte shuffling.
static void sha512_block(ulong *State, const ulong *Win) {
  ulong W[0x50];
  for (int i = 0; i < 16; i++) W[i] = Win[i];
  for (int i = 16; i < 80; i++) W[i] = W[i-16] + little_s0(W[i-15]) + W[i-7] + little_s1(W[i-2]);
  ulong a = State[0], b = State[1], c = State[2], d = State[3];
  ulong e = State[4], f = State[5], g = State[6], h = State[7];
  for (int i = 0; i < 80; i += 16) { ROUND_STEP_SHA512(i) }
  State[0] += a; State[1] += b; State[2] += c; State[3] += d;
  State[4] += e; State[5] += f; State[6] += g; State[7] += h;
}

// A 64-byte digest (held as 8 big-endian state words) as one padded block of a 192-byte message.
#define MK_DIGEST_BLOCK(W, ST) { \
  for (int i = 0; i < 8; i++) (W)[i] = (ST)[i]; \
  (W)[8] = 0x8000000000000000UL; \
  for (int i = 9; i < 15; i++) (W)[i] = 0UL; \
  (W)[15] = 192UL * 8UL; }

static void bip39_seed(uchar *mnemonic, int L, __global const ulong *saltw, uchar *seed) {
  uchar key[128];
  for (int x = 0; x < 128; x++) key[x] = 0;
  if (L > 128) {                       // RFC 2104: pre-hash keys longer than the block
    uchar tmp[512];
    for (int x = 0; x < 512; x++) tmp[x] = 0;
    for (int x = 0; x < L; x++) tmp[x] = mnemonic[x];
    uchar h[64];
    sha512((ulong *)tmp, L, (ulong *)h);
    for (int x = 0; x < 64; x++) key[x] = h[x];
  } else {
    for (int x = 0; x < L; x++) key[x] = mnemonic[x];
  }
  // ipad / opad midstates: computed once, reused by all 4096 HMAC halves
  ulong ist[8], ost[8], W[16], kw;
  for (int i = 0; i < 8; i++) { ist[i] = H512_0[i]; ost[i] = H512_0[i]; }
  for (int i = 0; i < 16; i++) { kw = SWAP512(((ulong *)key)[i]); W[i] = kw ^ 0x3636363636363636UL; }
  sha512_block(ist, W);
  for (int i = 0; i < 16; i++) { kw = SWAP512(((ulong *)key)[i]); W[i] = kw ^ 0x5c5c5c5c5c5c5c5cUL; }
  sha512_block(ost, W);

  ulong in[8], out[8], T[8];
  // U1 = HMAC(key, salt || INT(1)) - one host-built padded block
  for (int i = 0; i < 8; i++) in[i] = ist[i];
  for (int i = 0; i < 16; i++) W[i] = saltw[i];         /* __global -> private, once per work-item */
  sha512_block(in, W);
  MK_DIGEST_BLOCK(W, in);
  for (int i = 0; i < 8; i++) out[i] = ost[i];
  sha512_block(out, W);
  for (int i = 0; i < 8; i++) T[i] = out[i];

  for (int n = 1; n < 2048; n++) {
    MK_DIGEST_BLOCK(W, out);
    for (int i = 0; i < 8; i++) in[i] = ist[i];
    sha512_block(in, W);
    MK_DIGEST_BLOCK(W, in);
    for (int i = 0; i < 8; i++) out[i] = ost[i];
    sha512_block(out, W);
    for (int i = 0; i < 8; i++) T[i] ^= out[i];
  }
  for (int i = 0; i < 8; i++) ((ulong *)seed)[i] = SWAP512(T[i]);
}

static int eq20(uchar *a, uchar *b) {
  for (int j = 0; j < 20; j++) if (a[j] != b[j]) return 0;
  return 1;
}

// Build the mnemonic string and derive the BIP32 master key.
static void master_from_indices(__global const ushort *idx, uint NW,
                                __global const ulong *saltw, extended_private_key_t *m) {
  uchar mnemonic[256];
  int L = 0;
  for (uint w = 0; w < NW; w++) {
    ushort wi = idx[w];
    uchar wl = word_lengths[wi];
    for (int j = 0; j < wl; j++) mnemonic[L++] = words[wi][j];
    mnemonic[L++] = 32;
  }
  L--;
  uchar seed[64];
  bip39_seed(mnemonic, L, saltw, seed);
  new_master_from_seed(BITCOIN_MAINNET, seed, m);
}

// normal_private_child_from_private, but with the parent's serialized pubkey already in hand.
// Every leaf under one chain node shares that pubkey, so the stock function recomputed the same
// EC multiplication once per address. Same hoist as check_seed() in blmc.c.
static void normal_child_with_pub(extended_private_key_t *parent, uchar *ppub33,
                                  extended_private_key_t *child, uint i) {
  uchar hmacsha512_result[64] = { 0 };
  uchar hmac_input[37] = {0};
  for (int x = 0; x < 33; x++) hmac_input[x] = ppub33[x];
  hmac_input[33] = i >> 24;
  hmac_input[34] = (i & 0x00FF0000) >> 16;
  hmac_input[35] = (i & 0x0000FF00) >> 8;
  hmac_input[36] = (i & 0x000000FF);
  hmac_sha512(&parent->chain_code, 32, &hmac_input, 37, &hmacsha512_result);
  private_key_t sk;
  sk.compressed = true;
  sk.network = parent->network;
  memcpy(&sk.key, &hmacsha512_result, 32);
  secp256k1_ec_seckey_tweak_add(&sk.key, &parent->private_key.key);
  child->network = parent->network;
  child->depth = parent->depth + 1;
  child->child_number = i;
  child->private_key = sk;
  memcpy_offset(&child->chain_code, &hmacsha512_result, 32, 32);
}

// hash160 of the compressed pubkey of k; returns p+1 / FLAG|(p+1) / 0
static uint test_key(extended_private_key_t *k, uchar *tgt, uchar *cn, uint p) {
  extended_public_key_t pub;
  public_from_private(k, &pub);
  uchar ser[33];
  serialized_public_key(&pub, ser);
  uchar h[20];
  hash160(ser, 33, (char *)h);
  if (eq20(h, tgt)) return p + 1;
  if (eq20(h, cn)) return 0x80000000u | (p + 1);
  return 0;
}

__kernel void blm_check(__global const ushort *indices, const uint NW, const uint n_addr,
                        __global const uchar *target, __global const uchar *canary,
                        __global const ulong *saltw, __global uint *result) {
  uint gid = get_global_id(0);
  uchar tgt[20], cn[20];
  for (int j = 0; j < 20; j++) { tgt[j] = target[j]; cn[j] = canary[j]; }
  extended_private_key_t k;
  master_from_indices(indices + gid * NW, NW, saltw, &k);
  hardened_private_child_from_private(&k, &k, 44);
  hardened_private_child_from_private(&k, &k, 0);
  hardened_private_child_from_private(&k, &k, 0);
  normal_private_child_from_private(&k, &k, 0);
  extended_public_key_t chainpub;                 // one EC mult for the whole address range
  public_from_private(&k, &chainpub);
  uchar cpub[33];
  serialized_public_key(&chainpub, &cpub);
  uint hit = 0;
  for (uint i = 0; i < n_addr && hit == 0; i++) {
    extended_private_key_t leaf;
    normal_child_with_pub(&k, cpub, &leaf, i);
    hit = test_key(&leaf, tgt, cn, i);
  }
  result[gid] = hit;
}

// Walk a chain node's children i < n, path-ids base..base+n-1. Returns hit or 0.
static uint scan_chain(extended_private_key_t *chain, uint n, uint base, uchar *tgt, uchar *cn) {
  for (uint i = 0; i < n; i++) {
    extended_private_key_t leaf;
    normal_private_child_from_private(chain, &leaf, i);
    uint r = test_key(&leaf, tgt, cn, base + i);
    if (r) return r;
  }
  return 0;
}

// WIDE path table (must match gpu.py WIDE_PATHS and solve.py WIDE_TREE):
//   0-19  m/44'/0'/0'/0/i     20-29 m/44'/0'/0'/1/i
//  30-39  m/44'/0'/1'/0/i     40-49 m/44'/0'/1'/1/i
//  50-59  m/0'/0/i            60-69 m/0'/1/i
//  70-79  m/0/i               80-89 m/1/i
//  90-99  m/0'/0'/i'          100   m
//  101-112 m/44'/0'/0'/0/i for i = 20..31 (appended; the image's 20 and 21 live here)
__kernel void blm_check_wide(__global const ushort *indices, const uint NW, const uint n_addr,
                             __global const uchar *target, __global const uchar *canary,
                             __global const ulong *saltw, __global uint *result) {
  uint gid = get_global_id(0);
  uchar tgt[20], cn[20];
  for (int j = 0; j < 20; j++) { tgt[j] = target[j]; cn[j] = canary[j]; }
  extended_private_key_t m;
  master_from_indices(indices + gid * NW, NW, saltw, &m);
  uint hit = test_key(&m, tgt, cn, 100);                       // bare master

  extended_private_key_t a, c;
  // m/44'/0'/0'
  if (!hit) {
    hardened_private_child_from_private(&m, &a, 44);
    hardened_private_child_from_private(&a, &a, 0);
    hardened_private_child_from_private(&a, &a, 0);
    normal_private_child_from_private(&a, &c, 0); hit = scan_chain(&c, 20, 0, tgt, cn);
    if (!hit) { for (uint i = 20; i < 32 && !hit; i++) { extended_private_key_t leaf; normal_private_child_from_private(&c, &leaf, i); hit = test_key(&leaf, tgt, cn, 101 + (i - 20)); } }
    if (!hit) { normal_private_child_from_private(&a, &c, 1); hit = scan_chain(&c, 10, 20, tgt, cn); }
  }
  // m/44'/0'/1'
  if (!hit) {
    hardened_private_child_from_private(&m, &a, 44);
    hardened_private_child_from_private(&a, &a, 0);
    hardened_private_child_from_private(&a, &a, 1);
    normal_private_child_from_private(&a, &c, 0); hit = scan_chain(&c, 10, 30, tgt, cn);
    if (!hit) { normal_private_child_from_private(&a, &c, 1); hit = scan_chain(&c, 10, 40, tgt, cn); }
  }
  // m/0'/{0,1}/i
  if (!hit) {
    hardened_private_child_from_private(&m, &a, 0);
    normal_private_child_from_private(&a, &c, 0); hit = scan_chain(&c, 10, 50, tgt, cn);
    if (!hit) { normal_private_child_from_private(&a, &c, 1); hit = scan_chain(&c, 10, 60, tgt, cn); }
    // m/0'/0'/i'  (all-hardened)
    if (!hit) {
      hardened_private_child_from_private(&a, &c, 0);
      for (uint i = 0; i < 10 && !hit; i++) {
        extended_private_key_t leaf;
        hardened_private_child_from_private(&c, &leaf, i);
        hit = test_key(&leaf, tgt, cn, 90 + i);
      }
    }
  }
  // m/{0,1}/i
  if (!hit) { normal_private_child_from_private(&m, &c, 0); hit = scan_chain(&c, 10, 70, tgt, cn); }
  if (!hit) { normal_private_child_from_private(&m, &c, 1); hit = scan_chain(&c, 10, 80, tgt, cn); }
  result[gid] = hit;
}
