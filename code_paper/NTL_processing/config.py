"""
Single place where every path in the analysis is defined.

The code lives wherever this file is (code_paper/NTL_processing), but the data
and outputs live in a separate location. BASE is the data/output root and
defaults to the shared OneDrive MarketActivityIndex folder. Override it by
setting the MAI_BASE environment variable.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_POINTER = os.path.join(_HERE, "mai_base.txt")


def _resolve_base():
    env = os.environ.get("MAI_BASE")
    if env:
        return os.path.abspath(os.path.expanduser(env.strip())), "MAI_BASE"
    if os.path.exists(_POINTER):
        with open(_POINTER, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    return os.path.abspath(os.path.expanduser(line)), "mai_base.txt"
    return os.path.abspath(os.path.join(_HERE, "..", "..")), "location of config.py"


BASE, _BASE_SOURCE = _resolve_base()

DATA = os.path.join(BASE, "data")
PROCESSED = os.path.join(BASE, "processed_data")
OUTPUT = os.path.join(BASE, "output_paper")

# Every figure and table in the paper is written here, named by its exhibit number
# (fig05a_..., table1_...). See EXHIBITS.md at the repository root for which script
# or notebook cell makes each one.
PAPER_EXHIBITS = os.path.join(OUTPUT, "paper_exhibits")

if not os.path.isdir(DATA):
    raise RuntimeError(
        "Could not find the MAI data tree.\n"
        "  BASE resolved to : %s\n"
        "  (from            : %s)\n"
        "  Expected a 'data' folder inside it.\n\n"
        "Point the code at the MarketActivityIndex folder by either\n"
        "  setting the MAI_BASE environment variable, or\n"
        "  writing that path on one line in %s" % (BASE, _BASE_SOURCE, _POINTER)
    )

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

for _d in (PROCESSED, OUTPUT, PAPER_EXHIBITS, WORK_DIR):
    os.makedirs(_d, exist_ok=True)

    
