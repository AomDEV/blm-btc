// BLM puzzle GPU kernels. Appended after the 11 base files from bip39-solver-gpu
// (common, ripemd, sha2, mnemonic_constants, secp256k1_*, address).
//
// Both kernels take NW ushort word-indices per work-item (any BIP39 length),
// a real target hash160 and a canary hash160, and write result[gid]:
//     p+1              real hit at path-id p
//     0x80000000|(p+1) canary hit at path-id p   (proves the launch ran)
//     0                nothing
//
// blm_check      : narrow  - m/44'/0'/0'/0/i, i < n_addr           (path-id = i)
// blm_check_wide : wide    - the same 101 paths as the CPU's WIDE_TREE (ids below)

static void bip39_seed(uchar *mnemonic, int L, uchar *seed) {
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
  uchar ipad[128], opad[128];
  for (int x = 0; x < 128; x++) { ipad[x] = key[x] ^ 0x36; opad[x] = key[x] ^ 0x5c; }
  uchar salt[12] = { 109, 110, 101, 109, 111, 110, 105, 99, 0, 0, 0, 1 };
  uchar joined[256];
  uchar r[64];
  for (int x = 0; x < 256; x++) joined[x] = 0;
  for (int x = 0; x < 128; x++) joined[x] = ipad[x];
  for (int x = 0; x < 12; x++) joined[128 + x] = salt[x];
  sha512((ulong *)joined, 140, (ulong *)r);
  copy_pad_previous(opad, r, joined);
  sha512((ulong *)joined, 192, (ulong *)r);
  for (int x = 0; x < 64; x++) seed[x] = r[x];
  for (int n = 1; n < 2048; n++) {
    copy_pad_previous(ipad, r, joined);
    sha512((ulong *)joined, 192, (ulong *)r);
    copy_pad_previous(opad, r, joined);
    sha512((ulong *)joined, 192, (ulong *)r);
    for (int x = 0; x < 64; x++) seed[x] ^= r[x];
  }
}

static int eq20(uchar *a, uchar *b) {
  for (int j = 0; j < 20; j++) if (a[j] != b[j]) return 0;
  return 1;
}

// Build the mnemonic string and derive the BIP32 master key.
static void master_from_indices(__global const ushort *idx, uint NW, extended_private_key_t *m) {
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
  bip39_seed(mnemonic, L, seed);
  new_master_from_seed(BITCOIN_MAINNET, seed, m);
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
                        __global uint *result) {
  uint gid = get_global_id(0);
  uchar tgt[20], cn[20];
  for (int j = 0; j < 20; j++) { tgt[j] = target[j]; cn[j] = canary[j]; }
  extended_private_key_t k;
  master_from_indices(indices + gid * NW, NW, &k);
  hardened_private_child_from_private(&k, &k, 44);
  hardened_private_child_from_private(&k, &k, 0);
  hardened_private_child_from_private(&k, &k, 0);
  normal_private_child_from_private(&k, &k, 0);
  uint hit = 0;
  for (uint i = 0; i < n_addr && hit == 0; i++) {
    extended_private_key_t leaf;
    normal_private_child_from_private(&k, &leaf, i);
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
                             __global uint *result) {
  uint gid = get_global_id(0);
  uchar tgt[20], cn[20];
  for (int j = 0; j < 20; j++) { tgt[j] = target[j]; cn[j] = canary[j]; }
  extended_private_key_t m;
  master_from_indices(indices + gid * NW, NW, &m);
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
