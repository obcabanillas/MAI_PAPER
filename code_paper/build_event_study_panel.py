"""
Build the analysis-ready event-study panel and write it to processed_data/.

Run this once, after the NTL_processing scripts. Results_paper.ipynb then
loads the panel it writes and needs none of the heavy raw inputs below.

Outputs
-------
processed_data/event_study_panel.dta   137 markets x 8 years (2018-2025), with
processed_data/event_study_panel.csv   the outcome variables, the three
                                       baseline market characteristics, the two
                                       time-varying controls, the district
                                       cluster id, and the two NTL sample flags
                                       (always-lit n=52, ever-lit n=107).

Inputs
------
processed_data/ntl_bnr_periodic137_8years.csv   (from NTL_processing/06_)
document/Repo_09042026/data/...                 market activity, ACLED, NDVI,
                                                population, district shapefile
"""
import os
import re
import sys

import numpy as np
import pandas as pd

# fiona >= 1.10 no longer imports this submodule eagerly, but geopandas 0.13
# reaches for fiona.path when opening a file. Import it before geopandas.
import fiona
import fiona.path  # noqa: F401
import geopandas as gpd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "NTL_processing"))
from config import DATA, PROCESSED, REPO_DATA  # noqa: E402

YEARS = list(range(2018, 2026))
TARGET = "activity_area_norm2020"

# Markets whose trading days are known but missing from the registry file.
SUPPLIED_DAYS = {
    'lon62_5018lat34_2416': {1},
    'lon63_7803lat35_731':  {2, 3, 6},
    'lon69_3316lat35_0459': {6},
    'lon70_3678lat34_8331': {4},
}
HERAT_MKT = 'lon62_5018lat34_2416'

# Conflict channels counted in the district-year death rate.
IED = {'Remote explosive/landmine/IED'}
GATHER = {'Air/drone strike', 'Shelling/artillery/missile attack', 'Attack',
          'Suicide bomb', 'Grenade'}
CLASH = {'Armed clash'}
CHANNELS = IED | GATHER | CLASH


def _daystr(days):
    return '{' + ', '.join(f"'{d}'" for d in sorted(days)) + '}'


def build_panel():
    """Reimplements common.panel(include_herat=True) without the matplotlib
    import that common.py otherwise requires."""
    p = pd.read_csv(os.path.join(REPO_DATA, 'derived', 'periodict_act.csv'), low_memory=False)
    fill = p.mktID.map({k: _daystr(v) for k, v in SUPPLIED_DAYS.items()})
    p['marketDays'] = p.marketDays.where(p.marketDays.notna(), fill)
    raw = pd.read_csv(os.path.join(REPO_DATA, 'afg_periodic_markets_20260213',
                                   'forAFG_paper_activity_all.csv'), low_memory=False)
    raw = raw.rename(columns={'Location': 'mktID'})
    h = raw[raw.mktID == HERAT_MKT].copy()
    d = pd.to_datetime(h.date, format='mixed')
    h['year'] = d.dt.year
    h['month'] = d.dt.month
    h['quarter'] = (h.month - 1) // 3 + 1
    h['week'] = d.dt.isocalendar().week.astype(int)
    h['weekday'] = (d.dt.dayofweek + 1) % 7
    hd = SUPPLIED_DAYS[HERAT_MKT]
    h['mktDay'] = h.weekday.isin(hd).astype(int)
    h = h[h.mktDay == 1]
    h['marketDays'] = _daystr(hd)
    for c in p.columns:
        if c not in h.columns:
            h[c] = np.nan
    h['mktID'] = HERAT_MKT
    for c, v in [('admLvl1', 'Hirat'), ('un_region', 'West'), ('un_region_small', 'West')]:
        h[c] = v
    return pd.concat([p, h[p.columns]], ignore_index=True)


def market_year_activity(d):
    """Nested means: day -> week -> month -> quarter -> year, so no month or
    quarter is over-weighted because it happened to contain more market days."""
    return (d.groupby(['mktID', 'year', 'quarter', 'month', 'week'])[TARGET].mean().reset_index()
             .groupby(['mktID', 'year', 'quarter', 'month'])[TARGET].mean().reset_index()
             .groupby(['mktID', 'year', 'quarter'])[TARGET].mean().reset_index()
             .groupby(['mktID', 'year'])[TARGET].mean().unstack())


def haversine(lat1, lon1, lat2, lon2):
    a1, b1, a2, b2 = map(np.radians, [lat1, lon1, lat2, lon2])
    return 2 * 6371 * np.arcsin(np.sqrt(
        np.sin((a2 - a1) / 2) ** 2 + np.cos(a1) * np.cos(a2) * np.sin((b2 - b1) / 2) ** 2))


# ---------------------------------------------------------------- 1. markets
print("Loading market activity panel...")
pnl = build_panel()
mk = pnl.drop_duplicates('mktID')[['mktID', 'admLvl1', 'un_region', 'wp_SUM',
                                   'marketlat', 'marketlon', 'marketDays']].copy()
assert len(mk) == 137, f"expected 137 periodic markets, got {len(mk)}"

mk['once_a_week'] = mk.marketDays.apply(
    lambda x: 1 if len({int(v) for v in re.findall(r'\d+', str(x))}) == 1 else 0)
mk['log_pop'] = np.log(mk.wp_SUM)

osm = pd.read_csv(os.path.join(DATA, 'osm_markets_nearest_detected_distance.csv'))
osm_lat, osm_lon = osm.osm_lat.to_numpy(), osm.osm_lon.to_numpy()
mk['dist_osm'] = [haversine(lat, lon, osm_lat, osm_lon).min()
                  for lat, lon in zip(mk.marketlat, mk.marketlon)]
print(f"  baseline characteristics built for {len(mk)} markets")

# ---------------------------------------------------------------- 2. districts
print("Joining markets to districts...")
d2 = gpd.read_file(os.path.join(REPO_DATA, 'ADM2_Dist_2024', 'ADM2_Dist_2024.shp'))
d2 = d2[['Pcode_24', 'Dist_ID_24', 'Prov_name', 'geometry']]
gp = gpd.GeoDataFrame(mk, geometry=gpd.points_from_xy(mk.marketlon, mk.marketlat), crs='EPSG:4326')
j = gpd.sjoin(gp, d2, how='left', predicate='within')
j = j[~j.index.duplicated(keep='first')]
mk['Pcode_24'] = j.Pcode_24.values
print(f"  {mk.Pcode_24.isna().sum()} unmatched; {mk.Pcode_24.nunique()} distinct districts")

# ---------------------------------------------------------------- 3. conflict
print("Building district-year conflict deaths...")
a = pd.read_csv(os.path.join(REPO_DATA, 'ACLED', 'ACLED_Conflict_Events.csv'), low_memory=False)
a['event_date'] = pd.to_datetime(a.event_date, format='mixed')
a['year'] = a.event_date.dt.year
a = a[a.sub_event_.isin(CHANNELS) & a.year.isin(YEARS)]
ag = gpd.GeoDataFrame(a, geometry=gpd.points_from_xy(a.longitude, a.latitude), crs='EPSG:4326')
aj = gpd.sjoin(ag, d2[['Pcode_24', 'geometry']], how='left', predicate='within')
aj = aj[~aj.index.duplicated(keep='first')].dropna(subset=['Pcode_24'])
deaths_dy = aj.groupby(['Pcode_24', 'year']).fatalities.sum().rename('deaths')

pop_path = next(p for p in [
    os.path.join(REPO_DATA, 'population', 'AFG_Population_Long_Format.csv'),
    os.path.join(DATA, 'population', 'AFG_Population_Long_Format.csv'),
] if os.path.exists(p))
pop = pd.read_csv(pop_path, encoding='utf-8-sig')
pw = (pop.groupby(['adm2_pcode', 'year'], as_index=False).population.sum()
        .rename(columns={'adm2_pcode': 'Pcode_24'}).set_index(['Pcode_24', 'year']).population)

dy = pd.DataFrame(index=pd.MultiIndex.from_product(
    [mk.Pcode_24.dropna().unique(), YEARS], names=['Pcode_24', 'year'])).reset_index()
dy['deaths'] = dy.set_index(['Pcode_24', 'year']).index.map(deaths_dy).fillna(0).to_numpy()
dy['population'] = dy.set_index(['Pcode_24', 'year']).index.map(pw).to_numpy()
dy['deaths_pc'] = 1e5 * dy.deaths / dy.population
dy['log_deaths_pc'] = np.log1p(dy.deaths_pc)
print(f"  district-years: {len(dy)}, missing population: {dy.population.isna().sum()}")

# ---------------------------------------------------------------- 4. NDVI
print("Building growing-season (Q2) NDVI deviation...")
ndvi_path = next(p for p in [
    os.path.join(REPO_DATA, 'ndvi', 'NDVI_markted.csv'),
    os.path.join(DATA, 'ndvi', 'NDVI_markted.csv'),
] if os.path.exists(p))
nd = pd.read_csv(ndvi_path, low_memory=False)
nd = nd[nd.quarter == 2].copy()
nd['ndvi_dev'] = (nd.ndvi_mean - nd.ndvi_mean_long_term) / nd.ndvi_std_long_term
ndvi_my = nd.set_index(['mktID', 'year']).ndvi_dev

# ---------------------------------------------------------------- 5. outcomes
print("Market-year activity index (Model A outcome)...")
mm = market_year_activity(pnl)
idx = 100 * mm.div(mm[2020], axis=0)
act_long = idx.stack().rename('y_activity').reset_index().rename(columns={'level_1': 'year'})

print("Nighttime lights (Model B outcome) from processed_data...")
bnr = pd.read_csv(os.path.join(PROCESSED, 'ntl_bnr_periodic137_8years.csv'), low_memory=False)
bnr = bnr.rename(columns={'orig_id': 'mktID'})
assert len(bnr) == 137 and bnr.mktID.is_unique
mean_cols = {y: sorted(c for c in bnr.columns if c.startswith(f'MEAN_BNR_{y}')) for y in YEARS}
for y in YEARS:
    assert len(mean_cols[y]) == 12, f"{y}: expected 12 monthly MEAN_BNR columns"

rows = []
for y in YEARS:
    mcols = mean_cols[y]
    feb_jun = [c for c in mcols if c[-2:] in ('02', '03', '04', '05', '06')]
    rows.append(pd.DataFrame({
        'mktID': bnr.mktID, 'year': y,
        'annual_mean_bnr': bnr[mcols].mean(axis=1).to_numpy(),
        'feb_jun_median_bnr': bnr[feb_jun].median(axis=1).to_numpy(),
    }))
ntl_my = pd.concat(rows, ignore_index=True)
ntl_my['log_feb_jun_bnr'] = np.log(ntl_my.feb_jun_median_bnr.where(ntl_my.feb_jun_median_bnr > 0))
print(f"  {(ntl_my.feb_jun_median_bnr <= 0).sum()} of {len(ntl_my)} market-years are dark")

always = ntl_my.groupby('mktID').annual_mean_bnr.apply(lambda s: (s > 0).all())
ever = ntl_my.groupby('mktID').annual_mean_bnr.apply(lambda s: (s > 0).any())
lit_markets = sorted(always[always].index)
ever_lit_markets = sorted(ever[ever].index)
print(f"  always-lit: {len(lit_markets)}   ever-lit: {len(ever_lit_markets)}")

# ---------------------------------------------------------------- 6. assemble
print("Assembling the long panel...")
panel = act_long.merge(mk[['mktID', 'once_a_week', 'dist_osm', 'log_pop', 'Pcode_24']], on='mktID')
panel = panel.merge(dy[['Pcode_24', 'year', 'log_deaths_pc']], on=['Pcode_24', 'year'], how='left')
panel = panel.merge(ndvi_my.reset_index(), on=['mktID', 'year'], how='left')
panel = panel.merge(ntl_my, on=['mktID', 'year'], how='left')
panel = panel[panel.year.isin(YEARS)].copy()

panel['lit_market'] = panel.mktID.isin(lit_markets).astype('int8')
panel['ever_lit_market'] = panel.mktID.isin(ever_lit_markets).astype('int8')
panel['once_a_week'] = panel.once_a_week.astype('int8')
print(f"  panel: {panel.shape}, years {sorted(panel.year.unique())}")

VAR_LABELS = {
    'mktID': 'Market ID',
    'year': 'Year',
    'y_activity': 'Market activity index (2020=100), each market rescaled to own 2020',
    'once_a_week': 'Once-a-week trading day indicator',
    'dist_osm': 'Distance to nearest OSM market (km)',
    'log_pop': 'Log catchment population',
    'Pcode_24': 'District pcode (2024 boundaries)',
    'log_deaths_pc': 'Log district deaths per 100,000 (district-year)',
    'ndvi_dev': 'Growing-season NDVI deviation (SD units)',
    'annual_mean_bnr': 'Annual mean BNR-filtered radiance (10km buffer)',
    'feb_jun_median_bnr': 'Feb-Jun median BNR-filtered radiance (10km buffer)',
    'log_feb_jun_bnr': 'Log of Feb-Jun median BNR-filtered radiance',
    'lit_market': 'In always-lit sample (positive BNR every year 2018-2025)',
    'ever_lit_market': 'In ever-lit sample (positive BNR in at least one year 2018-2025)',
}

dta = os.path.join(PROCESSED, 'event_study_panel.dta')
csv = os.path.join(PROCESSED, 'event_study_panel.csv')
panel.to_stata(dta, write_index=False, variable_labels=VAR_LABELS, version=118)
panel.to_csv(csv, index=False)
print(f"wrote {dta}")
print(f"wrote {csv}")
print("DONE")
