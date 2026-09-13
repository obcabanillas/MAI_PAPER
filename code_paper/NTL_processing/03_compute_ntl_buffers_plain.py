"""
Compute VIIRS NTL (avg_rad) sum/mean in 10km geodesic buffers around:
  - 137 detected periodic markets (data/MAI_periodic_markets_137.csv)
  - 729 OSM markets (data/osm_markets_nearest_detected_distance.csv)
for each of 148 monthly rasters (2014-01 .. 2026-04).

Buffers are true geodesic circles (pyproj Geod), built directly in EPSG:4326
to match the raster CRS exactly -- no projection/reprojection distortion.
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

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Geod
from rasterstats import zonal_stats
from shapely.geometry import Polygon

os.makedirs(OUT_DIR, exist_ok=True)

BUFFER_KM = 10.0
N_VERTS = 72
GEOD = Geod(ellps="WGS84")


def geodesic_circle(lon, lat, radius_km, n_points=N_VERTS):
    dist_m = radius_km * 1000.0
    angles = np.linspace(0, 360, n_points, endpoint=False)
    lons, lats, _ = GEOD.fwd(
        np.full(n_points, lon), np.full(n_points, lat), angles, np.full(n_points, dist_m)
    )
    return Polygon(zip(lons, lats))


def haversine_matrix_km(lat_deg, lon_deg):
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    R = 6371.0088
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    )
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def circle_overlap_frac(d_km, r_km=BUFFER_KM):
    if d_km >= 2 * r_km:
        return 0.0
    if d_km <= 0:
        return 1.0
    part = 2 * r_km**2 * np.arccos(d_km / (2 * r_km)) - (d_km / 2) * np.sqrt(
        4 * r_km**2 - d_km**2
    )
    return part / (np.pi * r_km**2)


# ---------------------------------------------------------------- load markets
periodic = pd.read_csv(os.path.join(DATA, "MAI_periodic_markets_137.csv"))
periodic = periodic.rename(
    columns={"mktID": "orig_id", "latitude": "lat", "longitude": "lon"}
)
periodic["source"] = "periodic_137"
periodic["mkt_uid"] = "P_" + periodic["orig_id"].astype(str)
keep_p = [
    "mkt_uid", "source", "orig_id", "lat", "lon",
    "province", "district", "trading_days",
]
periodic = periodic[keep_p]

osm = pd.read_csv(os.path.join(DATA, "osm_markets_nearest_detected_distance.csv"))
osm = osm.rename(columns={"osm_id": "orig_id", "osm_lat": "lat", "osm_lon": "lon"})
osm["source"] = "osm_729"
osm["mkt_uid"] = "O_" + osm["orig_id"].astype(str)
keep_o = [
    "mkt_uid", "source", "orig_id", "lat", "lon",
    "name", "fclass", "distance_km_to_nearest_detected_market",
]
osm = osm[keep_o]

markets = pd.concat([periodic, osm], ignore_index=True, sort=False)
assert markets["mkt_uid"].is_unique, "duplicate mkt_uid"
assert len(markets) == 137 + 729, f"expected 866 markets, got {len(markets)}"
print(f"Loaded {len(periodic)} periodic + {len(osm)} OSM = {len(markets)} markets")


# ---------------------------------------------------------------- buffers
print("Building 10km geodesic buffers...")
markets["geometry"] = [
    geodesic_circle(lon, lat, BUFFER_KM)
    for lon, lat in zip(markets["lon"], markets["lat"])
]
gdf = gpd.GeoDataFrame(markets, geometry="geometry", crs="EPSG:4326")
gdf.to_file(os.path.join(OUT_DIR, "market_buffers_10km.geojson"), driver="GeoJSON")

# ---------------------------------------------------------------- overlap flag
print("Computing nearest-neighbor distances and overlap flags...")
dmat = haversine_matrix_km(gdf["lat"].to_numpy(), gdf["lon"].to_numpy())
np.fill_diagonal(dmat, np.inf)
nn_idx = dmat.argmin(axis=1)
nn_dist = dmat.min(axis=1)
gdf["nearest_neighbor_km"] = nn_dist
gdf["nearest_neighbor_uid"] = gdf["mkt_uid"].to_numpy()[nn_idx]
gdf["nearest_neighbor_source"] = gdf["source"].to_numpy()[nn_idx]
gdf["buffers_overlap"] = gdf["nearest_neighbor_km"] < (2 * BUFFER_KM)
gdf["overlap_frac_vs_nearest"] = [
    circle_overlap_frac(d) for d in gdf["nearest_neighbor_km"]
]
print(
    f"{gdf['buffers_overlap'].sum()} of {len(gdf)} markets have an overlapping "
    f"10km buffer with their nearest neighbor"
)


# ---------------------------------------------------------------- zonal stats
YEARS = {"2018", "2020", "2023", "2025"}
tif_files = sorted(glob.glob(os.path.join(VIIRS_DIR, "afg_viirs_*.tif")))
tif_files = [f for f in tif_files if os.path.basename(f)[10:14] in YEARS]
pattern = re.compile(r"afg_viirs_(\d{6})\.tif$")

out = gdf.drop(columns="geometry").copy()
manifest = []
n = len(tif_files)
for i, tif in enumerate(tif_files, 1):
    m = pattern.search(os.path.basename(tif))
    if not m:
        continue
    ym = m.group(1)
    stats = zonal_stats(
        gdf, tif, stats=["sum", "mean", "count"], nodata=np.nan, all_touched=False
    )
    out[f"SUM_{ym}"] = [s["sum"] for s in stats]
    out[f"MEAN_{ym}"] = [s["mean"] for s in stats]
    out[f"NPIX_{ym}"] = [s["count"] for s in stats]
    manifest.append({"month": ym, "file": os.path.basename(tif)})
    if i % 10 == 0 or i == n:
        print(f"[{i}/{n}] processed {ym}")

out_path = os.path.join(DATA, "markets_VIIRS_10km_buffer_137_729_2018_2020_2023_2025.csv")
out.to_csv(out_path, index=False)
pd.DataFrame(manifest).to_csv(
    os.path.join(OUT_DIR, "manifest_months.csv"), index=False
)
print(f"DONE. Wrote {out_path}  shape={out.shape}")
