"""Shared paths and data builders for the figure replication package.

The figures' palette, sizes and fonts are in style.py and the drawing in
plots.py; this module finds the inputs and computes the series they draw.
"""
import os, sys, warnings
warnings.filterwarnings('ignore')
import matplotlib
if 'ipykernel' not in sys.modules:      # scripts render off-screen; notebooks keep inline display
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd, numpy as np

# --------------------------------------------------------------- paths
# Nothing here is hard-coded to one machine. Every input is resolved at import
# time by looking for it, in this order:
#
#   1. an explicit entry in paths.json beside this file, e.g.
#         {"PANEL": "/data/derived/periodict_act.csv", "ROOTS": ["/data"]}
#   2. the environment variable MAI_<KEY>, e.g. MAI_PANEL
#   3. each candidate relative path under each search root
#   4. a bounded search for the file's basename under each search root
#
# Search roots are, in order: $MAI_ROOT, any "ROOTS" listed in paths.json, a
# `data` directory beside or above this package, the package's parent, and the
# current working directory. No machine-specific path is baked in, so
# `MAI_ROOT=/path/to/data python run_all.py` is normally all that is needed,
# whatever the tree looks like underneath. See paths.json.example.
#
# `python common.py` prints what resolved, what did not, and where it looked.
import glob as _glob
import json as _json

HERE = os.path.dirname(os.path.abspath(__file__))

# In this repository the data stay in the shared MarketActivityIndex folder that
# code_paper/NTL_processing/config.py resolves (MAI_BASE or mai_base.txt): the
# inputs are under document/Repo_09042026/data there, and outputs go to
# output_paper/exhibits. Without config.py the package falls back to ./out.
import sys as _sys
_sys.path.insert(0, os.path.join(HERE, '..', 'NTL_processing'))
try:
    import config as _project
    _PROJECT_DATA, _PROJECT_OUT = _project.REPO_DATA, os.path.join(_project.OUTPUT, 'exhibits')
    _PROJECT_PAPER = _project.PAPER_EXHIBITS
except Exception:
    _PROJECT_DATA, _PROJECT_OUT, _PROJECT_PAPER = None, None, None
# OUT: diagnostic outputs (paper_checks.csv). PAPER: the paper's figures and tables,
# shared with the notebooks and the Stata do-file (config.PAPER_EXHIBITS).
OUT = _PROJECT_OUT or os.path.join(HERE, 'out')
PAPER = _PROJECT_PAPER or os.path.join(HERE, 'out', 'paper_exhibits')
os.makedirs(OUT, exist_ok=True)
os.makedirs(PAPER, exist_ok=True)
REFERENCE = os.path.join(HERE, 'reference')     # fixtures shipped with the package

_CFG = {}
_cfg_path = os.path.join(HERE, 'paths.json')
if os.path.exists(_cfg_path):
    with open(_cfg_path, encoding='utf-8') as _f:
        _CFG = _json.load(_f)

def _search_roots():
    r = []
    if os.environ.get('MAI_ROOT'):
        r.append(os.environ['MAI_ROOT'])
    r += list(_CFG.get('ROOTS', []))
    if _PROJECT_DATA:                       # the project's data tree, from config.py
        r.append(_PROJECT_DATA)
    # HERE first: a `data/` tree shipped inside the package resolves with no
    # setting at all, and from any working directory.
    r += [HERE, os.path.join(HERE, 'data'), os.path.join(HERE, '..', 'data'),
          os.path.join(HERE, '..'), os.getcwd()]
    seen, out = set(), []
    for p in r:
        p = os.path.abspath(p)
        if p not in seen and os.path.isdir(p):
            seen.add(p); out.append(p)
    return out

ROOTS = _search_roots()
_MAXDEPTH = int(os.environ.get('MAI_SEARCH_DEPTH', 6))
_WHERE = {}          # key -> how it was resolved, for check_inputs()

def _resolve(key, *relpaths):
    """Find one input. Returns a path, existing or not; _WHERE records how."""
    if key in _CFG:
        _WHERE[key] = 'paths.json'
        return _CFG[key]
    env = os.environ.get(f'MAI_{key}')
    if env:
        _WHERE[key] = f'$MAI_{key}'
        return env
    for root in ROOTS:
        for rel in relpaths:
            p = os.path.join(root, rel)
            if os.path.exists(p):
                _WHERE[key] = f'{root} + {rel}'
                return p
    base = os.path.basename(relpaths[0])
    for root in ROOTS:
        for depth in range(1, _MAXDEPTH + 1):
            hits = _glob.glob(os.path.join(root, *(['*'] * (depth - 1)), base))
            if hits:
                _WHERE[key] = f'found by name under {root}'
                return sorted(hits)[0]
    _WHERE[key] = 'NOT FOUND'
    return os.path.join(ROOTS[0] if ROOTS else '.', relpaths[0])


# Each input lists the relative paths it is known by. The first is canonical.
PANEL      = _resolve('PANEL', 'derived/periodict_act.csv', 'MAI_AFG/derived/periodict_act.csv')
ACT_ALL    = _resolve('ACT_ALL', 'data/afg_periodic_markets_20260213/forAFG_paper_activity_all.csv',
                      'MAI_AFG/data/afg_periodic_markets_20260213/forAFG_paper_activity_all.csv')
MKT_ACC    = _resolve('MKT_ACC', 'derived/mkt_access.csv', 'MAI_AFG/derived/mkt_access.csv')
# The control panel is the raw source. `derived/taliban_control.csv` is the same
# table with a province column and a merge indicator bolted on; the code reads
# only date, district_id and status, on which the two are identical, so the
# derived copy is not shipped and CONTROL points at the raw file.
CONTROL    = _resolve('CTRL_PANEL', 'data/taliban control/control_panel.csv',
                      'taliban control/control_panel.csv',
                      'MAI_AFG/data/taliban control/control_panel.csv')
BUF_BNR    = _resolve('BUF_BNR', 'data/afg_markets_10km_buffer_VIIRS_stats/markets_VIIRS_stats_10km_buffer_bnr.csv',
                      'MAI_AFG/data/afg_markets_10km_buffer_VIIRS_stats/markets_VIIRS_stats_10km_buffer_bnr.csv')
BUF_BNR_X  = _resolve('BUF_BNR_X', 'data/Geospatial Analysis Outputs/missing_markets_VIIRS_BNR_stats_10km_buffer.csv',
                      'MAI_AFG/data/Geospatial Analysis Outputs/missing_markets_VIIRS_BNR_stats_10km_buffer.csv')
NTL_ADU    = _resolve('NTL_ADU', 'data/raw_nightlights_ADU/NTL_ADU2.xlsx',
                      'MAI_AFG/data/raw_nightlights_ADU/NTL_ADU2.xlsx')
ADM1       = _resolve('ADM1', 'data/ADM1_Prov_2017_NSIA/ADM1_Prov_2017_NSIA.shp',
                      'MAI_AFG/data/ADM1_Prov_2017_NSIA/ADM1_Prov_2017_NSIA.shp')
ADM2       = _resolve('ADM2', 'data/ADM2_Dist_2024/ADM2_Dist_2024.shp',
                      'MAI_AFG/data/ADM2_Dist_2024/ADM2_Dist_2024.shp')
ACLED      = _resolve('ACLED', 'data/ACLED/ACLED_Conflict_Events.csv',
                      'MAI_AFG/data/ACLED/ACLED_Conflict_Events.csv')
GEOJSON    = _resolve('GEOJSON', 'data/taliban control/districts.geojson',
                      'MAI_AFG/data/taliban control/districts.geojson')
CTRL_PANEL = _resolve('CTRL_PANEL', 'data/taliban control/control_panel.csv',
                      'MAI_AFG/data/taliban control/control_panel.csv')
PROX50K    = _resolve('PROX50K', 'data/ProximityToSettlements/afg_markets_distance_to_closest_50k_pop_settlement.xls',
                      'MAI_AFG/data/ProximityToSettlements/afg_markets_distance_to_closest_50k_pop_settlement.xls')
MACRO      = _resolve('MACRO', 'data_external/macro/macro_series.xlsx',
                      'replication/data_external/macro/macro_series.xlsx')
POP_LONG   = _resolve('POP_LONG', 'data_external/population/AFG_Population_Long_Format.csv',
                      'replication/data_external/population/AFG_Population_Long_Format.csv')
NTL_DIST   = _resolve('NTL_DIST', 'data_external/nightlights/monthly_summary_stats_adm2_2014_2024.xlsx',
                      'replication/data_external/nightlights/monthly_summary_stats_adm2_2014_2024.xlsx')
NDVI_MKT   = _resolve('NDVI_MKT', 'data_external/ndvi/NDVI_markted.csv',
                      'replication/data_external/ndvi/NDVI_markted.csv')

DATA   = os.path.dirname(os.path.dirname(NTL_ADU))    # kept for backwards compatibility
DERIV  = os.path.dirname(PANEL)

TARGET     = 'activity_area_norm2020'    # activity normalised to each market's 2020 level
# Trading days supplied by the authors for markets the registry leaves blank.
# Weekdays are 0 = Sunday ... 6 = Saturday, matching the panel's own coding.
# Every one of these is corroborated by weekdayThisAreaIsActive on the market's
# own mktDay == 1 rows, except HERAT_MKT: the data there flags Monday AND
# Thursday, and the authors supplied Monday, which is what the package uses.
SUPPLIED_DAYS = {
    'lon62_5018lat34_2416': {1},          # Hirat        Monday
    'lon63_7803lat35_731':  {2, 3, 6},    # Badghis      Tuesday, Wednesday, Saturday
    'lon69_3316lat35_0459': {6},          # Kapisa       Saturday
    'lon70_3678lat34_8331': {4},          # Laghman      Thursday
}
HERAT_MKT  = 'lon62_5018lat34_2416'      # absent from the published derived file
HERAT_DAY  = 1                           # kept for backwards compatibility


def _daystr(days):
    """Render a set of weekday numbers the way the registry's marketDays does."""
    return '{' + ', '.join(f"'{d}'" for d in sorted(days)) + '}'

# Reference fixtures SHIPPED WITH THE PACKAGE. verify.py compares the values this
# package computes against these, so the cross-check means the same thing on
# every machine. They are not inputs: no figure or table reads them.
REF_NDVI_LVL = os.path.join(REFERENCE, 'ndvi_levels.csv')
REF_NTL_NAT  = os.path.join(REFERENCE, '04_ntl_national.csv')
REF_STAGGER  = os.path.join(REFERENCE, 'staggering_test.csv')
REF_POPPY    = os.path.join(REFERENCE, 'mai_poppy_splits.csv')

# --------------------------------------------------------------- shared constants
# The palette, sizes and fonts are in style.py; importing it applies the house style.
import style as _style  # noqa: F401
YEARS = list(range(2018, 2026))
REGIONS = _style.REGIONS
RNAME = _style.REGION_NAME

def save(fig, name, folder=None):
    """Save a figure as PNG. Paper exhibits pass folder=PAPER (see save_paper)."""
    p = f'{folder or OUT}/{name}.png'
    fig.savefig(p, dpi=300, bbox_inches='tight'); plt.close(fig)
    print(f'   saved {name}.png')
    return p


def save_paper(fig, name):
    """Save one of the paper's figures to the shared paper_exhibits folder."""
    return save(fig, name, folder=PAPER)


def save_paper_table(T, name, index=False):
    """Save one of the paper's tables, as laid out in the paper, to paper_exhibits."""
    p = f'{PAPER}/{name}.csv'
    T.to_csv(p, index=index, encoding='utf-8-sig')
    print(f'   saved {name}.csv')
    return p


# 2026 WFP field validation, one row per visited market (135 of the 137; the two
# Baghlan markets were not visited). Sheet "Market list" carries the day-match
# classification used by Table 1, Table 2 and Figure A.1.
WFP = (os.path.join(_project.DATA, 'WFP_validation', 'market_validation_corrected.xlsx')
       if _PROJECT_DATA else _resolve('WFP', 'WFP_validation/market_validation_corrected.xlsx'))


def wfp_validation():
    return pd.read_excel(WFP, sheet_name='Market list')

# --------------------------------------------------------------- shared builders
def panel(include_herat=True):
    """The market-day activity panel.

    The published derived file holds 136 markets. A 137th detected market,
    HERAT_MKT, is absent because the registry records no trading weekday for it.
    With include_herat=True its rows are rebuilt from the raw activity file on
    the day the authors supplied and appended, giving the paper's 137 markets.
    Its imagery ends in 2024, so it contributes nothing to 2025.

    Three markets that ARE in the published file have a blank registry entry:
    Badghis lon63_7803lat35_731, Kapisa lon69_3316lat35_0459 and Laghman
    lon70_3678lat34_8331. Their trading days are filled in from SUPPLIED_DAYS,
    so every market in the returned panel carries a marketDays value. Anything
    keyed on trading day - the day-of-operation figure, the staggering test, the
    frequency pairs - therefore covers all 137 markets rather than 133.
    """
    p = pd.read_csv(PANEL, low_memory=False)
    fill = p.mktID.map({k: _daystr(v) for k, v in SUPPLIED_DAYS.items()})
    p['marketDays'] = p.marketDays.where(p.marketDays.notna(), fill)
    if not include_herat:
        return p
    raw = pd.read_csv(ACT_ALL, low_memory=False).rename(columns={'Location': 'mktID'})
    h = raw[raw.mktID == HERAT_MKT].copy()
    if not len(h):
        return p
    d = pd.to_datetime(h.date, format='mixed')
    h['year'] = d.dt.year; h['month'] = d.dt.month
    h['quarter'] = (h.month - 1) // 3 + 1
    h['week'] = d.dt.isocalendar().week.astype(int)
    h['weekday'] = (d.dt.dayofweek + 1) % 7          # 0 = Sunday, as in the panel
    hd = SUPPLIED_DAYS[HERAT_MKT]
    h['mktDay'] = h.weekday.isin(hd).astype(int)
    h = h[h.mktDay == 1]                              # the panel holds market days only
    h['marketDays'] = _daystr(hd)
    for c in p.columns:
        if c not in h.columns:
            h[c] = np.nan
    h['mktID'] = HERAT_MKT
    for c, v in [('admLvl1', 'Hirat'), ('un_region', 'West'), ('un_region_small', 'West')]:
        h[c] = v
    return pd.concat([p, h[p.columns]], ignore_index=True)

def mai_series(d, label='mai', by=None):
    """The published nested-mean cascade: market-week, normalise each market to its
    own 2020 mean, then mean across markets within year-month, quarter, year."""
    s = d.copy()
    s['aw'] = s.groupby(['mktID', 'year', 'month', 'week'])[TARGET].transform('mean')
    s = s.drop_duplicates(subset=['mktID', 'year', 'month', 'week'])
    avg = s[s.year == 2020].groupby('mktID').aw.mean()
    s['n'] = 100 * s.aw / s.mktID.map(avg)
    if by:                                    # optional intermediate grouping level
        s['n'] = s.groupby([by, 'year', 'month']).n.transform('mean')
        s = s.drop_duplicates(subset=[by, 'year', 'month'])
    s['n'] = s.groupby(['year', 'month']).n.transform('mean')
    s = s.drop_duplicates(subset=['year', 'month'])
    s['n'] = s.groupby(['year', 'quarter']).n.transform('mean')
    s = s.drop_duplicates(subset=['year', 'quarter'])
    return s.groupby('year').n.mean().rename(label)

def market_year_activity(d):
    """One activity value per market-year, same cascade truncated at the market."""
    return (d.groupby(['mktID', 'year', 'quarter', 'month', 'week'])[TARGET].mean().reset_index()
             .groupby(['mktID', 'year', 'quarter', 'month'])[TARGET].mean().reset_index()
             .groupby(['mktID', 'year', 'quarter'])[TARGET].mean().reset_index()
             .groupby(['mktID', 'year'])[TARGET].mean().unstack())

def buffer_ntl(months=range(1, 13), markets=None, stat='mean'):
    """Nightlights inside the 10 km market buffers, background-noise-removed.
    Both source files are read; a market with no signal enters as zero."""
    a = pd.read_csv(BUF_BNR, encoding='utf-8-sig')
    b = pd.read_csv(BUF_BNR_X, encoding='utf-8-sig')
    N = pd.concat([a, b], ignore_index=True).drop_duplicates('mktID')
    if markets is not None:
        N = N[N.mktID.isin(markets)]
    sc = [c for c in N.columns if c.startswith('SUM_') and not c.endswith('_UF')]
    L = N[['mktID'] + sc].melt(id_vars='mktID', var_name='ym', value_name='v')
    L['year'] = L.ym.str[4:8].astype(int); L['month'] = L.ym.str[8:10].astype(int)
    L = L[L.year.isin(YEARS) & L.month.isin(list(months))]
    my = L.groupby(['mktID', 'year']).v.agg(stat).unstack('year')
    if markets is not None:
        my = my.reindex(sorted(markets))
    return my.fillna(0)

def access_categories():
    """The paper's three access categories: travel time to a 50k+ settlement and
    catchment population within thirty minutes."""
    pa = panel().drop_duplicates('mktID')[['mktID', 'admLvl1', 'un_region', 'wp_SUM',
                                           'marketlat', 'marketlon']]
    acc = pd.read_csv(MKT_ACC)
    m = pa.merge(acc, on='mktID', how='left')
    m['access'] = np.where(m.travel_50 > 40, 'Remote',
                    np.where(m.wp_SUM >= 250_000, 'High access', 'Intermediate access'))
    return m


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in km."""
    a1, b1, a2, b2 = map(np.radians, [lat1, lon1, lat2, lon2])
    return 2 * 6371 * np.arcsin(np.sqrt(
        np.sin((a2 - a1) / 2) ** 2 + np.cos(a1) * np.cos(a2) * np.sin((b2 - b1) / 2) ** 2))


def market_index():
    """Per-market activity index, each market's own 2020 = 100."""
    mm = market_year_activity(panel())
    return 100 * mm.div(mm[2020], axis=0)


def frequency_pairs(max_km=30):
    """Neighbouring pairs made of one once-a-week market and one that trades more
    often. Returns a frame with one row per pair."""
    import re
    mk = panel().drop_duplicates('mktID')[['mktID', 'marketlat', 'marketlon', 'marketDays']].copy()
    mk['ndays'] = mk.marketDays.apply(lambda x: len(set(re.findall(r'\d+', str(x)))))
    mk = mk[mk.ndays > 0].reset_index(drop=True)
    once = mk[mk.ndays == 1]; more = mk[mk.ndays > 1]
    rows = []
    for _, o in once.iterrows():
        d = haversine(o.marketlat, o.marketlon, more.marketlat.values, more.marketlon.values)
        for j, km in zip(more.mktID.values[d <= max_km], d[d <= max_km]):
            rows.append({'once': o.mktID, 'twice': j, 'km': km})
    return pd.DataFrame(rows)


def district_control_2020():
    """Every district with its control status on 21 October 2020, its province and
    its population by year.

    21 October 2020 is the last pre-transition observation. The panel also holds a
    2020-07-08 reading; the two are identical for every district, so the 2020
    classification is unambiguous. Districts are matched to the control geometry by
    representative point, which resolves all 401 districts of the 2024 boundary
    file. (The original version of this exhibit lost ten districts holding 1.8
    percent of the national population to an unmatched join; that gap is closed
    here, so the group populations differ slightly from the earlier note.)
    """
    import geopandas as gpd
    d2 = gpd.read_file(ADM2)[['Pcode_24', 'Prov_name', 'geometry']]
    cd = gpd.read_file(GEOJSON)[['district_id', 'geometry']]
    cen = d2.copy(); cen['geometry'] = cen.geometry.representative_point()
    j = gpd.sjoin(cen, cd, how='left', predicate='within')
    j = j[~j.index.duplicated(keep='first')]

    ctl = pd.read_csv(CTRL_PANEL)
    ctl['date'] = pd.to_datetime(ctl.date, errors='coerce')
    days = sorted(ctl.loc[ctl.date.dt.year == 2020, 'date'].unique())
    wide = ctl[ctl.date.isin(days)].pivot_table(index='district_id', columns='date',
                                                values='status', aggfunc='first')
    assert wide.nunique(axis=1).max() == 1, '2020 control readings disagree'
    st = wide.iloc[:, -1]                      # the last pre-transition observation

    D = d2.drop(columns='geometry').copy()
    D['status'] = j.district_id.map(st).values
    D['status'] = D.status.str.replace(' Control', '-held', regex=False)
    D = D.dropna(subset=['status'])

    pop = pd.read_csv(POP_LONG, encoding='utf-8-sig')
    pw = pop.groupby(['adm2_pcode', 'year'], as_index=False).population.sum()
    D = D.merge(pw[pw.year.isin(YEARS)], left_on='Pcode_24', right_on='adm2_pcode', how='left')
    return D.drop(columns='adm2_pcode')


def ntl_per_capita_by_control(months=range(2, 7)):
    """Civilian nightlights per person by 2020 district control status.

    Nightlights exist only at province level, so each province's February-to-June
    civilian composite is split across the three statuses in proportion to the
    population living under each status WITHIN that province, with the allocation
    weights fixed at 2020. Differences between groups therefore reflect variation
    between provinces, not within them. February to June is the window available in
    every year. Returns (per-capita levels, group populations).
    """
    D = district_control_2020()
    w = D[D.year == 2020].groupby(['Prov_name', 'status']).population.sum()
    w = (w / w.groupby('Prov_name').transform('sum')).rename('w').reset_index()

    n = pd.read_excel(NTL_ADU)
    n = n[n.month.isin(list(months)) & n.year.isin(YEARS)]
    prov = n.groupby(['province', 'year'], as_index=False).civilian_coalition.sum()

    a = prov.merge(w, left_on='province', right_on='Prov_name', how='inner')
    assert a.province.nunique() == prov.province.nunique(), 'a province lost its allocation'
    a['rad'] = a.civilian_coalition * a.w
    rad = a.groupby(['status', 'year']).rad.sum().unstack('status')
    popg = D.groupby(['status', 'year']).population.sum().unstack('status')
    return (rad / popg).reindex(YEARS), popg.reindex(YEARS)


# ---------------------------------------------------------------- derived inputs
# Three quantities used to be read from files produced elsewhere in the wider
# repository (`staggering_test.csv`, `ndvi_levels.csv`, `04_ntl_national.csv`).
# They are computed here instead, so this package depends only on raw inputs.
# Each function checks itself against the stored file when that file is present.

def ntl_national(months=range(2, 7)):
    """National civilian nightlights by year, summed over the given months.
    Reproduces the shipped reference/04_ntl_national.csv exactly."""
    n = pd.read_excel(NTL_ADU)
    n = n[n.month.isin(list(months)) & n.year.isin(YEARS)]
    return n.groupby('year').civilian_coalition.sum().rename('civilian_feb_jun')


def ndvi_levels(quarter=2, base=range(2012, 2026)):
    """National growing-season NDVI by year, standardised across years.

    The market-catchment zonal means for the chosen quarter are averaged across
    the 136 markets of the published derived file, then the resulting national
    series is standardised over `base` (sample standard deviation). Reproduces
    ndvi_levels.csv exactly.
    """
    nd = pd.read_csv(NDVI_MKT)
    keep = set(panel(include_herat=False).mktID)
    q = nd[(nd.quarter == quarter) & nd.mktID.isin(keep)]
    nat = q.groupby('year').ndvi_mean.mean()
    w = nat.reindex([y for y in base if y in nat.index]).dropna()
    return ((nat - w.mean()) / w.std(ddof=1)).rename(f'Q{quarter}')


# The threshold grid starts at 5 km. Below that the pair count collapses (three
# pairs at 2 km), so the share is dominated by sampling noise and the null band
# spans the whole unit interval; including those points stretches the axis and
# flattens the 5-30 km range where the result actually lives.
STAGGER_GRID = list(range(5, 31))


def staggering_test(thresholds=STAGGER_GRID, n_perm=5000, seed=0, legacy=False):
    """Do neighbouring markets avoid trading on the same day?

    For each distance threshold, take every unordered pair of markets within that
    great-circle distance and compute the share of pairs whose trading days
    overlap on at least one weekday. The null shuffles the observed weekday sets
    across market locations, preserving the national frequency of each weekday and
    each market's number of trading days. Returns one row per threshold with the
    observed share, the null mean, the 5th and 95th percentiles and a one-sided
    p-value (the share of permutations at or below the observed value).

    Runs on every market with a known trading day: 136 once the three blank
    registry entries are filled from SUPPLIED_DAYS, against the 133 the
    manuscript reported. Pass legacy=True for the original 133-market
    configuration, which uses registry days only; that is what verify.py checks
    against reference/staggering_test.csv.

    Pass thresholds=range(2, 31) for the full grid: the manuscript's grid omits
    3 and 4 km, and this one also omits 2 km (see STAGGER_GRID). `obs`,
    `null_mean`, `lo` and `hi` are SHARES, not percentages.
    """
    import re as _re
    pa = panel(include_herat=False).drop_duplicates('mktID')
    if legacy:
        raw = pd.read_csv(PANEL, low_memory=False).drop_duplicates('mktID')
        pa = pa.assign(marketDays=pa.mktID.map(raw.set_index('mktID').marketDays))
    days = pa.marketDays.apply(lambda x: {int(v) for v in _re.findall(r'\d+', str(x))})
    keep = days.apply(len) > 0
    lat, lon = pa.marketlat[keep].values, pa.marketlon[keep].values
    sets = list(days[keep])
    n = len(sets)
    masks = np.array([sum(1 << d for d in s) for s in sets])      # weekdays as a bitmask
    iu = np.triu_indices(n, 1)
    dist = haversine(lat[:, None], lon[:, None], lat[None, :], lon[None, :])[iu]
    i, j = iu

    rng = np.random.RandomState(seed)
    perms = np.array([rng.permutation(n) for _ in range(n_perm)])
    overlap_obs = (masks[i] & masks[j]) > 0
    overlap_null = (masks[perms[:, i]] & masks[perms[:, j]]) > 0   # n_perm x n_pairs

    rows = []
    for thr in thresholds:
        m = dist <= thr
        if not m.any():
            continue
        obs = overlap_obs[m].mean()
        null = overlap_null[:, m].mean(axis=1)
        rows.append({'thr': thr, 'pairs': int(m.sum()), 'obs': obs,
                     'null_mean': null.mean(),
                     'lo': np.percentile(null, 5), 'hi': np.percentile(null, 95),
                     'p': (null <= obs).mean()})
    return pd.DataFrame(rows)


# --------------------------------------------------------------- input manifest
INPUTS = {
    'PANEL':      (PANEL,      'market-day activity panel, 136 markets'),
    'ACT_ALL':    (ACT_ALL,    'all-days activity file; source of the 137th market and of fig17'),
    'MKT_ACC':    (MKT_ACC,    'travel time and catchment population per market'),
    'BUF_BNR':    (BUF_BNR,    'VIIRS 10 km market buffers, background-noise-removed'),
    'BUF_BNR_X':  (BUF_BNR_X,  'the buffer markets missing from the file above'),
    'NTL_ADU':    (NTL_ADU,    'province monthly nightlights, civilian and coalition components'),
    'ADM1':       (ADM1,       'province boundaries carrying the CSO_Region field'),
    'ADM2':       (ADM2,       'district boundaries'),
    'ACLED':      (ACLED,      'ACLED conflict events'),
    'GEOJSON':    (GEOJSON,    'district geometries keyed to the control panel'),
    'CTRL_PANEL': (CTRL_PANEL, 'district control panel'),
    'PROX50K':    (PROX50K,    'road distance from each market to the nearest 50,000+ settlement'),
    'MACRO':      (MACRO,      'national accounts, agricultural and total real GDP'),
    'POP_LONG':   (POP_LONG,   'district population, long format'),
    'NTL_DIST':   (NTL_DIST,   'district monthly nightlights'),
    'NDVI_MKT':   (NDVI_MKT,   'market-catchment NDVI zonal statistics, quarterly'),
}

# Fixtures shipped inside the package. verify.py checks the computed values
# against these; no figure or table reads them.
REFERENCE_FILES = {
    'REF_NDVI_LVL': (REF_NDVI_LVL, 'national growing-season NDVI levels, for cross-checking ndvi_levels()'),
    'REF_NTL_NAT':  (REF_NTL_NAT,  'national civilian nightlights, for cross-checking ntl_national()'),
    'REF_STAGGER':  (REF_STAGGER,  'staggering permutation test, for cross-checking staggering_test()'),
    'REF_POPPY':    (REF_POPPY,    'published Hilmand and poppy-province index splits'),
}


def check_inputs(verbose=True):
    """Report which inputs resolved and how. Returns the list of missing keys."""
    missing = []
    if verbose:
        print(f'  search roots: {", ".join(ROOTS)}')
    for k, (p, what) in INPUTS.items():
        ok = os.path.exists(p)
        if not ok:
            missing.append(k)
        if verbose:
            print(f'  {"OK " if ok else "MISSING"}  {k:<11} {what}')
            print(f'{"":13}{p}   [{_WHERE.get(k, "?")}]')
    if verbose:
        print('  -- reference fixtures shipped with the package --')
        for k, (p, what) in REFERENCE_FILES.items():
            print(f'  {"OK " if os.path.exists(p) else "absent "}  {k:<13} {what}')
    if verbose and missing:
        print(f'\n{len(missing)} required input(s) not found. Point MAI_ROOT at the data tree,')
        print('or list explicit paths in paths.json beside common.py. Example:')
        print('  {"ROOTS": ["/data/mai"], "PANEL": "/elsewhere/periodict_act.csv"}')
    return missing


if __name__ == '__main__':
    check_inputs()
