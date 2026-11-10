# G5 fresh held-out: best-or-tied-best verdict

Seeds [301, 302, 303, 304, 305]; meshes [4, 8, 16, 32]; 13 traffic patterns; comparators ['xy', 'oefixed', 'dyad', 'topsis', 'duato', 'westfirst', 'dbar', 'footprint']; candidates ['saqr_sc', 'saqr_h'].
Complete (mesh, traffic) groups: 52 of 52. Safety: integrity errors 0.

Each cell: passes / checks (strict wins = throughput lower bound > +3 % over the best comparator).

## saqr_sc

| traffic | BT-T (throughput vs best) | strict wins | BT-L (crit p99 vs best) | never worse than XY |
|---|---:|---:|---:|---:|
| uniform | 36/36 | 0/36 | 36/36 | 36/36 |
| transpose | 36/36 | 10/36 | 36/36 | 36/36 |
| bursty | 36/36 | 0/36 | 36/36 | 36/36 |
| hotspot_corner | 28/36 | 0/36 | 36/36 | 36/36 |
| hotspot_edge | 25/36 | 0/36 | 36/36 | 36/36 |
| hotspot_center | 36/36 | 0/36 | 36/36 | 36/36 |
| bitcomp | 18/36 | 0/36 | 35/36 | 18/36 |
| bitrev | 36/36 | 11/36 | 36/36 | 36/36 |
| shuffle | 29/36 | 0/36 | 36/36 | 34/36 |
| tornado | 22/36 | 0/36 | 36/36 | 22/36 |
| neighbor | 36/36 | 0/36 | 36/36 | 36/36 |
| multiflow | 25/36 | 0/36 | 36/36 | 25/36 |
| mixed | 26/36 | 0/36 | 36/36 | 27/36 |
| **all** | **389/468** | **21/468** | **467/468** | **414/468** |

| failed check | where | vs | value | limit |
|---|---|---|---:|---:|
| BT-T | k16 bitcomp l4 | xy | -6.57 | -3.00 |
| XY | k16 bitcomp l4 | xy | -6.57 | -3.00 |
| BT-T | k16 bitcomp l5 | xy | -19.46 | -3.00 |
| XY | k16 bitcomp l5 | xy | -19.46 | -3.00 |
| BT-T | k16 bitcomp l6 | xy | -15.90 | -3.00 |
| XY | k16 bitcomp l6 | xy | -15.90 | -3.00 |
| BT-T | k16 bitcomp l7 | xy | -13.19 | -3.00 |
| XY | k16 bitcomp l7 | xy | -13.19 | -3.00 |
| BT-T | k16 bitcomp l8 | xy | -11.77 | -3.00 |
| XY | k16 bitcomp l8 | xy | -11.77 | -3.00 |
| BT-T | k16 hotspot_corner l5 | dbar | -9.65 | -3.00 |
| BT-T | k16 hotspot_corner l6 | topsis | -6.41 | -3.00 |
| BT-T | k16 hotspot_edge l4 | dbar | -3.30 | -3.00 |
| BT-T | k16 hotspot_edge l5 | topsis | -10.24 | -3.00 |
| BT-T | k16 hotspot_edge l6 | oefixed | -8.23 | -3.00 |
| BT-T | k16 hotspot_edge l7 | oefixed | -6.26 | -3.00 |
| BT-T | k16 mixed l6 | dbar | -14.16 | -3.00 |
| XY | k16 mixed l6 | xy | -9.03 | -3.00 |
| BT-T | k16 mixed l7 | dbar | -13.11 | -3.00 |
| XY | k16 mixed l7 | xy | -10.49 | -3.00 |
| BT-T | k16 mixed l8 | dbar | -11.06 | -3.00 |
| XY | k16 mixed l8 | xy | -8.43 | -3.00 |
| BT-T | k16 multiflow l6 | xy | -21.19 | -3.00 |
| XY | k16 multiflow l6 | xy | -21.19 | -3.00 |
| BT-T | k16 multiflow l7 | xy | -17.73 | -3.00 |
| XY | k16 multiflow l7 | xy | -17.73 | -3.00 |
| BT-T | k16 multiflow l8 | xy | -14.67 | -3.00 |
| XY | k16 multiflow l8 | xy | -14.67 | -3.00 |
| BT-T | k16 tornado l5 | xy | -30.67 | -3.00 |
| XY | k16 tornado l5 | xy | -30.67 | -3.00 |
| BT-T | k16 tornado l6 | xy | -20.41 | -3.00 |
| XY | k16 tornado l6 | xy | -20.41 | -3.00 |
| BT-T | k16 tornado l7 | xy | -16.54 | -3.00 |
| XY | k16 tornado l7 | xy | -16.54 | -3.00 |
| BT-T | k16 tornado l8 | xy | -13.42 | -3.00 |
| XY | k16 tornado l8 | xy | -13.42 | -3.00 |
| BT-T | k32 bitcomp l4 | xy | -11.42 | -3.00 |
| XY | k32 bitcomp l4 | xy | -11.42 | -3.00 |
| BT-T | k32 bitcomp l5 | xy | -17.49 | -3.00 |
| XY | k32 bitcomp l5 | xy | -17.49 | -3.00 |
| BT-T | k32 bitcomp l6 | xy | -11.52 | -3.00 |
| XY | k32 bitcomp l6 | xy | -11.52 | -3.00 |
| BT-T | k32 bitcomp l7 | xy | -9.78 | -3.00 |
| XY | k32 bitcomp l7 | xy | -9.78 | -3.00 |
| BT-T | k32 bitcomp l8 | xy | -10.81 | -3.00 |
| XY | k32 bitcomp l8 | xy | -10.81 | -3.00 |
| BT-T | k32 hotspot_corner l5 | dbar | -5.96 | -3.00 |
| BT-T | k32 hotspot_corner l6 | dbar | -9.80 | -3.00 |
| BT-T | k32 hotspot_corner l7 | dbar | -10.54 | -3.00 |
| BT-T | k32 hotspot_corner l8 | dbar | -7.84 | -3.00 |
| BT-T | k32 hotspot_edge l5 | topsis | -9.18 | -3.00 |
| BT-T | k32 hotspot_edge l6 | oefixed | -9.36 | -3.00 |
| BT-T | k32 hotspot_edge l7 | oefixed | -9.55 | -3.00 |
| BT-T | k32 hotspot_edge l8 | oefixed | -3.90 | -3.00 |
| BT-T | k32 mixed l6 | dbar | -8.40 | -3.00 |
| XY | k32 mixed l6 | xy | -5.60 | -3.00 |
| BT-T | k32 mixed l7 | dbar | -10.07 | -3.00 |
| XY | k32 mixed l7 | xy | -6.77 | -3.00 |
| BT-T | k32 mixed l8 | dbar | -9.10 | -3.00 |
| XY | k32 mixed l8 | xy | -5.40 | -3.00 |
| BT-T | k32 multiflow l6 | xy | -25.89 | -3.00 |
| XY | k32 multiflow l6 | xy | -25.89 | -3.00 |
| BT-T | k32 multiflow l7 | xy | -21.46 | -3.00 |
| XY | k32 multiflow l7 | xy | -21.46 | -3.00 |
| BT-T | k32 multiflow l8 | xy | -18.46 | -3.00 |
| XY | k32 multiflow l8 | xy | -18.46 | -3.00 |
| BT-T | k32 shuffle l6 | xy | -3.13 | -3.00 |
| XY | k32 shuffle l6 | xy | -3.13 | -3.00 |
| BT-T | k32 tornado l5 | xy | -36.87 | -3.00 |
| XY | k32 tornado l5 | xy | -36.87 | -3.00 |
| BT-T | k32 tornado l6 | xy | -22.17 | -3.00 |
| XY | k32 tornado l6 | xy | -22.17 | -3.00 |
| BT-T | k32 tornado l7 | xy | -15.06 | -3.00 |
| XY | k32 tornado l7 | xy | -15.06 | -3.00 |
| BT-T | k32 tornado l8 | xy | -10.43 | -3.00 |
| XY | k32 tornado l8 | xy | -10.43 | -3.00 |
| BT-T | k4 bitcomp l5 | xy | -14.42 | -3.00 |
| XY | k4 bitcomp l5 | xy | -14.42 | -3.00 |
| BT-T | k4 bitcomp l6 | xy | -13.24 | -3.00 |
| XY | k4 bitcomp l6 | xy | -13.24 | -3.00 |
| BT-T | k4 bitcomp l7 | xy | -11.81 | -3.00 |
| XY | k4 bitcomp l7 | xy | -11.81 | -3.00 |
| BT-T | k4 bitcomp l8 | xy | -10.33 | -3.00 |
| BT-L | k4 bitcomp l8 | xy | 8.85 | 8.38 |
| XY | k4 bitcomp l8 | xy | -10.33 | -3.00 |
| BT-T | k4 hotspot_edge l5 | topsis | -3.01 | -3.00 |
| BT-T | k4 mixed l6 | dbar | -3.01 | -3.00 |
| BT-T | k4 multiflow l7 | xy | -4.34 | -3.00 |
| XY | k4 multiflow l7 | xy | -4.34 | -3.00 |
| BT-T | k4 multiflow l8 | xy | -4.99 | -3.00 |
| XY | k4 multiflow l8 | xy | -4.99 | -3.00 |
| BT-T | k4 shuffle l6 | topsis | -5.05 | -3.00 |
| BT-T | k4 shuffle l7 | westfirst | -7.22 | -3.00 |
| BT-T | k4 shuffle l8 | oefixed | -7.39 | -3.00 |
| XY | k4 shuffle l8 | xy | -4.22 | -3.00 |
| BT-T | k4 tornado l7 | xy | -24.09 | -3.00 |
| XY | k4 tornado l7 | xy | -24.09 | -3.00 |
| BT-T | k4 tornado l8 | xy | -27.72 | -3.00 |
| XY | k4 tornado l8 | xy | -27.72 | -3.00 |
| BT-T | k8 bitcomp l5 | xy | -14.35 | -3.00 |
| XY | k8 bitcomp l5 | xy | -14.35 | -3.00 |
| BT-T | k8 bitcomp l6 | xy | -13.10 | -3.00 |
| XY | k8 bitcomp l6 | xy | -13.10 | -3.00 |
| BT-T | k8 bitcomp l7 | xy | -11.43 | -3.00 |
| XY | k8 bitcomp l7 | xy | -11.43 | -3.00 |
| BT-T | k8 bitcomp l8 | xy | -9.71 | -3.00 |
| XY | k8 bitcomp l8 | xy | -9.71 | -3.00 |
| BT-T | k8 hotspot_corner l5 | topsis | -6.40 | -3.00 |
| BT-T | k8 hotspot_corner l6 | dbar | -4.05 | -3.00 |
| BT-T | k8 hotspot_edge l5 | topsis | -7.27 | -3.00 |
| BT-T | k8 hotspot_edge l6 | dyad | -5.76 | -3.00 |
| BT-T | k8 mixed l6 | dbar | -13.93 | -3.00 |
| XY | k8 mixed l6 | xy | -7.51 | -3.00 |
| BT-T | k8 mixed l7 | dbar | -12.42 | -3.00 |
| XY | k8 mixed l7 | xy | -10.58 | -3.00 |
| BT-T | k8 mixed l8 | xy | -11.21 | -3.00 |
| XY | k8 mixed l8 | xy | -11.21 | -3.00 |
| BT-T | k8 multiflow l6 | xy | -9.46 | -3.00 |
| XY | k8 multiflow l6 | xy | -9.46 | -3.00 |
| BT-T | k8 multiflow l7 | xy | -8.42 | -3.00 |
| XY | k8 multiflow l7 | xy | -8.42 | -3.00 |
| BT-T | k8 multiflow l8 | xy | -7.54 | -3.00 |
| XY | k8 multiflow l8 | xy | -7.54 | -3.00 |
| BT-T | k8 shuffle l6 | topsis | -5.95 | -3.00 |
| BT-T | k8 shuffle l7 | duato | -5.45 | -3.00 |
| BT-T | k8 shuffle l8 | duato | -6.47 | -3.00 |
| BT-T | k8 tornado l5 | xy | -17.70 | -3.00 |
| XY | k8 tornado l5 | xy | -17.70 | -3.00 |
| BT-T | k8 tornado l6 | xy | -17.98 | -3.00 |
| XY | k8 tornado l6 | xy | -17.98 | -3.00 |
| BT-T | k8 tornado l7 | xy | -15.07 | -3.00 |
| XY | k8 tornado l7 | xy | -15.07 | -3.00 |
| BT-T | k8 tornado l8 | xy | -12.24 | -3.00 |
| XY | k8 tornado l8 | xy | -12.24 | -3.00 |

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
| multiflow | 25/36 | 0/36 | 36/36 | 25/36 |
| mixed | 25/36 | 0/36 | 36/36 | 27/36 |
| **all** | **399/468** | **21/468** | **468/468** | **414/468** |

| failed check | where | vs | value | limit |
|---|---|---|---:|---:|
| BT-T | k16 bitcomp l4 | xy | -6.39 | -3.00 |
| XY | k16 bitcomp l4 | xy | -6.39 | -3.00 |
| BT-T | k16 bitcomp l5 | xy | -19.61 | -3.00 |
| XY | k16 bitcomp l5 | xy | -19.61 | -3.00 |
| BT-T | k16 bitcomp l6 | xy | -15.89 | -3.00 |
| XY | k16 bitcomp l6 | xy | -15.89 | -3.00 |
| BT-T | k16 bitcomp l7 | xy | -13.09 | -3.00 |
| XY | k16 bitcomp l7 | xy | -13.09 | -3.00 |
| BT-T | k16 bitcomp l8 | xy | -11.86 | -3.00 |
| XY | k16 bitcomp l8 | xy | -11.86 | -3.00 |
| BT-T | k16 hotspot_edge l5 | topsis | -3.09 | -3.00 |
| BT-T | k16 mixed l6 | dbar | -13.65 | -3.00 |
| XY | k16 mixed l6 | xy | -8.38 | -3.00 |
| BT-T | k16 mixed l7 | dbar | -12.18 | -3.00 |
| XY | k16 mixed l7 | xy | -9.61 | -3.00 |
| BT-T | k16 mixed l8 | dbar | -11.26 | -3.00 |
| XY | k16 mixed l8 | xy | -8.84 | -3.00 |
| BT-T | k16 multiflow l6 | xy | -19.90 | -3.00 |
| XY | k16 multiflow l6 | xy | -19.90 | -3.00 |
| BT-T | k16 multiflow l7 | xy | -17.60 | -3.00 |
| XY | k16 multiflow l7 | xy | -17.60 | -3.00 |
| BT-T | k16 multiflow l8 | xy | -15.29 | -3.00 |
| XY | k16 multiflow l8 | xy | -15.29 | -3.00 |
| BT-T | k16 tornado l5 | xy | -29.91 | -3.00 |
| XY | k16 tornado l5 | xy | -29.91 | -3.00 |
| BT-T | k16 tornado l6 | xy | -20.44 | -3.00 |
| XY | k16 tornado l6 | xy | -20.44 | -3.00 |
| BT-T | k16 tornado l7 | xy | -16.47 | -3.00 |
| XY | k16 tornado l7 | xy | -16.47 | -3.00 |
| BT-T | k16 tornado l8 | xy | -13.72 | -3.00 |
| XY | k16 tornado l8 | xy | -13.72 | -3.00 |
| BT-T | k32 bitcomp l4 | xy | -11.50 | -3.00 |
| XY | k32 bitcomp l4 | xy | -11.50 | -3.00 |
| BT-T | k32 bitcomp l5 | xy | -17.34 | -3.00 |
| XY | k32 bitcomp l5 | xy | -17.34 | -3.00 |
| BT-T | k32 bitcomp l6 | xy | -11.30 | -3.00 |
| XY | k32 bitcomp l6 | xy | -11.30 | -3.00 |
| BT-T | k32 bitcomp l7 | xy | -10.08 | -3.00 |
| XY | k32 bitcomp l7 | xy | -10.08 | -3.00 |
| BT-T | k32 bitcomp l8 | xy | -10.86 | -3.00 |
| XY | k32 bitcomp l8 | xy | -10.86 | -3.00 |
| BT-T | k32 hotspot_corner l6 | dbar | -5.61 | -3.00 |
| BT-T | k32 hotspot_corner l7 | dbar | -5.38 | -3.00 |
| BT-T | k32 hotspot_corner l8 | dbar | -5.18 | -3.00 |
| BT-T | k32 hotspot_edge l5 | topsis | -5.42 | -3.00 |
| BT-T | k32 hotspot_edge l6 | oefixed | -6.32 | -3.00 |
| BT-T | k32 hotspot_edge l7 | oefixed | -7.06 | -3.00 |
| BT-T | k32 hotspot_edge l8 | oefixed | -3.80 | -3.00 |
| BT-T | k32 mixed l6 | dbar | -8.44 | -3.00 |
| XY | k32 mixed l6 | xy | -5.67 | -3.00 |
| BT-T | k32 mixed l7 | dbar | -9.63 | -3.00 |
| XY | k32 mixed l7 | xy | -6.70 | -3.00 |
| BT-T | k32 mixed l8 | dbar | -9.34 | -3.00 |
| XY | k32 mixed l8 | xy | -5.30 | -3.00 |
| BT-T | k32 multiflow l6 | xy | -24.93 | -3.00 |
| XY | k32 multiflow l6 | xy | -24.93 | -3.00 |
| BT-T | k32 multiflow l7 | xy | -21.27 | -3.00 |
| XY | k32 multiflow l7 | xy | -21.27 | -3.00 |
| BT-T | k32 multiflow l8 | xy | -17.55 | -3.00 |
| XY | k32 multiflow l8 | xy | -17.55 | -3.00 |
| BT-T | k32 shuffle l6 | xy | -3.47 | -3.00 |
| XY | k32 shuffle l6 | xy | -3.47 | -3.00 |
| BT-T | k32 tornado l5 | xy | -37.13 | -3.00 |
| XY | k32 tornado l5 | xy | -37.13 | -3.00 |
| BT-T | k32 tornado l6 | xy | -22.15 | -3.00 |
| XY | k32 tornado l6 | xy | -22.15 | -3.00 |
| BT-T | k32 tornado l7 | xy | -14.93 | -3.00 |
| XY | k32 tornado l7 | xy | -14.93 | -3.00 |
| BT-T | k32 tornado l8 | xy | -10.52 | -3.00 |
| XY | k32 tornado l8 | xy | -10.52 | -3.00 |
| BT-T | k4 bitcomp l5 | xy | -14.29 | -3.00 |
| XY | k4 bitcomp l5 | xy | -14.29 | -3.00 |
| BT-T | k4 bitcomp l6 | xy | -13.44 | -3.00 |
| XY | k4 bitcomp l6 | xy | -13.44 | -3.00 |
| BT-T | k4 bitcomp l7 | xy | -11.88 | -3.00 |
| XY | k4 bitcomp l7 | xy | -11.88 | -3.00 |
| BT-T | k4 bitcomp l8 | xy | -10.08 | -3.00 |
| XY | k4 bitcomp l8 | xy | -10.08 | -3.00 |
| BT-T | k4 mixed l6 | dbar | -4.20 | -3.00 |
| BT-T | k4 mixed l7 | dbar | -3.66 | -3.00 |
| BT-T | k4 multiflow l7 | xy | -4.96 | -3.00 |
| XY | k4 multiflow l7 | xy | -4.96 | -3.00 |
| BT-T | k4 multiflow l8 | xy | -5.46 | -3.00 |
| XY | k4 multiflow l8 | xy | -5.46 | -3.00 |
| BT-T | k4 shuffle l6 | topsis | -5.07 | -3.00 |
| BT-T | k4 shuffle l7 | westfirst | -6.94 | -3.00 |
| BT-T | k4 shuffle l8 | oefixed | -7.31 | -3.00 |
| XY | k4 shuffle l8 | xy | -4.14 | -3.00 |
| BT-T | k4 tornado l7 | xy | -24.30 | -3.00 |
| XY | k4 tornado l7 | xy | -24.30 | -3.00 |
| BT-T | k4 tornado l8 | xy | -27.59 | -3.00 |
| XY | k4 tornado l8 | xy | -27.59 | -3.00 |
| BT-T | k8 bitcomp l5 | xy | -14.61 | -3.00 |
| XY | k8 bitcomp l5 | xy | -14.61 | -3.00 |
| BT-T | k8 bitcomp l6 | xy | -12.82 | -3.00 |
| XY | k8 bitcomp l6 | xy | -12.82 | -3.00 |
| BT-T | k8 bitcomp l7 | xy | -11.31 | -3.00 |
| XY | k8 bitcomp l7 | xy | -11.31 | -3.00 |
| BT-T | k8 bitcomp l8 | xy | -9.73 | -3.00 |
| XY | k8 bitcomp l8 | xy | -9.73 | -3.00 |
| BT-T | k8 mixed l6 | dbar | -13.28 | -3.00 |
| XY | k8 mixed l6 | xy | -7.65 | -3.00 |
| BT-T | k8 mixed l7 | dbar | -11.40 | -3.00 |
| XY | k8 mixed l7 | xy | -9.71 | -3.00 |
| BT-T | k8 mixed l8 | xy | -11.76 | -3.00 |
| XY | k8 mixed l8 | xy | -11.76 | -3.00 |
| BT-T | k8 multiflow l6 | xy | -10.14 | -3.00 |
| XY | k8 multiflow l6 | xy | -10.14 | -3.00 |
| BT-T | k8 multiflow l7 | xy | -8.58 | -3.00 |
| XY | k8 multiflow l7 | xy | -8.58 | -3.00 |
| BT-T | k8 multiflow l8 | xy | -7.42 | -3.00 |
| XY | k8 multiflow l8 | xy | -7.42 | -3.00 |
| BT-T | k8 shuffle l6 | topsis | -6.09 | -3.00 |
| BT-T | k8 shuffle l7 | duato | -5.58 | -3.00 |
| BT-T | k8 shuffle l8 | duato | -6.59 | -3.00 |
| BT-T | k8 tornado l5 | xy | -17.04 | -3.00 |
| XY | k8 tornado l5 | xy | -17.04 | -3.00 |
| BT-T | k8 tornado l6 | xy | -18.16 | -3.00 |
| XY | k8 tornado l6 | xy | -18.16 | -3.00 |
| BT-T | k8 tornado l7 | xy | -15.03 | -3.00 |
| XY | k8 tornado l7 | xy | -15.03 | -3.00 |
| BT-T | k8 tornado l8 | xy | -12.39 | -3.00 |
| XY | k8 tornado l8 | xy | -12.39 | -3.00 |

