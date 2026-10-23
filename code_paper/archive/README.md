# archive

Code for exhibits that are **not** in the final paper (`document/AFG_paper_revised.docx`), moved here so that
the working code makes only the paper's figures and tables (listed in `../EXHIBITS.md`). Nothing here is
maintained or run, and it may depend on names or paths that have since changed.

| File | What it holds |
|---|---|
| `exhibits/figures_full.py` | The full `exhibits/figures.py` before the clean-up: `fig01`-`fig19` under an earlier draft's numbering (region map, days of operation, access and emissions, GDP and NDVI figures, Hilmand splits, decline grid, control status, staggering, frequency pairs, non-market days, nightlights by control status, and the two-panel versions of the overpass and poppy figures) |
| `exhibits/tables_full.py` | The full `exhibits/tables.py`: also the conflict-and-market-location table and the regional coverage table |
| `exhibits/verify_full.py` | The full set of 58 checks, including checks of the archived figures |
| `exhibits/paper_checks_full.py` | `paper_checks.py` as it was when it also wrote Table 2 and Figure A.1 |
| `Results_paper_archive.ipynb` | Cells moved out of `Results_paper.ipynb`: other CDF variants, per-year bar and dot plots by access, the older Python event study and its workbook |
| `Results_paper_stats_archive.ipynb` | Cells moved out of `Results_paper_stats.ipynb`: Hilmand splits, MAI by access, decline grid and its decomposition, frequency pairs, exploratory cells |
| `ActivityLevelsCehcks_archive.ipynb` | Cells moved out of `ActivityLevelsCehcks..ipynb`: an older version of Table 1, the switched-off `activity_measure` mirror, the goods workbook, secondary seasonality regressions |
| `A1_ndvi_mai_regression.ipynb` | NDVI and market-year activity regression (not in the paper) |
| `stata/run_event_study_ACCESS_full.do` | The do-file before the clean-up: also the per-access regressions with once-a-week terms (`MAI_access.xls`), their figures and the levels CSV |
| `move_cells.py` | The tool used to move notebook cells here (`python archive/move_cells.py SOURCE ARCHIVE CELL_ID ...`) |
