"""Numerical checks: do the rebuilt series match the published values?

Checks of the data and series behind the paper exhibits. Checks of figures and
tables that are no longer in the paper are in archive/exhibits/verify_full.py."""
import os
import common as C
from common import pd, np

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

# non-market-day panel: markets active in every year
_src = pd.read_csv(C.PANEL, low_memory=False)
_oc = [c for c in _src.columns if c.startswith('open_')]
_flag = _src.groupby('mktID')[_oc].first()
chk('always-active markets', int((_flag[_oc] == 1).all(axis=1).sum()), 120, 0)

# buffer nightlights, 2025 index on the estimation sample
b = C.buffer_ntl(markets=set(pa.mktID), stat='mean').sum()
chk('buffer NTL 2025 index', float(100 * b.loc[2025] / b.loc[2020]), 135.9, 0.3)


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
