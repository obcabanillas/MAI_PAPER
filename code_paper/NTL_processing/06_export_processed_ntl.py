"""
Assemble the outputs of scripts 03-05 into the analysis-ready NTL files that
Results_paper.ipynb consumes, and write them to processed_data/.

Writes three files:

  ntl_bnr_866markets_4years.csv    866 markets (137 periodic + 729 OSM),
                                   monthly SUM/MEAN/NPIX of BNR-filtered
                                   radiance in the 10 km buffer, for 2018,
                                   2020, 2023 and 2025. Feeds the CDF figures.

  ntl_bnr_periodic137_8years.csv   The 137 periodic markets, same columns, for
                                   every year 2018-2025. Feeds Model B of the
                                   event study.

  market_groups.csv                One row per market: id, source, lat/lon,
                                   distance to the nearest detected periodic
                                   market, and the three-way group used in the
                                   figures (Periodic / OSM only / OSM overlap).

No figures and no regression results are written here - those go to
output_paper/.
"""

# --- paths come from config.py (edit that one file, or set MAI_BASE) ---------
import os as _os_cfg
import sys as _sys_cfg
_sys_cfg.path.insert(0, _os_cfg.path.dirname(_os_cfg.path.abspath(__file__)))
from config import DATA, PROCESSED, WORK_DIR
# ---------------------------------------------------------------------------
import os

import pandas as pd

OVERLAP_KM = 1.0

BNR_866 = os.path.join(DATA, "markets_VIIRS_10km_buffer_137_729_2018_2020_2023_2025_BNR.csv")
PLAIN_866 = os.path.join(DATA, "markets_VIIRS_10km_buffer_137_729_2018_2020_2023_2025.csv")
BNR_EXTRA = os.path.join(WORK_DIR, "periodic137_BNR_2019_2021_2022_2024.csv")

print("Reading BNR buffer stats...")
bnr = pd.read_csv(BNR_866, low_memory=False)
plain = pd.read_csv(PLAIN_866, low_memory=False)
extra = pd.read_csv(BNR_EXTRA, low_memory=False)
assert len(bnr) == 866, f"expected 866 markets in the BNR file, got {len(bnr)}"

# ---------------------------------------------------------------- groups
dist_col = "distance_km_to_nearest_detected_market"
groups = plain[["mkt_uid", "source", "orig_id", "lat", "lon", dist_col]].copy()


def classify(row):
    if row["source"] == "periodic_137":
        return "Periodic"
    return "OSM only" if row[dist_col] > OVERLAP_KM else "OSM overlap"


groups["group"] = groups.apply(classify, axis=1)
print(groups["group"].value_counts().to_string())

# ---------------------------------------------------------------- 866 x 4 years
keep = ["mkt_uid", "source", "orig_id", "lat", "lon"]
bnr_cols = [c for c in bnr.columns if c.startswith(("SUM_BNR_", "MEAN_BNR_", "NPIX_BNR_"))]
out_866 = bnr[keep + sorted(bnr_cols)].copy()

# ---------------------------------------------------------------- periodic x 8 years
per = bnr[bnr.source == "periodic_137"].copy()
extra_cols = [c for c in extra.columns if c.startswith(("SUM_BNR_", "MEAN_BNR_", "NPIX_BNR_"))]
out_137 = per[keep + sorted(bnr_cols)].merge(
    extra[["orig_id"] + sorted(extra_cols)], on="orig_id", how="inner")
assert len(out_137) == 137 and out_137.orig_id.is_unique
mean_cols = [c for c in out_137.columns if c.startswith("MEAN_BNR_")]
assert len(mean_cols) == 96, f"expected 96 monthly MEAN_BNR columns (8 years), got {len(mean_cols)}"
out_137 = out_137[keep + sorted(c for c in out_137.columns if c not in keep)]

# ---------------------------------------------------------------- write
os.makedirs(PROCESSED, exist_ok=True)
for df, name in [(out_866, "ntl_bnr_866markets_4years.csv"),
                 (out_137, "ntl_bnr_periodic137_8years.csv"),
                 (groups, "market_groups.csv")]:
    p = os.path.join(PROCESSED, name)
    df.to_csv(p, index=False)
    print(f"wrote {name:36s} {df.shape}")
print("DONE")
