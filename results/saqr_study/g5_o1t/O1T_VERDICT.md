# G5 + O1TURN: is the SAQR gain just O1TURN?

Seeds [301, 302, 303, 304, 305]; meshes [4, 8, 16, 32]; 13 traffic patterns; candidates ['saqr_sc', 'saqr_h']; new routes ['o1turn', 'saqr_all'].
Complete (mesh, traffic) groups: 52 of 52. Safety: integrity errors 0.

Each cell: passes / checks; strict wins (lower bound > +3 %) in brackets.

## saqr_sc

| traffic | O-T vs o1turn | O-L p99 vs o1turn | A-T vs saqr_all | B9-T vs best of 9 |
|---|---:|---:|---:|---:|
| uniform | 36/36 (12) | 36/36 | 36/36 (9) | 36/36 (0) |
| transpose | 36/36 (18) | 33/33 | 36/36 (0) | 36/36 (10) |
| bursty | 36/36 (12) | 36/36 | 36/36 (9) | 36/36 (0) |
| hotspot_corner | 34/36 (0) | 36/36 | 27/36 (0) | 28/36 (0) |
| hotspot_edge | 32/36 (0) | 36/36 | 27/36 (0) | 25/36 (0) |
| hotspot_center | 36/36 (0) | 36/36 | 36/36 (0) | 36/36 (0) |
| bitcomp | 24/36 (2) | 36/36 | 36/36 (0) | 18/36 (0) |
| bitrev | 36/36 (18) | 33/33 | 36/36 (0) | 36/36 (11) |
| shuffle | 36/36 (12) | 36/36 | 36/36 (0) | 29/36 (0) |
| tornado | 25/36 (3) | 36/36 | 36/36 (0) | 22/36 (0) |
| neighbor | 36/36 (2) | 36/36 | 36/36 (0) | 36/36 (0) |
| multiflow | 30/36 (2) | 36/36 | 36/36 (0) | 25/36 (0) |
| mixed | 27/36 (3) | 36/36 | 36/36 (3) | 26/36 (0) |
| **all** | **424/468** (84) | **462/462** | **450/468** (21) | **389/468** (21) |

| failed check | where | vs | value | limit |
|---|---|---|---:|---:|
| O-T | k16 bitcomp l4 | o1turn | -6.58 | -3.00 |
| B9-T | k16 bitcomp l4 | xy | -6.57 | -3.00 |
| O-T | k16 bitcomp l5 | o1turn | -8.37 | -3.00 |
| B9-T | k16 bitcomp l5 | xy | -19.46 | -3.00 |
| O-T | k16 bitcomp l6 | o1turn | -8.20 | -3.00 |
| B9-T | k16 bitcomp l6 | xy | -15.90 | -3.00 |
| O-T | k16 bitcomp l7 | o1turn | -6.87 | -3.00 |
| B9-T | k16 bitcomp l7 | xy | -13.19 | -3.00 |
| O-T | k16 bitcomp l8 | o1turn | -6.28 | -3.00 |
| B9-T | k16 bitcomp l8 | xy | -11.77 | -3.00 |
| A-T | k16 hotspot_corner l5 | saqr_all | -9.38 | -3.00 |
| B9-T | k16 hotspot_corner l5 | dbar | -9.65 | -3.00 |
| A-T | k16 hotspot_corner l6 | saqr_all | -8.88 | -3.00 |
| B9-T | k16 hotspot_corner l6 | topsis | -6.41 | -3.00 |
| A-T | k16 hotspot_corner l7 | saqr_all | -4.33 | -3.00 |
| A-T | k16 hotspot_edge l4 | saqr_all | -3.40 | -3.00 |
| B9-T | k16 hotspot_edge l4 | dbar | -3.30 | -3.00 |
| A-T | k16 hotspot_edge l5 | saqr_all | -8.45 | -3.00 |
| B9-T | k16 hotspot_edge l5 | topsis | -10.24 | -3.00 |
| A-T | k16 hotspot_edge l6 | saqr_all | -6.26 | -3.00 |
| B9-T | k16 hotspot_edge l6 | oefixed | -8.23 | -3.00 |
| A-T | k16 hotspot_edge l7 | saqr_all | -3.98 | -3.00 |
| B9-T | k16 hotspot_edge l7 | oefixed | -6.26 | -3.00 |
| O-T | k16 mixed l6 | o1turn | -12.21 | -3.00 |
| B9-T | k16 mixed l6 | dbar | -14.16 | -3.00 |
| O-T | k16 mixed l7 | o1turn | -14.65 | -3.00 |
| B9-T | k16 mixed l7 | o1turn | -14.65 | -3.00 |
| O-T | k16 mixed l8 | o1turn | -14.31 | -3.00 |
| B9-T | k16 mixed l8 | o1turn | -14.31 | -3.00 |
| O-T | k16 multiflow l6 | o1turn | -15.77 | -3.00 |
| B9-T | k16 multiflow l6 | xy | -21.19 | -3.00 |
| O-T | k16 multiflow l7 | o1turn | -12.98 | -3.00 |
| B9-T | k16 multiflow l7 | xy | -17.73 | -3.00 |
| O-T | k16 multiflow l8 | o1turn | -10.44 | -3.00 |
| B9-T | k16 multiflow l8 | xy | -14.67 | -3.00 |
| O-T | k16 tornado l5 | o1turn | -19.43 | -3.00 |
| B9-T | k16 tornado l5 | xy | -30.67 | -3.00 |
| O-T | k16 tornado l6 | o1turn | -17.15 | -3.00 |
| B9-T | k16 tornado l6 | xy | -20.41 | -3.00 |
| O-T | k16 tornado l7 | o1turn | -15.00 | -3.00 |
| B9-T | k16 tornado l7 | xy | -16.54 | -3.00 |
| O-T | k16 tornado l8 | o1turn | -12.18 | -3.00 |
| B9-T | k16 tornado l8 | xy | -13.42 | -3.00 |
| O-T | k32 bitcomp l4 | o1turn | -11.46 | -3.00 |
| B9-T | k32 bitcomp l4 | o1turn | -11.46 | -3.00 |
| O-T | k32 bitcomp l5 | o1turn | -14.41 | -3.00 |
| B9-T | k32 bitcomp l5 | xy | -17.49 | -3.00 |
| O-T | k32 bitcomp l6 | o1turn | -11.73 | -3.00 |
| B9-T | k32 bitcomp l6 | xy | -11.52 | -3.00 |
| O-T | k32 bitcomp l7 | o1turn | -10.11 | -3.00 |
| B9-T | k32 bitcomp l7 | xy | -9.78 | -3.00 |
| O-T | k32 bitcomp l8 | o1turn | -8.79 | -3.00 |
| B9-T | k32 bitcomp l8 | xy | -10.81 | -3.00 |
| A-T | k32 hotspot_corner l5 | saqr_all | -5.61 | -3.00 |
| B9-T | k32 hotspot_corner l5 | dbar | -5.96 | -3.00 |
| A-T | k32 hotspot_corner l6 | saqr_all | -8.55 | -3.00 |
| B9-T | k32 hotspot_corner l6 | dbar | -9.80 | -3.00 |
| O-T | k32 hotspot_corner l7 | o1turn | -3.36 | -3.00 |
| A-T | k32 hotspot_corner l7 | saqr_all | -9.31 | -3.00 |
| B9-T | k32 hotspot_corner l7 | dbar | -10.54 | -3.00 |
| O-T | k32 hotspot_corner l8 | o1turn | -4.98 | -3.00 |
| A-T | k32 hotspot_corner l8 | saqr_all | -6.56 | -3.00 |
| B9-T | k32 hotspot_corner l8 | dbar | -7.84 | -3.00 |
| O-T | k32 hotspot_edge l5 | o1turn | -3.63 | -3.00 |
| A-T | k32 hotspot_edge l5 | saqr_all | -8.41 | -3.00 |
| B9-T | k32 hotspot_edge l5 | topsis | -9.18 | -3.00 |
| O-T | k32 hotspot_edge l6 | o1turn | -4.63 | -3.00 |
| A-T | k32 hotspot_edge l6 | saqr_all | -7.14 | -3.00 |
| B9-T | k32 hotspot_edge l6 | oefixed | -9.36 | -3.00 |
| O-T | k32 hotspot_edge l7 | o1turn | -5.62 | -3.00 |
| A-T | k32 hotspot_edge l7 | saqr_all | -5.36 | -3.00 |
| B9-T | k32 hotspot_edge l7 | oefixed | -9.55 | -3.00 |
| O-T | k32 hotspot_edge l8 | o1turn | -3.27 | -3.00 |
| B9-T | k32 hotspot_edge l8 | oefixed | -3.90 | -3.00 |
| O-T | k32 mixed l6 | o1turn | -11.70 | -3.00 |
| B9-T | k32 mixed l6 | o1turn | -11.70 | -3.00 |
| O-T | k32 mixed l7 | o1turn | -14.74 | -3.00 |
| B9-T | k32 mixed l7 | o1turn | -14.74 | -3.00 |
| O-T | k32 mixed l8 | o1turn | -14.71 | -3.00 |
| B9-T | k32 mixed l8 | o1turn | -14.71 | -3.00 |
| O-T | k32 multiflow l6 | o1turn | -19.30 | -3.00 |
| B9-T | k32 multiflow l6 | xy | -25.89 | -3.00 |
| O-T | k32 multiflow l7 | o1turn | -16.44 | -3.00 |
| B9-T | k32 multiflow l7 | xy | -21.46 | -3.00 |
| O-T | k32 multiflow l8 | o1turn | -15.85 | -3.00 |
| B9-T | k32 multiflow l8 | xy | -18.46 | -3.00 |
| B9-T | k32 shuffle l6 | xy | -3.13 | -3.00 |
| O-T | k32 tornado l5 | o1turn | -29.24 | -3.00 |
| B9-T | k32 tornado l5 | xy | -36.87 | -3.00 |
| O-T | k32 tornado l6 | o1turn | -37.69 | -3.00 |
| B9-T | k32 tornado l6 | o1turn | -37.69 | -3.00 |
| O-T | k32 tornado l7 | o1turn | -32.09 | -3.00 |
| B9-T | k32 tornado l7 | o1turn | -32.09 | -3.00 |
| O-T | k32 tornado l8 | o1turn | -24.90 | -3.00 |
| B9-T | k32 tornado l8 | o1turn | -24.90 | -3.00 |
| B9-T | k4 bitcomp l5 | xy | -14.42 | -3.00 |
| B9-T | k4 bitcomp l6 | xy | -13.24 | -3.00 |
| B9-T | k4 bitcomp l7 | xy | -11.81 | -3.00 |
| B9-T | k4 bitcomp l8 | xy | -10.33 | -3.00 |
| B9-T | k4 hotspot_edge l5 | topsis | -3.01 | -3.00 |
| B9-T | k4 mixed l6 | dbar | -3.01 | -3.00 |
| B9-T | k4 multiflow l7 | xy | -4.34 | -3.00 |
| B9-T | k4 multiflow l8 | xy | -4.99 | -3.00 |
| B9-T | k4 shuffle l6 | topsis | -5.05 | -3.00 |
| B9-T | k4 shuffle l7 | westfirst | -7.22 | -3.00 |
| B9-T | k4 shuffle l8 | oefixed | -7.39 | -3.00 |
| B9-T | k4 tornado l7 | xy | -24.09 | -3.00 |
| B9-T | k4 tornado l8 | xy | -27.72 | -3.00 |
| B9-T | k8 bitcomp l5 | xy | -14.35 | -3.00 |
| B9-T | k8 bitcomp l6 | xy | -13.10 | -3.00 |
| O-T | k8 bitcomp l7 | o1turn | -3.87 | -3.00 |
| B9-T | k8 bitcomp l7 | xy | -11.43 | -3.00 |
| O-T | k8 bitcomp l8 | o1turn | -4.05 | -3.00 |
| B9-T | k8 bitcomp l8 | xy | -9.71 | -3.00 |
| A-T | k8 hotspot_corner l5 | saqr_all | -7.53 | -3.00 |
| B9-T | k8 hotspot_corner l5 | topsis | -6.40 | -3.00 |
| A-T | k8 hotspot_corner l6 | saqr_all | -4.82 | -3.00 |
| B9-T | k8 hotspot_corner l6 | dbar | -4.05 | -3.00 |
| A-T | k8 hotspot_edge l5 | saqr_all | -6.35 | -3.00 |
| B9-T | k8 hotspot_edge l5 | topsis | -7.27 | -3.00 |
| A-T | k8 hotspot_edge l6 | saqr_all | -4.29 | -3.00 |
| B9-T | k8 hotspot_edge l6 | dyad | -5.76 | -3.00 |
| O-T | k8 mixed l6 | o1turn | -7.14 | -3.00 |
| B9-T | k8 mixed l6 | dbar | -13.93 | -3.00 |
| O-T | k8 mixed l7 | o1turn | -10.72 | -3.00 |
| B9-T | k8 mixed l7 | dbar | -12.42 | -3.00 |
| O-T | k8 mixed l8 | o1turn | -11.58 | -3.00 |
| B9-T | k8 mixed l8 | o1turn | -11.58 | -3.00 |
| B9-T | k8 multiflow l6 | xy | -9.46 | -3.00 |
| B9-T | k8 multiflow l7 | xy | -8.42 | -3.00 |
| B9-T | k8 multiflow l8 | xy | -7.54 | -3.00 |
| B9-T | k8 shuffle l6 | topsis | -5.95 | -3.00 |
| B9-T | k8 shuffle l7 | duato | -5.45 | -3.00 |
| B9-T | k8 shuffle l8 | duato | -6.47 | -3.00 |
| O-T | k8 tornado l5 | o1turn | -4.80 | -3.00 |
| B9-T | k8 tornado l5 | xy | -17.70 | -3.00 |
| O-T | k8 tornado l6 | o1turn | -4.69 | -3.00 |
| B9-T | k8 tornado l6 | xy | -17.98 | -3.00 |
| O-T | k8 tornado l7 | o1turn | -3.91 | -3.00 |
| B9-T | k8 tornado l7 | xy | -15.07 | -3.00 |
| B9-T | k8 tornado l8 | xy | -12.24 | -3.00 |

## saqr_h

| traffic | O-T vs o1turn | O-L p99 vs o1turn | A-T vs saqr_all | B9-T vs best of 9 |
|---|---:|---:|---:|---:|
| uniform | 36/36 (12) | 36/36 | 36/36 (9) | 36/36 (0) |
| transpose | 36/36 (18) | 33/33 | 36/36 (0) | 36/36 (10) |
| bursty | 36/36 (12) | 36/36 | 36/36 (9) | 36/36 (0) |
| hotspot_corner | 36/36 (7) | 36/36 | 33/36 (0) | 33/36 (0) |
| hotspot_edge | 35/36 (4) | 36/36 | 34/36 (0) | 31/36 (0) |
| hotspot_center | 36/36 (0) | 36/36 | 36/36 (0) | 36/36 (0) |
| bitcomp | 24/36 (2) | 36/36 | 36/36 (0) | 18/36 (0) |
| bitrev | 36/36 (18) | 33/33 | 36/36 (0) | 36/36 (11) |
| shuffle | 36/36 (12) | 36/36 | 36/36 (0) | 29/36 (0) |
| tornado | 24/36 (3) | 36/36 | 36/36 (0) | 22/36 (0) |
| neighbor | 36/36 (2) | 36/36 | 36/36 (0) | 36/36 (0) |
| multiflow | 30/36 (2) | 36/36 | 36/36 (0) | 25/36 (0) |
| mixed | 27/36 (3) | 36/36 | 36/36 (2) | 25/36 (0) |
| **all** | **428/468** (95) | **462/462** | **463/468** (20) | **399/468** (21) |

| failed check | where | vs | value | limit |
|---|---|---|---:|---:|
| O-T | k16 bitcomp l4 | o1turn | -6.31 | -3.00 |
| B9-T | k16 bitcomp l4 | xy | -6.39 | -3.00 |
| O-T | k16 bitcomp l5 | o1turn | -8.21 | -3.00 |
| B9-T | k16 bitcomp l5 | xy | -19.61 | -3.00 |
| O-T | k16 bitcomp l6 | o1turn | -7.73 | -3.00 |
| B9-T | k16 bitcomp l6 | xy | -15.89 | -3.00 |
| O-T | k16 bitcomp l7 | o1turn | -6.93 | -3.00 |
| B9-T | k16 bitcomp l7 | xy | -13.09 | -3.00 |
| O-T | k16 bitcomp l8 | o1turn | -6.31 | -3.00 |
| B9-T | k16 bitcomp l8 | xy | -11.86 | -3.00 |
| B9-T | k16 hotspot_edge l5 | topsis | -3.09 | -3.00 |
| O-T | k16 mixed l6 | o1turn | -11.29 | -3.00 |
| B9-T | k16 mixed l6 | dbar | -13.65 | -3.00 |
| O-T | k16 mixed l7 | o1turn | -13.73 | -3.00 |
| B9-T | k16 mixed l7 | o1turn | -13.73 | -3.00 |
| O-T | k16 mixed l8 | o1turn | -14.71 | -3.00 |
| B9-T | k16 mixed l8 | o1turn | -14.71 | -3.00 |
| O-T | k16 multiflow l6 | o1turn | -14.21 | -3.00 |
| B9-T | k16 multiflow l6 | xy | -19.90 | -3.00 |
| O-T | k16 multiflow l7 | o1turn | -12.72 | -3.00 |
| B9-T | k16 multiflow l7 | xy | -17.60 | -3.00 |
| O-T | k16 multiflow l8 | o1turn | -10.97 | -3.00 |
| B9-T | k16 multiflow l8 | xy | -15.29 | -3.00 |
| O-T | k16 tornado l5 | o1turn | -18.77 | -3.00 |
| B9-T | k16 tornado l5 | xy | -29.91 | -3.00 |
| O-T | k16 tornado l6 | o1turn | -17.35 | -3.00 |
| B9-T | k16 tornado l6 | xy | -20.44 | -3.00 |
| O-T | k16 tornado l7 | o1turn | -14.85 | -3.00 |
| B9-T | k16 tornado l7 | xy | -16.47 | -3.00 |
| O-T | k16 tornado l8 | o1turn | -12.43 | -3.00 |
| B9-T | k16 tornado l8 | xy | -13.72 | -3.00 |
| O-T | k32 bitcomp l4 | o1turn | -11.55 | -3.00 |
| B9-T | k32 bitcomp l4 | o1turn | -11.55 | -3.00 |
| O-T | k32 bitcomp l5 | o1turn | -14.06 | -3.00 |
| B9-T | k32 bitcomp l5 | xy | -17.34 | -3.00 |
| O-T | k32 bitcomp l6 | o1turn | -11.58 | -3.00 |
| B9-T | k32 bitcomp l6 | xy | -11.30 | -3.00 |
| O-T | k32 bitcomp l7 | o1turn | -10.37 | -3.00 |
| B9-T | k32 bitcomp l7 | xy | -10.08 | -3.00 |
| O-T | k32 bitcomp l8 | o1turn | -8.73 | -3.00 |
| B9-T | k32 bitcomp l8 | xy | -10.86 | -3.00 |
| A-T | k32 hotspot_corner l6 | saqr_all | -4.45 | -3.00 |
| B9-T | k32 hotspot_corner l6 | dbar | -5.61 | -3.00 |
| A-T | k32 hotspot_corner l7 | saqr_all | -4.19 | -3.00 |
| B9-T | k32 hotspot_corner l7 | dbar | -5.38 | -3.00 |
| A-T | k32 hotspot_corner l8 | saqr_all | -3.57 | -3.00 |
| B9-T | k32 hotspot_corner l8 | dbar | -5.18 | -3.00 |
| A-T | k32 hotspot_edge l5 | saqr_all | -4.45 | -3.00 |
| B9-T | k32 hotspot_edge l5 | topsis | -5.42 | -3.00 |
| A-T | k32 hotspot_edge l6 | saqr_all | -4.20 | -3.00 |
| B9-T | k32 hotspot_edge l6 | oefixed | -6.32 | -3.00 |
| B9-T | k32 hotspot_edge l7 | oefixed | -7.06 | -3.00 |
| O-T | k32 hotspot_edge l8 | o1turn | -3.55 | -3.00 |
| B9-T | k32 hotspot_edge l8 | oefixed | -3.80 | -3.00 |
| O-T | k32 mixed l6 | o1turn | -11.74 | -3.00 |
| B9-T | k32 mixed l6 | o1turn | -11.74 | -3.00 |
| O-T | k32 mixed l7 | o1turn | -14.51 | -3.00 |
| B9-T | k32 mixed l7 | o1turn | -14.51 | -3.00 |
| O-T | k32 mixed l8 | o1turn | -14.78 | -3.00 |
| B9-T | k32 mixed l8 | o1turn | -14.78 | -3.00 |
| O-T | k32 multiflow l6 | o1turn | -18.29 | -3.00 |
| B9-T | k32 multiflow l6 | xy | -24.93 | -3.00 |
| O-T | k32 multiflow l7 | o1turn | -16.15 | -3.00 |
| B9-T | k32 multiflow l7 | xy | -21.27 | -3.00 |
| O-T | k32 multiflow l8 | o1turn | -15.50 | -3.00 |
| B9-T | k32 multiflow l8 | xy | -17.55 | -3.00 |
| B9-T | k32 shuffle l6 | xy | -3.47 | -3.00 |
| O-T | k32 tornado l5 | o1turn | -29.59 | -3.00 |
| B9-T | k32 tornado l5 | xy | -37.13 | -3.00 |
| O-T | k32 tornado l6 | o1turn | -37.65 | -3.00 |
| B9-T | k32 tornado l6 | o1turn | -37.65 | -3.00 |
| O-T | k32 tornado l7 | o1turn | -32.25 | -3.00 |
| B9-T | k32 tornado l7 | o1turn | -32.25 | -3.00 |
| O-T | k32 tornado l8 | o1turn | -24.79 | -3.00 |
| B9-T | k32 tornado l8 | o1turn | -24.79 | -3.00 |
| B9-T | k4 bitcomp l5 | xy | -14.29 | -3.00 |
| B9-T | k4 bitcomp l6 | xy | -13.44 | -3.00 |
| B9-T | k4 bitcomp l7 | xy | -11.88 | -3.00 |
| B9-T | k4 bitcomp l8 | xy | -10.08 | -3.00 |
| B9-T | k4 mixed l6 | dbar | -4.20 | -3.00 |
| B9-T | k4 mixed l7 | dbar | -3.66 | -3.00 |
| B9-T | k4 multiflow l7 | xy | -4.96 | -3.00 |
| B9-T | k4 multiflow l8 | xy | -5.46 | -3.00 |
| B9-T | k4 shuffle l6 | topsis | -5.07 | -3.00 |
| B9-T | k4 shuffle l7 | westfirst | -6.94 | -3.00 |
| B9-T | k4 shuffle l8 | oefixed | -7.31 | -3.00 |
| B9-T | k4 tornado l7 | xy | -24.30 | -3.00 |
| B9-T | k4 tornado l8 | xy | -27.59 | -3.00 |
| B9-T | k8 bitcomp l5 | xy | -14.61 | -3.00 |
| B9-T | k8 bitcomp l6 | xy | -12.82 | -3.00 |
| O-T | k8 bitcomp l7 | o1turn | -3.77 | -3.00 |
| B9-T | k8 bitcomp l7 | xy | -11.31 | -3.00 |
| O-T | k8 bitcomp l8 | o1turn | -4.05 | -3.00 |
| B9-T | k8 bitcomp l8 | xy | -9.73 | -3.00 |
| O-T | k8 mixed l6 | o1turn | -7.06 | -3.00 |
| B9-T | k8 mixed l6 | dbar | -13.28 | -3.00 |
| O-T | k8 mixed l7 | o1turn | -9.63 | -3.00 |
| B9-T | k8 mixed l7 | dbar | -11.40 | -3.00 |
| O-T | k8 mixed l8 | o1turn | -12.64 | -3.00 |
| B9-T | k8 mixed l8 | o1turn | -12.64 | -3.00 |
| B9-T | k8 multiflow l6 | xy | -10.14 | -3.00 |
| B9-T | k8 multiflow l7 | xy | -8.58 | -3.00 |
| B9-T | k8 multiflow l8 | xy | -7.42 | -3.00 |
| B9-T | k8 shuffle l6 | topsis | -6.09 | -3.00 |
| B9-T | k8 shuffle l7 | duato | -5.58 | -3.00 |
| B9-T | k8 shuffle l8 | duato | -6.59 | -3.00 |
| O-T | k8 tornado l5 | o1turn | -4.21 | -3.00 |
| B9-T | k8 tornado l5 | xy | -17.04 | -3.00 |
| O-T | k8 tornado l6 | o1turn | -4.90 | -3.00 |
| B9-T | k8 tornado l6 | xy | -18.16 | -3.00 |
| O-T | k8 tornado l7 | o1turn | -4.08 | -3.00 |
| B9-T | k8 tornado l7 | xy | -15.03 | -3.00 |
| O-T | k8 tornado l8 | o1turn | -3.07 | -3.00 |
| B9-T | k8 tornado l8 | xy | -12.39 | -3.00 |

