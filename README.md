# MAI_PAPER

Code for the figures and tables in the Afghanistan periodic-markets paper (`AFG_paper_revised.docx`, October 2026 draft).

The data are not in this repository. They are in the shared `MarketActivityIndex` folder. Write that folder's path in `code_paper/NTL_processing/mai_base.txt`, or set `MAI_BASE`. All outputs go to `MarketActivityIndex/output_paper/`.

## Which code makes which exhibit

All code is in `code_paper/`. Output paths are relative to `output_paper/`.

| Paper | Code | Output |
|---|---|---|
| Figure 1 | None (adapted from von Carnap et al. 2026) | |
| Figure 2 | None (Esri World Imagery Wayback scenes) | |
| Figure 3a | `exhibits/figures.py` (`fig01_region_map`) | `exhibits/fig01_region_map.png` |
| Figure 3b | `exhibits/figures.py` (`fig02_days_of_operation`) | `exhibits/fig02_days_of_operation.png` |
| Table 1 | `ActivityLevelsCehcks..ipynb` (summary table) | `market_day_validation/market_day_validation_table_2025_activity_area_norm2022.xlsx` |
| Figure 4a | `figure4_population_coverage.py` (see note 1) | `figures/fig4a_population_coverage.png` |
| Figure 4b | Not found (see note 1) | |
| Figure 5a | `exhibits/figures.py` (`fig03_access_categories`) | `exhibits/fig03_access_categories.png` |
| Figure 5b, 5c | `Results_paper.ipynb` (section 3.1) | `figures/cdf_nighttime_light_2018_by_access.png`, `..._2025_by_access.png` |
| Table 2 | `exhibits/paper_checks.py` | `exhibits/table2_goods_by_access.csv` |
| Figure 7a | `ActivityLevelsCehcks..ipynb` (market activity across the year) | `seasonality/monthly_market_day_activity_by_year.png` |
| Figure 7b | `ActivityLevelsCehcks..ipynb` (market activity across the year) | `seasonality/panel_E.png` |
| Table 3 | `exhibits/tables.py` (`tableA3_ndvi_marketday`) | `exhibits/tableA3_ndvi_marketday.csv` |
| Figure 8a | `Results_paper_stats.ipynb` (section 3) | `figures/fig05_gdp_vs_mai.png` |
| Figure 8b | `Results_paper_stats.ipynb` (section 3) | `figures/fig06_ntl_mai.png` |
| Figure 9 | `exhibits/figures.py` (`fig10_region_panels`) | `exhibits/fig10_region_panels.png` |
| Figure 10a | `exhibits/figures.py` (`fig08_mai_by_access`) | `exhibits/fig08_mai_by_access.png` |
| Figure 10b, c, d | `stata/run_event_study_ACCESS.do` | `event_study/fig_A_Access_H.png`, `_Int.png`, `_R.png` |
| Figure 11a, b, c | `stata/run_event_study_ACCESS.do` | `event_study/fig_A_Access_H_NLT.png`, `_Int_NLT.png`, `_R_NLT.png` |
| Figure A.1 | `exhibits/paper_checks.py` | `exhibits/figA1_validation_samples.png` |
| Figure A.2 | `exhibits/figures.py` (`fig13_poppy`, panel a) | `exhibits/fig13_poppy.png` |
| Table A.1 | `exhibits/tables.py` (`tableA2_poppy`) | `exhibits/tableA2_poppy.csv` |
| Figure A.3 | `ActivityLevelsCehcks..ipynb` (timing of weekday activity signals) | `market_day_validation/timing_weekday_activity_signals_A.png`, `_B.png` |
| Figure A.4 | `exhibits/figures.py` (`fig12_overpass`) | `exhibits/fig12_overpass.png` |
| Numbers in the text | `exhibits/paper_checks.py` | `exhibits/paper_checks.csv` |

The draft has no Figure 6: its numbering goes from Figure 5 to Figure 7.

## Order to run

Python 3.10 (the `py310` conda environment) and Stata 19 with `reghdfe`, `ftools`, `coefplot` and `outreg2`. Run from `code_paper/`.

1. `python data_build/build_derived.py`
2. `build_event_study_panel.ipynb`
3. `cd exhibits && python run_all.py && python paper_checks.py`
4. `ActivityLevelsCehcks..ipynb`, `Results_paper.ipynb` and `Results_paper_stats.ipynb`
5. `stata -b do stata/run_event_study_ACCESS.do`

Steps 3 and 4 do not depend on each other. Step 5 needs step 2. The upstream nighttime-light and NDVI processing (`NTL_processing/`, `NDVI_processing/`) only needs rerunning when the raw imagery changes; see their own READMEs.

## Notes

1. **Figure 4** comes from the detection team's notebook (`MAI_AFG/Code/AFG20250825.ipynb`), copied here without its database credentials. It needs Earth Engine access to the `projects/planetupload` and `projects/mali-candidate-locs` assets. It was not run here, because this account cannot read them. No code was found for panel b (OpenStreetMap markets).
2. **Figure 8**: the code's Market Activity Index line peaks at 110 in 2022 and ends at 88 in 2025, the same as every other figure. The image in the draft peaks at about 114 and ends at about 91, so it looks like an older version and should be replaced with the current output.
