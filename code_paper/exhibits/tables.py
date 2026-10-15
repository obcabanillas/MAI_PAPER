"""One function per regression table in the paper.

Each returns (DataFrame of the rendered rows, dict of metadata). run_all.py
writes them to CSV. `AS_IMAGE` lists the tables the paper carries as a picture
rather than as a Word table; `render_png()` draws those.
"""
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


def _rob(formula, data, family=None):
    f = (smf.ols(formula, data=data).fit(cov_type='HC1', use_t=True) if family is None
         else smf.glm(formula, data=data, family=family).fit(cov_type='HC1'))
    df = int(f.nobs) - len(f.params)
    f._p = {k: 2 * (1 - _st.t.cdf(abs(f.params[k] / f.bse[k]), df)) for k in f.params.index}
    return f


def _star(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.10 else ''


def _cell(c, s, p, d=4):
    return f'{c:+.{d}f}'.replace('+', '').replace('-', '−') + _star(p), f'({s:.{d}f})'


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


def table1_conflict_markets():
    """Table 1 — Conflict, Market Location and the Trajectory of Market Activity."""
    D = _district_panel()
    XA = ['deaths_pc', 'log_pop18', 'ever_contested', 'taliban_always', 'ntl_share', 'pop_share']
    NA = {'deaths_pc': 'Conflict deaths per 100,000, 2017–2018 (district level)',
          'log_pop18': 'Log district population, 2018',
          'ever_contested': 'District ever contested, 2017–2018',
          'taliban_always': 'District always Taliban-held, 2017–2018',
          'ntl_share': 'Share of province luminosity produced in the district, 2018',
          'pop_share': 'Share of province population living in the district, 2018'}
    S = D.dropna(subset=['M'] + XA)
    fA = _clus('M ~ ' + ' + '.join(XA) + ' + C(Prov_name)', S, 'Prov_name')

    PR = D.groupby('Prov_name').apply(lambda g: pd.Series({
        'n_markets': g.n_markets.sum(), 'pop18': g.pop18.sum(), 'area': g.AREA_GEO.sum(),
        'deaths': g.deaths.sum(), 'person_years': g.person_years.sum(),
        'share_contested': g.loc[g.ever_contested.astype(bool), 'pop18'].sum() / g.pop18.sum(),
        'share_taliban_always': g.loc[g.taliban_always.astype(bool), 'pop18'].sum() / g.pop18.sum()
    })).reset_index()
    PR['log_density'] = np.log(PR.pop18 / PR.area)
    PR['deaths_pc'] = 1e5 * PR.deaths / PR.person_years
    XB = ['log_density', 'deaths_pc', 'share_contested', 'share_taliban_always']
    NB = {'log_density': 'Log population density, 2018',
          'deaths_pc': 'Conflict deaths per 100,000, 2017–2018',
          'share_contested': 'Population share ever contested, 2017–2018',
          'share_taliban_always': 'Population share always Taliban-held, 2017–2018'}
    fB = _rob('n_markets ~ ' + ' + '.join(XB), PR, family=sm.families.Poisson())
    pseudo = 1 - fB.deviance / fB.null_deviance

    rows = [['A. District characteristics', '', '']]
    for k in XA:
        c, s = _cell(fA.params[k], fA.bse[k], fA._p[k])
        rows += [[NA[k], c, '—'], ['', s, '—']]
    rows.append(['B. Province characteristics', '', ''])
    for k in XB:
        c, s = _cell(fB.params[k], fB.bse[k], fB._p[k])
        rows += [[NB[k], '—', c], ['', '—', s]]
    ca, sa = _cell(fA.params['Intercept'], fA.bse['Intercept'], fA._p['Intercept'])
    cb, sb = _cell(fB.params['Intercept'], fB.bse['Intercept'], fB._p['Intercept'])
    rows += [['Constant', ca, cb], ['', sa, sb],
             ['Unit of observation', 'District', 'Province'],
             ['Estimator', 'OLS', 'Poisson'],
             ['Fixed effects', 'Province', 'None'],
             ['Standard errors', 'Province-clustered', 'Robust (HC1)'],
             ['R² / pseudo R²', f'{fA.rsquared:.3f}', f'{pseudo:.3f}†'],
             ['Observations', f'{int(fA.nobs)}', f'{int(fB.nobs)}']]
    T = pd.DataFrame(rows, columns=['', 'District includes at least a market',
                                    'Markets in the province'])
    return T, dict(n_district=int(fA.nobs), n_province=int(fB.nobs),
                   r2=fA.rsquared, pseudo=pseudo)


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


def tableA3_ndvi_marketday():
    """Table A3 - market-day activity and growing-season NDVI."""
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


def tableA2_poppy():
    """Table A.1 of the paper - poppy cultivation and the 2022-2025 decline in
    market activity. Four nested columns: poppy alone; plus access category;
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



def render_png(T, path, col_widths=None, bold_last=True, dpi=300):
    """Draw a small DataFrame as a table image in the manuscript's house style:
    a light header band, hairline row rules, heavy rules top and bottom, and a
    bold total row. Used for the exhibits the document carries as pictures."""
    import matplotlib.pyplot as plt
    from matplotlib.table import Table
    cols = list(T.columns)
    nr, nc = len(T), len(cols)
    w = col_widths or ([0.20] + [(0.80) / (nc - 1)] * (nc - 1))
    fig, ax = plt.subplots(figsize=(6.5, 0.26 * (nr + 1.6)))
    ax.set_axis_off()
    tb = Table(ax, bbox=[0, 0, 1, 1])
    HDR, RULE, INK = '#f2f2f0', '#c9c9c4', '#1a1a1a'
    hh = 1.0 / (nr + 1.6)
    for c, (name, cw) in enumerate(zip(cols, w)):
        cell = tb.add_cell(0, c, cw, hh * 1.6, text=str(name), loc='left', facecolor=HDR)
        cell.get_text().set(fontweight='bold', fontsize=7.4, color=INK)
        cell.set_edgecolor('none'); cell.set_linewidth(0); cell.PAD = 0.035
    for r in range(nr):
        last = bold_last and r == nr - 1
        for c, (name, cw) in enumerate(zip(cols, w)):
            cell = tb.add_cell(r + 1, c, cw, hh, text=str(T.iloc[r, c]),
                               loc='left', facecolor='white')
            cell.get_text().set(fontsize=7.4, color=INK,
                                fontweight='bold' if last else 'normal')
            cell.set_edgecolor(RULE); cell.set_linewidth(0.5)
            cell.visible_edges = 'T' if not last else 'TB'
            cell.PAD = 0.035
    ax.add_table(tb)
    for y, lw in [(1.0, 0.9), (0.0, 0.9)]:
        ax.axhline(y, color=INK, lw=lw, clip_on=False)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'   saved {path.split("/")[-1]}')
    return path


# ------------------------------------------------------------------ regional coverage
def tableA1_region_coverage():
    """How far the detected markets reach: markets, districts and provinces per
    region, against the districts and provinces the region actually contains.

    Regions are the six-region grouping the manuscript uses in this table, i.e.
    the seven UN regions with North East folded into East (CM.panel()'s
    `un_region_small`). Province and district universes come from the boundary
    files, so every region reports its full extent, not only the parts that hold
    a market. Districts and provinces "with a market" are counted by locating
    each market point inside a district polygon.
    """
    ORDER = ['Central', 'East', 'NorthWest', 'SouthEast', 'SouthWest', 'West']

    # province -> region, from the CSO_Region field, West Central folded into West
    a1 = gpd.read_file(CM.ADM1)[['Prov_name', 'CSO_Region']].copy()
    a1['Prov_name'] = a1.Prov_name.replace(PROV_ALIAS)
    a1['region'] = a1.CSO_Region.map(
        {'Central': 'Central', 'East': 'East', 'Northeast': 'East', 'North': 'NorthWest',
         'South': 'SouthEast', 'Southwest': 'SouthWest', 'West': 'West', 'WestCentral': 'West'})

    # districts, and the province each belongs to
    d2 = gpd.read_file(ADM2)[['Pcode_24', 'Prov_name', 'geometry']].copy()
    d2['Prov_name'] = d2.Prov_name.replace(PROV_ALIAS)
    d2 = d2.merge(a1[['Prov_name', 'region']], on='Prov_name', how='left')
    assert d2.region.notna().all(), 'a district fell outside the region map'

    # locate every market inside a district, for the district counts
    mk = CM.panel().drop_duplicates('mktID')[['mktID', 'admLvl1', 'marketlat', 'marketlon']]
    gp = gpd.GeoDataFrame(mk, geometry=gpd.points_from_xy(mk.marketlon, mk.marketlat),
                          crs='EPSG:4326')
    j = gpd.sjoin(gp, d2[['Pcode_24', 'geometry']], how='left', predicate='within')
    j = j[~j.index.duplicated(keep='first')]
    assert j.Pcode_24.notna().all(), 'a market fell outside every district'
    dreg = d2.set_index('Pcode_24').region
    j['dist_region'] = j.Pcode_24.map(dreg)

    # Markets and provinces are counted by the market's OWN province, which is how
    # the manuscript assigns them. Two Nimroz markets sit inside Farah district
    # polygons, so a district-based count would move them from South West to West;
    # the district columns keep them in the district they physically occupy.
    mk['prov'] = mk.admLvl1.replace(PROV_ALIAS)
    p2r = a1.set_index('Prov_name').region
    mk['region'] = mk.prov.map(p2r)
    assert mk.region.notna().all(), f'unmapped province: {sorted(set(mk.prov[mk.region.isna()]))}'

    rows = []
    for r in ORDER:
        held = mk[mk.region == r]
        univ = d2[d2.region == r]
        rows.append({'Region': CM.RNAME.get(r, r),
                     'Markets': len(held),
                     'Districts with a market': j.loc[j.dist_region == r, 'Pcode_24'].nunique(),
                     'Districts in region': univ.Pcode_24.nunique(),
                     'Provinces with a market': held.prov.nunique(),
                     'Provinces in region': univ.Prov_name.nunique()})
    T = pd.DataFrame(rows)
    T.loc[len(T)] = ['All', len(mk), j.Pcode_24.nunique(), d2.Pcode_24.nunique(),
                     mk.prov.nunique(), d2.Prov_name.nunique()]
    meta = dict(markets=len(mk), districts=int(d2.Pcode_24.nunique()),
                provinces=int(d2.Prov_name.nunique()),
                districts_with=int(j.Pcode_24.nunique()),
                provinces_with=int(mk.prov.nunique()))
    return T, meta


# tables the document carries as a picture rather than as a Word table
AS_IMAGE = {'tableA1_region_coverage'}

ALL = [table1_conflict_markets, tableA1_region_coverage,
       tableA2_poppy, tableA3_ndvi_marketday]


if __name__ == '__main__':
    import common as _C
    for fn in ALL:
        T, meta = fn()
        p = f'{_C.OUT}/{fn.__name__.split("_")[0].replace("table", "table")}'
        T.to_csv(f'{_C.OUT}/{fn.__name__}.csv', index=False)
        print(f'--- {fn.__name__}  ->  out/{fn.__name__}.csv')
        print(T.to_string(index=False))
        print(f'    {meta}\n')
