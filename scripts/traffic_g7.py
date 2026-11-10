"""Two traffic patterns added for the fresh held-out G7 (docs/SAQR_SPEC_V2.md §23).

Never used to design, tune or select any candidate. Same trace format, injection process and
class mix as scripts/traffic_g6.py, which is not modified.
  antitranspose  (x, y) -> (k-1-y, k-1-x)        (reflection about the anti-diagonal)
  unshuffle      d = s rotated right by one bit  (inverse perfect shuffle)
"""
from pathlib import Path
import numpy as np

PATTERNS = ['antitranspose', 'unshuffle']


def trace(path, k, load, seed, traffic, warm=5000, cycles=20000):
    assert traffic in PATTERNS, traffic
    rng = np.random.default_rng(seed)
    n = k * k; b = n.bit_length() - 1
    assert 1 << b == n, 'bit permutations need k a power of two'
    s = np.arange(n); x, y = s % k, s // k
    if traffic == 'antitranspose':
        perm = (k - 1 - x) * k + (k - 1 - y)
    else:
        perm = (s >> 1) | ((s & 1) << (b - 1))
    count = 0
    with Path(path).open('w') as out:
        for t in range(warm + cycles):
            sources = np.flatnonzero(rng.random(n) < load / 5)
            dest = perm[sources]
            cls = np.where(rng.random(len(sources)) < .25, 0, 1)
            out.writelines(f'{t} {s_} {d} {c}\n' for s_, d, c in zip(sources, dest, cls))
            count += len(sources)
    return count
