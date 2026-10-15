"""
Build the two derived inputs every exhibit reads, from raw data:

    derived/periodict_act.csv   market-day activity panel (one row per market and date)
    derived/mkt_access.csv      travel time to a 50,000+ settlement and the access category
    ndvi/NDVI_markted.csv       quarterly NDVI in each market catchment (the NDVI table)

Ported from MAI_AFG/Code/Master.ipynb (cells 12, 14, 19, 43, 44, 45, 22, 24, 26 and 36), which
wrote these files to a Desktop and a Downloads folder. The logic is unchanged; only the paths
and the order of the steps are made explicit. Outputs go to processed_data/derived/, and the
script then compares them with the copies the exhibits read (document/Repo_09042026/data/derived).

    python build_derived.py           # build and compare
"""
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "NTL_processing"))
from config import DATA, PROCESSED, REPO_DATA  # noqa: E402

TARGET = "activity_area_norm2020"     # tgtvar in Master.ipynb (tgtyear = 2020)
NORM = ["activity_area_norm2018", "activity_area_norm2019", "activity_area_norm2020",
        "activity_area_norm2021", "activity_area_norm2022", "activity_area_norm2023"]
GAO = os.path.join(DATA, "Geospatial Analysis Outputs")
OUT = os.path.join(PROCESSED, "derived")
os.makedirs(OUT, exist_ok=True)


def accessibility():
    """Population within a 30-minute mixed-mode journey (wp_SUM), Master.ipynb cell 12."""
    a = pd.read_excel(os.path.join(GAO, "afg_markets_points_accessibility_wp_and_GHSL.xlsx"))
    a = a[(a.TravelType == "mixed") & (a.Threshold == 30)][["mktID", "TravelType", "Threshold", "wp_SUM"]]
    b = pd.read_excel(os.path.join(GAO, "afg_missing_markets_points_accessibility_wp_and_GHSL.xlsx"),
                      sheet_name="ZonalSt_missing_markets_wp")
    b = b[(b.TravelType == "mixed") & (b.Threshold == 30)][["mktID", "TravelType", "Threshold", "SUM"]]
    return pd.concat([a, b.rename(columns={"SUM": "wp_SUM"})], axis=0)


def proximity():
    """Road travel time and distance to the nearest 5k/10k/20k/50k settlement, cell 14."""
    out = None
    for k in (5, 10, 20, 50):
        d = pd.read_excel(os.path.join(GAO, "ProximityToSettlements",
                                       f"afg_markets_distance_to_closest_{k}k_pop_settlement.xls"))
        d.columns = d.columns.str.replace(" ", "")
        d = d.rename(columns={f"roads_to_{k}k_PathCost": f"travel_{k}",
                              f"roads_to_{k}k_Shape_Length_km": f"distance_{k}"})[["mktID", f"travel_{k}", f"distance_{k}"]]
        out = d if out is None else out.merge(d, on="mktID", how="left")
    return out


def opening(acc):
    """Years each market is open and days open per year, with the 119-day noise rule, cell 19."""
    o = pd.read_csv(os.path.join(DATA, "afg_permanent_markets_012626", "market_activity_periods_new_winsorized_2020.csv"))
    act = pd.read_csv(os.path.join(DATA, "afg_periodic_markets_20260213", "forAFG_paper_activity_all.csv"),
                      usecols=["un_region", "Location"])
    act["un_region_small"] = np.where(act.un_region == "NorthEast", "East", act.un_region)
    o = o[o.Location.isin(act.Location)].merge(act.drop_duplicates("Location"), on="Location", how="inner")
    o = o.rename(columns={"Location": "mktID"}).merge(acc, on="mktID", how="left")
    o["start_date"], o["end_date"] = pd.to_datetime(o.start_date), pd.to_datetime(o.end_date)
    for y in range(2017, 2026):
        y0, y1 = pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31")
        o[f"open_{y}"] = ((o.start_date <= y1) & (o.end_date >= y0)).astype(int)
        o[f"open_{y}"] = o.groupby("mktID")[f"open_{y}"].transform("max")
        start = pd.to_datetime(np.where(o.start_date <= y0, y0, o.start_date))
        span = np.where(o.end_date >= y1, y1 - start, o.end_date - start)
        span = pd.to_timedelta(span)
        span = span.where(span > pd.Timedelta(0), pd.Timedelta(0))
        o[f"days_open_{y}"] = pd.Series(span, index=o.index).groupby(o.mktID).transform("sum")
    close = pd.Timedelta("119 days")
    for y in range(2017, 2026):
        o[f"days_open_{y}"] = o[f"days_open_{y}"].where(o[f"days_open_{y}"] > close, pd.Timedelta(0))
        o[f"open_{y}"] = np.where(o[f"days_open_{y}"] <= close, 0, o[f"open_{y}"])
    o["always_open"] = o[[f"open_{y}" for y in range(2018, 2026)]].sum(axis=1)
    return o


def market_days():
    """Registry trading days, from the market shapefile (df_map in Master.ipynb)."""
    import geopandas as gpd
    m = gpd.read_file(os.path.join(DATA, "afg_periodic_markets_20250827", "afg_periodic_markets_20250827.shp"))
    return pd.DataFrame(m[["mktID", "marketDays"]])


def fiscal_year(year, quarter):
    fy = np.where(quarter == 1, year - 1, year)
    return np.array([f"FY_{y}/{str(y + 1)[2:]}" for y in fy])


def build_panel(o, days):
    """Market-day panel, Master.ipynb cells 43-45."""
    p = pd.read_csv(os.path.join(DATA, "afg_periodic_markets_20260213", "forAFG_paper_activity_all.csv"))
    p = p[p.mktDay == 1].rename(columns={"Location": "mktID"})
    p = p[~p.mktID.isin(["0"])]
    # readings outside [-5, 300] or missing are dropped
    p["DataWithIssue"] = np.where(~p[TARGET].between(-5, 300), 1, 0)
    p["DataWithIssue"] = np.where(p[TARGET].isnull(), np.nan, p.DataWithIssue)
    p["count"] = np.where(p[TARGET].isnull(), 0, 1)
    p["DataWithIssue_share"] = p.groupby("mktID").DataWithIssue.transform("sum") / p.groupby("mktID")["count"].transform("sum")
    p = p[p.DataWithIssue == 0].copy()
    oc = ["days_open_2018"] + [f"open_{y}" for y in range(2018, 2026)] + ["un_region_small", "wp_SUM"]
    p = p.merge(o.drop_duplicates("mktID")[["mktID"] + oc], on="mktID", how="inner")
    # markets with no registry trading day are left out (the 137th market, lon62_5018lat34_2416)
    p = p[~p.mktID.isin(days[days.marketDays == "None"].mktID)]
    for v in NORM:
        p[v] = p.groupby(["date", "mktID"])[v].transform("mean")
    p = p.drop_duplicates(subset=["date", "mktID"])
    p["year"] = p.date.str.slice(0, 4).astype(int)
    p["month"] = p.date.str.slice(5, 7).astype(int)
    p["day"] = p.date.str.slice(8, 10).astype(int)
    p["week"] = pd.to_datetime(p.date).dt.isocalendar().week.astype(int)
    st = pd.to_datetime(p.image_id.str.slice(9, 15), format="%H%M%S") + pd.Timedelta(hours=4, minutes=30)
    p["sat_time"] = st.dt.time
    p["sat_hour"] = st.dt.hour
    p["quarter"] = (p.month - 1) // 3 + 1
    p["FY"] = fiscal_year(p.year.values, p.quarter.values)
    p = p.merge(days, on="mktID", how="left")
    p["log_wp_SUM"] = np.log(p.wp_SUM)
    p["wp_SUM_thousand"] = p.wp_SUM / 1000
    in_window = p.date.between("2018-01-01", "2026-12-31")
    p["CV"] = (p[in_window].groupby("mktID").activity_area_norm2018.transform("std")
               / p.groupby("mktID").activity_area_norm2018.transform("mean"))
    return p


def build_access(o, prox):
    """Access categories, Master.ipynb cells 22, 24, 26 and 36."""
    f = o.drop_duplicates("mktID")[["mktID", "wp_SUM"]].merge(prox, on="mktID", how="left")
    f["density"] = np.where((f.travel_50 < 40) & (f.wp_SUM > 250000), "high density", "")
    f["density"] = np.where((f.travel_50 < 40) & (f.wp_SUM <= 250000), "mid density", f.density)
    f["density"] = np.where(f.travel_50 >= 40, "low density", f.density)
    return f[["mktID", "travel_50", "density"]].drop_duplicates("mktID")


def market_ndvi():
    """Quarterly NDVI in each market catchment, with the previous quarter and the market-quarter
    long-run mean and standard deviation (Master.ipynb cell 1, kept there as commented-out code)."""
    n = pd.concat([pd.read_csv(os.path.join(GAO, "OldData", "markets_ndvi_monthly_zonalstats_masked_per_market.csv")),
                   pd.read_csv(os.path.join(GAO, "missing_markets_ndvi_monthly_zonalstats_masked_per_market.csv"))],
                  ignore_index=True)
    n["month"] = pd.to_datetime(n.month)
    n["quarter"] = (n.month.dt.month - 1) // 3 + 1
    n["year"] = n.month.dt.year
    q = n.groupby(["mktID", "year", "quarter"]).ndvi_mean.mean().reset_index().sort_values(["mktID", "year", "quarter"])
    q["ndvi_mean_lag"] = q.groupby("mktID").ndvi_mean.shift(1)
    q["ndvi_mean_long_term"] = q.groupby(["mktID", "quarter"]).ndvi_mean.transform("mean")
    q["ndvi_std_long_term"] = q.groupby(["mktID", "quarter"]).ndvi_mean.transform("std")
    return q


def compare(new, old, keys, cols, label):
    """Cell-by-cell comparison of a rebuilt file with the published copy."""
    m = old.merge(new, on=keys, how="outer", suffixes=("_pub", "_new"), indicator="_src")
    print(f"\n{label}: published {len(old):,} rows, rebuilt {len(new):,} rows; "
          f"only published {int((m._src == 'left_only').sum())}, only rebuilt {int((m._src == 'right_only').sum())}")
    both = m[m._src == "both"]
    for c in cols:
        a, b = both[f"{c}_pub"], both[f"{c}_new"]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            diff = ~(np.isclose(a, b, rtol=1e-9, atol=1e-9, equal_nan=True))
        else:
            diff = a.astype(str) != b.astype(str)
        print(f"   {c:<24} {'identical' if not diff.any() else f'{int(diff.sum()):,} cells differ'}")


if __name__ == "__main__":
    acc, prox = accessibility(), proximity()
    o = opening(acc)
    days = market_days()
    panel = build_panel(o, days)
    access = build_access(o, prox)
    panel.to_csv(os.path.join(OUT, "periodict_act.csv"), index=False)
    access.to_csv(os.path.join(OUT, "mkt_access.csv"), index=False)
    print("written", os.path.join(OUT, "periodict_act.csv"), "and mkt_access.csv")

    pub_panel = pd.read_csv(os.path.join(REPO_DATA, "derived", "periodict_act.csv"), low_memory=False)
    pub_access = pd.read_csv(os.path.join(REPO_DATA, "derived", "mkt_access.csv"))
    pub_panel["date"] = pd.to_datetime(pub_panel.date).dt.strftime("%Y-%m-%d")
    panel["date"] = pd.to_datetime(panel.date).dt.strftime("%Y-%m-%d")
    compare(panel, pub_panel, ["mktID", "date"],
            ["image_id", "mktDay", "weekday", TARGET, "activity_area_norm2018", "activity_area_norm2022",
             "year", "month", "week", "quarter", "marketDays", "wp_SUM", "un_region", "un_region_small",
             "admLvl1", "open_2020", "open_2025", "FY", "sat_hour"], "derived/periodict_act.csv")
    compare(access, pub_access, ["mktID"], ["travel_50", "density"], "derived/mkt_access.csv")

    nd = market_ndvi()
    nd.to_csv(os.path.join(OUT, "NDVI_markted.csv"), index=False)
    pub_nd = pd.read_csv(os.path.join(REPO_DATA, "ndvi", "NDVI_markted.csv"))
    compare(nd, pub_nd, ["mktID", "year", "quarter"],
            ["ndvi_mean", "ndvi_mean_lag", "ndvi_mean_long_term", "ndvi_std_long_term"], "ndvi/NDVI_markted.csv")
