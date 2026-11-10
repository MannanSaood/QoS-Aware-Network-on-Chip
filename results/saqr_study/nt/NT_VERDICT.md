# Netrace (PARSEC) traces: best-or-tied-best verdict

Seeds [601, 602, 603]; meshes [8]; 3 traffic patterns; comparators ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst', 'dbar', 'footprint', 'o1turn']; candidates ['saqr_h', 'saqr_c'].
Complete (mesh, traffic) groups: 3 of 3. Safety: integrity errors 0.

Each cell: passes / checks (strict wins = throughput lower bound > +3 % over the best comparator).

## saqr_h

| traffic | BT-T (throughput vs best) | strict wins | BT-L (crit p99 vs best) | never worse than XY |
|---|---:|---:|---:|---:|
| nt_blackscholes | 7/9 | 0/9 | 3/4 | 7/9 |
| nt_fluidanimate | 8/9 | 0/9 | 1/1 | 9/9 |
| nt_x264 | 6/9 | 0/9 | 3/4 | 9/9 |
| **all** | **21/27** | **0/27** | **7/9** | **25/27** |

| failed check | where | vs | value | limit |
|---|---|---|---:|---:|
| BT-L | k8 nt_blackscholes l1 | topsis | 12.00 | 11.50 |
| BT-T | k8 nt_blackscholes l7 | duato | -5.24 | -3.00 |
| XY | k8 nt_blackscholes l7 | xy | -4.08 | -3.00 |
| BT-T | k8 nt_blackscholes l8 | duato | -5.73 | -3.00 |
| XY | k8 nt_blackscholes l8 | xy | -4.48 | -3.00 |
| BT-T | k8 nt_fluidanimate l6 | dbar | -3.07 | -3.00 |
| BT-L | k8 nt_x264 l1 | duato | 11.00 | 7.80 |
| BT-T | k8 nt_x264 l4 | oefixed | -7.78 | -3.00 |
| BT-T | k8 nt_x264 l5 | footprint | -5.72 | -3.00 |
| BT-T | k8 nt_x264 l7 | footprint | -3.61 | -3.00 |

## saqr_c

| traffic | BT-T (throughput vs best) | strict wins | BT-L (crit p99 vs best) | never worse than XY |
|---|---:|---:|---:|---:|
| nt_blackscholes | 9/9 | 0/9 | 2/4 | 9/9 |
| nt_fluidanimate | 7/9 | 0/9 | 1/1 | 9/9 |
| nt_x264 | 3/9 | 0/9 | 1/4 | 9/9 |
| **all** | **19/27** | **0/27** | **4/9** | **27/27** |

| failed check | where | vs | value | limit |
|---|---|---|---:|---:|
| BT-L | k8 nt_blackscholes l1 | topsis | 20.00 | 11.50 |
| BT-L | k8 nt_blackscholes l3 | footprint | 110.00 | 94.30 |
| BT-T | k8 nt_fluidanimate l6 | dbar | -8.21 | -3.00 |
| BT-T | k8 nt_fluidanimate l7 | duato | -3.32 | -3.00 |
| BT-L | k8 nt_x264 l1 | duato | 15.00 | 7.80 |
| BT-L | k8 nt_x264 l2 | footprint | 78.00 | 20.90 |
| BT-T | k8 nt_x264 l3 | dyad | -5.74 | -3.00 |
| BT-L | k8 nt_x264 l3 | footprint | 979.00 | 272.10 |
| BT-T | k8 nt_x264 l4 | oefixed | -12.79 | -3.00 |
| BT-T | k8 nt_x264 l5 | footprint | -10.99 | -3.00 |
| BT-T | k8 nt_x264 l6 | dbar | -5.51 | -3.00 |
| BT-T | k8 nt_x264 l7 | footprint | -7.28 | -3.00 |
| BT-T | k8 nt_x264 l8 | footprint | -3.88 | -3.00 |

