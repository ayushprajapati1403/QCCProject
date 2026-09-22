# H5 post hoc analysis (EXPLORATORY — not pre-registered)

Written after reading `results/h5_analysis.md`. Nothing here is a confirmatory test.

## P2 re-expressed as the relative gap reduction 1 - gap2(QI-MRFO+CXM) / gap2(QI-MRFO)

| family                  |   relative gap reduction |   baseline unused improving swaps |
|:------------------------|-------------------------:|----------------------------------:|
| n100 m10 bimodal high   |                    0.920 |                            25.350 |
| n100 m20 lognormal low  |                    0.218 |                             0.350 |
| n120 m12 lognormal high |                    0.923 |                            37.550 |
| n150 m15 uniform high   |                    0.918 |                           158.650 |
| n200 m10 bimodal none   |                    0.978 |                           195.350 |
| n300 m30 uniform high   |                    0.961 |                           617.950 |
| n60 m12 uniform low     |                    0.927 |                            35.200 |
| n80 m8 uniform high     |                    0.935 |                            47.250 |

Spearman (baseline unused swaps vs relative reduction): families rho = 0.714 (p = 0.047); instances rho = 0.348 (p = 0.0016, n = 80).

## Why QI-MRFO+CXM loses to Max-Min on 'n100 m20 lognormal low'

| inst_seed | LB2 | L_max / S_max | total work / total speed | Max-Min makespan | QI-MRFO+CXM (mean of 2 seeds) |
|---|---|---|---|---|---|
| 101 | 32.240 | 32.240 | 25.279 | 32.240 | 33.014 |
| 102 | 30.036 | 30.036 | 24.912 | 30.036 | 32.511 |
| 103 | 33.672 | 33.672 | 24.558 | 33.672 | 36.416 |
| 104 | 33.005 | 33.005 | 27.771 | 33.005 | 35.671 |
| 105 | 29.367 | 29.367 | 25.020 | 29.367 | 30.342 |
| 106 | 48.382 | 48.382 | 22.770 | 48.382 | 48.603 |
| 107 | 57.730 | 57.730 | 26.571 | 57.730 | 57.730 |
| 108 | 51.161 | 51.161 | 34.574 | 51.161 | 51.161 |
| 109 | 29.259 | 29.259 | 22.933 | 29.259 | 29.704 |
| 110 | 46.305 | 46.305 | 27.641 | 46.305 | 46.725 |

On every instance the bound is set by the largest task alone on the fastest VM, and Max-Min attains it, so it is provably optimal. Reaching that schedule by local moves requires emptying the fastest VM first; every such move is makespan-neutral and is rejected by strict acceptance (a plateau, like the V4 identical-task case).

