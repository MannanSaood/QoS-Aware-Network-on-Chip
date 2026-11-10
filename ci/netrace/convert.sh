#!/bin/bash
# Netrace conversion (GitHub Actions only): download the Netrace 1.0 library and three PARSEC
# traces, check them against the hashes recorded by the probe, and convert the region of interest
# into demand traces for the 8x8 study (ci/netrace/convert.c; docs/SAQR_SPEC_V2.md §24).
# Output: $OUT/traces/*.txt plus manifest.json (per-trace packets, offered load, sha256).
set -euo pipefail
OUT=${OUT:-$PWD/nt_out}; mkdir -p "$OUT/traces" nt && cd nt
BASE=https://www.cs.utexas.edu/~netrace/download
declare -A SHA=(
  [netrace-1.0.tar.bz2]=04a2cb58afd77e56d19078bcd22c86a7d4018a43ed36ce9da508fbeb1225f6af
  [blackscholes_64c_simsmall.tra.bz2]=10bcebb7c21b7787defa3faf9ecf684d70a97a00237915ca9c5035372cf9141f
  [fluidanimate_64c_simsmall.tra.bz2]=fb9929f932becafad48129873d4cce3629c98e213bd4d15d33021ca13cd6e9fa
  [x264_64c_simsmall.tra.bz2]=b2b25680a8a03a2d5bdfb7c728aae85894f08dba91d2fd4053fcd98d393ec90f )
for f in "${!SHA[@]}"; do
  curl -fsSL -o "$f" "$BASE/$f"
  echo "${SHA[$f]}  $f" | sha256sum -c -
done
tar xjf netrace-1.0.tar.bz2
src=$(dirname "$(find . -name netrace.h | head -1)")
gcc -O2 -I"$src" "$GITHUB_WORKSPACE/ci/netrace/convert.c" "$src/netrace.c" -o convert
# One window per benchmark, compressed by F so the full window offers ~0.4-0.5 flits/node/cycle;
# nine load points keep 2 % ... 100 % of its packets (permille).
declare -A F=( [blackscholes]=98 [fluidanimate]=152 [x264]=303 )
KEEP="20 50 100 200 300 400 600 800 1000"
for b in blackscholes fluidanimate x264; do
  ./convert ${b}_64c_simsmall.tra.bz2 "$OUT/traces/$b" 100 ${F[$b]} $KEEP 2>/dev/null | sed "s/^/$b ${F[$b]} /" | tee -a "$OUT/counts.txt"
done
cd "$OUT" && python3 - <<'PY'
import hashlib, json
from pathlib import Path
m = {}
for line in Path('counts.txt').read_text().split('\n'):
    if not line.strip(): continue
    b, f, q, n, crit = line.split()
    p = Path('traces') / f'{b}_q{q}.txt'
    m[f'{b}_q{q}'] = dict(benchmark=b, factor=int(f), keep_permille=int(q), packets=int(n), critical=int(crit),
                         offered_flits_per_node_cycle=round(int(n) * 5 / (64 * 25000), 6),
                         sha256=hashlib.sha256(p.read_bytes()).hexdigest())
Path('manifest.json').write_text(json.dumps(m, indent=1, sort_keys=True) + '\n')
for k, v in sorted(m.items(), key=lambda kv: (kv[1]['benchmark'], kv[1]['keep_permille'])): print(k, v['offered_flits_per_node_cycle'], v['packets'])
PY
