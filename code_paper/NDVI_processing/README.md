# NDVI_processing

District-quarter NDVI over agricultural land, from MODIS MOD13Q1 composites
masked by ESA WorldCover land cover. Paths come from
`../NTL_processing/config.py`.

## Method

Agricultural land is **cropland (WorldCover class 40) + grassland (class 30)**,
28.1% of Afghanistan's land area. Cropland alone is 7.1%, grassland 21.0%, so
rangeland carries roughly three-quarters of the weight — every output therefore
carries a cropland-only column beside it (`ndvi_crop`) so the two can be
compared rather than assumed equivalent. They correlate 0.74, not 1.0.

The land cover is 10 m and the NDVI is 250 m, so each NDVI pixel covers ~625
land-cover pixels. Rather than force pixels in or out with a threshold, script
01 computes the **share** of each NDVI pixel that is cropland, grassland and
mapped land, and those shares become the weights in the district mean. This
matters: only 6.3% of land pixels are majority-cropland but 18.4% contain some,
so a 50% cutoff would discard most of the cropland signal.

MOD13Q1 composites are 16-day windows fixed from 1 January and do not align to
calendar quarters, so each composite is weighted by **how many of its days fall
in the quarter**. Only Q2 (Apr-Jun) and Q3 (Jul-Sep) are kept.

Deviations standardize each district-quarter against that same district's own
long-run mean and standard deviation for that quarter, matching the convention
already used for market-level NDVI in the event study:

    ndvi_ag_dev = (ndvi_ag - mean over years) / sd over years

## Scripts

| Script | What it does | Runtime |
|---|---|---|
| `00_extract_ndvi_zips.py` | Unpacks the Drive export zips into the NDVI folder, Apr-Sep only. Skips files already present, so it is safe to re-run | ~90 min, Box-bound |
| `01_build_ag_fraction.py` | Streams the 10 m land cover in blocks and writes `processed_data/ndvi_ag_fraction_250m.tif` (bands: crop_frac, grass_frac, valid_frac) | ~20 min, run once |
| `02_build_district_ndvi.py` | Rasterizes the 401 districts onto the NDVI grid, takes weighted district means per composite | ~85 min for 229 dates |
| `03_build_quarterly_ndvi.py` | Aggregates composites to quarters and adds deviations | seconds |

Check on 01: the area-weighted mean shares it reports (cropland 0.0705,
grassland 0.2102) reproduce the 10 m class histogram (7.05%, 21.02%) — area is
conserved through the aggregation.

Everything except 03 is I/O-bound on Box, not CPU-bound. Python sits near zero
CPU while Box hydrates files on demand; expect long stretches with no output.

## Outputs, in processed_data/

| File | Contents |
|---|---|
| `ndvi_ag_fraction_250m.tif` | Per-NDVI-pixel cropland / grassland / mapped-land shares |
| `district_index_250m.tif` | District index on the NDVI grid, 0 = outside |
| `ndvi_district_composite.csv` | One row per district x composite date |
| `ndvi_district_monthly.csv` | One row per district x year x month |
| `ndvi_district_quarterly.csv` | **The measure**: district x year x quarter, Q2 and Q3 |

Quarterly columns: `district_id` (Pcode_24, the same key the event study
clusters on), `year`, `quarter`, `days`, `n_composites`, then for each of
`ndvi_ag` and `ndvi_crop`: the level, `_dev` (standardized), `_anom` (level
minus long-run mean, in NDVI units), `_mean_lr`, `_sd_lr` and `_n_years`.

`days` is how many composite-days back each figure — 85-92 of a ~91-day quarter,
so coverage is effectively complete. `_n_years` shows the depth of the baseline
behind each deviation (median 14, minimum 9), so thin baselines are visible
rather than implicit.

## Two things to know about the input NDVI

**The archive mixes two encodings.** Raw MOD13Q1 `int16` scaled by 10000, and
`float64` already divided by 10000 and clipped to Afghanistan. Some dates appear
in both. `pick_files()` keeps one file per date and `load_ndvi()` scales the
integers — but anything that reads these rasters naively will silently destroy
the integer files, since their values sit far outside the valid NDVI range.

**The float export clips 31 border districts.** Nangarhar, Kunar, Nuristan,
Badakhshan, Herat, Farah and Nimroz frontier districts, plus Jalalabad, Herat
city and Zaranj, fall outside the mask baked into the float files, so on those
dates they have no data. The int16 files carry no such clip and rely on this
pipeline's own WorldCover and district masking, which is explicit and
consistent. Re-exporting every date as unclipped int16 would remove the gap.

**Drive export parts 002 and 006 were missing** when the zips were unpacked, so
whatever composites they held are absent.
