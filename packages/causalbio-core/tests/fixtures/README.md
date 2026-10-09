# Numerical reference fixture

`stan_bernoulli_diagnostics.npz` contains only the `lp__` and `theta` numerical
columns of the four 1,000-draw Stan Bernoulli diagnostic test chains, with array
shape `(chain, draw)`. Retrieved 2026-10-02 from the Stan project:

- [Original CSV directory](https://github.com/stan-dev/stan/tree/babdd0e67933e92355207a7cfe4c1dd07459e8c6/src/test/unit/analyze/mcmc/test_csv_files), files `bern1.csv` through `bern4.csv`.
- [Independent ESS expectations](https://github.com/stan-dev/stan/blob/babdd0e67933e92355207a7cfe4c1dd07459e8c6/src/test/unit/analyze/mcmc/split_rank_normalized_ess_test.cpp), calculated there using R's `posterior` package: `lp__` = 1512.7684, `theta` = 1407.5124.
- [Rank-normalized R-hat reference](https://github.com/stan-dev/stan/blob/babdd0e67933e92355207a7cfe4c1dd07459e8c6/src/test/unit/analyze/mcmc/split_rank_normalized_rhat_test.cpp), also calculated using R's `posterior`: `lp__` = 1.00073, `theta` = 1.006789.

The fixture is bundled so validation requires no network or additional sampling
library. It tests diagnostic calculations, not the CausalBio sampler or biology.
The Stan project is licensed under the BSD 3-Clause license; no Stan implementation
code is included here. Original project license: https://github.com/stan-dev/stan/blob/babdd0e67933e92355207a7cfe4c1dd07459e8c6/LICENSE.md.

Source commit: `babdd0e67933e92355207a7cfe4c1dd07459e8c6`. Both arrays were checked for exact equality against this commit's four original CSV columns. Fixture SHA-256: `da2a6cd58e4177f70e261d988435d6e023159a8f59d3186a155764b59ccf426c`. The original license is preserved in [STAN-LICENSE.md](STAN-LICENSE.md).
