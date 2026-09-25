#!/bin/zsh
# Builds blmc (optimized) and blmc_asan (AddressSanitizer + UBSan, for the correctness checks).
set -e
cd "$(dirname "$0")"
SSL=$(brew --prefix openssl@3); SECP=$(brew --prefix secp256k1)
# Apple Silicon: enable the ARMv8.2 SHA-512 instructions (sha512_fast.h falls back to OpenSSL otherwise)
[[ $(uname -m) == arm64 ]] && ARCH=(-march=armv8.2-a+sha3) || ARCH=()
FLAGS=("${ARCH[@]}" -std=c11 -Wall -Wextra -Wno-unused-parameter -Wno-deprecated-declarations -I$SSL/include -I$SECP/include -L$SSL/lib -L$SECP/lib -lcrypto -lsecp256k1 -lpthread)
clang -O2 ${NWAY:+-DNWAY=$NWAY} -o blmc blmc.c "${FLAGS[@]}"
clang -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer ${NWAY:+-DNWAY=$NWAY} -o blmc_asan blmc.c "${FLAGS[@]}"
echo "built: blmc (O2), blmc_asan (ASan+UBSan)"
