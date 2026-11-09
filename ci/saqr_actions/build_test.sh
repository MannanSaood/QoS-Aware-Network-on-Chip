#!/bin/bash
# Build + test job for the §21 comparator binary, run on GitHub Actions (saqr-build workflow).
#  1. rebuild the frozen QoS tree's derivative with DBAR/Footprint routes (scripts/setup_saqr_x.py),
#     starting from the frozen source tree shipped byte-exact in qos_tree.tar.gz (its hashes are
#     checked by the setup script against the frozen build manifest);
#  2. every unit test (CHR, SAQR, SAQR-SC, SAQR-H, comparators, mechanical deadlock check);
#  3. RTL equivalence: rtl/saqr/saqr_h_classifier.sv vs the C++ model, with and without the tracker;
#  4. simulator equivalence + smoke (x_smoke.py): the new binary reproduces the frozen binaries
#     bit for bit on shared routes, and DBAR/Footprint run clean (invariants, integrity).
# Outputs go to $OUT (uploaded as the build artifact).
set -euo pipefail
OUT=${OUT:-$PWD/build_out}; mkdir -p "$OUT"
tar xzf ci/saqr_actions/bundle.tar.gz
tar xzf ci/saqr_actions/qos_tree.tar.gz
log(){ echo "== $*" | tee -a "$OUT/build_test.log"; }

log "build comparator binary"
python3 -s scripts/setup_saqr_x.py --jobs 4 > "$OUT/setup_saqr_x.log" 2>&1 || { tail -40 "$OUT/setup_saqr_x.log"; exit 1; }
tail -6 "$OUT/setup_saqr_x.log" | tee -a "$OUT/build_test.log"
cp .deps/booksim2_saqr_x/src/booksim "$OUT/booksim_saqr_x"
cp .deps/booksim2_saqr_x/build_manifest.json "$OUT/build_manifest_saqr_x.json"
sha256sum "$OUT/booksim_saqr_x" | tee -a "$OUT/build_test.log"

log "unit tests"
mkdir -p /tmp/ut
for t in chr_test saqr_test saqr_src_test saqr_hot_test comparators_test saqr_deadlock_check; do
  g++ -std=c++17 -O2 -Wall tests/$t.cpp -o /tmp/ut/$t
  /tmp/ut/$t | tail -2 | tee -a "$OUT/build_test.log"
done

log "RTL equivalence (iverilog)"
g++ -std=c++17 -O2 tests/rtl/saqr_h_vectors.cpp -o /tmp/ut/vec
for h in 0 1; do
  /tmp/ut/vec $h /tmp/ut/vec$h.txt | tee -a "$OUT/build_test.log"
  iverilog -g2012 -P saqr_h_classifier_tb.HOT_EN=$h -o /tmp/ut/tb$h rtl/saqr/saqr_h_classifier.sv tests/rtl/saqr_h_classifier_tb.sv
  vvp /tmp/ut/tb$h +vectors=/tmp/ut/vec$h.txt | tee /tmp/ut/tb$h.log | tee -a "$OUT/build_test.log"
  grep -q '^PASS' /tmp/ut/tb$h.log
done

log "simulator equivalence + smoke"
cd ci/saqr_actions && python3 -s x_smoke.py "$OUT/x_smoke.json" | tee -a "$OUT/build_test.log"
