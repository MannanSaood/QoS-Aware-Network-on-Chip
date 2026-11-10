"""Two traffic patterns added for the fresh held-out G6 (docs/SAQR_SPEC_V2.md §22).

Never used to design, tune or select any candidate. Same trace format, injection process
(Bernoulli per node per cycle, probability load/5, 5-flit packets) and class mix (25 %
critical) as scripts/traffic_ext.py, which is not modified.
  butterfly  d = s with its most and least significant bits swapped
  randperm   a random permutation of the nodes, drawn once per trace from the trace seed
"""
from pathlib import Path
import numpy as np

PATTERNS = ['butterfly', 'randperm']


def trace(path, k, load, seed, traffic, warm=5000, cycles=20000):
    assert traffic in PATTERNS, traffic
    rng = np.random.default_rng(seed)
    n = k * k; b = n.bit_length() - 1
    assert 1 << b == n, 'bit permutations need k a power of two'
    s = np.arange(n)
    if traffic == 'butterfly':
        hi, lo = (s >> (b - 1)) & 1, s & 1
        perm = (s & ~((1 << (b - 1)) | 1)) | (lo << (b - 1)) | hi
    else:
        perm = rng.permutation(n)
    count = 0
    with Path(path).open('w') as out:
        for t in range(warm + cycles):
            sources = np.flatnonzero(rng.random(n) < load / 5)
            dest = perm[sources]
            cls = np.where(rng.random(len(sources)) < .25, 0, 1)
            out.writelines(f'{t} {s_} {d} {c}\n' for s_, d, c in zip(sources, dest, cls))
            count += len(sources)
    return count
