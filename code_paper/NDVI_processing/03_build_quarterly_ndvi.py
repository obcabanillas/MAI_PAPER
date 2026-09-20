"""
Stage 3. District-quarter NDVI for Q2 and Q3: raw levels and deviations.

Reads the composite-level table from stage 2 and aggregates to quarters,
weighting each 16-day composite by how many of its days fall in the quarter.

Deviations follow the convention already used for the market-level NDVI in
the event study: standardize each district-quarter against that same
district's own long-run mean and standard deviation for that quarter, so the
figure reads as "how unusual was this quarter for this district".

    ndvi_ag_dev = (ndvi_ag - mean_over_years) / sd_over_years

Both the standardized deviation and the plain anomaly (level minus long-run
mean, in NDVI units) are written, along with the number of years behind each
district-quarter baseline so thin baselines are visible rather than implicit.
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
import datetime as dt

import numpy as np
import pandas as pd



IN_COMPOSITE = os.path.join(PROCESSED, "ndvi_district_composite.csv")
OUT_QUARTERLY = os.path.join(PROCESSED, "ndvi_district_quarterly.csv")

QUARTER_MONTHS = {2: (4, 5, 6), 3: (7, 8, 9)}
COMPOSITE_DAYS = 16
MEASURES = ("ndvi_ag", "ndvi_crop")


def quarter_overlap(start, n_days=COMPOSITE_DAYS):
    """Days of a 16-day composite window falling in each (year, quarter)."""
    out = {}
    for k in range(n_days):
        d = start + dt.timedelta(days=k)
        for q, months in QUARTER_MONTHS.items():
            if d.month in months:
                out[(d.year, q)] = out.get((d.year, q), 0) + 1
    return out


def main():
    comp = pd.read_csv(IN_COMPOSITE, parse_dates=["composite_start"])
    comp["composite_start"] = comp["composite_start"].dt.date
    print("composite table:", comp.shape,
          "| dates:", comp.composite_start.nunique(),
          "| districts:", comp.district_id.nunique())

    # expand each composite into the quarters its days fall in
    parts = []
    for start, grp in comp.groupby("composite_start"):
        for (yr, q), days in quarter_overlap(start).items():
            g = grp.copy()
            g["year"], g["quarter"], g["days"] = yr, q, days
            parts.append(g)
    if not parts:
        raise SystemExit("no composite days fall in Q2 or Q3")
    long = pd.concat(parts, ignore_index=True)

    # day-weighted quarter means, counting only days with a usable value
    for c in MEASURES:
        long[c + "_wd"] = long[c] * long["days"]
        long[c + "_days"] = np.where(long[c].notna(), long["days"], 0)

    keys = ["district_id", "year", "quarter"]
    agg = long.groupby(keys).agg(
        **{c + "_wd": (c + "_wd", "sum") for c in MEASURES},
        **{c + "_days": (c + "_days", "sum") for c in MEASURES},
        n_composites=("composite_start", "nunique"),
    ).reset_index()
    for c in MEASURES:
        agg[c] = np.where(agg[c + "_days"] > 0, agg[c + "_wd"] / agg[c + "_days"], np.nan)
    agg = agg.rename(columns={"ndvi_ag_days": "days"}).drop(
        columns=[c + "_wd" for c in MEASURES] + ["ndvi_crop_days"])
    print("quarter table:", agg.shape)
    return agg


def add_deviations(agg):
    """Standardize each district-quarter against its own long-run baseline."""
    g = agg.groupby(["district_id", "quarter"])
    for c in MEASURES:
        mean = g[c].transform("mean")
        sd = g[c].transform(lambda s: s.std(ddof=1))
        n = g[c].transform("count")
        agg[c + "_mean_lr"] = mean
        agg[c + "_sd_lr"] = sd
        agg[c + "_anom"] = agg[c] - mean
        agg[c + "_dev"] = np.where((sd > 0) & (n >= 2), (agg[c] - mean) / sd, np.nan)
        agg[c + "_n_years"] = n
    return agg


if __name__ == "__main__":
    agg = add_deviations(main())
    cols = ["district_id", "year", "quarter", "days", "n_composites"]
    for c in MEASURES:
        cols += [c, c + "_dev", c + "_anom", c + "_mean_lr", c + "_sd_lr", c + "_n_years"]
    agg = agg[cols].sort_values(["district_id", "year", "quarter"]).reset_index(drop=True)
    agg.to_csv(OUT_QUARTERLY, index=False)
    print("\nwrote", OUT_QUARTERLY, agg.shape)

    print("\nyears x quarter coverage:")
    print(agg.groupby(["year", "quarter"]).agg(
        districts=("district_id", "nunique"),
        ndvi_ag=("ndvi_ag", "mean"),
        ndvi_crop=("ndvi_crop", "mean"),
        days=("days", "median")).to_string())

    print("\nbaseline depth (years per district-quarter):")
    print(agg.groupby("quarter").ndvi_ag_n_years.describe()[
        ["min", "25%", "50%", "75%", "max"]].to_string())

    d = agg.ndvi_ag_dev.dropna()
    print("\nndvi_ag_dev: n=%d  mean %.4f  sd %.4f  min %.2f  max %.2f"
          % (len(d), d.mean(), d.std(), d.min(), d.max()))
    print("(mean ~0 and sd ~1 by construction; extremes flag thin baselines)")
    print("\nsample:")
    print(agg.head(10).to_string(index=False))
