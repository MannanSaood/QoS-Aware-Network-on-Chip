"""Additional synthetic traffic patterns for the fresh held-out G5 (docs/SAQR_SPEC_V2.md §21).

Never used to design or tune any candidate. Same trace format, injection process
(Bernoulli per node per cycle, probability load/5, 5-flit packets) and class mix
(25 % critical) as the frozen generator in qos_common.py, which is not modified.
Meshes must be k x k with k a power of two (bit permutations).

Patterns (s = source id, (x, y) its coordinates, b = log2(k*k) bits):
  bitcomp    d = ~s                          (bit complement)
  bitrev     d = reverse of s's b bits       (bit reversal)
  shuffle    d = s rotated left by one bit   (perfect shuffle)
  tornado    (x + k/2 - 1 mod k, y + k/2 - 1 mod k)
  neighbor   (x + 1 mod k, y)
  multiflow  each source has 4 fixed destinations (seeded), chosen uniformly per packet
  mixed      each packet: 50 % to its transpose partner, 50 % uniform random
Sources whose permutation maps to themselves send to themselves (as the frozen transpose does).
"""
from pathlib import Path
import numpy as np

PATTERNS = ['bitcomp', 'bitrev', 'shuffle', 'tornado', 'neighbor', 'multiflow', 'mixed']


def _perm(k, traffic):
    n = k * k; b = n.bit_length() - 1
    assert 1 << b == n, 'bit permutations need k a power of two'
    s = np.arange(n); x, y = s % k, s // k
    if traffic == 'bitcomp':
        return (~s) & (n - 1)
    if traffic == 'bitrev':
        return np.array([int(format(v, f'0{b}b')[::-1], 2) for v in s])
    if traffic == 'shuffle':
        return ((s << 1) | (s >> (b - 1))) & (n - 1)
    if traffic == 'tornado':
        h = k // 2 - 1
        return ((y + h) % k) * k + (x + h) % k
    if traffic == 'neighbor':
        return y * k + (x + 1) % k
    raise ValueError(traffic)


def trace(path, k, load, seed, traffic, warm=5000, cycles=20000, classes=2):
    assert traffic in PATTERNS, traffic
    rng = np.random.default_rng(seed)
    n = k * k
    flows = rng.integers(0, n, (n, 4)) if traffic == 'multiflow' else None
    perm = _perm(k, traffic) if traffic not in ('multiflow', 'mixed') else None
    partner = (np.arange(n) % k) * k + np.arange(n) // k
    count = 0
    with Path(path).open('w') as out:
        for t in range(warm + cycles):
            sources = np.flatnonzero(rng.random(n) < load / 5)
            if traffic == 'multiflow':
                dest = flows[sources, rng.integers(0, 4, len(sources))]
            elif traffic == 'mixed':
                dest = np.where(rng.random(len(sources)) < .5, partner[sources], rng.integers(0, n, len(sources)))
            else:
                dest = perm[sources]
            cls = np.where(rng.random(len(sources)) < .25, 0, 1) if classes == 2 else np.zeros(len(sources), dtype=int)
            out.writelines(f'{t} {s} {d} {c}\n' for s, d, c in zip(sources, dest, cls))
            count += len(sources)
    return count
