"""
Paper checks: rebuild Table 2 and Figure A.1, and compare every number quoted in the text of
AFG_paper_revised_tracked.docx (version of 13 October 2026) with what the code produces.

    python paper_checks.py

Writes, to the same output folder as the rest of the package (output_paper/exhibits):
    table2_goods_by_access.csv     Table 2, goods, schedule and field validation by access category
    figA1_validation_samples.png   Figure A.1, the index under the field-validation subsamples
    paper_checks.csv               one row per claim: section, claim, paper value, code value, status

Status: "match" (equal at the paper's precision), "close" (within the stated tolerance),
"DIFFERS", or "not reproducible" (no code or data in this repository).

The field-validation shares of Table 1, Figure 7 and Figure A.3 come from
ActivityLevelsCehcks..ipynb, and Figure 10 from stata/run_event_study_ACCESS.do; they are
checked there, not here.
"""
import os
import re
import warnings

import numpy as np
import pandas as pd

import common as cm
import tables

warnings.filterwarnings("ignore")
pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 80)

DATA, PROCESSED = cm._project.DATA, cm._project.PROCESSED
WFP = os.path.join(DATA, "WFP_validation", "market_validation_corrected.xlsx")
DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
ACC = ["High access", "Intermediate access", "Remote"]

ROWS = []


def check(section, claim, paper, code, ok=None, tol=None, note=""):
    """Record one claim. ok overrides; tol compares numbers within an absolute tolerance."""
    if ok is None:
        if tol is not None:
            ok = abs(float(paper) - float(code)) <= tol
            status = "match" if abs(float(paper) - float(code)) < 1e-9 else ("close" if ok else "DIFFERS")
        else:
            status = "match" if str(paper) == str(code) else "DIFFERS"
    else:
        status = ok if isinstance(ok, str) else ("match" if ok else "DIFFERS")
    ROWS.append(dict(section=section, claim=claim, paper=paper, code=code, status=status, note=note))


def not_repro(section, claim, paper, note):
    ROWS.append(dict(section=section, claim=claim, paper=paper, code="", status="not reproducible", note=note))


# ------------------------------------------------------------------ shared inputs
pa = cm.panel()
mk = pa.drop_duplicates("mktID").copy()
mk["days"] = mk.marketDays.apply(lambda x: sorted({int(v) for v in re.findall(r"\d+", str(x))}))
mk["ndays"] = mk.days.apply(len)
acc = cm.access_categories().set_index("mktID")
w = pd.read_excel(WFP, sheet_name="Market list")
nat = cm.mai_series(pa)
nat = 100 * nat / nat.loc[2020]


# ------------------------------------------------------------------ Section 1-2.1: markets and map
S = "2.1 Markets"
check(S, "periodic markets detected", 137, mk.mktID.nunique())
g = pd.read_csv(os.path.join(PROCESSED, "market_groups.csv"))
ov, per = g[g.group == "OSM overlap"], g[g.group == "Periodic"]
thr = ov.distance_km_to_nearest_detected_market.max()
d = cm.haversine(per.lat.values[:, None], per.lon.values[:, None], ov.lat.values[None, :], ov.lon.values[None, :])
absent = 100 * (1 - (d <= thr + 1e-9).any(axis=1).mean())
check(S, "share of markets absent from OpenStreetMap (%)", "about two-thirds", round(absent, 1), ok=60 <= absent <= 72)
check("1 Methodology", "OSM locations tagged as marketplaces", 729, int((g.group != "Periodic").sum()))
check(S, "markets in Hilmand", 52, int((mk.admLvl1 == "Hilmand").sum()))
check(S, "South West share of markets (%)", "about half", round(100 * (mk.un_region == "SouthWest").mean(), 1),
      ok=45 <= 100 * (mk.un_region == "SouthWest").mean() <= 55)
NOTE3 = {"Kabul": 1, "Kapisa": 6, "Logar": 1, "Panjsher": 0, "Parwan": 1, "Wardak": 1, "Kunar": 1, "Laghman": 5,
         "Nangarhar": 8, "Nuristan": 0, "Badakhshan": 0, "Baghlan": 2, "Kunduz": 0, "Takhar": 2, "Balkh": 0,
         "Faryab": 6, "Jawzjan": 5, "Samangan": 0, "Sar-e-Pul": 1, "Ghazni": 1, "Khost": 1, "Paktika": 2,
         "Paktya": 3, "Hilmand": 52, "Kandahar": 9, "Nimroz": 5, "Uruzgan": 3, "Zabul": 0, "Badghis": 6,
         "Bamyan": 0, "Daykundi": 0, "Farah": 4, "Ghor": 0, "Hirat": 11}
cnt = mk.admLvl1.value_counts()
bad = {p: (n, int(cnt.get(p, 0))) for p, n in NOTE3.items() if int(cnt.get(p, 0)) != n}
check("Figure 3 / 9 notes", "markets per province (34 provinces)", "as listed", "all equal" if not bad else bad, ok=not bad)

# ------------------------------------------------------------------ 2.2 trading days
S = "2.2 Trading days"
nd = mk.ndays.value_counts()
check(S, "markets trading once / twice / three times a week", "104 / 32 / 1",
      f"{nd.get(1, 0)} / {nd.get(2, 0)} / {nd.get(3, 0)}")
wd = pd.Series([x for s in mk.days for x in s]).value_counts()
top3 = sorted(DAYS[i] for i in wd.index[:3])
check(S, "most common trading days", "Fri, Mon, Thu", ", ".join(top3))
tw = mk[mk.ndays == 2]
gap = tw.days.apply(lambda s: min((s[1] - s[0]) % 7, (s[0] - s[1]) % 7))
check(S, "twice-weekly markets three days apart (%)", 94, round(100 * (gap == 3).mean()), tol=0.5)
check(S, "twice-weekly markets two days apart (%)", 6, round(100 * (gap == 2).mean()), tol=0.5)
check(S, "twice-weekly markets on consecutive days", 0, int((gap == 1).sum()))
pair = tw.days.apply(lambda s: "+".join(DAYS[i] for i in s)).value_counts().index[0]
check(S, "most common twice-weekly pair", "Mon+Thu", pair)
three = mk[mk.ndays == 3]
check(S, "three-times-a-week market", "Badghis: Tue, Wed, Sat",
      f"{three.admLvl1.iloc[0]}: " + ", ".join(DAYS[i] for i in three.days.iloc[0]))
lat, lon = mk.marketlat.values, mk.marketlon.values
D = cm.haversine(lat[:, None], lon[:, None], lat[None, :], lon[None, :]); np.fill_diagonal(D, np.inf)
check(S, "markets with another market within 12 km (%)", "half", round(100 * (D.min(axis=1) <= 12).mean(), 1),
      ok=45 <= 100 * (D.min(axis=1) <= 12).mean() <= 55)
st = cm.staggering_test(thresholds=range(2, 31)).set_index("thr")
check(S, "pairs sharing a day, random assignment (%) [30 km]", 22, round(100 * st.loc[30, "null_mean"], 1), tol=0.5)
check(S, "pairs sharing a day, observed (%) [30 km]", 15, round(100 * st.loc[30, "obs"], 1), tol=0.75)
check(S, "fully matched schedules among markets with a schedule", "94 of 132",
      f"{int(w.day_match.isin(['Exact match', 'Continuous bazaar, main day correct']).sum())} of "
      f"{int(w.day_match.isin(['Exact match', 'Continuous bazaar, main day correct', 'Continuous bazaar, no main day named', 'Partial overlap', 'Complete miss']).sum())}")
for lab, val, key in [("complete overlap", 86, "Exact match"), ("daily, main day matched", 8, "Continuous bazaar, main day correct"),
                      ("daily, no main day", 4, "Continuous bazaar, no main day named"),
                      ("partial overlap", 21, "Partial overlap"), ("no overlap", 13, "Complete miss")]:
    check(S, f"markets: {lab}", val, int((w.day_match == key).sum()))

# ------------------------------------------------------------------ 2.1 field visits
S = "2.1 Field validation"
visited = len(w)
active = int(w.field_status.isin(["active", "less active"]).sum())
check(S, "locations visited (two Baghlan markets not visited)", 135, visited)
check(S, "visited locations confirmed active at the visit", "132 of 135", f"{active} of {visited}")
check("Introduction", "'All 135 locations visited were confirmed to be markets'", "135 of 135", f"{active} of {visited}",
      ok=active == visited, note="Section 2.1 says 132 of 135 were active and three were not; the two statements disagree.")
mw = w[w.district.str.contains("Maywand", na=False) & (w.day_match == "No trading day reported")]
check("Footnote 6", "Maywand locations with no bazaar at the coordinates", 2, len(mw))
a, b = acc.loc["lon68_7092lat35_9503"], acc.loc["lon69_5107lat35_9643"]
check("Footnote 5", "distance between the two Baghlan markets (km)", 72.2,
      round(float(cm.haversine(a.marketlat, a.marketlon, b.marketlat, b.marketlon)), 1))
check("Footnote 5", "Khost wa Firing: travel time to a 50,000+ town (min)", "more than 40", round(b.travel_50),
      ok=b.travel_50 > 40)

# ------------------------------------------------------------------ 2.3 accessibility and nighttime lights
S = "2.3 Access"
cnts = acc.access.value_counts()
check(S, "markets high / intermediate / remote", "47 / 36 / 54",
      f"{cnts['High access']} / {cnts['Intermediate access']} / {cnts['Remote']}")
med = acc.groupby("access")[["travel_50", "wp_SUM"]].median()
check(S, "median travel time, high / intermediate / remote (min)", "6 / 25 / 75",
      " / ".join(f"{med.loc[k, 'travel_50']:.0f}" for k in ACC))
check(S, "median catchment, high / intermediate / remote (thousand)", "430 / 152 / 20",
      " / ".join(f"{med.loc[k, 'wp_SUM'] / 1000:.0f}" for k in ACC))
ntl = pd.read_csv(os.path.join(PROCESSED, "ntl_bnr_866markets_4years.csv"), low_memory=False)
ntl = ntl.merge(g[["mkt_uid", "group"]], on="mkt_uid", how="left")
pn = ntl[ntl.group == "Periodic"].copy()
pn["access"] = pn.orig_id.map(acc.access)
for y, paper_any, paper_acc in [(2018, 55, "94 / 64 / 20"), (2025, 71, "100 / 92 / 39")]:
    cols = sorted(c for c in pn.columns if c.startswith(f"SUM_BNR_{y}"))
    lit = pn[cols].median(axis=1, skipna=True).fillna(0).clip(lower=0)
    check(S, f"periodic markets with positive emissions, {y} (%) [median > 1]", paper_any, round(100 * (lit > 1).mean()), tol=0.5,
          note="matches with the CDF figure's definition (median above 1)")
    check(S, f"periodic markets with positive emissions, {y} (%) [median > 0]", paper_any, round(100 * (lit > 0).mean()), tol=0.5,
          note="the by-access shares use this definition; the two definitions give different totals")
    sh = (lit > 0).groupby(pn.access).mean() * 100
    check(S, f"positive emissions by access {y}, high / intermediate / remote (%)", paper_acc,
          " / ".join(f"{sh[k]:.0f}" for k in ACC))
not_repro("2.3 Population", "population within 20 km of a periodic market (%)", "about 40",
          "needs the WorldPop raster and a distance surface (Figure 4); no code in the repository")
not_repro("2.3 Population", "population within 20 km of an OSM permanent market (%)", "nearly 90", "as above")
not_repro("Footnote 8", "Ethiopian population within 20 km of a periodic market (%)", "about 95", "from von Carnap et al. (2026)")

# ------------------------------------------------------------------ Table 2 and 2.4 goods
S = "Table 2"
GOODS = {"Food only": "Food only", "Food and livestock, no general goods": "Food and livestock",
         "Food and general goods, no livestock": "Food and general goods", "All goods, unspecified": "Food and general goods",
         "Food, livestock and general goods": "Food, livestock and general goods",
         "Livestock only": "Livestock only", "General goods only": "Car markets"}
T = acc[["access"]].join(w.set_index("mktID")[["category_label", "day_match"]], how="left")
T["goods"] = T.category_label.map(GOODS)
T.loc[T.category_label == "Not specified", "goods"] = "Not specified"
T.loc[T.day_match == "No trading day reported", "goods"] = "Not trading"
T.loc[T.category_label.isna(), "goods"] = "Not covered"
T["ndays"] = mk.set_index("mktID").ndays.reindex(T.index)
reported = T.day_match.isin(["Exact match", "Partial overlap", "Complete miss", "Continuous bazaar, main day correct",
                             "Continuous bazaar, no main day named"])
full = T.day_match.isin(["Exact match", "Continuous bazaar, main day correct"])


def by_access(s, share=False, den=None):
    out = {}
    for k, mask in [("All", pd.Series(True, index=T.index))] + [(a, T.access == a) for a in ACC]:
        if den is not None:
            out[k] = 100 * (s & mask).sum() / (den & mask).sum()
        else:
            out[k] = 100 * s[mask].mean() if share else int(s[mask].sum())
    return out


rows = {"Markets (number)": by_access(pd.Series(True, index=T.index))}
for k in ["Food only", "Food and livestock", "Food and general goods", "Food, livestock and general goods",
          "Livestock only", "Car markets", "Not specified", "Not trading", "Not covered"]:
    rows[k] = by_access(T.goods == k)
rows["Trades once a week (%)"] = by_access(T.ndays == 1, share=True)
rows["Visited (number)"] = by_access(T.category_label.notna())
rows["Reported a trading day (number)"] = by_access(reported)
rows["Schedule fully confirmed (% with a reported day)"] = by_access(full, den=reported)
rows["No overlap with reported days (% with a reported day)"] = by_access(T.day_match == "Complete miss", den=reported)
rows["Trades daily with a weekly peak (number)"] = by_access(T.day_match.str.startswith("Continuous", na=False))
TAB2 = pd.DataFrame(rows).T[["All"] + ACC].round(0).astype(int)
TAB2.to_csv(os.path.join(cm.OUT, "table2_goods_by_access.csv"))
PAPER_T2 = {"Markets (number)": [137, 47, 36, 54], "Food only": [29, 10, 8, 11], "Food and livestock": [9, 2, 5, 2],
            "Food and general goods": [28, 6, 7, 15], "Food, livestock and general goods": [48, 20, 11, 17],
            "Livestock only": [8, 3, 4, 1], "Car markets": [3, 3, 0, 0], "Not specified": [7, 1, 0, 6],
            "Not trading": [3, 1, 1, 1], "Not covered": [2, 1, 0, 1], "Trades once a week (%)": [76, 77, 67, 81],
            "Visited (number)": [132, 46, 36, 53], "Schedule fully confirmed (% with a reported day)": [68, 67, 83, 67]}
for r, vals in PAPER_T2.items():
    code = TAB2.loc[r].tolist()
    check(S, r + " (All / High / Intermediate / Remote)", " / ".join(map(str, vals)), " / ".join(map(str, code)),
          ok=vals == code)
S = "2.4 Goods"
info = T.category_label.notna() & (T.category_label != "Not specified")
food = T.goods.isin(["Food only", "Food and livestock", "Food and general goods", "Food, livestock and general goods"])
check(S, "markets with goods information", 125, int(info.sum()))
check(S, "markets selling food", 114, int(food.sum()))
check(S, "food combined with livestock and/or general goods", 85,
      int(T.goods.isin(["Food and livestock", "Food and general goods", "Food, livestock and general goods"]).sum()))
check(S, "markets with no food reported", 11, int((info & ~food).sum()))
check(S, "car markets that are high access", "3 of 3", f"{int(((T.goods == 'Car markets') & (T.access == 'High access')).sum())} of {int((T.goods == 'Car markets').sum())}")
check(S, "food, livestock and general goods markets that are high access", "20 of 48",
      f"{int(((T.goods == 'Food, livestock and general goods') & (T.access == 'High access')).sum())} of {int((T.goods == 'Food, livestock and general goods').sum())}")
check(S, "food and general goods markets that are remote", "15 of 28",
      f"{int(((T.goods == 'Food and general goods') & (T.access == 'Remote')).sum())} of {int((T.goods == 'Food and general goods').sum())}")
daily = T.day_match.str.startswith("Continuous", na=False)
check("2.3 Access", "markets reported as trading daily that are high access", "most",
      f"{int((daily & (T.access == 'High access')).sum())} of {int(daily.sum())}",
      ok=(daily & (T.access == "High access")).sum() > daily.sum() / 2)
cm_ = T.day_match == "Complete miss"
check("2.3 Access", "no-overlap disagreements that are remote", "more often remote",
      f"{int((cm_ & (T.access == 'Remote')).sum())} of {int(cm_.sum())}", ok=(cm_ & (T.access == "Remote")).sum() > cm_.sum() / 2)

# ------------------------------------------------------------------ NDVI table ("Table 1", second one)
S = "NDVI table"
TN, meta = tables.tableA3_ndvi_marketday()
PAPER_NDVI = [["Market day", "+85.30***", "+85.31***", "+85.26***", "+98.25***", "+97.54***"],
              ["", "(3.42)", "(3.45)", "(3.51)", "(2.09)", "(2.17)"],
              ["Growing-season NDVI", "−0.42", "−0.78", "−0.41", "−0.22", "−0.18"],
              ["", "(0.32)", "(0.50)", "(0.85)", "(0.16)", "(0.15)"],
              ["Market day × NDVI", "+3.26***", "+3.37***", "+3.10***", "+1.54***", "+1.56***"],
              ["", "(0.88)", "(0.91)", "(0.91)", "(0.27)", "(0.27)"],
              ["Observations", "6,376", "6,376", "6,376", "24,982", "24,982"],
              ["Markets", "137", "137", "137", "137", "137"],
              ["R-squared", "0.460", "0.483", "0.542", "0.474", "0.506"]]
code_rows = TN.values.tolist()
n_bad = 0
for prow in PAPER_NDVI:
    crow = next((r for r in code_rows if r[0] == prow[0] and (prow[0] or r[1].startswith("("))), None)
    if prow[0] == "":
        idx = [i for i, r in enumerate(code_rows) if r[0] == PAPER_NDVI[PAPER_NDVI.index(prow) - 1][0]][0] + 1
        crow = code_rows[idx]
    n_bad += sum(str(p) != str(c) for p, c in zip(prow[1:], crow[1:]))
check(S, "all coefficient, SE, N and R-squared cells (45)", "as printed", "all equal" if n_bad == 0 else f"{n_bad} cells differ",
      ok=n_bad == 0)
check(S, "text: harvest-quarter interaction, column 3", 3.10, 3.10, ok=TN.iloc[4, 3].startswith("+3.10"))
check(S, "text: increase relative to the market-day coefficient (%)", 3.6, round(100 * 3.10 / 85.26, 1), tol=0.05)

# ------------------------------------------------------------------ 3.1 national index and overpass
S = "3.1 Trend"
check(S, "index peaks in 2022", 2022, int(nat.loc[2018:2025].idxmax()))
check(S, "fall from the 2022 peak to 2025 (%)", 19.8, round(100 * (nat[2025] / nat[2022] - 1) * -1, 1), tol=0.05)
check(S, "fall 2020 to 2025 (%)", 11.5, round(100 * (nat[2025] / nat[2020] - 1) * -1, 1), tol=0.05)
check("Methodology", "2018 and 2019 close to 2020 (index)", "close to 100", f"{nat[2018]:.1f}, {nat[2019]:.1f}",
      ok=abs(nat[2018] - 100) < 5 and abs(nat[2019] - 100) < 5)

S = "A.4 Overpass"
p = pa.copy()
tt = pd.to_datetime(p.image_id.str.slice(9, 15), format="%H%M%S", errors="coerce") + pd.Timedelta(hours=4, minutes=30)
p["minutes"] = tt.dt.hour * 60 + tt.dt.minute + tt.dt.second / 60
p = p.dropna(subset=["minutes", cm.TARGET]).copy()
mt = p.groupby("year").minutes.mean()
fmt = lambda m: f"{int(round(m) // 60)}:{int(round(m) % 60):02d}"
check(S, "mean overpass 2018 / 2025", "10:19 / 11:14", f"{fmt(mt[2018])} / {fmt(mt[2025])}")
check(S, "shift in the mean overpass (min)", 55, round(mt[2025] - mt[2018]), tol=1)
check(S, "market-day images", 40667, len(p))
p["slot"] = (p.minutes // 60).astype(int).map(lambda h: f"{h:02d}")
vc = p.slot.value_counts()
check(S, "images in the dropped 06:00 window", 9, int(vc.get("06", 0)))
p = p[p.slot.isin(vc[vc >= 200].index)].copy()
check(S, "2025 images in the 11:00 window (%)", 84, round(100 * (p[p.year == 2025].slot == "11").mean()), tol=0.5)
X = pd.DataFrame({f"T_{s}": (p.slot == s).astype(float) for s in ["07", "08", "09", "11"]}, index=p.index)
for q in [2, 3, 4]: X[f"Q{q}"] = (p.quarter == q).astype(float)
Xy = X.copy()
for y in sorted(p.year.unique())[1:]: Xy[f"Y{y}"] = (p.year == y).astype(float)


def within(Xm):
    gidx = p.mktID.values
    y_ = p[cm.TARGET].values.astype(float)
    yd = y_ - pd.Series(y_, index=p.index).groupby(gidx).transform("mean").values
    Xd = Xm.values - pd.DataFrame(Xm.values, index=p.index).groupby(gidx).transform("mean").values
    b_, *_ = np.linalg.lstsq(Xd, yd, rcond=None); r_ = yd - Xd @ b_
    n_, k_ = Xd.shape; G = p.mktID.nunique(); dof = n_ - k_ - G
    Xi = np.linalg.inv(Xd.T @ Xd); meat = np.zeros((k_, k_))
    for _, ix in p.groupby("mktID").indices.items():
        xu = Xd[ix].T @ r_[ix]; meat += np.outer(xu, xu)
    V = Xi @ meat @ Xi * (G / (G - 1)) * ((n_ - 1) / dof)
    return pd.Series(b_, index=Xm.columns), pd.Series(np.sqrt(np.diag(V)), index=Xm.columns), V


b1, se1, V1 = within(Xy)
b0, _, _ = within(X)
for s, val in [("07", "+0.64 (2.26)"), ("08", "+8.38 (1.73)"), ("09", "+2.46 (1.13)"), ("11", "-4.70 (1.87)")]:
    check(S, f"{s}:00 window vs 10:00 (index points, SE)", val, f"{b1[f'T_{s}']:+.2f} ({se1[f'T_{s}']:.2f})",
          tol=None, ok="close" if abs(b1[f"T_{s}"] - float(val.split()[0])) <= 0.5 else "DIFFERS")
Ti = [Xy.columns.get_loc(f"T_{s}") for s in ["07", "08", "09", "11"]]
bt = b1.values[Ti]; F = float(bt @ np.linalg.inv(V1[np.ix_(Ti, Ti)]) @ bt) / len(Ti)
check(S, "joint F-test of the windows", 9.19, round(F, 2), tol=0.5)
check(S, "11:00 window without year dummies", -15.85, round(b0["T_11"], 2), tol=0.25)
check("3.1 Trend", "11:00-noon images lower than 10:00-11:00 (points)", 4.7, round(-b1["T_11"], 1), tol=0.35)
beta = {s: b1[f"T_{s}"] for s in ["07", "08", "09", "11"]}
adj = pa.copy()
hh = (pd.to_datetime(adj.image_id.str.slice(9, 15), format="%H%M%S", errors="coerce") + pd.Timedelta(hours=4, minutes=30)).dt.hour
adj[cm.TARGET] = adj[cm.TARGET] - hh.map(lambda h: beta.get(f"{int(h):02d}", 0.0) if pd.notna(h) else 0.0)
na_ = cm.mai_series(adj)
check(S, "adjusted fall from the 2022 peak to 2025 (%)", 16.3, round(-100 * (na_[2025] / na_[2022] - 1), 1), tol=0.25)
check(S, "adjusted fall 2020 to 2025 (%)", 6.2, round(-100 * (na_[2025] / na_[2020] - 1), 1), tol=0.25)

# ------------------------------------------------------------------ Figure A.1 validation subsamples
S = "Figure A.1"
s1 = w.mktID[w.day_match.isin(["Exact match", "Continuous bazaar, main day correct"])]
s2 = pd.concat([s1, w.mktID[(w.day_match == "Partial overlap") & (w.partial_type == "Field reports an extra day the MAI does not detect")]])
SER = {"All markets": nat}
for lab, ids in [("Exact schedule match", s1), ("Exact match + validated MAI day", s2)]:
    s_ = cm.mai_series(pa[pa.mktID.isin(ids)])
    SER[lab] = 100 * s_ / s_.loc[2020]
A1 = pd.DataFrame(SER).loc[2018:2025]
dmax = (A1.drop(columns="All markets").sub(A1["All markets"], axis=0)).abs().max().max()
check(S, "markets in the exact-match sample", 92, len(s1),
      note="94 now: Nijrab joined the exact matches after the WFP update, and the Hirat market is in the 137-market panel")
check(S, "markets in the exact-match + validated-MAI-day sample", 105, len(s2))
check("3.1 Trend", "largest gap between a restricted sample and the full sample (points)", "no more than 3",
      round(dmax, 1), ok=dmax <= 3)
import matplotlib.pyplot as plt
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9))
STY = {"All markets": (cm.INK, "-", "o"), "Exact schedule match": (cm.COLOR["mai"], "--", "s"),
       "Exact match + validated MAI day": (cm.COLOR["ntl_total"], ":", "^")}
N = {"All markets": 137, "Exact schedule match": len(s1), "Exact match + validated MAI day": len(s2)}
for lab, (col, ls, mkr) in STY.items():
    a1.plot(A1.index, A1[lab], ls=ls, marker=mkr, ms=3, lw=1.6, color=col, label=f"{lab} (n={N[lab]})", zorder=3)
    if lab != "All markets":
        a2.plot(A1.index, A1[lab] - A1["All markets"], ls=ls, marker=mkr, ms=3, lw=1.6, color=col, zorder=3)
cm.grid(a1, 100); cm.years(a1); cm.grid(a2, 0); cm.years(a2)
a1.set_ylabel("Index, 2020 = 100", fontsize=7.4); a2.set_ylabel("Difference from all markets (points)", fontsize=7.4)
a1.set_title("a. Market activity by sample", fontsize=7.4, loc="left", pad=4)
a2.set_title("b. Restricted sample minus full sample", fontsize=7.4, loc="left", pad=4)
a2.set_ylim(-5, 5)
a1.legend(fontsize=6.2, loc="lower left")
fig.tight_layout(pad=0.4)
cm.save(fig, "figA1_validation_samples")

# ------------------------------------------------------------------ 3.3 regions and access
S = "3.3 Regions"
reg = pd.concat([cm.mai_series(gp, r) for r, gp in pa.groupby("un_region")], axis=1)
reg = 100 * reg / reg.loc[2020]
check(S, "regions ending 2025 above 2020", "2 of 7", f"{int((reg.loc[2025] > 100).sum())} of {reg.shape[1]}")
mm = cm.market_year_activity(pa)
chg = 100 * (mm[2025] / mm[2020] - 1)
prov_chg = chg.groupby(mk.set_index("mktID").admLvl1).mean()
for prov, val in [("Kabul", -37), ("Parwan", -34), ("Kapisa", 21)]:
    check(S, f"{prov}: change in activity 2020-2025 (%)", val, round(prov_chg[prov]), tol=0.5)
check(S, "Kabul and Parwan markets: travel time to a 50,000+ town (min)", "0 and 0",
      " and ".join(f"{acc[acc.admLvl1 == p].travel_50.iloc[0]:.0f}" for p in ["Kabul", "Parwan"]))
ea = mk[mk.un_region == "East"].admLvl1.value_counts()
check(S, "East: markets in Nangarhar and Laghman", "13 of 14", f"{ea.get('Nangarhar', 0) + ea.get('Laghman', 0)} of {ea.sum()}")
check(S, "East: Kunar declined; Nangarhar and Laghman held up", "Kunar < 0 < Nangarhar, Laghman",
      f"Kunar {prov_chg['Kunar']:+.0f}, Nangarhar {prov_chg['Nangarhar']:+.0f}, Laghman {prov_chg['Laghman']:+.0f}",
      ok=prov_chg["Kunar"] < 0 < min(prov_chg["Nangarhar"], prov_chg["Laghman"]))
S = "3.3 Access"
ACCS = pd.concat([cm.mai_series(pa[pa.mktID.isin(acc.index[acc.access == a])], a) for a in ACC], axis=1)
ACCS = 100 * ACCS / ACCS.loc[2020]
check(S, "high-access index in 2025 (close to 2020)", "about 100", round(ACCS.loc[2025, "High access"], 1),
      ok=abs(ACCS.loc[2025, "High access"] - 100) <= 3)
check(S, "remote: points below 2020 in 2025 (paper: about 12)", 12, round(100 - ACCS.loc[2025, "Remote"], 1), tol=2)
check(S, "intermediate: points below 2020 in 2025 (paper: about 24)", 24, round(100 - ACCS.loc[2025, "Intermediate access"], 1), tol=2)
check(S, "2020-2022: high and remote rose, intermediate flat (2022 index)", "high > remote > intermediate ~ 100",
      " / ".join(f"{ACCS.loc[2022, a]:.1f}" for a in ACC),
      ok=ACCS.loc[2022, "High access"] > ACCS.loc[2022, "Remote"] > ACCS.loc[2022, "Intermediate access"])

# ------------------------------------------------------------------ A.2 poppy
S = "A.2 Poppy"
POP = {"Hilmand", "Kandahar", "Uruzgan", "Faryab", "Nangarhar", "Badakhshan", "Zabul", "Farah", "Nimroz"}
ppy = mk.admLvl1.isin(POP)
check(S, "markets in poppy / non-poppy / poppy outside Hilmand provinces", "87 / 50 / 35",
      f"{int(ppy.sum())} / {int((~ppy).sum())} / {int((ppy & (mk.admLvl1 != 'Hilmand')).sum())}")
TA, ma = tables.tableA2_poppy()
PAPER_A1 = [["Poppy province", "−2.26", "−1.70", "−2.15", "−2.73"], ["", "(4.84)", "(4.59)", "(4.79)", "(4.43)"],
            ["Intermediate access (vs high)", "", "−7.91*", "−8.70*", "−9.58**"], ["", "", "(4.38)", "(4.55)", "(3.84)"],
            ["Remote (vs high)", "", "+0.63", "−0.48", "−4.57"], ["", "", "(5.42)", "(5.25)", "(5.10)"],
            ["Conflict deaths per 100,000, 2017–2018", "", "", "+0.0077**", "+0.0098***"], ["", "", "", "(0.0034)", "(0.0034)"],
            ["Change in growing-season NDVI, 2022–2025 (sd)", "", "", "", "−5.24**"], ["", "", "", "", "(2.38)"],
            ["Constant", "−18.92***", "−17.67***", "−18.52***", "−13.75***"], ["", "(3.89)", "(5.17)", "(5.35)", "(4.92)"],
            ["R²", "0.003", "0.029", "0.043", "0.071"], ["Observations", "124", "124", "124", "124"],
            ["Province clusters", "22", "22", "22", "22"]]
tv = TA.values.tolist()
bad_a = 0
for i, pr in enumerate(PAPER_A1):
    if pr[0]:
        cr = next(r for r in tv if r[0] == pr[0])
    else:
        prev = PAPER_A1[i - 1][0]
        cr = tv[[j for j, r in enumerate(tv) if r[0] == prev][0] + 1]
    bad_a += sum(str(a_) != str(c_) for a_, c_ in zip(pr[1:], cr[1:]))
check(S, "Table A.1 cells (all four columns)", "as printed", "all equal" if bad_a == 0 else f"{bad_a} differ", ok=bad_a == 0)
check(S, "Table A.1 note: markets active in 2022 and 2025", 124, ma["n"])
check(S, "Table A.1 note: of which in poppy provinces", 79, ma["n_poppy"])
check(S, "Table A.1 note: mean change 2022-2025 (%)", -20.4, round(ma["mean_dv"], 1), tol=0.05)

# ------------------------------------------------------------------ not reproducible from this repository
for sec, claim, val, note in [
        ("1 Methodology", "search area after the road and built-up filters (% of landmass)", "about 25", "upstream detection pipeline (PlanetScope/Sentinel-2 screening); not in the repository"),
        ("1 Methodology", "candidate locations screened", "more than 2,500", "upstream detection pipeline"),
        ("1 Methodology", "area of each candidate location (ha)", "about 20", "upstream detection pipeline"),
        ("Footnote 1", "median PlanetScope revisit interval (hours)", "about 30", "external (Roy et al. 2021)"),
        ("Footnote 14", "AWMS poverty rates (urban 58%; rural 51% to 44%)", "as quoted", "external (World Bank 2023b)")]:
    not_repro(sec, claim, val, note)

# ------------------------------------------------------------------ report
R = pd.DataFrame(ROWS)
R.to_csv(os.path.join(cm.OUT, "paper_checks.csv"), index=False)
print(R.to_string(index=False))
print("\nstatus counts:", R.status.value_counts().to_dict())
print("saved", os.path.join(cm.OUT, "paper_checks.csv"), "and table2_goods_by_access.csv")
