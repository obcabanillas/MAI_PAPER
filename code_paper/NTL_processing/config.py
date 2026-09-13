"""
Single place where every path in the NTL processing chain is defined.

BASE is resolved two levels up from this file (code_paper/NTL_processing ->
MarketActivityIndex), so the package works wherever the MarketActivityIndex
folder is placed, as long as the internal layout is preserved. Override it by
setting the MAI_BASE environment variable.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

BASE = os.environ.get("MAI_BASE") or os.path.abspath(os.path.join(_HERE, "..", ".."))

DATA = os.path.join(BASE, "data")
PROCESSED = os.path.join(BASE, "processed_data")
OUTPUT = os.path.join(BASE, "output_paper")

# Monthly VIIRS avg_rad rasters (afg_viirs_YYYYMM.tif), cropped to Afghanistan.
# EXTERNAL INPUT - not produced by any script in this folder. See README.
VIIRS_DIR = os.path.join(DATA, "Geospatial Analysis Outputs", "AFG_NTL_CROPPED", "viirs")

# Annual average_masked composites used as the per-year BNR reference mask.
# Produced by 01_ and 02_download_annual_masks_*.py.
MASK_DIR = os.path.join(DATA, "_ntl_buffer_work", "annual_masked_bnr")

# Scratch / intermediate outputs of the buffer and BNR scripts.
WORK_DIR = os.path.join(DATA, "_ntl_buffer_work")

# Market location inputs.
PERIODIC_137 = os.path.join(DATA, "MAI_periodic_markets_137.csv")
OSM_729 = os.path.join(DATA, "osm_markets_nearest_detected_distance.csv")

# Non-NTL inputs to the event study (market activity, ACLED, NDVI, population,
# district boundaries) live in the existing replication package.
REPO = os.path.join(BASE, "document", "Repo_09042026")
REPO_DATA = os.path.join(REPO, "data")

# Google Earth Engine project used by the two download scripts. Replace with
# your own registered EE project, or set the EE_PROJECT environment variable.
EE_PROJECT = os.environ.get("EE_PROJECT", "ee-my-obcabanillas")

# Kabul city center, used for the CDF reference line (see Results_paper.ipynb).
KABUL_LON, KABUL_LAT = 69.1783, 34.5253

BUFFER_KM = 10.0
MAX_RAD_CAP = 300.0

for _d in (PROCESSED, OUTPUT, WORK_DIR):
    os.makedirs(_d, exist_ok=True)
