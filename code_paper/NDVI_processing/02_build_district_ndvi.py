"""
District-month NDVI over agricultural land.

Stage 2. Rasterizes the 2024 district boundaries onto the MODIS 250 m grid
once, then for every NDVI composite takes a district mean weighted by the
agricultural share of each pixel (from stage 1). Composites are 16-day, so
the monthly figure weights each composite by how many of its days fall in
the calendar month.

Two weightings are carried through in parallel:
  ndvi_ag    weighted by cropland + grassland share (classes 40 + 30)
  ndvi_crop  weighted by cropland share alone (class 40)
"""

# --- paths come from ../NTL_processing/config.py -----------------------
import os as _os_cfg
import sys as _sys_cfg
_sys_cfg.path.insert(0, _os_cfg.path.join(
    _os_cfg.path.dirname(_os_cfg.path.dirname(_os_cfg.path.abspath(__file__))),
    "NTL_processing"))
from config import BASE, DATA, PROCESSED  # noqa: E402
# -----------------------------------------------------------------------

import os
import re
import glob
import datetime as dt

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

import fiona
import fiona.path  # noqa: F401  (fiona >= 1.10 with geopandas 0.13)
import geopandas as gpd


RAW = os.path.join(BASE, "data", "Geospatial_RAW")


ADM2 = os.path.join(BASE, "document", "Repo_09042026", "data",
                    "ADM2_Dist_2024", "ADM2_Dist_2024.shp")
FRAC = os.path.join(PROCESSED, "ndvi_ag_fraction_250m.tif")
DIST_RAS = os.path.join(PROCESSED, "district_index_250m.tif")
NDVI_DIR = os.path.join(RAW, "MODIS_NDVI")

OUT_COMPOSITE = os.path.join(PROCESSED, "ndvi_district_composite.csv")
OUT_MONTHLY = os.path.join(PROCESSED, "ndvi_district_monthly.csv")

KEEP_MONTHS = [4, 5, 6, 7, 8, 9]   # Q2 and Q3
COMPOSITE_DAYS = 16
DATE_RE = re.compile(r"(\d{4})_(\d{2})_(\d{2})")


def build_district_index(ref_path):
    """Rasterize districts onto the NDVI grid; 0 means no district."""
    d2 = gpd.read_file(ADM2).to_crs("EPSG:4326")
    key = "Pcode_24" if "Pcode_24" in d2.columns else d2.columns[0]
    d2 = d2.reset_index(drop=True)
    d2["_idx"] = np.arange(1, len(d2) + 1, dtype="int32")
    with rasterio.open(ref_path) as ref:
        out = rasterize(
            ((geom, idx) for geom, idx in zip(d2.geometry, d2["_idx"])),
            out_shape=(ref.height, ref.width), transform=ref.transform,
            fill=0, dtype="int32", all_touched=False,
        )
        prof = ref.profile.copy()
    prof.update(count=1, dtype="int32", compress="deflate", nodata=0)
    with rasterio.open(DIST_RAS, "w", **prof) as dst:
        dst.write(out, 1)
    lookup = d2[["_idx", key]].copy()
    lookup.columns = ["_idx", "district_id"]
    for extra in ("Dist_Name", "Dist_name", "Prov_name", "Dist_ID_24"):
        if extra in d2.columns:
            lookup[extra.lower()] = d2[extra].values
    return out, lookup, key


def weighted_by_district(values, weights, idx, n_dist):
    """Sum(w*v)/Sum(w) per district index, ignoring non-finite values."""
    ok = np.isfinite(values) & (weights > 0) & (idx > 0)
    if not ok.any():
        return np.full(n_dist + 1, np.nan), np.zeros(n_dist + 1)
    i = idx[ok].ravel()
    w = weights[ok].ravel().astype("float64")
    v = values[ok].ravel().astype("float64")
    wsum = np.bincount(i, weights=w, minlength=n_dist + 1)
    vsum = np.bincount(i, weights=w * v, minlength=n_dist + 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(wsum > 0, vsum / wsum, np.nan)
    return mean, wsum


def load_ndvi(path):
    """Return NDVI in real units, whatever encoding the export used.

    The folder holds two exports of the same composites: raw MOD13Q1 int16
    scaled by 10000, and float64 already divided by 10000 and masked to
    Afghanistan. Scale the integers; treat MODIS fill and out-of-range as
    missing in both.
    """
    with rasterio.open(path) as ds:
        a = ds.read(1)
        nod, is_int = ds.nodata, np.issubdtype(np.dtype(ds.dtypes[0]), np.integer)
    a = a.astype("float32")
    if nod is not None:
        a = np.where(a == nod, np.nan, a)
    if is_int:
        a = np.where((a >= -2000) & (a <= 10000), a, np.nan) / 10000.0
    return np.where((a >= -1) & (a <= 1), a, np.nan)


def pick_files(dirpath):
    """One file per composite date, preferring the float (masked) export."""
    by_date = {}
    for p in sorted(glob.glob(os.path.join(dirpath, "*.tif"))):
        m = DATE_RE.search(os.path.basename(p))
        if not m:
            continue
        d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        with rasterio.open(p) as ds:
            is_float = np.issubdtype(np.dtype(ds.dtypes[0]), np.floating)
        rank = (1 if is_float else 0, os.path.getsize(p))
        if d not in by_date or rank > by_date[d][0]:
            by_date[d] = (rank, p)
    return [(d, v[1]) for d, v in sorted(by_date.items())]


def month_overlap_weights(start, n_days=COMPOSITE_DAYS):
    """Days of a composite window falling in each (year, month)."""
    out = {}
    for k in range(n_days):
        d = start + dt.timedelta(days=k)
        out[(d.year, d.month)] = out.get((d.year, d.month), 0) + 1
    return out


def main():
    n_raw = len(glob.glob(os.path.join(NDVI_DIR, "*.tif")))
    files = pick_files(NDVI_DIR)
    print("NDVI files on disk: %d -> %d distinct composite dates" % (n_raw, len(files)))

    print("Rasterizing districts onto the 250 m grid...")
    didx, lookup, key = build_district_index(FRAC)
    n_dist = int(lookup["_idx"].max())
    print("  %d districts (key column '%s'); %d of %d pixels fall in one"
          % (n_dist, key, int((didx > 0).sum()), didx.size))

    with rasterio.open(FRAC) as f:
        crop, grass, valid = f.read()
    w_ag = np.where(valid > 0, crop + grass, 0.0)
    w_crop = np.where(valid > 0, crop, 0.0)
    print("  weight totals: ag %.1f px-equivalents, cropland %.1f"
          % (w_ag.sum(), w_crop.sum()))

    rows = []
    for start, p in files:
        ndvi = load_ndvi(p)
        mean_ag, wsum_ag = weighted_by_district(ndvi, w_ag, didx, n_dist)
        mean_cr, wsum_cr = weighted_by_district(ndvi, w_crop, didx, n_dist)
        sub = lookup.copy()
        sub["composite_start"] = start
        sub["ndvi_ag"] = mean_ag[sub["_idx"].values]
        sub["ndvi_crop"] = mean_cr[sub["_idx"].values]
        sub["w_ag"] = wsum_ag[sub["_idx"].values]
        sub["w_crop"] = wsum_cr[sub["_idx"].values]
        rows.append(sub)
        print("  %s  districts with data: %d / %d   mean ndvi_ag %.4f"
              % (start, int(np.isfinite(sub.ndvi_ag).sum()), len(sub),
                 np.nanmean(sub.ndvi_ag)), flush=True)

    comp = pd.concat(rows, ignore_index=True).drop(columns=["_idx"])
    comp.to_csv(OUT_COMPOSITE, index=False)
    print("wrote", OUT_COMPOSITE, comp.shape)
    return comp


def to_monthly(comp):
    """Day-weighted aggregation of 16-day composites to calendar months."""
    parts = []
    for start, grp in comp.groupby("composite_start"):
        for (yr, mo), days in month_overlap_weights(start).items():
            g = grp.copy()
            g["year"], g["month"], g["days"] = yr, mo, days
            parts.append(g)
    long = pd.concat(parts, ignore_index=True)
    long = long[long.month.isin(KEEP_MONTHS)].copy()

    for col in ("ndvi_ag", "ndvi_crop"):
        long[col + "_wd"] = long[col] * long["days"]
    long["days_ok"] = np.where(long.ndvi_ag.notna(), long.days, 0)

    keys = ["district_id", "year", "month"]
    agg = long.groupby(keys).agg(
        ndvi_ag_wd=("ndvi_ag_wd", "sum"),
        ndvi_crop_wd=("ndvi_crop_wd", "sum"),
        days=("days_ok", "sum"),
        n_composites=("composite_start", "nunique"),
    ).reset_index()
    agg["ndvi_ag"] = agg.ndvi_ag_wd / agg.days
    agg["ndvi_crop"] = agg.ndvi_crop_wd / agg.days
    agg["quarter"] = np.where(agg.month.isin([4, 5, 6]), 2, 3)
    agg = agg.drop(columns=["ndvi_ag_wd", "ndvi_crop_wd"])
    agg = agg[["district_id", "year", "quarter", "month", "ndvi_ag",
               "ndvi_crop", "days", "n_composites"]]
    return agg.sort_values(["district_id", "year", "month"]).reset_index(drop=True)


if __name__ == "__main__":
    comp = main()
    monthly = to_monthly(comp)
    monthly.to_csv(OUT_MONTHLY, index=False)
    print("\nwrote", OUT_MONTHLY, monthly.shape)
    print(monthly.head(12).to_string(index=False))
    print("\ncoverage by year-month:")
    print(monthly.groupby(["year", "month"])
          .agg(districts=("district_id", "nunique"),
               mean_ndvi_ag=("ndvi_ag", "mean"),
               mean_ndvi_crop=("ndvi_crop", "mean"),
               days=("days", "max")).to_string())
