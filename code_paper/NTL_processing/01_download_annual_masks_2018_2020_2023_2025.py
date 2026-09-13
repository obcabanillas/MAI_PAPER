"""
Download the VIIRS annual masked-composite raster for Afghanistan for
2018, 2020, 2023, 2025 -- used to replicate the masking behind the old
markets_VIIRS_stats_10km_buffer_bnr.csv file.

Source: NOAA/VIIRS/DNB/ANNUAL_V21 (2013-2021), NOAA/VIIRS/DNB/ANNUAL_V22
(2022-2025). Band: average_masked.

Downloaded on the native monthly-VIIRS grid (not the annual image's own
.projection(), which is a degenerate 1-degree placeholder for this asset)
so it lines up pixel-for-pixel with the existing monthly avg_rad rasters.
"""

# --- paths come from config.py (edit that one file, or set MAI_BASE) ---------
import os as _os_cfg
import sys as _sys_cfg
_sys_cfg.path.insert(0, _os_cfg.path.dirname(_os_cfg.path.abspath(__file__)))
from config import BASE, DATA, VIIRS_DIR, MASK_DIR, WORK_DIR
OUT_DIR = MASK_DIR
# ---------------------------------------------------------------------------
import os
import time

import ee
import requests

from config import EE_PROJECT
ee.Initialize(project=EE_PROJECT,
              opt_url='https://earthengine-highvolume.googleapis.com')

os.makedirs(OUT_DIR, exist_ok=True)

YEARS = [2018, 2020, 2023, 2025]
BAND = "average_masked"

def collection_for_year(y):
    if y <= 2021:
        return f"NOAA/VIIRS/DNB/ANNUAL_V21/{y}0101"
    return f"NOAA/VIIRS/DNB/ANNUAL_V22/{y}0101"


def get_aoi():
    fc = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017").filter(
        ee.Filter.eq("country_na", "Afghanistan")
    )
    geom = fc.geometry().dissolve(maxError=100)
    bbox = geom.bounds(maxError=100)
    return geom, bbox


def native_monthly_grid():
    proj = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG").first() \
        .select("avg_rad").projection().getInfo()
    return proj["crs"], proj["transform"]


def download(image, region, crs, transform, path):
    params = {"region": region, "crs": crs, "crsTransform": transform,
              "format": "GEO_TIFF"}
    for attempt in range(1, 5):
        try:
            url = image.getDownloadURL(params)
            resp = requests.get(url, timeout=600)
            resp.raise_for_status()
            tmp = path + ".part"
            with open(tmp, "wb") as fh:
                fh.write(resp.content)
            os.replace(tmp, path)
            return len(resp.content)
        except Exception as exc:
            if attempt == 4:
                raise
            print(f"  attempt {attempt} failed ({exc}); retrying")
            time.sleep(10 * attempt)


def main():
    geom, bbox = get_aoi()
    region = bbox.getInfo()["coordinates"]
    crs, transform = native_monthly_grid()
    print(f"Native grid: {crs} {transform}")

    for y in YEARS:
        img = ee.Image(collection_for_year(y)).select(BAND).clip(geom)
        path = os.path.join(OUT_DIR, f"afg_viirs_annual_masked_{y}.tif")
        nbytes = download(img, region, crs, transform, path)
        print(f"{y}  {BAND}  {nbytes/1e6:.2f} MB  -> {path}")

    print("DONE")


if __name__ == "__main__":
    main()
