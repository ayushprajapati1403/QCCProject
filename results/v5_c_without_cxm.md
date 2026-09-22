# V5 observation: is the decoherence floor needed without CXM? (development set, 10 seeds; descriptive)

Same 4 development instances, seeds and budget as `results/v5_c_under_cxm.md`. Pairs = (family, instance seed, run seed); p values are run-level Wilcoxon tests, descriptive only (4 instances, no held-out seeds).

## Paired contrast c = 0 − c = 1, gap2 (%)

| condition                      | host        |   pairs |   mean c=0 |   mean c=1 |   diff c0-c1 |   CI95 lo |   CI95 hi |   c=0 better |   c=1 better |   p (run-level, descriptive) |
|:-------------------------------|:------------|--------:|-----------:|-----------:|-------------:|----------:|----------:|-------------:|-------------:|-----------------------------:|
| without CXM                    | P-MRFO      |      40 |    19.6763 |     4.5613 |      15.1150 |   10.3359 |   20.5216 |            2 |           38 |                       0.0000 |
| without CXM                    | QI-MRFO     |      40 |     9.8480 |     3.7271 |       6.1210 |    4.4162 |    7.9316 |            2 |           38 |                       0.0000 |
| with CXM (from v5_c_under_cxm) | P-MRFO+CXM  |      40 |     0.7206 |     0.6845 |       0.0361 |   -0.2164 |    0.3575 |           21 |           19 |                       0.6380 |
| with CXM (from v5_c_under_cxm) | QI-MRFO+CXM |      40 |     0.6260 |     0.8164 |      -0.1904 |   -0.8052 |    0.4447 |           24 |           14 |                       0.0998 |

## Paired contrast c = 0 − c = 1, global duplicate evaluations (%)

| condition                      | host        |   pairs |   mean c=0 |   mean c=1 |   diff c0-c1 |   CI95 lo |   CI95 hi |   c=0 better |   c=1 better |   p (run-level, descriptive) |
|:-------------------------------|:------------|--------:|-----------:|-----------:|-------------:|----------:|----------:|-------------:|-------------:|-----------------------------:|
| without CXM                    | P-MRFO      |      40 |    84.6658 |    47.4548 |      37.2110 |   35.3456 |   39.0792 |            0 |           40 |                       0.0000 |
| without CXM                    | QI-MRFO     |      40 |    83.4384 |    38.2194 |      45.2190 |   43.5016 |   46.8561 |            0 |           40 |                       0.0000 |
| with CXM (from v5_c_under_cxm) | P-MRFO+CXM  |      40 |    36.3247 |    12.0172 |      24.3075 |   21.1741 |   27.5768 |            0 |           40 |                       0.0000 |
| with CXM (from v5_c_under_cxm) | QI-MRFO+CXM |      40 |    28.7190 |     7.2564 |      21.4626 |   18.0201 |   25.1305 |            1 |           39 |                       0.0000 |

## mean gap2 (%) by family, without CXM

| host    |      c |   n100 m10 uniform high |   n30 m5 uniform high |   n50 m10 bimodal high |   n50 m10 uniform none |    mean |
|:--------|-------:|------------------------:|----------------------:|-----------------------:|-----------------------:|--------:|
| P-MRFO  | 0.0000 |                 34.3315 |                3.9102 |                27.6216 |                12.8421 | 19.6763 |
| P-MRFO  | 1.0000 |                  1.3255 |                0.7826 |                13.2466 |                 2.8906 |  4.5613 |
| QI-MRFO | 0.0000 |                 12.3386 |                2.6240 |                16.8075 |                 7.6220 |  9.8480 |
| QI-MRFO | 1.0000 |                  1.0874 |                0.9594 |                 9.9557 |                 2.9057 |  3.7271 |
