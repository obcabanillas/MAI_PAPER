"""
Build the 10 m -> 250 m agricultural-fraction grid.

For every MODIS NDVI pixel, compute what share of its area is cropland
(ESA WorldCover class 40), grassland (class 30), and mapped land at all
(any non-zero class, i.e. inside Afghanistan). Those shares become the
weights for the district NDVI means, so partially cropped pixels count in
proportion rather than being forced in or out by a threshold.

Computed once; reused for every NDVI date.
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
import time

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds, transform as win_transform
from rasterio.warp import reproject, Resampling


RAW = os.path.join(BASE, "data", "Geospatial_RAW")
LC = os.path.join(RAW, "ESA_Landcover_2022_10m", "AFG_ESA_LandCover_2022.tif")
ND_REF = os.path.join(RAW, "MODIS_NDVI", "NDVI_AFG_Box_2012_07_11(1).tif")
OUT = os.path.join(BASE, "processed_data", "ndvi_ag_fraction_250m.tif")

CROPLAND = (40,)
GRASSLAND = (30,)

DST_BLOCK_COLS, DST_BLOCK_ROWS = 512, 256


def main():
    t0 = time.time()
    with rasterio.open(ND_REF) as nd, rasterio.open(LC) as lc:
        prof = nd.profile.copy()
        prof.update(count=3, dtype="float32", compress="deflate", predictor=2,
                    tiled=True, blockxsize=256, blockysize=256, nodata=None)
        H, W = nd.height, nd.width
        print("target grid: %d x %d   source: %d x %d" % (H, W, lc.height, lc.width))

        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with rasterio.open(OUT, "w", **prof) as dst:
            dst.set_band_description(1, "crop_frac")
            dst.set_band_description(2, "grass_frac")
            dst.set_band_description(3, "valid_frac")

            n_blocks = ((W + DST_BLOCK_COLS - 1) // DST_BLOCK_COLS) * \
                       ((H + DST_BLOCK_ROWS - 1) // DST_BLOCK_ROWS)
            done = 0
            for row_off in range(0, H, DST_BLOCK_ROWS):
                for col_off in range(0, W, DST_BLOCK_COLS):
                    h = min(DST_BLOCK_ROWS, H - row_off)
                    w = min(DST_BLOCK_COLS, W - col_off)
                    dst_win = Window(col_off, row_off, w, h)
                    dst_tr = win_transform(dst_win, nd.transform)
                    left, bottom, right, top = rasterio.windows.bounds(dst_win, nd.transform)

                    src_win = from_bounds(left, bottom, right, top, lc.transform)
                    src_win = Window(int(np.floor(src_win.col_off)) - 2,
                                     int(np.floor(src_win.row_off)) - 2,
                                     int(np.ceil(src_win.width)) + 4,
                                     int(np.ceil(src_win.height)) + 4)
                    src_win = src_win.intersection(Window(0, 0, lc.width, lc.height))

                    out = np.zeros((3, h, w), dtype="float32")
                    if src_win.width > 0 and src_win.height > 0:
                        src_tr = win_transform(src_win, lc.transform)
                        a = lc.read(1, window=src_win)
                        layers = [np.isin(a, CROPLAND), np.isin(a, GRASSLAND), a > 0]
                        for i, m in enumerate(layers):
                            reproject(
                                source=m.astype("float32"),
                                destination=out[i],
                                src_transform=src_tr, src_crs=lc.crs,
                                dst_transform=dst_tr, dst_crs=nd.crs,
                                resampling=Resampling.average,
                            )
                    dst.write(out, window=dst_win,
                              indexes=[1, 2, 3])
                    done += 1
                    if done % 25 == 0 or done == n_blocks:
                        el = time.time() - t0
                        print("  block %4d/%4d  %5.1f%%  %6.1fs elapsed" %
                              (done, n_blocks, 100.0 * done / n_blocks, el), flush=True)

    print("wrote", OUT)
    with rasterio.open(OUT) as d:
        c, g, v = d.read()
        land = v > 0.5
        print("\nAfghan land pixels at 250 m: %d" % land.sum())
        print("  mean cropland share  : %.4f" % c[land].mean())
        print("  mean grassland share : %.4f" % g[land].mean())
        print("  mean ag share (40+30): %.4f" % (c[land] + g[land]).mean())
        for name, arr in (("cropland", c), ("grassland", g)):
            for thr in (0.01, 0.10, 0.50):
                print("  %s: %6.2f%% of land pixels have share > %.2f"
                      % (name, 100.0 * (arr[land] > thr).mean(), thr))
    print("total %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
