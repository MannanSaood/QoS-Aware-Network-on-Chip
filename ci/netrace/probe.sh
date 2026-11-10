#!/bin/bash
# Netrace probe (runs on GitHub Actions only): download the Netrace 1.0 library and the three
# smallest PARSEC traces from the authors' site, print the library header and README, and report
# per-trace statistics (regions, packet types and sizes, region-of-interest injection rate).
# Nothing downloaded here is committed to the repository.
set -euo pipefail
OUT=${OUT:-$PWD/netrace_out}; mkdir -p "$OUT" nt && cd nt
BASE=https://www.cs.utexas.edu/~netrace/download
curl -fsSL -o netrace-1.0.tar.bz2 "$BASE/netrace-1.0.tar.bz2"
for t in blackscholes_64c_simsmall fluidanimate_64c_simsmall x264_64c_simsmall; do curl -fsSL -o $t.tra.bz2 "$BASE/$t.tra.bz2"; done
sha256sum *.bz2 | tee "$OUT/sha256.txt"; ls -la | tee -a "$OUT/sha256.txt"
tar xjf netrace-1.0.tar.bz2; find . -maxdepth 3 -type f | grep -v '\.tra\.bz2$' | tee "$OUT/files.txt"
src=$(dirname "$(find . -name netrace.h | head -1)")
cp "$src/netrace.h" "$OUT/"; cp "$src"/README* "$OUT/" 2>/dev/null || true; cp "$src/netrace.c" "$OUT/"
cp "$GITHUB_WORKSPACE/ci/netrace/stats.c" stats.c
gcc -O2 -I"$src" stats.c "$src/netrace.c" -o stats 2> "$OUT/stats_build.log" || { cat "$OUT/stats_build.log"; exit 1; }
for t in blackscholes_64c_simsmall fluidanimate_64c_simsmall x264_64c_simsmall; do echo "== $t"; ./stats $t.tra.bz2; done 2>&1 | tee "$OUT/stats.txt"
