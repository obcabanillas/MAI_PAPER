# code_paper

All the code that produces the tables, figures and numbers in the Afghanistan periodic-markets paper
(`document/AFG_paper_revised.docx`, final version). The code lives in this repository. The data and the
outputs do not: they stay in the MarketActivityIndex folder on OneDrive/Box.

**`EXHIBITS.md` lists every figure and table in the paper, the script or notebook cell that makes it, and the
output file.** All paper exhibits are written to `output_paper/paper_exhibits/`, named by exhibit number.

```
code_paper/
  EXHIBITS.md                  exhibit -> script / cell -> file, for every figure and table in the paper
  NTL_processing/              VIIRS rasters -> nighttime lights in 10 km market buffers (own README); config.py
  NDVI_processing/             district NDVI for the event-study panel (own README)
  data_build/                  raw data -> derived market panel, access categories, market NDVI; two-day-market panel
  build_event_study_panel.ipynb  the market-year panel for the event study (processed_data/event_study_panel.dta)
  exhibits/                    Figures 5a, 8, A.1, A.2, A.4; Tables 1, 2, 3, A.1; paper_checks.py
  stata/run_event_study_ACCESS.do  Figures 9 and 10, the event study
  Results_paper_stats.ipynb    Figures 3 and 7; also writes processed_data/market_images.csv
  Results_paper.ipynb          Figure 5b-c
  ActivityLevelsCehcks..ipynb  Figures 6 and A.3 (market-day validation tests and seasonality)
  figure4_population_coverage.py  Figure 4a (needs the detection team's Earth Engine assets)
  archive/                     code for exhibits not in the final paper (not maintained)
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
  output_paper/paper_exhibits/   every figure and table in the paper (see EXHIBITS.md)
  output_paper/                  supporting outputs: event_study/ (regression tables behind Figures 9-10),
                                 market_day_validation/ (diagnostics behind Figure A.3), seasonality/,
                                 exhibits/paper_checks.csv
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
| 4 | `build_event_study_panel.ipynb`; `python data_build/build_event_study_days_panel.py` | `processed_data/event_study_panel.dta`, `event_study_days_panel.dta` |
| 5 | `Results_paper_stats.ipynb` (run all) | `processed_data/market_images.csv`; Figures 3, 7 |
| 6 | `cd exhibits && python run_all.py` | Figures 5a, 8, A.1, A.2, A.4; Tables 1, 2, 3, A.1; data checks |
| 7 | `Results_paper.ipynb`, `ActivityLevelsCehcks..ipynb` (run all) | Figures 5b-c, 6, A.3 |
| 8 | `cd stata && stata -b do run_event_study_ACCESS.do` | Figures 9, 10 |
| 9 | `cd exhibits && python paper_checks.py` | `output_paper/exhibits/paper_checks.csv` (numbers in the text vs the code) |

Steps 1-4 only need rerunning when the raw data change. Step 3's comparison should report every column as
identical; that confirms the derived files `exhibits/` reads are the ones the raw data produce.
`Results_paper_stats.ipynb` rebuilds `market_images.csv` when `process = 1` in its data cell; set it to 0 to
reuse the existing file.

## Where each exhibit comes from

See `EXHIBITS.md`.

## Not in this repository

| Item | Why |
|---|---|
| Market detection: the 137 market outlines, their trading days and the per-image activity readings (`forAFG_paper_activity_all.csv`, the market registry) | Produced by the PlanetScope / Sentinel-2 pipeline (von Carnap et al. 2026), run outside this project; includes the 729 OSM locations, the 25% search area and the 2,500 screened candidates |
| Figure 1, the detection method | Adapted from von Carnap et al. (2026); not generated from data |
| Figure 2, a market on market and non-market days | Esri World Imagery Wayback scenes |
| Figure 4, population within 20 km (the 40% and 90% shares) | Panel a is `figure4_population_coverage.py`, from the detection team's notebook; it needs their Earth Engine assets and has not been run here. Panel b (OSM markets) is external: no code for it exists in this repository |
| WFP field validation (`data/WFP_validation/market_validation_corrected.xlsx`) | Field data, compiled by hand |
| Travel times, catchment populations, nighttime-light buffers, monthly NDVI zonal statistics | Geospatial outputs (GRUFS, WorldPop, VIIRS, MODIS) in `data/Geospatial Analysis Outputs/`; the scripts that produced them are not in this repository, except the VIIRS buffers (`NTL_processing/`) |
| National accounts, ACLED, control-status panel, UNODC poppy areas | External data |

## Conventions and known issues

- Activity is `activity_area_norm2020` throughout, except the day-validation tests of Table 1 and Figure A.3
  (`ActivityLevelsCehcks..ipynb`), which use `activity_area_norm2022`.
- Market `lon62_5018lat34_2416` (Pashtonzarghon, Hirat) has no registry trading day. The paper uses Monday
  (`exhibits/common.py` `SUPPLIED_DAYS`, and `FIX_MKT` in the notebooks). The imagery shows it trading on
  Monday and Thursday; the WFP field team reported Wednesday in 2026.
- Figures 9 and 10 show 90% confidence intervals (t with G-1 degrees of freedom, G = province clusters);
  the notes to both figures in the paper still say 95 percent. Figure 6b also shows 90% intervals.
- The older Python event study that was in `Results_paper.ipynb` is not used in the paper; it is in
  `archive/Results_paper_archive.ipynb`.
