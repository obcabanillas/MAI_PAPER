# Reference fixtures

These three files are **not inputs**. No figure or table reads them. They are the
values the package's own functions are expected to reproduce, kept here so that
`verify.py` means the same thing on every machine.

| File | Checked against | Notes |
|---|---|---|
| `04_ntl_national.csv` | `common.ntl_national()` | Reproduced exactly. |
| `ndvi_levels.csv` | `common.ndvi_levels()` | Reproduced exactly. See the caution below. |
| `staggering_test.csv` | `common.staggering_test()` | `pairs` and `obs` reproduced exactly. The null mean, band and p-value are seed-dependent and are checked with a tolerance. `obs`, `null_mean`, `lo` and `hi` are stored here as **shares**; `verify.py` also accepts a percent-scaled file. |

## Caution on `ndvi_levels.csv`

This is the file the original Figure 6 was drawn from. It is **not** the same
construction as the repository's `07_greenness_by_year.csv`, and the two must not
be substituted for one another:

- **This file** (and `common.ndvi_levels()`): quarter-2 catchment NDVI averaged
  across the 136 published markets, then the national series standardised over
  2012–2025.
- **`07_greenness_by_year.csv`**: each market-quarter standardised against its
  own long-run mean and standard deviation, then Q2 and Q3 averaged.

They correlate at about 0.97 but differ materially in level — 2018 is −1.59 on
the first and −0.84 on the second. Which one Figure 6 should use is a question
for the authors; the package currently reproduces this file.
