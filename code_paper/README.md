# code_paper

Code for the figures and regressions in the Afghanistan market-activity paper.

```
code_paper/
  NTL_processing/            VIIRS -> market-level nighttime lights (own README)
  build_event_study_panel.py builds the analysis panel from the NTL output + covariates
  Results_paper.ipynb        all figures and regressions in the paper
```

The code lives in this repository. The data does not — it stays in the
MarketActivityIndex folder on Box, which also holds the outputs:

```
MarketActivityIndex/
  data/                      raw inputs (VIIRS rasters, market lists, ACLED, ...)
  processed_data/            analysis-ready data - no figures, no results
  output_paper/
    event_study/             final regression workbook and coefficient figure
    figures/                 CDF figures
```

## Pointing the code at the data

Every path is derived from one value, `BASE`, resolved in `NTL_processing/config.py`:

1. the `MAI_BASE` environment variable, if set;
2. the path in `NTL_processing/mai_base.txt` — one line, git-ignored, so each
   machine keeps its own;
3. two levels up from `config.py`, which is only right if the code sits inside
   the MarketActivityIndex folder.

If the resolved `BASE` has no `data/` folder, `config.py` raises instead of
letting the scripts run against wrong paths. On a new machine, create
`mai_base.txt` containing the absolute path to the MarketActivityIndex folder.

## Order to run

1. `NTL_processing/01` … `06` — see `NTL_processing/README.md`. Produces the
   three NTL files in `processed_data/`.
2. `python build_event_study_panel.py` — joins the periodic-market nighttime
   lights to market activity, conflict, NDVI and population, and writes
   `processed_data/event_study_panel.dta` (and `.csv`).
3. Open `Results_paper.ipynb` and run all cells.

Steps 1 and 2 only need rerunning if the underlying data changes. The notebook
reads `processed_data/` and is self-contained apart from Section 3, which reads
the monthly VIIRS rasters once to compute the Kabul reference value and then
caches it.

## What the notebook produces

| Section | Output |
|---|---|
| 3 | Kabul reference light value, cached to `processed_data/kabul_reference_10km_bnr.csv` |
| 4 | `output_paper/figures/cdf_nighttime_light_{2018,2025}_periodic_vs_osm.png` |
| 5-6 | `output_paper/event_study/AFG_event_study_models_EVERLIT.xlsx` and `event_study_everlit_figure.png` |

## Reading the CDF figures

The horizontal axis is the median monthly **total radiance summed over the
10 km buffer**, on a log scale. Because a sum scales with buffer area, the
Kabul reference is computed on the same 10 km buffer; the notebook also
computes and caches the per-pixel mean alongside it, so switching the axis to a
mean is a one-line change in `draw_cdf`.

Each curve **starts at the share of markets with any light** and accumulates
from there across the lit markets' brightness, reaching 100% at the brightest
market. Dark markets carry no brightness information, so they set the starting
height and are not placed on the horizontal axis. A vertical riser carries each
curve down to the x-axis at its leftmost value, so the lines never run into the
y-axis.

The axis starts at zero on the log scale, i.e. a buffer total of 1. The handful
of lit markets dimmer than that are clipped to the left edge (`FLOOR` in the
notebook), which lifts the visible starting height marginally above the
positive-light share: 58.6% against 56.9% for periodic markets in 2018, 74.8%
against 73.7% in 2025, 48.9% against 47.7% and 59.0% against 58.7% for OSM-only.
Both numbers print when the cell runs. Setting `FLOOR = 0` and letting the axis
start at the true minimum makes the curve start exactly at the positive-light
share, at the cost of an axis that begins near −1.2 rather than 0.

The dashed line is the same measure computed for a 10 km buffer on Kabul city
centre (`config.KABUL_LON/LAT`, 69.1783 E / 34.5253 N), for the same year.

## The three event-study models

Year dummies (2020 omitted) interacted with three time-invariant baseline
characteristics — once-a-week trading, distance to the nearest OSM market, log
catchment population — with market and year fixed effects, standard errors
clustered by district, and two time-varying controls (log district deaths per
100,000 and growing-season NDVI deviation).

| Model | Sample | Outcome |
|---|---|---|
| A | all 137 markets | market activity index, each market rescaled to its own 2020 = 100 |
| A | 52 always-lit markets | same, restricted to markets with positive BNR radiance in *every* year |
| B | 107 ever-lit markets | log Feb-Jun median BNR radiance, for markets lit in *at least one* year |

Model B's ever-lit sample is an unbalanced panel: a market-year in which the
market was dark drops out as a missing outcome rather than being set to zero.

Expected output when the models run: Model A all markets n=1077, R²=0.4826;
Model A always-lit n=416, R²=0.5579; Model B ever-lit n=600 over 106 markets,
R²=0.8992.

## Environment

Built and verified on Python 3.8 with pandas, numpy, statsmodels, scipy,
matplotlib, geopandas, rasterio, rasterstats, shapely, pyproj and openpyxl.

`geopandas` 0.13 with `fiona` 1.10 needs `import fiona.path` before the first
`geopandas.read_file` call; `build_event_study_panel.py` already does this.
