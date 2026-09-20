"""
Extract the MODIS NDVI exports into the folder the pipeline reads.

Only April-September composites are extracted (Q2 and Q3, the quarters the
measure covers) - that roughly halves ~17.8 GB of GeoTIFF. The zips are left
in place, so other months can be pulled out later without re-downloading.

Files already present are skipped, so the script is safe to re-run.
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
import time
import shutil
import zipfile

D = os.path.join(DATA, "Geospatial_RAW", "MODIS_NDVI")
KEEP_MONTHS = {4, 5, 6, 7, 8, 9}
DATE_RE = re.compile(r"(\d{4})_(\d{2})_(\d{2})")

t0 = time.time()
zips = sorted(glob.glob(os.path.join(D, "*.zip")))
print("zips: %d" % len(zips))
print("free before: %.1f GB" % (shutil.disk_usage("C:\\")[2] / 1e9))

n_extracted = n_skipped = n_other_month = 0
bytes_out = 0

for zi, zpath in enumerate(zips, 1):
    print("\n[%d/%d] %s" % (zi, len(zips), os.path.basename(zpath)), flush=True)
    try:
        zf = zipfile.ZipFile(zpath)
    except Exception as e:
        print("   CANNOT OPEN: %s" % e, flush=True)
        continue
    with zf:
        entries = [i for i in zf.infolist() if not i.is_dir()]
        print("   %d entries" % len(entries), flush=True)
        for info in entries:
            base = os.path.basename(info.filename)
            if not base.lower().endswith(".tif"):
                continue
            m = DATE_RE.search(base)
            if not m or int(m.group(2)) not in KEEP_MONTHS:
                n_other_month += 1
                continue
            dst = os.path.join(D, base)
            if os.path.exists(dst) and os.path.getsize(dst) == info.file_size:
                n_skipped += 1
                continue
            tmp = dst + ".part"
            with zf.open(info) as src, open(tmp, "wb") as out:
                shutil.copyfileobj(src, out, length=8 * 1024 * 1024)
            os.replace(tmp, dst)
            n_extracted += 1
            bytes_out += info.file_size
            print("   + %-34s %5.1f MB   (%d extracted, %.1f GB, %.0f s)"
                  % (base, info.file_size / 1e6, n_extracted,
                     bytes_out / 1e9, time.time() - t0), flush=True)

print("\nextracted %d, skipped %d already present, %d outside Apr-Sep"
      % (n_extracted, n_skipped, n_other_month))
print("wrote %.2f GB in %.0f s" % (bytes_out / 1e9, time.time() - t0))
print("free after: %.1f GB" % (shutil.disk_usage("C:\\")[2] / 1e9))
tifs = glob.glob(os.path.join(D, "*.tif"))
print("tif files now in folder: %d" % len(tifs))
