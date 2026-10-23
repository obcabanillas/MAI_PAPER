"""The paper's tables. One function per table, laid out as in the paper.

Each returns (DataFrame of the rendered rows, dict of metadata). run_all.py writes
them to the shared paper_exhibits folder (config.PAPER_EXHIBITS) as CSV.

    PAPER EXHIBIT  FUNCTION                  FILE
    Table 1        table1_day_validation     table1_day_validation.csv
    Table 2        table2_goods_by_access    table2_goods_by_access.csv
    Table 3        table3_ndvi_marketday     table3_ndvi_marketday.csv
    Table A.1      tableA1_poppy             tableA1_poppy.csv

Tables that are not in the final paper (the older conflict-and-market-location
table and the regional coverage table) are in archive/exhibits/tables_full.py.
"""
import re
import common as CM
from common import pd, np
import statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats as _st
import geopandas as gpd

asinh = np.arcsinh
YRS = [2017, 2018]
# the market registry and the boundary files spell five provinces differently
PROV_ALIAS = {'Badghes': 'Badghis', 'Kunarha': 'Kunar', 'Nemroz': 'Nimroz',
              'Pakteka': 'Paktika', 'Maydanwardag': 'Wardak', 'Noristan': 'Nuristan'}
IED = {'Remote explosive/landmine/IED'}
GATHER = {'Air/drone strike', 'Shelling/artillery/missile attack', 'Attack',
          'Suicide bomb', 'Grenade'}
CLASH = {'Armed clash'}
ADM2 = CM.ADM2
ACLED = CM.ACLED
POP_LONG = CM.POP_LONG
NTL_DIST = CM.NTL_DIST
GEOJSON = CM.GEOJSON
CONTROL_PANEL = CM.CTRL_PANEL
NDVI_MKT = CM.NDVI_MKT


def _clus(formula, data, group):
    g = data[group]
    f = smf.ols(formula, data=data).fit(cov_type='cluster', cov_kwds={'groups': g}, use_t=True)
    G = g.nunique()
    f._p = {k: 2 * (1 - _st.t.cdf(abs(f.params[k] / f.bse[k]), G - 1)) for k in f.params.index}
    return f


def _star(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.10 else ''


def _pct(x):
    return f'{x:.0f}%'


# ============================================================ Table 1
WEEKDAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']     # panel coding 0 = Sunday


def _dayset(s):
    return set() if pd.isna(s) else {d.strip() for d in str(s).split(',') if d.strip()}


def table1_day_validation():
    """Table 1. Validation of satellite-detected trading days against field-reported
    schedules (2026 WFP field validation).

    Markets: the WFP day-match classification of the 135 visited markets, plus the
    two unvisited Baghlan markets, counted under "No trading day reported".
    Trading days: "Predicted (total)" counts MAI trading days (a two-day market adds
    2); "Field validated (share)" is the share of those days the field team also
    reported as trading days. Predicted days come from the WFP workbook's
    predicted_days column for visited markets and from the panel for the two
    unvisited ones. The total share leaves out the two NA rows (no field day to
    compare with); the total predicted count includes every market."""
    w = CM.wfp_validation()
    w['pred'] = w.predicted_days.apply(_dayset)
    w['field'] = w.field_days.apply(_dayset)
    mk = CM.panel().drop_duplicates('mktID').set_index('mktID')
    unvisited = sorted(set(mk.index) - set(w.mktID))
    add = pd.DataFrame({'mktID': unvisited,
                        'pred': [{WEEKDAY[int(v)] for v in re.findall(r'\d', str(mk.marketDays[m]))}
                                 for m in unvisited],
                        'field': [set() for _ in unvisited],
                        'day_match': 'No trading day reported'})
    t = pd.concat([w[['mktID', 'pred', 'field', 'day_match']], add], ignore_index=True)
    t['n_pred'] = t.pred.apply(len)
    t['n_val'] = t.apply(lambda r: len(r.pred & r.field), axis=1)
    g = t.groupby('day_match').agg(n=('mktID', 'size'), pred=('n_pred', 'sum'), val=('n_val', 'sum'))
    N = len(t)
    ROWS = [('Exact match', 'Complete day overlap', 'Exact match', True),
            ('', 'Continuously operating markets', 'Continuous bazaar, main day correct', True),
            ('Continuous operating market, no main day', '', 'Continuous bazaar, no main day named', False),
            ('Partial day overlap between MAI and field validation', '', 'Partial overlap', True),
            ('No market day overlap between MAI and field validation', '', 'Complete miss', True),
            ('No trading day reported', '', 'No trading day reported', None)]
    rows = []
    for a, b, key, has_field in ROWS:
        r = g.loc[key]
        pred = int(r.pred) if has_field is not False else 'NA'
        share = _pct(100 * r.val / r.pred) if has_field else 'NA'
        rows.append([a, b, int(r.n), _pct(100 * r.n / N), pred, share])
    keep = [k for _, _, k, f in ROWS if f]
    rows.append(['Total markets', '', N, '100%', int(g.pred.sum()),
                 _pct(100 * g.loc[keep, 'val'].sum() / g.loc[keep, 'pred'].sum())])
    T = pd.DataFrame(rows, columns=['Comparing MAI and field visit predicted trading days', '',
                                    'Markets: No.', 'Markets: Share (%)',
                                    'Trading days: Predicted (total)',
                                    'Trading days: Field validated (share)'])
    return T, dict(markets=N, predicted=int(g.pred.sum()))


# ============================================================ Table 2
ACC = ['High access', 'Intermediate access', 'Remote']
GOODS = {'Food only': 'Food only', 'Food and livestock, no general goods': 'Food and livestock',
         'Food and general goods, no livestock': 'Food and general goods',
         'All goods, unspecified': 'Food and general goods',
         'Food, livestock and general goods': 'Food, livestock and general goods',
         'Livestock only': 'Livestock only', 'General goods only': 'Car markets'}


def table2_goods_by_access():
    """Table 2. Market characteristics and field validation, for all markets and by
    access category. Goods categories from the 2026 WFP field validation (mutually
    exclusive); trading frequency from the satellite-identified schedule."""
    acc = CM.access_categories().set_index('mktID')
    w = CM.wfp_validation().set_index('mktID')
    T = acc[['access']].join(w[['category_label', 'day_match']], how='left')
    T['goods'] = T.category_label.map(GOODS)
    T.loc[T.category_label == 'Not specified', 'goods'] = 'Not specified'
    T.loc[T.day_match == 'No trading day reported', 'goods'] = 'Not trading'
    T.loc[T.category_label.isna(), 'goods'] = 'Not covered'
    mk = CM.panel().drop_duplicates('mktID').set_index('mktID')
    T['ndays'] = mk.marketDays.apply(lambda x: len(set(re.findall(r'\d+', str(x))))).reindex(T.index)
    reported = T.day_match.isin(['Exact match', 'Partial overlap', 'Complete miss',
                                 'Continuous bazaar, main day correct',
                                 'Continuous bazaar, no main day named'])
    full = T.day_match.isin(['Exact match', 'Continuous bazaar, main day correct'])

    def by_access(s, share=False, den=None):
        out = []
        for mask in [pd.Series(True, index=T.index)] + [T.access == a for a in ACC]:
            if den is not None:
                out.append(round(100 * (s & mask).sum() / (den & mask).sum()))
            else:
                out.append(round(100 * s[mask].mean()) if share else int(s[mask].sum()))
        return out

    rows = [['A. Location and goods sold', '', '', '', '', ''],
            ['Markets (number)', ''] + by_access(pd.Series(True, index=T.index))]
    for grp, k in [('Food is sold', 'Food only'), ('', 'Food and livestock'),
                   ('', 'Food and general goods'), ('', 'Food, livestock and general goods'),
                   ('Food not sold', 'Livestock only'), ('', 'Car markets'),
                   ('Not specified', None), ('Not trading', None), ('Not covered', None)]:
        rows.append([grp, k or ''] + by_access(T.goods == (k or grp)))
    rows += [['B. Operating schedule identified from satellite imagery', '', '', '', '', ''],
             ['Trades once a week (%)', ''] + by_access(T.ndays == 1, share=True),
             ['C. Field validation in 2026', '', '', '', '', ''],
             ['Visited (number)', ''] + by_access(T.category_label.notna()),
             ['Schedule fully confirmed (% with a reported day)', ''] + by_access(full, den=reported)]
    TT = pd.DataFrame(rows, columns=['', ' ', 'All', 'High access', 'Intermediate', 'Remote'])
    return TT, dict(markets=len(T), visited=int(T.category_label.notna().sum()))


# ============================================================ Table A.1 helpers
def _district_panel():
    """All 401 Afghan districts with market presence, conflict, population,
    control status and the district share of provincial luminosity."""
    d2 = gpd.read_file(ADM2)[['Pcode_24', 'Dist_ID_24', 'Prov_name', 'AREA_GEO', 'geometry']]
    d2['Dist_ID_24'] = d2.Dist_ID_24.astype(int)
    # the published table counts the 136 markets of the derived file; adding the
    # 137th (Herat) moves panel B by a few thousandths and leaves panel A unchanged
    mk = CM.panel(include_herat=False).drop_duplicates('mktID')[['mktID', 'marketlat', 'marketlon']]
    gp = gpd.GeoDataFrame(mk, geometry=gpd.points_from_xy(mk.marketlon, mk.marketlat),
                          crs='EPSG:4326')
    j = gpd.sjoin(gp, d2[['Pcode_24', 'geometry']], how='left', predicate='within')
    j = j[~j.index.duplicated(keep='first')]
    n_mkt = j.groupby('Pcode_24').size()
    d2['has_mkt'] = d2.Pcode_24.isin(set(j.Pcode_24))

    pop = pd.read_csv(POP_LONG, encoding='utf-8-sig')
    pw = pop.groupby(['adm2_pcode', 'year'], as_index=False).population.sum()
    py = pw[pw.year.isin(YRS)].groupby('adm2_pcode').population.sum().rename('person_years')
    p18 = pw[pw.year == 2018].set_index('adm2_pcode').population.rename('pop18')

    a = pd.read_csv(ACLED, low_memory=False)
    a['event_date'] = pd.to_datetime(a.event_date, format='mixed')
    a = a[a.event_date.dt.year.isin(YRS)]
    aj = gpd.sjoin(gpd.GeoDataFrame(a, geometry=gpd.points_from_xy(a.longitude, a.latitude),
                                    crs='EPSG:4326'), d2[['Pcode_24', 'geometry']],
                   how='left', predicate='within')
    aj = aj[~aj.index.duplicated(keep='first')].dropna(subset=['Pcode_24'])
    aj = aj[aj.sub_event_.isin(IED | GATHER | CLASH)]
    deaths = aj.groupby('Pcode_24').fatalities.sum()

    D = (d2.drop(columns='geometry')
           .merge(deaths.rename('deaths'), left_on='Pcode_24', right_index=True, how='left')
           .merge(py, left_on='Pcode_24', right_index=True, how='left')
           .merge(p18, left_on='Pcode_24', right_index=True, how='left'))
    D['deaths'] = D.deaths.fillna(0)
    D['deaths_pc'] = 1e5 * D.deaths / D.person_years
    D['M'] = D.has_mkt.astype(int)
    D['log_pop18'] = np.log(D.pop18)
    D['n_markets'] = D.Pcode_24.map(n_mkt).fillna(0)

    cd = gpd.read_file(GEOJSON)[['district_id', 'geometry']]
    dm = gpd.sjoin(d2[['Pcode_24', 'geometry']], cd, how='left', predicate='intersects')
    dm = dm[~dm.index.duplicated(keep='first')].set_index('Pcode_24').district_id
    ctl = pd.read_csv(CONTROL_PANEL); ctl['date'] = pd.to_datetime(ctl.date, errors='coerce')
    st = ctl[ctl.date.dt.year.isin(YRS)].pivot_table(index='district_id', columns='date',
                                                     values='status', aggfunc='first')
    ever_c = st.apply(lambda r: (r == 'Contested').any() or r.dropna().nunique() > 1, axis=1)
    tal_all = st.apply(lambda r: r.dropna().size > 0 and (r.dropna() == 'Taliban Control').all(), axis=1)
    D['did'] = D.Pcode_24.map(dm)
    D['ever_contested'] = D.did.map(ever_c).fillna(False).astype(int)
    D['taliban_always'] = D.did.map(tal_all).fillna(False).astype(int)

    ntl = pd.read_excel(NTL_DIST)
    mo = [f'2018-{m:02d}' for m in range(1, 13)]
    ntl['civ'] = sum(ntl[f'{m}_sum'].fillna(0) - ntl[f'{m}_sum(Coalition)'].fillna(0) for m in mo)
    ntl = ntl.rename(columns={'District24 ': 'Dist_ID_24'})[['Dist_ID_24', 'civ']]
    ntl['Dist_ID_24'] = ntl.Dist_ID_24.astype(int)
    D = D.merge(ntl, on='Dist_ID_24', how='left')
    D['civ'] = D.civ.fillna(0)
    D['ntl_share'] = D.civ / D.groupby('Prov_name').civ.transform('sum')
    D['pop_share'] = D.pop18 / D.groupby('Prov_name').pop18.transform('sum')
    return D


def _ndvi_cells():
    """Market by year-month by market-day cells joined to growing-season NDVI.

    The specification that reproduces the manuscript exactly:
      * outcome activity_area_norm2020, averaged within
        market x year x month x market-day-status cells;
      * growing-season NDVI is the LAGGED quarterly mean, ndvi_mean_lag - the
        previous quarter's greenness, which is what a harvest quarter responds to;
      * it is standardised against the market's own long-run mean and standard
        deviation for the quarter (the climatology in the NDVI file), not against
        its own across-year mean;
      * the harvest sample is each market's own harvest quarter, the one after its
        peak-greenness quarter.
    Note that the long-run mean and standard deviation are those of the quarter the
    observation falls in, while the numerator is the previous quarter's greenness;
    that is how the published series is built and it is preserved here.
    """
    TGT = CM.TARGET                      # activity_area_norm2020
    nd = pd.read_csv(NDVI_MKT, low_memory=False)
    nd['std_lag'] = ((nd.ndvi_mean_lag - nd.ndvi_mean_long_term) / nd.ndvi_std_long_term)
    lv = nd.groupby(['mktID', 'quarter']).ndvi_mean.mean().unstack()
    harv = (lv.idxmax(axis=1) % 4 + 1).rename('harv_q')

    raw = pd.read_csv(CM.ACT_ALL, low_memory=False).rename(columns={'Location': 'mktID'})
    dt = pd.to_datetime(raw.date, format='mixed')
    raw['year'] = dt.dt.year; raw['month'] = dt.dt.month
    raw['quarter'] = (raw.month - 1) // 3 + 1
    raw = raw[raw.year.between(2018, 2025)].dropna(subset=[TGT, 'mktDay'])
    raw['MktDay'] = raw.mktDay.astype(float)
    raw = raw.join(harv, on='mktID').dropna(subset=['harv_q'])
    d = raw.merge(nd[['mktID', 'year', 'quarter', 'std_lag']],
                  on=['mktID', 'year', 'quarter'], how='left')

    cell = (d.groupby(['mktID', 'year', 'month', 'quarter', 'MktDay', 'harv_q'],
                      as_index=False).agg({TGT: 'mean', 'std_lag': 'mean'})
              .rename(columns={TGT: 'y', 'std_lag': 'z', 'MktDay': 'mktday'}).dropna())
    cell['ym'] = cell.year.astype(str) + '-' + cell.month.astype(str).str.zfill(2)
    cell['inter'] = cell.mktday * cell.z
    return cell[cell.quarter == cell.harv_q].copy(), cell


# ============================================================ Table 3
def table3_ndvi_marketday():
    """Table 3. Market-day activity and growing-season NDVI (equation A.2 in Annex A.5)."""
    H, A = _ndvi_cells()
    specs = [('Own harvest quarter', 'No', 'No', H, 'y ~ mktday + z + inter'),
             ('Own harvest quarter', 'Yes', 'No', H, 'y ~ mktday + z + inter + C(ym)'),
             ('Own harvest quarter', 'Yes', 'Yes', H,
              'y ~ mktday + z + inter + C(ym) + C(mktID)'),
             ('All quarters', 'Yes', 'No', A, 'y ~ mktday + z + inter + C(ym)'),
             ('All quarters', 'Yes', 'Yes', A,
              'y ~ mktday + z + inter + C(ym) + C(mktID)')]
    out, meta = [], []
    for samp, ym, mfe, d, form in specs:
        f = smf.ols(form, data=d).fit(cov_type='cluster', cov_kwds={'groups': d.mktID})
        out.append(f); meta.append((samp, ym, mfe, int(f.nobs), d.mktID.nunique(), f.rsquared))
    rows = []
    for k, lab in [('mktday', 'Market day'), ('z', 'Growing-season NDVI'),
                   ('inter', 'Market day × NDVI')]:
        rows.append([lab] + [f'{f.params[k]:+.2f}'.replace('-', '−') + _star(f.pvalues[k])
                             for f in out])
        rows.append([''] + [f'({f.bse[k]:.2f})' for f in out])
    for i, lab in enumerate(['Sample', 'Year-month fixed effects', 'Market fixed effects']):
        rows.append([lab] + [m[i] for m in meta])
    rows.append(['Observations'] + [f'{m[3]:,}' for m in meta])
    rows.append(['Markets'] + [f'{m[4]}' for m in meta])
    rows.append(['R-squared'] + [f'{m[5]:.3f}' for m in meta])
    T = pd.DataFrame(rows, columns=[''] + [f'({i})' for i in range(1, 6)])
    return T, dict(n_harvest=meta[0][3], n_all=meta[3][3], markets=meta[0][4])


# ============================================================ Table A.1
def tableA1_poppy():
    """Table A.1. Poppy cultivation and the decline in market activity, 2022 to 2025. Four nested columns: poppy alone; plus access category;
    plus conflict deaths; plus the change in growing-season NDVI.

    Growing-season NDVI is each market-quarter's catchment NDVI standardised
    against that market-quarter's long-run mean and standard deviation, averaged
    over the second and third quarters; the regressor is its 2025 value less its
    2022 value, so it is already in standard-deviation units."""
    POPPY_HA = {'Hilmand': 122000, 'Kandahar': 29200, 'Uruzgan': 14600, 'Faryab': 6900,
                'Nangarhar': 5200, 'Badakhshan': 4300, 'Farah': 3000, 'Nimroz': 2000,
                'Zabul': 1550}
    pa = CM.panel()
    mm = CM.market_year_activity(pa)
    flags = pa.groupby('mktID')[['open_2022', 'open_2025', 'wp_SUM']].first()
    both = flags.index[(flags.open_2022 == 1) & (flags.open_2025 == 1)]
    D = pd.DataFrame({'a22': mm[2022], 'a25': mm[2025]}).loc[mm.index.intersection(both)].dropna()
    D['chg'] = 100 * (D.a25 / D.a22 - 1)
    prov = pa.groupby('mktID').admLvl1.first()
    D['province'] = prov.reindex(D.index)
    D['poppy'] = D.province.isin(POPPY_HA).astype(int)

    dens = _district_panel().set_index('Pcode_24')
    px = pd.read_excel(CM.PROX50K); px.columns = [c.strip() for c in px.columns]
    px = px.set_index('mktID')
    D['district'] = px['Pcode_24'].reindex(D.index)
    D['deaths_pc'] = dens.deaths_pc.reindex(D.district).values

    acc = CM.access_categories().set_index('mktID').access.reindex(D.index)
    D['inter'] = (acc == 'Intermediate access').astype(int)
    D['remote'] = (acc == 'Remote').astype(int)

    nd = pd.read_csv(NDVI_MKT, low_memory=False)
    nd['z'] = (nd.ndvi_mean - nd.ndvi_mean_long_term) / nd.ndvi_std_long_term
    gs = nd[nd.quarter.isin([2, 3])].pivot_table(index='mktID', columns='year', values='z')
    D['d_ndvi'] = (gs[2025] - gs[2022]).reindex(D.index)

    X = ['poppy', 'inter', 'remote', 'deaths_pc', 'd_ndvi']
    N = {'poppy': 'Poppy province', 'inter': 'Intermediate access (vs high)',
         'remote': 'Remote (vs high)',
         'deaths_pc': 'Conflict deaths per 100,000, 2017–2018',
         'd_ndvi': 'Change in growing-season NDVI, 2022–2025 (sd)'}
    S = D.dropna(subset=['chg'] + X)
    fits = [_clus('chg ~ ' + ' + '.join(x), S, 'province')
            for x in (X[:1], X[:3], X[:4], X)]
    DEC = {'deaths_pc': 4}
    rows = []
    for k in X + ['Intercept']:
        d = DEC.get(k, 2)
        rows.append([N.get(k, 'Constant')] +
                    [f'{f.params[k]:+.{d}f}'.replace('-', '−') + _star(f._p[k])
                     if k in f.params.index else '' for f in fits])
        rows.append([''] + [f'({f.bse[k]:.{d}f})' if k in f.params.index else ''
                            for f in fits])
    rows.append(['R²'] + [f'{f.rsquared:.3f}' for f in fits])
    rows.append(['Observations'] + [f'{int(f.nobs)}' for f in fits])
    rows.append(['Province clusters'] + [f'{S.province.nunique()}'] * len(fits))
    T = pd.DataFrame(rows, columns=[''] + [f'({i})' for i in range(1, len(fits) + 1)])
    return T, dict(n=int(fits[0].nobs), clusters=S.province.nunique(),
                   mean_dv=S.chg.mean(), n_poppy=int(S.poppy.sum()))



ALL = [table1_day_validation, table2_goods_by_access, table3_ndvi_marketday, tableA1_poppy]


if __name__ == '__main__':
    for fn in ALL:
        T, meta = fn()
        CM.save_paper_table(T, fn.__name__)
        print(f'--- {fn.__name__}')
        print(T.to_string(index=False))
        print(f'    {meta}\n')
