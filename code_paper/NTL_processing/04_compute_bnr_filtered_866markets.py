"""
Compute a BNR-filtered (World Bank viirs_versatile "background noise
reduction") version of the monthly VIIRS avg_rad zonal stats, for the
866-market universe (137 periodic + 729 OSM), for 2018, 2020, 2023, 2025.

Filter (VIIRS_analyzer.ipynb cell 22, worldbank/viirs_versatile), applied
PER YEAR using that year's OWN average_masked composite as the reference
mask (the "appropriate" fix vs. the World Bank script's default of reusing
one static year for the whole panel):

    mask_bool = average_masked[year] > 0
    avg_rad_BNR = avg_rad.where(mask_bool & (avg_rad > 0) & (avg_rad < 300))

Adds SUM_BNR_YYYYMM / MEAN_BNR_YYYYMM / NPIX_BNR_YYYYMM columns alongside
the plain SUM/MEAN/NPIX already in the main output file.
"""

# --- paths come from config.py (edit that one file, or set MAI_BASE) ---------
import os as _os_cfg
import sys as _sys_cfg
_sys_cfg.path.insert(0, _os_cfg.path.dirname(_os_cfg.path.abspath(__file__)))
from config import BASE, DATA, VIIRS_DIR, MASK_DIR, WORK_DIR
OUT_DIR = WORK_DIR
# ---------------------------------------------------------------------------
import glob
import os
import re

import numpy as np
import pandas as pd
import rasterio
from pyproj import Geod
from rasterstats import zonal_stats
from shapely.geometry import Polygon


YEARS = ["2018", "2020", "2023", "2025"]
MAX_RAD_CAP = 300.0

GEOD = Geod(ellps="WGS84")


def geodesic_circle(lon, lat, radius_km=10.0, n_points=72):
    dist_m = radius_km * 1000.0
    angles = np.linspace(0, 360, n_points, endpoint=False)
    lons, lats, _ = GEOD.fwd(
        np.full(n_points, lon), np.full(n_points, lat), angles, np.full(n_points, dist_m)
    )
    return Polygon(zip(lons, lats))


# ---------------------------------------------------------------- load markets
periodic = pd.read_csv(os.path.join(DATA, "MAI_periodic_markets_137.csv"))
periodic = periodic.rename(columns={"mktID": "orig_id", "latitude": "lat", "longitude": "lon"})
periodic["source"] = "periodic_137"
periodic["mkt_uid"] = "P_" + periodic["orig_id"].astype(str)
periodic = periodic[["mkt_uid", "source", "orig_id", "lat", "lon"]]

osm = pd.read_csv(os.path.join(DATA, "osm_markets_nearest_detected_distance.csv"))
osm = osm.rename(columns={"osm_id": "orig_id", "osm_lat": "lat", "osm_lon": "lon"})
osm["source"] = "osm_729"
osm["mkt_uid"] = "O_" + osm["orig_id"].astype(str)
osm = osm[["mkt_uid", "source", "orig_id", "lat", "lon"]]

markets = pd.concat([periodic, osm], ignore_index=True, sort=False)
assert len(markets) == 137 + 729, f"expected 866, got {len(markets)}"
print(f"Loaded {len(markets)} markets (137 periodic + 729 OSM)")

geoms = [geodesic_circle(lon, lat) for lon, lat in zip(markets["lon"], markets["lat"])]
out = markets.copy()


# ---------------------------------------------------------------- per-year BNR filter
pattern = re.compile(r"afg_viirs_(\d{6})\.tif$")

for year in YEARS:
    mask_path = os.path.join(MASK_DIR, f"afg_viirs_annual_masked_{year}.tif")
    with rasterio.open(mask_path) as ds:
        mask_arr = ds.read(1)
    mask_bool = mask_arr > 0
    print(f"\n=== {year}: reference mask {mask_bool.sum()}/{mask_bool.size} "
          f"pixels valid ({100*mask_bool.mean():.1f}%) ===")

    month_tifs = sorted(
        f for f in glob.glob(os.path.join(VIIRS_DIR, f"afg_viirs_{year}*.tif"))
        if "cf_cvg" not in os.path.basename(f)
    )
    for tif in month_tifs:
        m = pattern.search(os.path.basename(tif))
        if not m:
            continue
        ym = m.group(1)
        with rasterio.open(tif) as ds:
            avg_rad = ds.read(1)
            transform = ds.transform
            crs = ds.crs

        if avg_rad.shape != mask_bool.shape:
            print(f"  {ym}: SHAPE MISMATCH avg_rad{avg_rad.shape} vs mask{mask_bool.shape} -- BNR set to NaN")
            out[f"SUM_BNR_{ym}"] = np.nan
            out[f"MEAN_BNR_{ym}"] = np.nan
            out[f"NPIX_BNR_{ym}"] = 0
            continue

        valid = mask_bool & (avg_rad > 0) & (avg_rad < MAX_RAD_CAP) & ~np.isnan(avg_rad)
        bnr_arr = np.where(valid, avg_rad, np.nan).astype("float64")

        stats = zonal_stats(
            geoms, bnr_arr, affine=transform, stats=["sum", "mean", "count"],
            nodata=np.nan, all_touched=False
        )
        out[f"SUM_BNR_{ym}"] = [s["sum"] for s in stats]
        out[f"MEAN_BNR_{ym}"] = [s["mean"] for s in stats]
        out[f"NPIX_BNR_{ym}"] = [s["count"] for s in stats]
        print(f"  {ym} done")

out_path = os.path.join(DATA, "markets_VIIRS_10km_buffer_137_729_2018_2020_2023_2025_BNR.csv")
out.to_csv(out_path, index=False)
print(f"\nDONE. Wrote {out_path}  shape={out.shape}")
