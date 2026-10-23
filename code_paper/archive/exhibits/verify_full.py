"""Numerical checks: do the rebuilt series match the published values?"""
import os
import common as C
from common import pd, np
import figures as F

CHECKS, fails = [], 0
def chk(name, got, want, tol):
    global fails
    ok = abs(got - want) <= tol
    CHECKS.append((name, got, want, tol, ok))
    if not ok: fails += 1

# the published figures were built on the 136-market derived file, so the
# reproduction check uses that sample; the 137-market version is checked below.
pa = C.panel(include_herat=False)
mai = C.mai_series(pa)
# published national index, 2020 = 100 (01_mai_calendar_year.csv / Master.ipynb cell 48)
PUB = {2018: 102.09, 2019: 100.42, 2020: 99.99, 2021: 108.87,
       2022: 110.29, 2023: 103.04, 2024: 95.25, 2025: 88.47}
for y, v in PUB.items():
    chk(f'national MAI {y}', float(mai.loc[y]), v, 0.05)

# market counts
chk('markets, published derived file', pa.mktID.nunique(), 136, 0)
pa137 = C.panel(include_herat=True)
chk('markets, with the Herat market added', pa137.mktID.nunique(), 137, 0)
h = pa137[pa137.mktID == C.HERAT_MKT]
chk('Herat market: all rows are Mondays', int((h.weekday == C.HERAT_DAY).all()), 1, 0)
chk('Herat market: market-day rows', int(len(h) > 0), 1, 0)
chk('Herat market: last year of imagery', int(h.year.max()), 2024, 0)
m137 = C.mai_series(pa137)
chk('MAI 2025 unchanged by the addition', float(m137.loc[2025]), float(mai.loc[2025]), 0.01)
chk('MAI 2022 shifts only slightly', float(m137.loc[2022]), 110.29, 0.15)
acc = C.access_categories()
# with the Herat market restored these are the manuscript's counts: 47 / 36 / 54
for k, v in [('High access', 47), ('Intermediate access', 36), ('Remote', 54)]:
    chk(f'access: {k}', int((acc.access == k).sum()), v, 0)

# Hilmand split, against the published values shipped in reference/
sp = pd.read_csv(C.REF_POPPY, index_col=0)
for lab, col, sub in [('excl. Hilmand', 'Excl. Hilmand', pa[pa.admLvl1 != 'Hilmand']),
                      ('Hilmand only', 'Hilmand only', pa[pa.admLvl1 == 'Hilmand'])]:
    s = C.mai_series(sub)
    chk(f'{lab} 2025', float(s.loc[2025]), float(sp.loc[2025, col]), 0.05)

# frequency pairs: 28 km reproduces the manuscript's 80 pairs
pr = C.frequency_pairs(28)
# 83 pairs, not the manuscript's 80: the 28 km threshold is unchanged, but the
# three markets whose trading days were filled in from SUPPLIED_DAYS now qualify.
chk('frequency pairs at 28 km', len(pr), 83, 0)

# non-market-day panel: the manuscript's counts (image22)
import figures as _F
_src = pd.read_csv(C.PANEL, low_memory=False)
_oc = [c for c in _src.columns if c.startswith('open_')]
_flag = _src.groupby('mktID')[_oc].first()
chk('always-active markets', int((_flag[_oc] == 1).all(axis=1).sum()), 120, 0)

# staggering permutation test, observed share at 30 km
st = C.staggering_test()                       # 136 markets, supplied days filled in
st_legacy = C.staggering_test(legacy=True)     # the manuscript's original 133
chk('staggering pairs at 30 km', float(st.iloc[-1].pairs), 318, 0)
chk('staggering observed share at 30 km', float(st.iloc[-1].obs), 0.1572, 0.001)
chk('staggering, legacy 133-market pairs at 30 km', float(st_legacy.iloc[-1].pairs), 308, 0)

# buffer nightlights, 2025 index on the estimation sample
b = C.buffer_ntl(markets=set(pa.mktID), stat='mean').sum()
chk('buffer NTL 2025 index', float(100 * b.loc[2025] / b.loc[2020]), 135.9, 0.3)


# Figure 3 panel b: the CDF is built on the MEDIAN monthly buffer radiance
_mk = set(C.panel().mktID)
med = C.buffer_ntl(markets=_mk, stat='median')[2025].fillna(0)
chk('fig03b: markets in the CDF', float(len(med)), 137, 0)
chk('fig03b: markets with zero median radiance', float((med <= 0).sum()), 73, 0)
chk('fig03b: highest log1p radiance', float(np.log1p(med.max())), 8.18, 0.05)

# Figure 5: the background bar is the national index, so its 2025 height must be
# the national series itself
_acc = C.access_categories().set_index('mktID').access
_pa = C.panel(); _pa['access'] = _pa.mktID.map(_acc)
chk('fig05 bar 2025 = national index', float(C.mai_series(_pa, 'x').reindex([2025]).iloc[0]),
    88.47, 0.02)
chk('fig05 high access 2025', float(C.mai_series(_pa[_pa.access == 'High access'], 'x')
                                     .reindex([2025]).iloc[0]), 98.53, 0.05)


# Figure 3 panel d: the median rule is taken over markets WITH emissions
_ac = C.access_categories()
_b = C.buffer_ntl(markets=set(_ac.mktID), stat='mean')[2025]
_x = _ac.merge(_b.rename('v'), left_on='mktID', right_index=True, how='left').fillna({'v': 0})
_p = _x[_x.v > 0]
for _k, _want in [('High access', 202), ('Intermediate access', 23), ('Remote', 4)]:
    chk(f'fig04b median, positive {_k.lower()}',
        float(_p.loc[_p.access == _k, 'v'].median()), _want, 0.5)


# Table A1, regional coverage: the district and province universes are fixed
import tables as _T
_A1, _m1 = _T.tableA1_region_coverage()
chk('tableA1: districts in Afghanistan', float(_m1['districts']), 401, 0)
chk('tableA1: provinces in Afghanistan', float(_m1['provinces']), 34, 0)
chk('tableA1: districts holding a market', float(_m1['districts_with']), 71, 0)
chk('tableA1: provinces holding a market', float(_m1['provinces_with']), 24, 0)
chk('tableA1: markets sum to the panel', float(_A1.Markets.iloc[:-1].sum()), 137, 0)
chk('tableA1: South West markets', float(_A1.set_index('Region').loc['South West', 'Markets']), 69, 0)


# Figure 19: nightlights per capita by 2020 control status
_pc, _pg = C.ntl_per_capita_by_control()
_D = C.district_control_2020()
chk('fig19: districts classified', float(_D.Pcode_24.nunique()), 401, 0)
chk('fig19: 2020 government-held population, m',
    float(_pg.loc[2020, 'Government-held'] / 1e6), 18.4, 0.1)
chk('fig19: 2020 contested population, m', float(_pg.loc[2020, 'Contested'] / 1e6), 14.7, 0.1)
chk('fig19: 2020 Taliban-held population, m', float(_pg.loc[2020, 'Taliban-held'] / 1e6), 5.3, 0.1)
_ix = 100 * _pc / _pc.loc[2020]
chk('fig19: government-held 2022 index', float(_ix.loc[2022, 'Government-held']), 89.3, 0.3)
chk('fig19: Taliban-held 2025 index', float(_ix.loc[2025, 'Taliban-held']), 132.8, 0.3)
chk('fig19: government-held 2025 index', float(_ix.loc[2025, 'Government-held']), 118.5, 0.3)


# The three quantities that used to be read from the wider repository's pipeline
# are computed here now. They are checked against fixtures SHIPPED WITH THE
# PACKAGE (reference/), so the comparison means the same thing on every machine.
def _ref(path):
    if not os.path.exists(path):
        print(f'   (skipped: {os.path.basename(path)} missing from reference/)')
        return None
    return pd.read_csv(path)

_r = _ref(C.REF_NTL_NAT)
if _r is not None:
    _r = _r.set_index('year').civilian_feb_jun
    chk('ntl_national reproduces reference/04_ntl_national.csv',
        float((C.ntl_national().reindex(_r.index) - _r).abs().max()), 0.0, 1e-6)

_r = _ref(C.REF_NDVI_LVL)
if _r is not None:
    _r = _r.set_index('year').iloc[:, 0]
    chk('ndvi_levels reproduces reference/ndvi_levels.csv',
        float((C.ndvi_levels().reindex(_r.index) - _r).abs().max()), 0.0, 1e-9)

_r = _ref(C.REF_STAGGER)
if _r is not None:
    # The stored file may hold shares or percentages depending on which script
    # wrote it; normalise before comparing rather than assuming a scale.
    _cols = ['obs', 'null_mean', 'lo', 'hi']
    if _r[_cols].to_numpy().max() > 1.5:
        _r[_cols] = _r[_cols] / 100.0
        print('   (reference/staggering_test.csv is percent-scaled; converted to shares)')
    _m = _r.merge(st_legacy, on='thr', suffixes=('_ref', '_new'))
    chk('staggering_test reproduces pairs', float((_m.pairs_ref - _m.pairs_new).abs().max()), 0, 0)
    chk('staggering_test reproduces obs', float((_m.obs_ref - _m.obs_new).abs().max()), 0, 1e-9)
    chk('staggering_test null mean within permutation noise',
        float((_m.null_mean_ref - _m.null_mean_new).abs().max()), 0, 0.02)
    chk('staggering_test thresholds covered', float(len(_m)), float(len(st_legacy)), 0)


# Trading days: every market now carries one
import re as _re
_mk = C.panel().drop_duplicates('mktID')
_nd = _mk.marketDays.apply(lambda x: len(set(_re.findall(r'\d+', str(x)))))
chk('markets with a trading day', float((_nd > 0).sum()), 137, 0)
chk('markets trading once a week', float((_nd == 1).sum()), 104, 0)
chk('markets trading twice a week', float((_nd == 2).sum()), 32, 0)
chk('markets trading three times a week', float((_nd == 3).sum()), 1, 0)
chk('total market-days', float(_nd.sum()), 171, 0)

w = max(len(c[0]) for c in CHECKS)
print(f'{"check".ljust(w)}  {"got":>9} {"expected":>9}  ok')
for n, g, e, t, ok in CHECKS:
    print(f'{n.ljust(w)}  {g:9.2f} {e:9.2f}  {"OK" if ok else "FAIL"}')
print(f'\n{len(CHECKS)-fails} of {len(CHECKS)} checks passed')
