# NTL_processing

Everything that turns raw VIIRS nighttime-lights imagery into the market-level
light measures used in the paper. Run the scripts in numerical order. All paths
live in `config.py` — that is the only file to edit when the folder moves.

## The measure

Light is measured inside a **10 km geodesic buffer** around each market
(`pyproj.Geod`, WGS84, 72-vertex polygon built directly in EPSG:4326 so it lines
up with the raster grid without reprojection). Zonal statistics use
`rasterstats.zonal_stats` with `all_touched=False` (pixel-centre-in-polygon).

Before the buffer statistics are taken, each monthly raster is passed through
the World Bank **BNR (background noise reduction)** filter from
[`worldbank/viirs_versatile`](https://github.com/worldbank/viirs_versatile):

```python
avg_rad_BNR = avg_rad.where(mask_bool & (avg_rad > 0) & (avg_rad < 300))
```

where `mask_bool` comes from the VIIRS annual `average_masked` composite.

**One deliberate departure from the World Bank script.** That script builds
`mask_bool` from a *single* reference year and applies it to every month of
every year, which freezes the set of lit and dark markets across the whole
panel — the dark share cannot move over time even if conditions do. Here the
mask is rebuilt **per year from that year's own `average_masked` composite**, so
2018 is masked with the 2018 composite, 2025 with the 2025 composite, and so on.
Every figure and regression in the paper uses this per-year-corrected version.

## Scripts

| Script | What it does | Needs |
|---|---|---|
| `01_download_annual_masks_2018_2020_2023_2025.py` | Downloads the annual `average_masked` composites used as per-year reference masks | Earth Engine |
| `02_download_annual_masks_2019_2021_2022_2024.py` | Same, for the four remaining years | Earth Engine |
| `03_compute_ntl_buffers_plain.py` | Unfiltered 10 km buffer SUM/MEAN/pixel-count for all 866 markets | monthly rasters |
| `04_compute_bnr_filtered_866markets.py` | BNR-filtered buffer statistics, 866 markets, 2018/2020/2023/2025 | monthly rasters + masks |
| `05_compute_bnr_filtered_periodic137_extra_years.py` | BNR-filtered buffer statistics, 137 periodic markets, 2019/2021/2022/2024 | monthly rasters + masks |
| `06_export_processed_ntl.py` | Assembles the above into `processed_data/` | outputs of 03-05 |

Scripts 01 and 02 authenticate to Google Earth Engine with the project named in
`config.EE_PROJECT`. Set the `EE_PROJECT` environment variable or edit
`config.py` to use your own registered project.

Scripts 04 and 05 are the same method applied to different market sets and
years; they are kept separate rather than merged so that each reproduces exactly
the run that produced the published numbers.

## External input: the monthly VIIRS rasters

The monthly `avg_rad` GeoTIFFs
(`NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG`, cropped to Afghanistan, one file per
month named `afg_viirs_YYYYMM.tif`) are **not** downloaded by any script here.
They are treated as a given input and are expected at `config.VIIRS_DIR`:

```
data/Geospatial Analysis Outputs/AFG_NTL_CROPPED/viirs/
```

They were produced by an earlier download step that is not part of this package.
Anyone rebuilding from scratch needs to obtain that monthly collection first;
everything downstream of it is reproduced by the scripts above.

## Outputs

Written to `processed_data/`:

| File | Contents |
|---|---|
| `ntl_bnr_866markets_4years.csv` | 866 markets (137 periodic + 729 OSM), monthly SUM/MEAN/pixel-count of BNR radiance, 2018/2020/2023/2025 |
| `ntl_bnr_periodic137_8years.csv` | 137 periodic markets, same columns, every year 2018-2025 |
| `market_groups.csv` | Market id, source, coordinates, distance to the nearest detected periodic market, and the three-way grouping used in the figures |

The three-way grouping is: **Periodic** (137), **OSM only** (OSM markets more
than 1 km from any detected periodic market, 646) and **OSM overlap** (OSM
markets within 1 km of one, 83).

## Requirements

`numpy`, `pandas`, `rasterio`, `rasterstats`, `shapely`, `pyproj`, `geopandas`,
and `earthengine-api` + `requests` for scripts 01-02.
