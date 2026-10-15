# Figures and tables — Afghanistan periodic markets (MAI)

Builds every figure and every table in the paper from raw data, and verifies the
result. Nineteen figures as PNG, four tables as CSV, 58 numerical checks.

This package produces exhibits only. It does not rebuild the manuscript, does
not write the prose statistics file, and writes nothing outside `out/`.

## Running it

The input data ships inside the package, so there is nothing to configure:

```
python run_all.py                 # 19 figures, 4 tables and 58 checks into ./out
python common.py                  # lists every input and how each one resolved
```

`run_all.py` also takes a stage — `figures`, `tables` or `verify` — to run just
that part. Nothing has to run in a particular order. Exit status is 0 only when
every figure and table was produced and every check passed.

To run against a different data tree, point `MAI_ROOT` at it; it takes
precedence over the bundled `data/`.

Python 3.11 with `pandas`, `numpy`, `geopandas`, `statsmodels`, `scipy`,
`matplotlib`, `openpyxl`, `xlrd`.

## What each file does

| File | Contents |
|---|---|
| `common.py` | Path resolution, the colour palette, and the shared helpers: `panel()`, `mai_series()`, `market_year_activity()`, `buffer_ntl()`, `access_categories()`, `haversine()`, `market_index()`, `frequency_pairs()`, `district_control_2020()`, `ntl_per_capita_by_control()`, `ntl_national()`, `ndvi_levels()`, `staggering_test()`, `check_inputs()`. |
| `figures.py` | One function per figure, `fig01_…` through `fig19_…`. `ALL` lists them in order. |
| `tables.py` | `table1_conflict_markets()`, `tableA1_region_coverage()`, `tableA2_poppy()`, `tableA3_ndvi_marketday()`. Each returns the formatted table and the frame behind it. `render_png()` draws a table as a picture for the exhibits the paper carries as images; `AS_IMAGE` lists them. |
| `verify.py` | 58 checks against published values and against the shipped `reference/` fixtures. |
| `run_all.py` | Runs the stages and reports what failed. |
| `paths.json.example` | Copy to `paths.json` to pin input locations explicitly. |
| `data/` | Every file the code reads, and nothing else — 31 files, 155 MB. See `data/README.md` for the contents and for what was left out and why. |
| `reference/` | Fixtures `verify.py` checks the computed values against. **Not inputs** — no figure or table reads them. |

## Output

Everything lands in `out/`, which is created on first run:

- `fig01_region_map.png` … `fig19_ntl_per_capita_by_control.png` — 19 figures at
  300 dpi.
- `table1_conflict_markets.csv`, `tableA1_region_coverage.csv`,
  `tableA2_poppy.csv`, `tableA3_ndvi_marketday.csv`.
- `tableA1_region_coverage.png` — the one table the paper carries as a picture
  rather than as a typeset table.

## Inputs and paths

**No machine-specific path is baked in, and the package reads only raw inputs.**
It does not depend on any other part of the repository having been run first.

The bundled `data/` folder holds every input, so `python run_all.py` works from
a fresh unzip with nothing set. `MAI_ROOT=/path/to/other/tree` overrides it.

Each input is resolved at import time by looking for it, in this order:

1. an explicit entry in `paths.json` beside `common.py` (copy
   `paths.json.example`);
2. the environment variable `MAI_<KEY>`, e.g. `MAI_PANEL`;
3. each known relative path under each search root;
4. a bounded search for the file's basename under each search root.

Search roots are `$MAI_ROOT`, any `ROOTS` listed in `paths.json`, the package
directory itself (which is how the bundled `data/` is found), a `data` directory
beside or above the package, the package's parent, and the working directory.
`python common.py` prints every input, whether it resolved, and **which rule
resolved it** — so a wrong file is visible, not just a missing one.

### Computed, not read

Three quantities used to be read from intermediate files produced by the wider
repository's pipeline (`Code/code_AFG_outline` scripts 02, 04 and 07). They are
computed from raw data inside the package:

| Was read from | Now computed by | Fidelity |
|---|---|---|
| `04_ntl_national.csv` | `common.ntl_national()` | Exact to floating point |
| `ndvi_levels.csv` | `common.ndvi_levels()` | Exact to floating point |
| `staggering_test.csv` | `common.staggering_test()` | `pairs` and `obs` exact; null mean, band and p-value move in the second or third decimal (seed-dependent draw) |

### `reference/` — fixtures, not inputs

`reference/` ships the files the package's own functions are expected to
reproduce, so `verify.py` means the same thing on every machine rather than
comparing against whatever happens to sit at a path. Four files: the three
above, plus `mai_poppy_splits.csv`, the published Hilmand and poppy-province
index splits. No figure or table reads any of them.

The staggering cross-check accepts either scale: some scripts write `obs` as a
share and some as a percentage, so `verify.py` detects and normalises rather than
assuming. `common.staggering_test()` itself returns **shares**;
`fig14_staggering` plots percentages, which is how the manuscript quotes them.

**`ndvi_levels.csv` needs an author decision.** The shipped fixture is the file
the original Figure 6 was drawn from, and `common.ndvi_levels()` reproduces it
exactly. It is *not* the same construction as the repository's
`07_greenness_by_year.csv`, and the two must not be substituted:

- **This file**: quarter-2 catchment NDVI averaged across the 136 published
  markets, then the national series standardised over 2012–2025.
- **`07_greenness_by_year.csv`**: each market-quarter standardised against its
  own long-run mean and standard deviation, then Q2 and Q3 averaged.

They correlate at about 0.97 but differ materially in level — 2018 is −1.59 on
the first and −0.84 on the second. Which one Figure 6 should use is an open
question; see `reference/README.md`.

### Other definitions recovered while removing the dependency

- **National nightlights**: civilian composite (total less the
  coalition-associated component) summed across all 34 provinces, February to
  June.
- **The staggering test** runs over `range(5, 31)` km. It starts at 5 km
  deliberately: at 2 km only three pairs qualify, so the share is sampling noise
  and the null band spans the whole unit interval, which stretches the axis and
  flattens the range where the result lives. `STAGGER_GRID` sets the grid. The
  null shuffles whole weekday sets across market locations, preserving both the
  national frequency of each weekday and each market's number of trading days.
  5,000 permutations.

## Trading days — all 137 markets

The registry's `marketDays` field is blank for four markets. Their trading days
are supplied in `common.SUPPLIED_DAYS` and filled in by `panel()`, so every
market in the panel carries one and nothing keyed on trading day drops markets
silently:

| Market | Province | Days |
|---|---|---|
| `lon62_5018lat34_2416` | Hirat | Monday |
| `lon63_7803lat35_731` | Badghis | Tuesday, Wednesday, Saturday |
| `lon69_3316lat35_0459` | Kapisa | Saturday |
| `lon70_3678lat34_8331` | Laghman | Thursday |

The last three are corroborated by the panel's own `weekdayThisAreaIsActive`
field on those markets' `mktDay == 1` rows, which agrees with `marketDays` for
all 133 markets where both exist. **Hirat is the exception**: the data flags
Monday *and* Thursday there (414 and 411 market-day observations), while the
authors supplied Monday. The package uses Monday, as instructed — see the open
items below.

Resulting distribution, against the 133 / 101 / 32 the manuscript reports:

| Days per week | Markets |
|---|---|
| 1 | 104 |
| 2 | 32 |
| 3 | 1 |

137 markets, **171 market-days**.

Two downstream counts move as a result, both because markets joined the pool
rather than because any method changed:

- **Frequency pairs**: 83 at 28 km, against the manuscript's 80. The threshold
  is unchanged — do not re-tune it to recover 80.
- **Staggering test**: 318 pairs at 30 km sharing a day 15.7 percent of the
  time, against 308 at 15.9 percent. `staggering_test(legacy=True)` reproduces
  the original 133-market configuration, and that is what `verify.py` checks
  against `reference/staggering_test.csv`.

## Key conventions

- **Target variable**: `activity_area_norm2020` throughout (`common.TARGET`).
- **The MAI cascade**: market-week → normalise each market to its own 2020 mean
  → mean across markets within year-month → quarter → year. `mai_series()`
  implements it; every index in the paper uses it.
- **137 markets.** The published derived file holds 136. `panel()` rebuilds the
  137th (`lon62_5018lat34_2416`, Hirat) from the raw all-days activity file,
  which reproduces the manuscript's access counts exactly: 47 high / 36
  intermediate / 54 remote. Its imagery ends in September 2024, so it
  contributes nothing to 2025. Pass `include_herat=False` for the published
  136-market file.
- **Calendar years** everywhere, not fiscal years.
- **Seven UN regions** from the `CSO_Region` field of the ADM1 boundary file,
  which covers all 34 provinces. `un_region_small` merges North East into East
  for the six-region version.
- **Buffer nightlights** are the background-noise-removed VIIRS 10 km market
  buffers, read from both source files, with a market that has no signal
  entering as zero rather than being dropped.
- **Control status** is taken from the last observation before January 2021.

## Verification

`verify.py` passes 58 of 58 checks. The national index is reproduced to two
decimals for all eight years (102.09, 100.42, 99.99, 108.87, 110.29, 103.04,
95.25, 88.47), as are the Hilmand splits, the access-category counts, the
trading-day distribution (137 / 104 / 32 / 1 / 171), the 120 always-active
markets, the legacy 308 staggering pairs, the buffer nightlights index, and the
inputs behind the two figures the authors respecified (Figure 3 panels b and d,
and Figure 5). The three `reference/` fixtures are reproduced exactly.

## Figure coverage

Slot names refer to the media files inside `AFG_paper_outline_revised.docx` and
are recorded here as provenance only; this package does not touch that document.

| Function | Paper slot | Status |
|---|---|---|
| `fig01_region_map` | image3 | Reproduced; seven regions — deviation 1 |
| `fig02_days_of_operation` | image6 | Reproduced on 137 markets — deviation 2 |
| `fig03_access_categories` | image9 / image10 | Panel b respecified — deviation 3 |
| `fig04_emissions_by_access` | image11 / image12 | Exact — medians 202 / 23 / 4, deviation 10 |
| `fig05_gdp_vs_mai` | image13 | Exact |
| `fig06_ndvi_ntl_mai` | image14 | Reproduced — deviation 4 |
| `fig07_hilmand` | image15 | Exact |
| `fig08_mai_by_access` | image16 | "All markets" is now a background bar — deviation 9 |
| `fig09_decline_grid` | image17 | Cell membership exact, means differ ~1 pt — deviation 5 |
| `fig10_region_panels` | image18 | Reproduced — deviation 1 |
| `fig11_control_status` | image19 / image20 | Ordering reproduced, levels differ — deviation 6 |
| `fig12_overpass` | image22 / image23 | Exact |
| `fig13_poppy` | image25 / image26 | Exact |
| `fig14_staggering` | image27 (paper shows panel b only) | Reproduced — deviation 2 |
| `fig15_region_change` | image28 | Exact |
| `fig16_frequency_pairs` | image21 | 83 pairs on the 137-market panel — deviation 7 |
| `fig17_nonmarket_days` | image24 | Exact — 120 markets, 689 tests, 94.2%, 4 survivors |
| `fig18_ntl_by_control` | *no slot* | Reproduced; the current draft has no place for it |
| `fig19_ntl_per_capita_by_control` | *no slot* | Reproduced — deviation 11 |

## Table coverage

| Function | Paper table | Status |
|---|---|---|
| `table1_conflict_markets` | Table 1, "Understanding the location of periodic markets" | Exact — every cell already matched the manuscript |
| `tableA1_region_coverage` | Figure 1 panel c (carried as `image5.emf`) | Exact — rendered as a PNG |
| `tableA2_poppy` | Table A2, poppy cultivation | Reproduced; 14 cells differ from the manuscript on the 137-market panel |
| `tableA3_ndvi_marketday` | Table A3, market-day activity and NDVI | Reproduced; 30 cells differ — see below |

**Table A3.** The NDVI regressor is `ndvi_mean_lag`, the *previous* quarter's
catchment greenness, standardised against the long-run climatology as
`(ndvi_mean_lag − ndvi_mean_long_term) / ndvi_std_long_term`. Note that the mean
and standard deviation belong to the observation's own quarter while the
numerator is the previous quarter's greenness; this is the authors' definition
and it is preserved deliberately. Each market's harvest quarter is the quarter
after its peak long-run greenness, which is the third calendar quarter for only
49 percent of markets. Imposing a common third-quarter harvest attenuates the
interaction from +3.10 to +1.19, the direction expected when half the sample is
assigned the wrong quarter.

This specification emits a `SingularMatrixWarning` — the design matrix is
rank-deficient, so at least one coefficient is not uniquely determined. The
table still populates. **Resolve the collinear term before these numbers go into
the appendix.**

## Deviations from the manuscript, and why

1. **Seven regions, not six.** The UN classification separates North East
   (Baghlan, Takhar) from East. East then holds 14 markets and North East 4.
   Measured on its own 2020 base, East ends 2025 about 14 percent above it while
   North East ends 22 percent below — a contrast the merged region hides.
2. **Four supplied trading days, and the 137th market.** See "Trading days"
   above. Adding the Hirat market moves 2022 from 110.29 to 110.37 and leaves
   2025 unchanged; filling the four blank trading days moves the day-of-operation
   shares, the staggering pool and the frequency-pair count.
3. **Figure 3 panel b was respecified by the authors.** It is now the cumulative
   distribution across the 137 markets of the **median** monthly buffer radiance
   in 2025, on a `log(1 + x)` horizontal scale so that the 73 markets with no
   measurable emissions sit at zero (53 percent of the sample). The highest
   market reaches 8.18 on that scale. The dashed reference at 10 is the median
   radiance within 5 km of the centre of Kabul, `figures.KABUL_REF`: it is
   **quoted from the manuscript, not computed**, because no 5 km Kabul-centre
   buffer exists in the shared data. Set `KABUL_REF` if a better value becomes
   available. `verify.py` pins the market count, the zero count and the maximum.
4. **NDVI is one series, and buffer nightlights are added**, implementing the
   ACTION comment on that figure. The manuscript split NDVI into above- and
   below-normal bars.
5. **`fig09` cell means differ by about one point** (−31.7 against −31.4). Cell
   membership is identical, so the tercile cuts agree; the gap is in the
   market-level change definition, which is not reproducible from the shared
   derived files. Treat this panel as approximate.
6. **`fig11` levels differ.** Group sizes are 26 government / 76 contested / 34
   Taliban-held and the ordering reproduces (Taliban-held peaks highest,
   government-held falls furthest), but levels run below the manuscript's. The
   manuscript allocates status with a district population composite that is not
   in the shared files.
7. **`fig16` pairs are rebuilt.** Every once-a-week market matched to a
   more-frequent market within 28 km. That threshold is not documented; it was
   recovered by search, and returned exactly the manuscript's 80 pairs on the
   panel before the four blank trading days were filled in. On the current
   137-market panel it returns 83. The more-frequent series matches closely; the
   once-weekly series runs about seven points low in 2023–2025, so the gap is
   understated here.
8. **Figure 5 draws "All markets" as a background bar**, not a dashed line, per
   instruction — the same convention `fig07_hilmand` already used. The bar is
   drawn from the 2020 base of 100, so its height reads as the deviation from
   2020, and the three access-category lines sit on top of it. The underlying
   series is unchanged; `verify.py` checks that the bar's 2025 height equals the
   national index (88.47).
9. **Figure 3 panel d takes its median over markets with emissions.** The rule on
   the intensity panel is the median across the markets that *have* positive
   emissions — 202 on the 34 high-access markets, 23 on 21 intermediate and 4 on
   9 remote — not the median across the whole access category, where the many
   dark markets would hold it at zero. That reproduces the manuscript's 202 and 4
   exactly. The only text change is dropping the word "log": these are radiance
   levels, not logs. `verify.py` pins all three medians.
10. **`fig19`, nightlights per person by 2020 control status.** Districts take
   their status from 21 October 2020, the last pre-transition observation; the
   panel's other 2020 reading is identical for every district, which the code
   asserts. Nightlights exist only at province level, so each province's
   February-to-June civilian composite is split across the three statuses in
   proportion to the population living under each status *within* that province,
   with the weights fixed at 2020 — group differences therefore reflect variation
   between provinces, not within them. Populations are the district populations
   of each group, summed by year.

   Districts are matched to the control geometry by representative point, which
   resolves **all 401** districts. The original version of this exhibit lost ten
   districts holding 1.8 percent of the national population to an unmatched join
   and reported group populations of 17.9 / 14.6 / 5.2 million; closing that gap
   gives **18.4 / 14.7 / 5.3**. Levels shift by about three percent, the indexed
   panel is unchanged to a decimal, and every conclusion holds. The levels panel
   is anchored at zero rather than truncated; pass `zero_base=False` for the
   original axis.

## Not reproduced

Five exhibits in the paper have no code path here, because the inputs they need
are not in the shared data:

- **image1.png** — illustration of the detection method, adapted from von Carnap
  et al. (2026). Not generated from data.
- **image2.jpeg** — satellite scenes of one market on a market and a non-market
  day. The PlanetScope imagery is not redistributable.
- **image4.jpg** — share of population, area and major cities within a given
  distance of a market. Needs a population raster and a distance surface.
- **image7.png** — detected markets and OpenStreetMap locations per 100,000
  people across the population-density distribution. Needs the OSM universe.
- **image8.jpeg** — density profile of detected markets. Same missing input.

## Open items for the authors

1. **Does the Hirat market trade twice?** `weekdayThisAreaIsActive` flags Monday
   *and* Thursday (414 and 411 market-day observations). The authors supplied
   Monday only and the package follows that. If Thursday is real,
   `SUPPLIED_DAYS['lon62_5018lat34_2416']` becomes `{1, 4}`, the market moves
   from once-weekly to twice-weekly, and the day-of-operation shares, the
   staggering pool and the frequency-pair split all shift again.
2. **Which NDVI construction does Figure 6 use?** See `reference/README.md`.
3. **Table A3 is rank-deficient.** Identify the collinear term.
4. **Figure 6 uses `KABUL_REF`, a number quoted from the manuscript rather than
   computed.** It needs a source or a 5 km Kabul-centre buffer.
5. **The manuscript's trading-day counts are stale** (133 / 101 / 32, 165
   market-days). The current panel gives 137 / 104 / 32 / 1 and 171.
