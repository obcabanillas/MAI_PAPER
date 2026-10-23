# Where each exhibit in the paper is made

The paper is `document/AFG_paper_revised.docx` (final version). Every figure and table it contains is listed
below, in the order it appears. All exhibits made by code are written to one folder,
`output_paper/paper_exhibits/` (`PAPER_EXHIBITS` in `NTL_processing/config.py`), with the exhibit number at the
start of the file name. Where the paper places panels as separate images, each panel is its own file.

In the code, each producing function or notebook cell is marked with the exhibit it makes: notebook cells start
with `# ==== PAPER FIGURE ...`, Python functions carry the exhibit in their docstring, and the Stata sections are
headed `* PAPER FIGURE ...`.

## Main text

| Exhibit | Content | Made by | File |
|---|---|---|---|
| Figure 1 | Detecting the signature of a periodic market | External: adapted from von Carnap et al. (2026) | — |
| Figure 2 | A detected market on market and non-market days | External: Esri World Imagery Wayback scenes | — |
| Figure 3a | Spatial distribution of periodic markets | `Results_paper_stats.ipynb`, cell `4abba201` | `fig03a_market_map.png` |
| Figure 3b | Day of market activity | `Results_paper_stats.ipynb`, cell `67b2d0b0` | `fig03b_days_of_operation.png` |
| Table 1 | Validation of satellite-detected trading days against field-reported schedules | `exhibits/tables.py`, `table1_day_validation` | `table1_day_validation.csv` |
| Figure 4a | Population and area coverage of periodic markets | `figure4_population_coverage.py` (needs the detection team's Earth Engine assets; not run here) | `fig04a_population_coverage.png` |
| Figure 4b | Population and area coverage of OpenStreetMap markets | External: no code in this repository | — |
| Figure 5a | Access categories defined by proximity and catchment population | `exhibits/figures.py`, `fig05a_access_categories` | `fig05a_access_categories.png` |
| Figure 5b | Markets with positive nighttime-light emissions, 2018 and 2025 | `Results_paper.ipynb`, cell `75e7e983` | `fig05b_positive_emissions.png` |
| Figure 5c | Nighttime-light radiance in 2018 and 2025 (CDF) | `Results_paper.ipynb`, cell `8ac2a286` | `fig05c_ntl_cdf.png` |
| Table 2 | Market characteristics and field validation, by access category | `exhibits/tables.py`, `table2_goods_by_access` | `table2_goods_by_access.csv` |
| Figure 6a | Aggregate market activity, yearly cycles | `ActivityLevelsCehcks..ipynb`, cell `ee7e61dd` | `fig06a_monthly_activity.png` |
| Figure 6b | Market activity by goods sold, quarterly patterns | `ActivityLevelsCehcks..ipynb`, cells `03922cee` (regression) and `13980027` (figure) | `fig06b_seasonality_by_goods.png` |
| Table 3 | Market-day activity and growing-season NDVI (equation A.2) | `exhibits/tables.py`, `table3_ndvi_marketday` | `table3_ndvi_marketday.csv` |
| Figure 7a | Market activity and real GDP | `Results_paper_stats.ipynb`, cell `079d7ef2` | `fig07a_mai_gdp.png` |
| Figure 7b | Market activity and nighttime-light emissions | `Results_paper_stats.ipynb`, cell `ec3f930c` | `fig07b_mai_ntl.png` |
| Figure 8 | Market activity and civilian nighttime lights by region | `exhibits/figures.py`, `fig08_regions` | `fig08_regions.png` |
| Figure 9a | Market activity by access category (equation 1) | `stata/run_event_study_ACCESS.do`, Regression 1 | `fig09a_access_categories.png` |
| Figure 9b | Local population and travel time (equation 2) | `stata/run_event_study_ACCESS.do`, Regression 2 | `fig09b_population_travel.png` |
| Figure 9c | Trading days within markets operating twice a week (equation 3) | `stata/run_event_study_ACCESS.do`, Regression 3 | `fig09c_two_day_markets.png` |
| Figure 9d | Once-a-week and multi-day markets | `stata/run_event_study_ACCESS.do`, Regression 4 | `fig09d_single_multi_day.png` |
| Figure 10a | Nighttime lights, changes by access category | `stata/run_event_study_ACCESS.do`, NTL by access | `fig10a_ntl_access_categories.png` |
| Figure 10b | Nighttime lights, local population and travel time | `stata/run_event_study_ACCESS.do`, NTL version of regression 2 | `fig10b_ntl_population_travel.png` |

## Annex

| Exhibit | Content | Made by | File |
|---|---|---|---|
| Figure A.1 | Market activity under alternative field-validation samples | `exhibits/figures.py`, `figA1_validation_samples` | `figA1_validation_samples.png` |
| Figure A.2 | Market activity by provincial poppy cultivation before the 2022 ban | `exhibits/figures.py`, `figA2_poppy` | `figA2_poppy.png` |
| Table A.1 | Poppy cultivation and the decline in market activity, 2022 to 2025 | `exhibits/tables.py`, `tableA1_poppy` | `tableA1_poppy.csv` |
| Figure A.3a | Last year with a signal on an MAI-predicted day | `ActivityLevelsCehcks..ipynb`, cell `4f642dc2` | `figA3a_last_signal.png` |
| Figure A.3b | First year with a signal on a field-reported day | `ActivityLevelsCehcks..ipynb`, cell `4f642dc2` | `figA3b_first_signal.png` |
| Figure A.4a | Distribution of market-day images by time window | `exhibits/figures.py`, `figA4a_overpass_composition` | `figA4a_overpass_composition.png` |
| Figure A.4b | Estimated differences in measured activity by time window | `exhibits/figures.py`, `figA4b_overpass_effects` | `figA4b_overpass_effects.png` |

## Running everything

The data steps come first (see `README.md`). Then, in any order:

| Command | Makes |
|---|---|
| `cd exhibits && python run_all.py` | Figures 5a, 8, A.1, A.2, A.4a, A.4b; Tables 1, 2, 3, A.1; data checks |
| `Results_paper_stats.ipynb` (run all) | Figures 3a, 3b, 7a, 7b |
| `Results_paper.ipynb` (run all) | Figures 5b, 5c |
| `ActivityLevelsCehcks..ipynb` (run all) | Figures 6a, 6b, A.3a, A.3b |
| `cd stata && stata -b do run_event_study_ACCESS.do` | Figures 9a-d, 10a-b (regression tables to `output_paper/event_study/`) |
| `python figure4_population_coverage.py` | Figure 4a (needs Earth Engine access) |

`cd exhibits && python paper_checks.py` compares the numbers quoted in the text with the code; it makes no
exhibit and writes `output_paper/exhibits/paper_checks.csv`.

## Not in the paper

Code for exhibits that are not in the final paper is kept, unmaintained, in `archive/` (see `archive/README.md`).
