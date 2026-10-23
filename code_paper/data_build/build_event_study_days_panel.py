"""
Build a market x trading-day x year activity panel for markets that trade on two days a week.

Used by stata/run_event_study_ACCESS.do (regression 3), which tests whether activity is the
same on both trading days in each year.

Activity is computed exactly as market_year_activity() in build_event_study_panel.ipynb
(same cleaning, then week -> month -> quarter -> year averaging), but separately for each
trading weekday. Each day's value is divided by the market's pooled 2020 level (both days
together, the same base as y_activity), so it is in the same units as y_activity:
100 = the market's average 2020 level.

Controls (NDVI, deaths, access, province, district) are merged from event_study_panel.dta,
so run build_event_study_panel.ipynb first.

Output: processed_data/event_study_days_panel.dta

    python data_build/build_event_study_days_panel.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "NTL_processing"))
from config import PROCESSED  # noqa: E402

TARGET = "activity_area_norm2020"
YEARS = list(range(2018, 2026))
DAY_NAMES = {0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
             4: "Thursday", 5: "Friday", 6: "Saturday"}


def activity(d, keys):
    """market_year_activity() from build_event_study_panel.ipynb, with extra grouping keys."""
    s = d[d["mktDay"] == 1].copy()
    s = s[s[TARGET].between(-5, 300)].copy()
    s[TARGET] = s.groupby(["date", "mktID"])[TARGET].transform("mean")
    s = s.drop_duplicates(subset=["date", "mktID"])
    k = ["mktID"] + keys
    return (s.groupby(k + ["year", "quarter", "month", "week"])[TARGET].mean().reset_index()
             .groupby(k + ["year", "quarter", "month"])[TARGET].mean().reset_index()
             .groupby(k + ["year", "quarter"])[TARGET].mean().reset_index()
             .groupby(k + ["year"])[TARGET].mean().reset_index())


df = pd.read_csv(os.path.join(PROCESSED, "market_images.csv"), low_memory=False)
df = df[df["year"].isin(YEARS)].copy()

# Two-day markets: exactly two distinct weekdays flagged as trading days.
ndays = df[df.mktDay == 1].groupby("mktID")["weekday"].nunique()
two_day = ndays[ndays == 2].index
df = df[df.mktID.isin(two_day)].copy()
print(f"two-day markets: {len(two_day)}")

# Pooled 2020 base per market (both trading days together), same as y_activity.
base = activity(df, []).query("year == 2020").set_index("mktID")[TARGET]

day = activity(df, ["weekday"])
day["y_activity_day"] = 100 * day[TARGET] / day.mktID.map(base)
day = day.drop(columns=TARGET)

# Order the two days within the Afghan week (Saturday first): day_b = the later day.
day["week_pos"] = (day["weekday"].astype(int) + 1) % 7
day["day_b"] = (day.week_pos == day.groupby("mktID").week_pos.transform("max")).astype("int8")
day["day_name"] = day["weekday"].astype(int).map(DAY_NAMES)
day = day.drop(columns="week_pos")

# Controls and identifiers from the market-year panel.
pan = pd.read_stata(os.path.join(PROCESSED, "event_study_panel.dta"))
keep = ["mktID", "year", "y_activity", "log_deaths_pc", "ndvi_ag_anom", "access",
        "Prov_ID", "Pcode_24", "travel_50"]
day = day.merge(pan[keep], on=["mktID", "year"], how="left")

# Check: the average of the two days should track the pooled market-year index.
chk = day.groupby(["mktID", "year"]).agg(m=("y_activity_day", "mean"), y=("y_activity", "first")).dropna()
print(f"corr(mean of two days, y_activity) = {np.corrcoef(chk.m, chk.y)[0, 1]:.3f}; "
      f"median |diff| = {(chk.m - chk.y).abs().median():.2f}")
print(day.groupby(["year", "day_b"]).y_activity_day.agg(["count", "mean"]).unstack())

out = os.path.join(PROCESSED, "event_study_days_panel.dta")
day.to_stata(out, write_index=False, version=118, variable_labels={
    "y_activity_day": "Activity on this trading day (market's pooled 2020 level = 100)",
    "day_b": "Later of the two trading days in the Sat-Fri week",
    "weekday": "Trading weekday (0 = Sunday ... 6 = Saturday)",
    "day_name": "Trading weekday name",
    "y_activity": "Market activity index, both days pooled (2020 = 100)",
})
print(f"wrote {out}  ({len(day)} rows)")
