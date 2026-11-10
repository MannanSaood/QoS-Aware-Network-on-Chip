# G6 fresh held-out: best-or-tied-best verdict

Seeds [401, 402, 403, 404, 405]; meshes [4, 8, 16, 32]; 15 traffic patterns; comparators ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst', 'dbar', 'footprint', 'o1turn']; candidates ['saqr_c', 'saqr_h'].
Complete (mesh, traffic) groups: 60 of 60. Safety: integrity errors 0.

Each cell: passes / checks (strict wins = throughput lower bound > +3 % over the best comparator).

## saqr_c

| traffic | BT-T (throughput vs best) | strict wins | BT-L (crit p99 vs best) | never worse than XY |
|---|---:|---:|---:|---:|
| uniform | 36/36 | 0/36 | 36/36 | 36/36 |
| transpose | 34/36 | 8/36 | 35/36 | 36/36 |
| bursty | 36/36 | 0/36 | 36/36 | 36/36 |
| hotspot_corner | 33/36 | 0/36 | 36/36 | 36/36 |
| hotspot_edge | 27/36 | 0/36 | 36/36 | 36/36 |
| hotspot_center | 36/36 | 0/36 | 36/36 | 36/36 |
| bitcomp | 36/36 | 0/36 | 36/36 | 36/36 |
| bitrev | 33/36 | 7/36 | 35/36 | 36/36 |
| shuffle | 25/36 | 0/36 | 34/36 | 36/36 |
| tornado | 33/36 | 0/36 | 36/36 | 36/36 |
| neighbor | 36/36 | 0/36 | 36/36 | 36/36 |
| multiflow | 32/36 | 0/36 | 35/36 | 33/36 |
| mixed | 27/36 | 1/36 | 36/36 | 30/36 |
| butterfly | 24/36 | 0/36 | 33/36 | 36/36 |
| randperm | 31/36 | 0/36 | 33/36 | 33/36 |
| **all** | **479/540** | **16/540** | **529/540** | **528/540** |

| failed check | where | vs | value | limit |
|---|---|---|---:|---:|
| BT-T | k16 butterfly l6 | duato | -9.50 | -3.00 |
| BT-T | k16 butterfly l7 | duato | -8.52 | -3.00 |
| BT-T | k16 butterfly l8 | o1turn | -8.92 | -3.00 |
| BT-T | k16 hotspot_edge l5 | topsis | -8.04 | -3.00 |
| BT-T | k16 hotspot_edge l6 | oefixed | -5.73 | -3.00 |
| BT-T | k16 hotspot_edge l7 | oefixed | -3.15 | -3.00 |
| BT-T | k16 mixed l7 | o1turn | -5.09 | -3.00 |
| BT-T | k16 mixed l8 | o1turn | -6.64 | -3.00 |
| BT-T | k16 shuffle l5 | dbar | -6.95 | -3.00 |
| BT-T | k16 shuffle l6 | oefixed | -3.27 | -3.00 |
| BT-T | k16 shuffle l7 | oefixed | -3.42 | -3.00 |
| BT-T | k16 shuffle l8 | dbar | -5.17 | -3.00 |
| BT-T | k32 butterfly l6 | o1turn | -7.44 | -3.00 |
| BT-T | k32 butterfly l7 | o1turn | -8.48 | -3.00 |
| BT-T | k32 butterfly l8 | o1turn | -9.35 | -3.00 |
| BT-T | k32 hotspot_corner l6 | dbar | -6.40 | -3.00 |
| BT-T | k32 hotspot_corner l7 | dbar | -5.93 | -3.00 |
| BT-T | k32 hotspot_corner l8 | dbar | -5.64 | -3.00 |
| BT-T | k32 hotspot_edge l5 | topsis | -8.13 | -3.00 |
| BT-T | k32 hotspot_edge l6 | oefixed | -8.48 | -3.00 |
| BT-T | k32 hotspot_edge l7 | oefixed | -6.68 | -3.00 |
| BT-T | k32 hotspot_edge l8 | oefixed | -3.09 | -3.00 |
| BT-T | k32 mixed l8 | o1turn | -3.58 | -3.00 |
| BT-T | k32 shuffle l5 | dbar | -9.09 | -3.00 |
| BT-T | k32 tornado l6 | o1turn | -19.99 | -3.00 |
| BT-T | k32 tornado l7 | o1turn | -19.79 | -3.00 |
| BT-T | k32 tornado l8 | o1turn | -16.28 | -3.00 |
| BT-T | k4 bitrev l6 | topsis | -8.15 | -3.00 |
| BT-T | k4 bitrev l7 | topsis | -7.66 | -3.00 |
| BT-T | k4 bitrev l8 | topsis | -7.30 | -3.00 |
| BT-L | k4 bitrev l8 | topsis | 7.96 | 5.60 |
| BT-T | k4 butterfly l6 | dbar | -13.02 | -3.00 |
| BT-T | k4 butterfly l7 | dbar | -11.32 | -3.00 |
| BT-L | k4 butterfly l7 | duato | 5.56 | 5.00 |
| BT-T | k4 butterfly l8 | dbar | -10.56 | -3.00 |
| BT-L | k4 butterfly l8 | duato | 15.18 | 5.00 |
| BT-T | k4 mixed l6 | dbar | -15.88 | -3.00 |
| XY | k4 mixed l6 | xy | -11.23 | -3.00 |
| BT-T | k4 mixed l7 | dbar | -6.31 | -3.00 |
| XY | k4 mixed l7 | xy | -3.89 | -3.00 |
| BT-T | k4 mixed l8 | dbar | -8.29 | -3.00 |
| XY | k4 mixed l8 | xy | -4.87 | -3.00 |
| BT-T | k4 multiflow l8 | dbar | -6.16 | -3.00 |
| BT-L | k4 multiflow l8 | footprint | 6.46 | 5.74 |
| BT-T | k4 randperm l6 | dbar | -12.06 | -3.00 |
| BT-T | k4 randperm l7 | xy | -4.96 | -3.00 |
| BT-L | k4 randperm l7 | westfirst | 5.18 | 5.00 |
| XY | k4 randperm l7 | xy | -4.96 | -3.00 |
| BT-T | k4 randperm l8 | xy | -6.20 | -3.00 |
| BT-L | k4 randperm l8 | footprint | 15.63 | 5.46 |
| XY | k4 randperm l8 | xy | -6.20 | -3.00 |
| BT-T | k4 shuffle l6 | topsis | -9.26 | -3.00 |
| BT-T | k4 shuffle l7 | westfirst | -5.30 | -3.00 |
| BT-T | k4 shuffle l8 | oefixed | -3.38 | -3.00 |
| BT-L | k4 shuffle l8 | westfirst | 5.82 | 5.00 |
| BT-T | k4 transpose l6 | dbar | -5.96 | -3.00 |
| BT-T | k4 transpose l7 | footprint | -3.47 | -3.00 |
| BT-L | k4 transpose l8 | topsis | 6.42 | 5.72 |
| BT-T | k8 butterfly l6 | duato | -11.96 | -3.00 |
| BT-T | k8 butterfly l7 | topsis | -11.00 | -3.00 |
| BT-T | k8 butterfly l8 | duato | -9.64 | -3.00 |
| BT-L | k8 butterfly l8 | dyad | 6.42 | 6.06 |
| BT-T | k8 hotspot_edge l5 | topsis | -5.87 | -3.00 |
| BT-T | k8 hotspot_edge l6 | dyad | -3.14 | -3.00 |
| BT-T | k8 mixed l6 | dbar | -13.95 | -3.00 |
| XY | k8 mixed l6 | xy | -7.43 | -3.00 |
| BT-T | k8 mixed l7 | dbar | -11.69 | -3.00 |
| XY | k8 mixed l7 | xy | -9.73 | -3.00 |
| BT-T | k8 mixed l8 | o1turn | -10.39 | -3.00 |
| XY | k8 mixed l8 | xy | -9.18 | -3.00 |
| BT-T | k8 multiflow l6 | xy | -4.46 | -3.00 |
| XY | k8 multiflow l6 | xy | -4.46 | -3.00 |
| BT-T | k8 multiflow l7 | xy | -6.33 | -3.00 |
| XY | k8 multiflow l7 | xy | -6.33 | -3.00 |
| BT-T | k8 multiflow l8 | xy | -5.34 | -3.00 |
| XY | k8 multiflow l8 | xy | -5.34 | -3.00 |
| BT-T | k8 randperm l5 | dbar | -3.38 | -3.00 |
| BT-T | k8 randperm l8 | xy | -3.01 | -3.00 |
| BT-L | k8 randperm l8 | westfirst | 9.85 | 8.02 |
| XY | k8 randperm l8 | xy | -3.01 | -3.00 |
| BT-T | k8 shuffle l6 | topsis | -11.60 | -3.00 |
| BT-T | k8 shuffle l7 | duato | -8.50 | -3.00 |
| BT-T | k8 shuffle l8 | duato | -9.74 | -3.00 |
| BT-L | k8 shuffle l8 | dyad | 8.82 | 6.60 |

## saqr_h

| traffic | BT-T (throughput vs best) | strict wins | BT-L (crit p99 vs best) | never worse than XY |
|---|---:|---:|---:|---:|
| uniform | 36/36 | 0/36 | 36/36 | 36/36 |
| transpose | 36/36 | 10/36 | 36/36 | 36/36 |
| bursty | 36/36 | 0/36 | 36/36 | 36/36 |
| hotspot_corner | 33/36 | 0/36 | 36/36 | 36/36 |
| hotspot_edge | 31/36 | 0/36 | 36/36 | 36/36 |
| hotspot_center | 36/36 | 0/36 | 36/36 | 36/36 |
| bitcomp | 18/36 | 0/36 | 36/36 | 18/36 |
| bitrev | 36/36 | 11/36 | 36/36 | 36/36 |
| shuffle | 29/36 | 0/36 | 36/36 | 34/36 |
| tornado | 22/36 | 0/36 | 36/36 | 22/36 |
| neighbor | 36/36 | 0/36 | 36/36 | 36/36 |
| multiflow | 25/36 | 0/36 | 36/36 | 24/36 |
| mixed | 24/36 | 0/36 | 36/36 | 27/36 |
| butterfly | 36/36 | 8/36 | 36/36 | 36/36 |
| randperm | 24/36 | 0/36 | 36/36 | 25/36 |
| **all** | **458/540** | **29/540** | **540/540** | **474/540** |

| failed check | where | vs | value | limit |
|---|---|---|---:|---:|
| BT-T | k16 bitcomp l4 | xy | -7.31 | -3.00 |
| XY | k16 bitcomp l4 | xy | -7.31 | -3.00 |
| BT-T | k16 bitcomp l5 | xy | -19.93 | -3.00 |
| XY | k16 bitcomp l5 | xy | -19.93 | -3.00 |
| BT-T | k16 bitcomp l6 | xy | -15.55 | -3.00 |
| XY | k16 bitcomp l6 | xy | -15.55 | -3.00 |
| BT-T | k16 bitcomp l7 | xy | -13.38 | -3.00 |
| XY | k16 bitcomp l7 | xy | -13.38 | -3.00 |
| BT-T | k16 bitcomp l8 | xy | -12.48 | -3.00 |
| XY | k16 bitcomp l8 | xy | -12.48 | -3.00 |
| BT-T | k16 hotspot_edge l5 | topsis | -3.37 | -3.00 |
| BT-T | k16 mixed l6 | dbar | -13.55 | -3.00 |
| XY | k16 mixed l6 | xy | -8.37 | -3.00 |
| BT-T | k16 mixed l7 | o1turn | -14.77 | -3.00 |
| XY | k16 mixed l7 | xy | -10.57 | -3.00 |
| BT-T | k16 mixed l8 | o1turn | -13.87 | -3.00 |
| XY | k16 mixed l8 | xy | -7.52 | -3.00 |
| BT-T | k16 multiflow l6 | xy | -19.43 | -3.00 |
| XY | k16 multiflow l6 | xy | -19.43 | -3.00 |
| BT-T | k16 multiflow l7 | xy | -18.00 | -3.00 |
| XY | k16 multiflow l7 | xy | -18.00 | -3.00 |
| BT-T | k16 multiflow l8 | xy | -14.77 | -3.00 |
| XY | k16 multiflow l8 | xy | -14.77 | -3.00 |
| BT-T | k16 randperm l6 | xy | -19.86 | -3.00 |
| XY | k16 randperm l6 | xy | -19.86 | -3.00 |
| BT-T | k16 randperm l7 | xy | -18.76 | -3.00 |
| XY | k16 randperm l7 | xy | -18.76 | -3.00 |
| BT-T | k16 randperm l8 | xy | -15.82 | -3.00 |
| XY | k16 randperm l8 | xy | -15.82 | -3.00 |
| BT-T | k16 tornado l5 | xy | -30.25 | -3.00 |
| XY | k16 tornado l5 | xy | -30.25 | -3.00 |
| BT-T | k16 tornado l6 | xy | -20.60 | -3.00 |
| XY | k16 tornado l6 | xy | -20.60 | -3.00 |
| BT-T | k16 tornado l7 | xy | -16.65 | -3.00 |
| XY | k16 tornado l7 | xy | -16.65 | -3.00 |
| BT-T | k16 tornado l8 | xy | -13.69 | -3.00 |
| XY | k16 tornado l8 | xy | -13.69 | -3.00 |
| BT-T | k32 bitcomp l4 | xy | -13.17 | -3.00 |
| XY | k32 bitcomp l4 | xy | -13.17 | -3.00 |
| BT-T | k32 bitcomp l5 | xy | -17.15 | -3.00 |
| XY | k32 bitcomp l5 | xy | -17.15 | -3.00 |
| BT-T | k32 bitcomp l6 | xy | -11.59 | -3.00 |
| XY | k32 bitcomp l6 | xy | -11.59 | -3.00 |
| BT-T | k32 bitcomp l7 | xy | -9.98 | -3.00 |
| XY | k32 bitcomp l7 | xy | -9.98 | -3.00 |
| BT-T | k32 bitcomp l8 | xy | -10.84 | -3.00 |
| XY | k32 bitcomp l8 | xy | -10.84 | -3.00 |
| BT-T | k32 hotspot_corner l6 | dbar | -5.89 | -3.00 |
| BT-T | k32 hotspot_corner l7 | dbar | -5.96 | -3.00 |
| BT-T | k32 hotspot_corner l8 | dbar | -4.71 | -3.00 |
| BT-T | k32 hotspot_edge l5 | topsis | -5.25 | -3.00 |
| BT-T | k32 hotspot_edge l6 | oefixed | -5.73 | -3.00 |
| BT-T | k32 hotspot_edge l7 | oefixed | -5.03 | -3.00 |
| BT-T | k32 hotspot_edge l8 | oefixed | -3.30 | -3.00 |
| BT-T | k32 mixed l6 | o1turn | -11.47 | -3.00 |
| XY | k32 mixed l6 | xy | -5.27 | -3.00 |
| BT-T | k32 mixed l7 | o1turn | -14.61 | -3.00 |
| XY | k32 mixed l7 | xy | -6.71 | -3.00 |
| BT-T | k32 mixed l8 | o1turn | -14.82 | -3.00 |
| XY | k32 mixed l8 | xy | -5.51 | -3.00 |
| BT-T | k32 multiflow l6 | xy | -27.09 | -3.00 |
| XY | k32 multiflow l6 | xy | -27.09 | -3.00 |
| BT-T | k32 multiflow l7 | xy | -22.19 | -3.00 |
| XY | k32 multiflow l7 | xy | -22.19 | -3.00 |
| BT-T | k32 multiflow l8 | xy | -19.19 | -3.00 |
| XY | k32 multiflow l8 | xy | -19.19 | -3.00 |
| BT-T | k32 randperm l6 | xy | -27.54 | -3.00 |
| XY | k32 randperm l6 | xy | -27.54 | -3.00 |
| BT-T | k32 randperm l7 | xy | -25.25 | -3.00 |
| XY | k32 randperm l7 | xy | -25.25 | -3.00 |
| BT-T | k32 randperm l8 | xy | -21.56 | -3.00 |
| XY | k32 randperm l8 | xy | -21.56 | -3.00 |
| BT-T | k32 shuffle l6 | xy | -3.36 | -3.00 |
| XY | k32 shuffle l6 | xy | -3.36 | -3.00 |
| BT-T | k32 tornado l5 | xy | -37.26 | -3.00 |
| XY | k32 tornado l5 | xy | -37.26 | -3.00 |
| BT-T | k32 tornado l6 | o1turn | -37.11 | -3.00 |
| XY | k32 tornado l6 | xy | -21.89 | -3.00 |
| BT-T | k32 tornado l7 | o1turn | -31.53 | -3.00 |
| XY | k32 tornado l7 | xy | -15.31 | -3.00 |
| BT-T | k32 tornado l8 | o1turn | -24.63 | -3.00 |
| XY | k32 tornado l8 | xy | -10.64 | -3.00 |
| BT-T | k4 bitcomp l5 | xy | -14.34 | -3.00 |
| XY | k4 bitcomp l5 | xy | -14.34 | -3.00 |
| BT-T | k4 bitcomp l6 | xy | -13.41 | -3.00 |
| XY | k4 bitcomp l6 | xy | -13.41 | -3.00 |
| BT-T | k4 bitcomp l7 | xy | -11.81 | -3.00 |
| XY | k4 bitcomp l7 | xy | -11.81 | -3.00 |
| BT-T | k4 bitcomp l8 | xy | -10.26 | -3.00 |
| XY | k4 bitcomp l8 | xy | -10.26 | -3.00 |
| BT-T | k4 mixed l6 | dbar | -4.80 | -3.00 |
| BT-T | k4 mixed l7 | dbar | -4.08 | -3.00 |
| BT-T | k4 mixed l8 | dbar | -3.06 | -3.00 |
| BT-T | k4 multiflow l6 | xy | -5.29 | -3.00 |
| XY | k4 multiflow l6 | xy | -5.29 | -3.00 |
| BT-T | k4 multiflow l7 | xy | -5.22 | -3.00 |
| XY | k4 multiflow l7 | xy | -5.22 | -3.00 |
| XY | k4 multiflow l8 | xy | -4.94 | -3.00 |
| BT-T | k4 randperm l6 | dbar | -4.68 | -3.00 |
| BT-T | k4 randperm l7 | xy | -13.02 | -3.00 |
| XY | k4 randperm l7 | xy | -13.02 | -3.00 |
| BT-T | k4 randperm l8 | xy | -15.09 | -3.00 |
| XY | k4 randperm l8 | xy | -15.09 | -3.00 |
| BT-T | k4 shuffle l6 | topsis | -5.46 | -3.00 |
| BT-T | k4 shuffle l7 | westfirst | -6.91 | -3.00 |
| BT-T | k4 shuffle l8 | oefixed | -7.48 | -3.00 |
| XY | k4 shuffle l8 | xy | -4.30 | -3.00 |
| BT-T | k4 tornado l7 | xy | -24.40 | -3.00 |
| XY | k4 tornado l7 | xy | -24.40 | -3.00 |
| BT-T | k4 tornado l8 | xy | -27.74 | -3.00 |
| XY | k4 tornado l8 | xy | -27.74 | -3.00 |
| BT-T | k8 bitcomp l5 | xy | -14.94 | -3.00 |
| XY | k8 bitcomp l5 | xy | -14.94 | -3.00 |
| BT-T | k8 bitcomp l6 | xy | -12.52 | -3.00 |
| XY | k8 bitcomp l6 | xy | -12.52 | -3.00 |
| BT-T | k8 bitcomp l7 | xy | -11.66 | -3.00 |
| XY | k8 bitcomp l7 | xy | -11.66 | -3.00 |
| BT-T | k8 bitcomp l8 | xy | -9.51 | -3.00 |
| XY | k8 bitcomp l8 | xy | -9.51 | -3.00 |
| BT-T | k8 mixed l6 | dbar | -13.04 | -3.00 |
| XY | k8 mixed l6 | xy | -6.63 | -3.00 |
| BT-T | k8 mixed l7 | dbar | -13.07 | -3.00 |
| XY | k8 mixed l7 | xy | -11.06 | -3.00 |
| BT-T | k8 mixed l8 | o1turn | -13.54 | -3.00 |
| XY | k8 mixed l8 | xy | -12.72 | -3.00 |
| BT-T | k8 multiflow l6 | xy | -12.42 | -3.00 |
| XY | k8 multiflow l6 | xy | -12.42 | -3.00 |
| BT-T | k8 multiflow l7 | xy | -11.31 | -3.00 |
| XY | k8 multiflow l7 | xy | -11.31 | -3.00 |
| BT-T | k8 multiflow l8 | xy | -8.05 | -3.00 |
| XY | k8 multiflow l8 | xy | -8.05 | -3.00 |
| BT-T | k8 randperm l6 | xy | -18.43 | -3.00 |
| XY | k8 randperm l6 | xy | -18.43 | -3.00 |
| BT-T | k8 randperm l7 | xy | -16.38 | -3.00 |
| XY | k8 randperm l7 | xy | -16.38 | -3.00 |
| BT-T | k8 randperm l8 | xy | -13.28 | -3.00 |
| XY | k8 randperm l8 | xy | -13.28 | -3.00 |
| BT-T | k8 shuffle l6 | topsis | -5.71 | -3.00 |
| BT-T | k8 shuffle l7 | duato | -5.37 | -3.00 |
| BT-T | k8 shuffle l8 | duato | -6.68 | -3.00 |
| BT-T | k8 tornado l5 | xy | -16.35 | -3.00 |
| XY | k8 tornado l5 | xy | -16.35 | -3.00 |
| BT-T | k8 tornado l6 | xy | -18.44 | -3.00 |
| XY | k8 tornado l6 | xy | -18.44 | -3.00 |
| BT-T | k8 tornado l7 | xy | -15.59 | -3.00 |
| XY | k8 tornado l7 | xy | -15.59 | -3.00 |
| BT-T | k8 tornado l8 | xy | -12.67 | -3.00 |
| XY | k8 tornado l8 | xy | -12.67 | -3.00 |

