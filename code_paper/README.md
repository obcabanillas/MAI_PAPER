# code_paper

All the code that produces the tables, figures and numbers in the Afghanistan periodic-markets paper
(`document/AFG_paper_revised.docx`). The code lives in this repository. The data and the outputs do
not: they stay in the MarketActivityIndex folder on OneDrive/Box.

```
code_paper/
  NTL_processing/              VIIRS rasters -> nighttime lights in 10 km market buffers (own README); config.py
  NDVI_processing/             district NDVI for the event-study panel (own README)
  data_build/build_derived.py  raw data -> the derived market panel, access categories and market NDVI
  build_event_study_panel.ipynb  the market-year panel for the event study (processed_data/event_study_panel.dta)
  exhibits/                    most figures and tables, and paper_checks.py (every number in the text)
  stata/run_event_study_ACCESS.do  Figures 10b-d and 11, the event study
  ActivityLevelsCehcks..ipynb  field validation (Table 1, Figure A.3) and seasonality (Figure 7)
  Results_paper.ipynb          nighttime-light distribution by access (Figure 5b-c)
  Results_paper_stats.ipynb    descriptive statistics and Figure 8
  figure4_population_coverage.py  Figure 4a (needs the detection team's Earth Engine assets)
  A1_ndvi_mai_regression.ipynb NDVI-MAI market-year regression (not in the current draft)
```

## Pointing the code at the data

Every path comes from `BASE`, resolved in `NTL_processing/config.py`: the `MAI_BASE` environment variable,
else the one-line file `NTL_processing/mai_base.txt` (git-ignored, one per machine), else two folders above
`config.py`. `BASE` is the MarketActivityIndex folder:

```
MarketActivityIndex/
  data/                          raw inputs (activity file, market registry, WFP validation, VIIRS, ACLED, ...)
  processed_data/                analysis-ready data written by the code (incl. derived/ from data_build)
  document/Repo_09042026/data/   the inputs exhibits/ reads (derived panel, NDVI, boundaries, nightlights, ...)
  output_paper/                  everything the code writes: exhibits/, figures/, seasonality/,
                                 market_day_validation/, event_study/, tables/
```

`exhibits/` finds its inputs through `config.py` as well (see `exhibits/common.py`); `exhibits/paths.json`
can pin individual files. Python 3.10 (the `py310` environment) with pandas, numpy, statsmodels, scipy,
matplotlib, seaborn, geopandas, shapely, rasterio, rasterstats, pyproj, openpyxl and xlrd. Stata 19 with
`reghdfe`, `ftools`, `coefplot` and `outreg2` for the event study.

## Order to run

| Step | Command | Writes |
|---|---|---|
| 1 | `NTL_processing/01` ... `06` (see its README) | nighttime lights in `processed_data/` |
| 2 | `NDVI_processing/00` ... `03` (see its README) | district NDVI in `processed_data/` |
| 3 | `python data_build/build_derived.py` | `processed_data/derived/`: market panel, access categories, market NDVI; compares them with the copies `exhibits/` reads |
| 4 | `build_event_study_panel.ipynb` | `processed_data/event_study_panel.dta` |
| 5 | `cd exhibits && python run_all.py` | 19 figures, 4 tables, 58 checks in `output_paper/exhibits/` |
| 6 | `cd exhibits && python paper_checks.py` | Table 2, Figure A.1, `paper_checks.csv` |
| 7 | `ActivityLevelsCehcks..ipynb`, `Results_paper.ipynb` (run all) | `output_paper/market_day_validation/`, `seasonality/`, `figures/` |
| 7b | `Results_paper_stats.ipynb` (run all) | `output_paper/figures/fig05_gdp_vs_mai.png`, `fig06_ntl_mai.png` |
| 8 | `cd stata && stata -b do run_event_study_ACCESS.do` | `output_paper/event_study/fig_A_Access_*.png`, `MAI_access.xls` |

Steps 1-4 only need rerunning when the raw data change. Step 3's comparison should report every column as
identical; that confirms the derived files `exhibits/` reads are the ones the raw data produce.

## Where each exhibit comes from

See the table in the repository's top-level `README.md`, which follows the numbering of the October 2026
draft (`document/AFG_paper_revised.docx`). The staggering test in the footnotes is
`exhibits/common.py` `staggering_test`, drawn as `exhibits/fig14_staggering.png`.

## Not in this repository

| Item | Why |
|---|---|
| Market detection: the 137 market outlines, their trading days and the per-image activity readings (`forAFG_paper_activity_all.csv`, the market registry) | Produced by the PlanetScope / Sentinel-2 pipeline (von Carnap et al. 2026), run outside this project; includes the 729 OSM locations, the 25% search area and the 2,500 screened candidates |
| Figure 1, the detection method | Adapted from von Carnap et al. (2026); not generated from data |
| Figure 2, a market on market and non-market days | Esri World Imagery Wayback scenes |
| Figure 4, population within 20 km (the 40% and 90% shares) | Panel a is `figure4_population_coverage.py`, from the detection team's notebook; it needs their Earth Engine assets and has not been run here. No code found for panel b (OSM markets) |
| WFP field validation (`data/WFP_validation/market_validation_corrected.xlsx`) | Field data, compiled by hand |
| Travel times, catchment populations, nighttime-light buffers, monthly NDVI zonal statistics | Geospatial outputs (GRUFS, WorldPop, VIIRS, MODIS) in `data/Geospatial Analysis Outputs/`; the scripts that produced them are not in this repository, except the VIIRS buffers (`NTL_processing/`) |
| National accounts, ACLED, control-status panel, UNODC poppy areas | External data |

## Conventions and known issues

- Activity is `activity_area_norm2020` throughout, except the day-validation tests of Table 1 and Figure A.3
  (`ActivityLevelsCehcks..ipynb`), which use `activity_area_norm2022`.
- Market `lon62_5018lat34_2416` (Pashtonzarghon, Hirat) has no registry trading day. The paper uses Monday
  (`exhibits/common.py` `SUPPLIED_DAYS`, and `FIX_MKT` in the notebooks). The imagery shows it trading on
  Monday and Thursday; the WFP field team reported Wednesday in 2026.
- `Results_paper.ipynb` section 5 is an older Python event study, not used in the paper (Figures 10 and 11
  come from the Stata do-file). It maps the panel's `ln_pop_30mixed` and `log_light_emissions` to the
  names it expects, `log_pop` and `log_feb_jun_bnr`.
