"""One function per figure in the paper. Each returns the saved path.

Naming follows the order the figures appear in the document; the media file each
one corresponds to is given in the docstring so the output can be checked against
the version embedded in the manuscript.
"""
import common as C
from common import (plt, pd, np, COLOR, LABEL, INK, MUTED, GRID, RULE, YEARS,
                    REGIONS, RNAME, grid, years, save)
from matplotlib.ticker import FuncFormatter
import geopandas as gpd
from scipy import stats


# ============================================================ 1. region map (image1)
def fig01_region_map():
    pa = C.panel(); mk = pa.drop_duplicates('mktID')
    a = gpd.read_file(C.ADM1)
    CSO = {'Central': 'Central', 'East': 'East', 'Northeast': 'NorthEast', 'North': 'NorthWest',
           'South': 'SouthEast', 'Southwest': 'SouthWest', 'West': 'West', 'WestCentral': 'West'}
    a['region'] = a.CSO_Region.map(CSO)
    RCOL = dict(zip(REGIONS, ['#2a78d6', '#eb6834', '#8c2d04', '#1baf7a',
                              '#eda100', '#e87ba4', '#4a3aa7']))
    n = mk.un_region.value_counts()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for r in REGIONS:
        a[a.region == r].plot(ax=ax, color=RCOL[r], edgecolor='white', lw=0.45, alpha=0.85)
    ax.scatter(mk.marketlon, mk.marketlat, s=2.4, color='#111111', zorder=7, linewidths=0)
    ax.set_axis_off()
    h = [plt.Rectangle((0, 0), 1, 1, color=RCOL[r]) for r in REGIONS] + \
        [plt.Line2D([], [], marker='o', ls='', color='#111111', ms=2.6)]
    ax.legend(h, [f'{RNAME.get(r, r)} — {int(n.get(r, 0))} markets' for r in REGIONS]
              + [f'Detected market ({len(mk)})'], loc='upper center', bbox_to_anchor=(0.5, 0.045),
              ncol=4, fontsize=6.8, frameon=False, handlelength=1.1, labelspacing=0.35,
              columnspacing=1.4, borderaxespad=0.0)
    return save(fig, 'fig01_region_map')


# ============================================================ 2. days of operation (image4)
def fig02_days_of_operation():
    import re
    pa = C.panel().drop_duplicates('mktID')
    days = pa.marketDays.apply(lambda x: {int(v) for v in re.findall(r'\d+', str(x))})
    once = days[days.apply(len) == 1]; more = days[days.apply(len) > 1]
    LAB = {6: 'Sat', 0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri'}
    ORD = [6, 0, 1, 2, 3, 4, 5]
    c1 = pd.Series([d for s in once for d in s]).value_counts().reindex(ORD).fillna(0)
    c2 = pd.Series([d for s in more for d in s]).value_counts().reindex(ORD).fillna(0)
    s1, s2 = 100 * c1 / c1.sum(), 100 * c2 / c2.sum()
    x = np.arange(7); w = 0.38
    fig, ax = plt.subplots(figsize=(6.5, 2.9))
    ax.bar(x - w/2, s1, w, color='#8fbdf0', label=f'Once-a-week markets (n = {len(once)})', zorder=3)
    ax.bar(x + w/2, s2, w, color=COLOR['ntl_total'], label=f'More-than-once-a-week markets (n = {len(more)})', zorder=3)
    for xi, v in zip(x - w/2, s1): ax.annotate(f'{v:.0f}%', (xi, v), ha='center', fontsize=6.2,
                                               xytext=(0, 2), textcoords='offset points')
    for xi, v in zip(x + w/2, s2): ax.annotate(f'{v:.0f}%', (xi, v), ha='center', fontsize=6.2,
                                               xytext=(0, 2), textcoords='offset points')
    ax.set_xticks(x); ax.set_xticklabels([LAB[d] for d in ORD])
    ax.set_ylabel('Share of market days (%)', fontsize=7.6)
    ax.set_ylim(0, max(s1.max(), s2.max()) * 1.30)     # headroom for the legend
    grid(ax); ax.legend(fontsize=6.8, loc='upper left', frameon=False)
    return save(fig, 'fig02_days_of_operation')


KABUL_REF = 10.0   # log1p radiance within 5 km of the centre of Kabul, from the manuscript


# ============================================================ 3. access categories (image7/8)
def fig03_access_categories():
    m = C.access_categories()
    buf = C.buffer_ntl(markets=set(m.mktID), stat='mean')
    m = m.merge(buf[2025].rename('ntl25'), left_on='mktID', right_index=True, how='left')
    m['ntl25'] = m.ntl25.fillna(0)
    AC = {'High access': COLOR['high'], 'Intermediate access': COLOR['inter'], 'Remote': COLOR['remote']}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9))
    for k, c in AC.items():
        s = m[m.access == k]
        a1.scatter(s.travel_50, s.wp_SUM / 1000, s=11, color=c, alpha=0.75,
                   edgecolor='none', label=f'{k} ({len(s)})', zorder=3)
    a1.axvline(40, color='#999995', ls='--', lw=0.9, zorder=2)
    a1.axhline(250, color='#999995', ls='--', lw=0.9, zorder=2)
    a1.set_yscale('log'); a1.set_yticks([10, 50, 250, 1000, 5000])
    a1.get_yaxis().set_major_formatter(FuncFormatter(lambda v, p: f'{v:,.0f}'))
    a1.set_xlabel('Travel time to a settlement of\n50,000 or more (minutes)', fontsize=7)
    a1.set_ylabel('Catchment population within\n30 minutes (thousands)', fontsize=7)
    a1.set_title('a. Two dimensions define three access categories', fontsize=7.4, loc='left', pad=4)
    grid(a1, axis='both'); a1.legend(fontsize=5.9, loc='upper right')

    # Panel b, as specified by the authors: the cumulative distribution of the
    # MEDIAN monthly buffer radiance in 2025, on a log1p scale so that markets
    # with no measurable emissions sit at zero. KABUL_REF is the manuscript's
    # reference for the median within 5 km of the centre of Kabul; it is quoted
    # from the manuscript because no 5 km Kabul-centre buffer exists in the
    # shared data, so the package cannot recompute it.
    med = C.buffer_ntl(markets=set(m.mktID), stat='median')[2025]
    v = np.sort(np.log1p(med.reindex(sorted(m.mktID)).fillna(0).clip(lower=0).values))
    a2.step(np.concatenate([[v[0]], v]), np.arange(0, len(v) + 1) / len(v),
            where='post', color=COLOR['ntl_buffer'], lw=1.7, zorder=3)
    a2.axvline(KABUL_REF, color='#c9c9c4', ls='--', lw=1.1, zorder=2)
    a2.annotate('Median value within\n5km from center\nof Kabul',
                xy=(KABUL_REF - 0.35, 0.30), ha='right', va='center',
                fontsize=7, color='#9a9a95')
    a2.set_xlim(-0.55, KABUL_REF + 0.35); a2.set_ylim(0, 1.0)
    a2.set_yticks(np.arange(0, 1.01, 0.2))
    a2.set_xlabel('Median nighttime light emissions (2025, log scale)', fontsize=7.4)
    a2.set_ylabel('Cum. share of detected marketplaces', fontsize=7.4)
    a2.set_title('b. Half of these markets are invisible to nighttime lights',
                 fontsize=7.4, loc='left', pad=4)
    for sp in ('top', 'right'):
        a2.spines[sp].set_visible(False)
    fig.tight_layout(pad=0.4)
    return save(fig, 'fig03_access_categories')


# ============================================================ 4. emissions by access (image9/10)
def fig04_emissions_by_access():
    m = C.access_categories()
    buf = C.buffer_ntl(markets=set(m.mktID), stat='mean')
    m = m.merge(buf[2025].rename('ntl25'), left_on='mktID', right_index=True, how='left')
    m['ntl25'] = m.ntl25.fillna(0)
    ORD = ['Remote', 'Intermediate access', 'High access']
    COL = [COLOR['remote'], COLOR['inter'], COLOR['high']]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9))
    sh = m.groupby('access').apply(lambda s: 100 * (s.ntl25 > 0).mean()).reindex(ORD)
    nn = m.groupby('access').size().reindex(ORD)
    a1.bar(range(3), 100, color='#ececea', zorder=2)
    a1.bar(range(3), sh.values, color=COL, zorder=3)
    for i, (v, k) in enumerate(zip(sh.values, ORD)):
        a1.annotate(f'{v:.0f}%', (i, v), ha='center', fontsize=7, fontweight='bold',
                    xytext=(0, 3), textcoords='offset points')
        a1.annotate(f'{int(round(v*nn[k]/100))} of {nn[k]}', (i, 3), ha='center',
                    fontsize=6, color='white')
    a1.set_xticks(range(3)); a1.set_xticklabels([f'{RNAME.get(k,k)}\n(n={nn[k]})' for k in ORD], fontsize=6.6)
    a1.set_ylabel('Markets with positive emissions (%)', fontsize=7.4); a1.set_ylim(0, 108)
    a1.set_title('a. Share of markets with positive emissions', fontsize=7.4, loc='left', pad=4)
    grid(a1)
    rng = np.random.RandomState(0)
    for i, (k, c) in enumerate(zip(ORD, COL)):
        s = m[(m.access == k) & (m.ntl25 > 0)]
        a2.scatter(i + rng.uniform(-.16, .16, len(s)), s.ntl25, s=9, color=c, alpha=.65,
                   edgecolor='none', zorder=3)
        # The median is taken over the markets that HAVE emissions — the ones the
        # panel plots — not over the whole access category, where the many dark
        # markets would drag it to zero.
        med = s.ntl25.median()
        a2.plot([i - .27, i + .27], [max(med, .3)] * 2, color=INK, lw=1.2, zorder=4)
        a2.annotate(f'median {med:,.0f}\n(n={len(s)})', (i, max(med, .3)), fontsize=6, color=INK,
                    ha='center', xytext=(0, 4), textcoords='offset points')
    a2.set_yscale('symlog', linthresh=1)
    a2.set_xticks(range(3)); a2.set_xticklabels([f'{k}\n(n={nn[k]})' for k in ORD], fontsize=6.6)
    a2.set_ylabel('Mean monthly emissions, 2025', fontsize=7.4)
    a2.set_title('b. Emissions in 2025, by access category', fontsize=7.4, loc='left', pad=4)
    grid(a2)
    fig.tight_layout(pad=0.4)
    return save(fig, 'fig04_emissions_by_access')


# ============================================================ 5. GDP vs MAI (image11)
def fig05_gdp_vs_mai():
    g = pd.read_excel(C.MACRO, sheet_name='Real')
    g['Sector'] = g['Sector'].ffill().astype(str).str.strip()
    lvl = g[g['Measure'] == 'million Afs'].set_index('Sector')
    cols = [2018, 2019, 2020, 2021, '2022p', 2023, 2024, 2025]
    ser = lambda s: pd.Series(100 * lvl.loc[s, cols].astype(float).values
                              / lvl.loc[s, cols].astype(float).values[2], index=YEARS)
    mai = C.mai_series(C.panel()).reindex(YEARS)
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    for key, s in [('ag_gdp', ser('Agriculture')), ('tot_gdp', ser('Total')), ('mai', mai)]:
        ax.plot(YEARS, s.values, '-o', color=COLOR[key], lw=1.8, ms=3.4, label=LABEL[key], zorder=3)
        ax.annotate(f'{s.iloc[-1]:.0f}', (2025, s.iloc[-1]), color=COLOR[key], fontsize=7,
                    xytext=(4, -2), textcoords='offset points')
    grid(ax, 100); years(ax)
    ax.set_ylabel('Index, 2020 = 100', fontsize=7.6); ax.set_xlabel('Year', fontsize=7.6)
    ax.legend(fontsize=7, loc='lower left')
    return save(fig, 'fig05_gdp_vs_mai')


# ============================================================ 6. NDVI, nightlights, MAI (image12)
def fig06_ndvi_ntl_mai():
    ndvi = C.ndvi_levels()
    mai = C.mai_series(C.panel()).reindex(YEARS)
    ntl = C.ntl_national()
    ntl_idx = 100 * ntl / ntl.loc[2020]
    b = C.buffer_ntl(months=range(2, 7), markets=set(C.panel().mktID), stat='mean').sum()
    buf_idx = 100 * b / b.loc[2020]
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    ax.bar(ndvi.index, ndvi.values, color=COLOR['ndvi'], width=0.66, alpha=0.55, zorder=1)
    ax.axhline(0, color='#8f8e8a', lw=1.0, zorder=2)
    grid(ax); years(ax)
    ax.set_ylabel('Growing-season NDVI\n(sd from long-run mean)', fontsize=7.6)
    ax.set_xlabel('Year', fontsize=7.6)
    R_LO, R_HI, L_HI = 60, 150, 2.6
    frac = (100 - R_LO) / (R_HI - R_LO)
    ax.set_ylim(-frac / (1 - frac) * L_HI, L_HI)
    ax2 = ax.twinx()
    for s, key in [(ntl_idx, 'ntl_total'), (buf_idx, 'ntl_buffer'), (mai, 'mai')]:
        ax2.plot(YEARS, s.reindex(YEARS).values, '-o', color=COLOR[key], lw=1.7, ms=3.2,
                 mec='white', mew=0.7, zorder=6)
    ax2.set_ylim(R_LO, R_HI); ax2.set_yticks([70, 80, 90, 100, 110, 120, 130, 140, 150])
    ax2.spines['top'].set_visible(False); ax2.spines['right'].set_color('#bdbdb8')
    ax2.tick_params(axis='y', colors=MUTED, labelsize=7)
    ax2.set_ylabel('Index, 2020 = 100', color=MUTED, fontsize=7.6)
    ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False); ax2.set_zorder(1)
    h = [plt.Rectangle((0, 0), 1, 1, color=COLOR['ndvi'], alpha=0.55)] + \
        [plt.Line2D([], [], color=COLOR[k], lw=1.8, marker='o', ms=3.4)
         for k in ('ntl_total', 'ntl_buffer', 'mai')]
    fig.legend(h, ['Growing-season NDVI (left axis)'] + [LABEL[k] for k in
               ('ntl_total', 'ntl_buffer', 'mai')], loc='lower center', ncol=2,
               fontsize=7, frameon=False, bbox_to_anchor=(0.52, -0.16))
    return save(fig, 'fig06_ndvi_ntl_mai')


# ============================================================ 7. Hilmand splits (image13)
def fig07_hilmand():
    pa = C.panel()
    S = pd.concat([C.mai_series(pa[pa.admLvl1 != 'Hilmand'], 'Excluding Hilmand'),
                   C.mai_series(pa[pa.admLvl1 == 'Hilmand'], 'Hilmand only'),
                   C.mai_series(pa, 'Provinces weighted equally', by='admLvl1'),
                   C.mai_series(pa, 'All markets')], axis=1).reindex(YEARS)
    n_e = pa[pa.admLvl1 != 'Hilmand'].mktID.nunique(); n_h = pa[pa.admLvl1 == 'Hilmand'].mktID.nunique()
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    ax.bar(YEARS, S['All markets'] - 100, bottom=100, width=0.62, color='#d7d6d0', zorder=1)
    for col, key, lab in [('Excluding Hilmand', 'ntl_buffer', f'Excluding Hilmand (n={n_e})'),
                          ('Hilmand only', 'mai', f'Hilmand only (n={n_h})'),
                          ('Provinces weighted equally', 'ntl_total', 'Provinces weighted equally (n=24)')]:
        ax.plot(YEARS, S[col], '-o', color=COLOR[key], lw=1.8, ms=3.4, zorder=3, label=lab)
    ax.axvline(2022, color='#bdbdb8', ls='--', lw=0.9, zorder=2)
    ax.axhline(100, color='#a9a8a2', lw=0.9, zorder=2)
    grid(ax); years(ax)
    ax.set_ylabel('Market Activity Index, 2020 = 100', fontsize=7.6); ax.set_xlabel('Year', fontsize=7.6)
    h, l = ax.get_legend_handles_labels()
    h.append(plt.Rectangle((0, 0), 1, 1, color='#d7d6d0'))
    l.append(f'National MAI, all markets equally weighted (n={pa.mktID.nunique()})')
    ax.legend(h, l, fontsize=6.8, loc='lower left')
    return save(fig, 'fig07_hilmand')


# ============================================================ 8. MAI by access (image14)
def fig08_mai_by_access():
    pa = C.panel(); m = C.access_categories().set_index('mktID').access
    pa['access'] = pa.mktID.map(m)
    S = pd.concat([C.mai_series(pa[pa.access == k], k) for k in
                   ['High access', 'Intermediate access', 'Remote']] +
                  [C.mai_series(pa, 'All markets')], axis=1).reindex(YEARS)
    n = m.value_counts()
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    # All markets is the background bar, drawn from the 2020 base of 100 so that
    # the bar height reads as the deviation from 2020, as in fig07_hilmand.
    ax.bar(YEARS, S['All markets'] - 100, bottom=100, width=0.62, color='#d7d6d0', zorder=1)
    hs = []
    for k, key in [('High access', 'high'), ('Intermediate access', 'inter'), ('Remote', 'remote')]:
        hs += ax.plot(YEARS, S[k], '-o', color=COLOR[key], lw=1.8, ms=3.4,
                      label=f'{k} (n={n[k]})', zorder=3)
    ax.axvline(2022, color='#bdbdb8', ls='--', lw=0.9, zorder=2)
    ax.axhline(100, color='#a9a8a2', lw=0.9, zorder=2)
    grid(ax); years(ax)
    ax.set_ylabel('Market Activity Index, 2020 = 100', fontsize=7.6); ax.set_xlabel('Year', fontsize=7.6)
    ax.set_title('Intermediate-access markets fell furthest', fontsize=8, loc='left', pad=5)
    hs.append(plt.Rectangle((0, 0), 1, 1, color='#d7d6d0'))
    ax.legend(hs, [h.get_label() for h in hs[:3]] + [f'All markets (n={int(n.sum())})'],
              fontsize=6.8, loc='lower left')
    return save(fig, 'fig08_mai_by_access')


# ============================================================ 9. decline heat map (image15)
def fig09_decline_grid():
    pa = C.panel(); mm = C.market_year_activity(pa)
    chg = (100 * (mm[2025] / mm[2020] - 1)).rename('chg')
    m = C.access_categories().set_index('mktID').join(chg).dropna(subset=['chg'])
    m['tt'] = pd.qcut(m.travel_50, 3, labels=['Close', 'Mid', 'Far'])
    m['cp'] = pd.qcut(m.wp_SUM, 3, labels=['Sparse', 'Mid', 'Dense'])
    g = m.groupby(['tt', 'cp']).chg.agg(['mean', 'size']).reset_index()
    piv = g.pivot(index='tt', columns='cp', values='mean')
    cnt = g.pivot(index='tt', columns='cp', values='size')
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    im = ax.imshow(piv.values, cmap='RdYlGn', vmin=-35, vmax=10, aspect='auto')
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v, c = piv.values[i, j], cnt.values[i, j]
            ax.text(j, i, ('no\nmarkets' if np.isnan(v) else f'{v:+.1f}%\nn={int(c)}'),
                    ha='center', va='center', fontsize=7.4,
                    color=INK if not np.isnan(v) else MUTED)
    ax.set_xticks(range(3)); ax.set_xticklabels(piv.columns, fontsize=7.4)
    ax.set_yticks(range(3)); ax.set_yticklabels(piv.index, fontsize=7.4)
    ax.set_xlabel('Catchment population tercile', fontsize=7.6)
    ax.set_ylabel('Travel-time tercile', fontsize=7.6)
    for s in ax.spines.values(): s.set_visible(False)
    return save(fig, 'fig09_decline_grid')


# ============================================================ 10. regional panels (image16)
def fig10_region_panels():
    pa = C.panel()
    mai = pd.concat([C.mai_series(g, r) for r, g in pa.groupby('un_region')], axis=1).reindex(YEARS)
    mai = 100 * mai / mai.loc[2020]
    p2r = pa.drop_duplicates('admLvl1').set_index('admLvl1').un_region.to_dict()
    ALIAS = {'Badghes': 'Badghis', 'Kunarha': 'Kunar', 'Nemroz': 'Nimroz',
             'Pakteka': 'Paktika', 'Maydanwardag': 'Wardak'}
    n = pd.read_excel(C.NTL_ADU)
    n['region'] = n['province'].replace(ALIAS).map(p2r)
    n = n.dropna(subset=['region'])
    n = n[n.month.between(2, 6) & n.year.isin(YEARS)]
    tot = n.groupby(['region', 'year']).civilian_coalition.sum().unstack('region').sort_index()
    tot = 100 * tot / tot.loc[2020]
    mk = pa[['mktID', 'un_region']].drop_duplicates('mktID')
    buf = C.buffer_ntl(months=range(2, 7), markets=set(mk.mktID), stat='mean')
    buf = buf.join(mk.set_index('mktID').un_region).groupby('un_region').sum().T
    buf = 100 * buf / buf.loc[2020]
    MK = mk.un_region.value_counts()
    LET = 'abcdefg'
    fig, axs = plt.subplots(2, 4, figsize=(6.5, 3.9), sharex=True, sharey=True)
    for k, (ax, r) in enumerate(zip(axs.ravel(), REGIONS)):
        for s, key in [(tot[r], 'ntl_total'), (buf[r], 'ntl_buffer'), (mai[r], 'mai')]:
            ax.plot(YEARS, s.reindex(YEARS).values, '-o', color=COLOR[key], lw=1.3, ms=2.2, zorder=3)
        ax.text(0.04, 0.05, f'MAI {mai[r].loc[2025]-100:+.0f}', transform=ax.transAxes,
                fontsize=6.2, color=COLOR['mai'], fontweight='bold')
        grid(ax, 100); years(ax)
        ax.set_title(f'{LET[k]}. {RNAME.get(r, r)} ({MK[r]})', fontsize=7.2, loc='left', pad=3)
        ax.tick_params(labelsize=6.2); ax.set_xlim(2017.7, 2025.8)
    for ax in (axs[0, 0], axs[1, 0]): ax.set_ylabel('Index, 2020 = 100', fontsize=7)
    axs[1, 3].axis('off')
    h = [plt.Line2D([], [], color=COLOR[k], lw=1.6, marker='o', ms=3)
         for k in ('ntl_total', 'ntl_buffer', 'mai')]
    axs[1, 3].legend(h, [LABEL[k] for k in ('ntl_total', 'ntl_buffer', 'mai')], loc='center',
                     fontsize=6.4, frameon=False, handlelength=1.4, labelspacing=0.8)
    fig.tight_layout(pad=0.4)
    return save(fig, 'fig10_region_panels')


# ============================================================ 11. control status (image17/18)
def fig11_control_status():
    pa = C.panel()
    ctl = pd.read_csv(C.CONTROL)
    ctl['date'] = pd.to_datetime(ctl.date, errors='coerce')
    pre = ctl[ctl.date < '2021-01-01']          # status before the January 2021 transition
    st = pre.sort_values('date').groupby('district_id').status.last()
    # map markets to districts through the control panel's own province field
    import geopandas as gpd
    d2 = gpd.read_file(C.ADM2)[['Pcode_24', 'geometry']]
    cd = gpd.read_file(C.GEOJSON)[['district_id', 'geometry']]
    mk = pa.drop_duplicates('mktID')[['mktID', 'marketlat', 'marketlon']]
    gp = gpd.GeoDataFrame(mk, geometry=gpd.points_from_xy(mk.marketlon, mk.marketlat), crs='EPSG:4326')
    j = gpd.sjoin(gp, cd, how='left', predicate='within'); j = j[~j.index.duplicated()]
    pa['status'] = pa.mktID.map(j.set_index('mktID').district_id.map(st))
    GRP = {'Government Control': 'Government-held', 'Contested': 'Contested',
           'Taliban Control': 'Taliban-held'}
    pa['grp'] = pa.status.map(GRP)
    S = pd.concat([C.mai_series(pa[pa.grp == g], g) for g in
                   ['Government-held', 'Contested', 'Taliban-held'] if (pa.grp == g).any()],
                  axis=1).reindex(YEARS)
    Sd = pd.concat([C.mai_series(pa[pa.grp == g], g, by='mktID') for g in S.columns], axis=1).reindex(YEARS)
    n = pa.drop_duplicates('mktID').grp.value_counts()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9), sharey=True)
    for ax, D, ttl in [(a1, S, 'a. Averaging across markets'),
                       (a2, Sd, 'b. Averaging within districts first')]:
        for g, key in [('Government-held', 'gov'), ('Contested', 'contested'), ('Taliban-held', 'taliban')]:
            if g in D.columns:
                ax.plot(YEARS, D[g], '-o', color=COLOR[key], lw=1.6, ms=3,
                        label=f'{g} (n={int(n.get(g, 0))})', zorder=3)
        grid(ax, 100); years(ax)
        ax.set_title(ttl, fontsize=7.4, loc='left', pad=4); ax.set_xlabel('Year', fontsize=7.4)
    a1.set_ylabel('Index, 2020 = 100', fontsize=7.4); a1.legend(fontsize=6.5, loc='lower left')
    fig.tight_layout(pad=0.4)
    return save(fig, 'fig11_control_status')


# ============================================================ 12. overpass drift (image20/21)
def fig12_overpass():
    pa = C.panel()
    t = pa.image_id.str.slice(9, 15)
    tt = pd.to_datetime(t, format='%H%M%S', errors='coerce') + pd.Timedelta(hours=4, minutes=30)
    pa['minutes'] = tt.dt.hour * 60 + tt.dt.minute
    pa = pa.dropna(subset=['minutes', C.TARGET]).copy()
    pa['slot'] = (pa.minutes // 60).astype(int).map(lambda h: f'{h:02d}:00')
    vc = pa.slot.value_counts(); pa = pa[pa.slot.isin(vc[vc >= 200].index)]
    BASE = vc.idxmax(); slots = sorted(s for s in pa.slot.unique() if s != BASE)
    X = pd.DataFrame({f'T_{s}': (pa.slot == s).astype(float) for s in slots}, index=pa.index)
    for q in [2, 3, 4]: X[f'Q{q}'] = (pa.quarter == q).astype(float)
    for y in sorted(pa.year.unique())[1:]: X[f'Y{y}'] = (pa.year == y).astype(float)
    y = pa[C.TARGET].values.astype(float); g = pa.mktID.values
    yd = y - pd.Series(y, index=pa.index).groupby(g).transform('mean').values
    Xd = X.values - pd.DataFrame(X.values, index=pa.index).groupby(g).transform('mean').values
    b, *_ = np.linalg.lstsq(Xd, yd, rcond=None); r = yd - Xd @ b
    n_, k = Xd.shape; nabs = pa.mktID.nunique(); dof = n_ - k - nabs
    Xi = np.linalg.inv(Xd.T @ Xd); meat = np.zeros((k, k))
    for _, ix in pa.groupby('mktID').indices.items():
        xu = Xd[ix].T @ r[ix]; meat += np.outer(xu, xu)
    V = Xi @ meat @ Xi * (nabs / (nabs - 1)) * ((n_ - 1) / dof)
    se = pd.Series(np.sqrt(np.diag(V)), index=X.columns); bb = pd.Series(b, index=X.columns)
    ct = pd.crosstab(pa.year, pa.slot, normalize='index').loc[2018:2025] * 100
    COLS = ['#b9b9b3', COLOR['mai'], COLOR['ntl_total'], COLOR['ndvi'], COLOR['ntl_buffer']]
    WIN = dict(zip(ct.columns, COLS))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9))
    bot = np.zeros(len(ct))
    for c in ct.columns:
        a1.bar(range(len(ct)), ct[c], bottom=bot, color=WIN[c], label=c, width=0.74, zorder=3)
        bot += ct[c].values
    a1.set_xticks(range(len(ct))); a1.set_xticklabels([str(y)[2:] for y in ct.index])
    a1.set_ylabel('Share of market-day images, %', fontsize=7.4); a1.set_xlabel('Year', fontsize=7.4)
    a1.set_ylim(0, 104)
    a1.set_title('a. Imaging time drifts late after 2023', fontsize=7.4, loc='left', pad=4)
    a1.legend(fontsize=6, ncol=5, loc='upper left', bbox_to_anchor=(0, -0.18),
              columnspacing=0.9, handlelength=1.1, title='Overpass window', title_fontsize=6)
    lab = [s.replace('T_', '') for s in [c for c in X.columns if c.startswith('T_')]]
    vals = [bb[f'T_{l}'] for l in lab]; errs = [1.96 * se[f'T_{l}'] for l in lab]
    bi = sum(1 for l in lab if l < BASE)
    lab.insert(bi, BASE); vals.insert(bi, 0.0); errs.insert(bi, 0.0)
    a2.bar(range(len(lab)), vals, yerr=errs, capsize=2.5, color=[WIN[l] for l in lab],
           width=0.6, zorder=3, error_kw=dict(lw=0.9, ecolor=MUTED))
    grid(a2, 0); a2.set_xticks(range(len(lab))); a2.set_xticklabels(lab, rotation=45, ha='right')
    a2.set_ylabel(f'Index points vs the {BASE} window', fontsize=7.4)
    a2.set_xlabel('Overpass window (local time)', fontsize=7.4)
    a2.set_title('b. Late overpasses read lower, early ones higher', fontsize=7.4, loc='left', pad=4)
    fig.tight_layout(pad=0.4)
    return save(fig, 'fig12_overpass')


# ============================================================ 13. poppy (image23)
def fig13_poppy():
    POPPY = {'Hilmand', 'Kandahar', 'Uruzgan', 'Faryab', 'Nangarhar', 'Badakhshan',
             'Zabul', 'Farah', 'Nimroz'}
    pa = C.panel(); pa['poppy'] = pa.admLvl1.isin(POPPY)
    S = pd.concat([C.mai_series(pa[~pa.poppy], 'Non-poppy'),
                   C.mai_series(pa[pa.poppy], 'Poppy'),
                   C.mai_series(pa[pa.poppy & (pa.admLvl1 != 'Hilmand')], 'Poppy excl. Hilmand')],
                  axis=1).reindex(YEARS)
    n = pa.drop_duplicates('mktID').poppy.value_counts()
    HA = {'Hilmand': 122000, 'Kandahar': 29200, 'Uruzgan': 14600, 'Faryab': 6900,
          'Nangarhar': 5200, 'Badakhshan': 4300, 'Farah': 3000, 'Nimroz': 2000, 'Zabul': 1550}
    mm = C.market_year_activity(pa)
    chg = 100 * (mm[2025] / mm[2020] - 1)
    prov = pa.drop_duplicates('mktID').set_index('mktID').admLvl1
    P = pd.DataFrame({'chg': chg.groupby(prov).mean(), 'n': chg.groupby(prov).size()}).dropna()
    P['ha'] = P.index.map(HA).fillna(0)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9))
    for col, key, lab in [('Non-poppy', 'ntl_total', f'Non-poppy (n={n[False]})'),
                          ('Poppy', 'ntl_buffer', f'Poppy (n={n[True]})'),
                          ('Poppy excl. Hilmand', 'mai', 'Poppy excl. Hilmand')]:
        a1.plot(YEARS, S[col], '-o', color=COLOR[key], lw=1.6, ms=3, label=lab, zorder=3)
    a1.axvline(2022, color='#bdbdb8', ls='--', lw=0.9, zorder=1)
    grid(a1, 100); years(a1)
    a1.set_ylabel('MAI, 2020 = 100', fontsize=7.4); a1.set_xlabel('Year', fontsize=7.4)
    a1.set_title('a. By poppy exposure', fontsize=7.4, loc='left', pad=4)
    a1.legend(fontsize=6.4, loc='lower left')
    x = (P.ha > 0).astype(int) + np.random.RandomState(1).uniform(-.08, .08, len(P))
    a2.scatter(x, P.chg, s=8 + 3.2 * P.n, color=COLOR['ntl_total'], alpha=.55, edgecolor='none', zorder=3)
    for pn, row in P.iterrows():
        if row.n >= 8 or abs(row.chg) > 15:
            a2.annotate(pn, ((row.ha > 0) * 1.0, row.chg), fontsize=6, color=MUTED,
                        xytext=(6, -2), textcoords='offset points')
    rho = stats.spearmanr(P.ha, P.chg)
    a2.set_xticks([0, 1]); a2.set_xticklabels(['No poppy', 'Poppy'], fontsize=7)
    grid(a2, 0); a2.set_ylabel('Change in MAI, 2025 vs 2020 (%)', fontsize=7.4)
    a2.set_title(f'b. By province (Spearman {rho.correlation:+.2f}, p = {rho.pvalue:.2f})',
                 fontsize=7.4, loc='left', pad=4)
    fig.tight_layout(pad=0.4)
    return save(fig, 'fig13_poppy')


# ============================================================ 14. staggering (image25)
def fig14_staggering():
    import re
    st = C.staggering_test()
    pa = C.panel().drop_duplicates('mktID')
    days = pa.marketDays.apply(lambda x: {int(v) for v in re.findall(r'\d+', str(x))})
    LAB = {6: 'Sat', 0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri'}
    ORD = [6, 0, 1, 2, 3, 4, 5]
    cnt = pd.Series([d for s in days for d in s]).value_counts().reindex(ORD).fillna(0)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.7))
    a1.bar(range(7), cnt.values, color=COLOR['ntl_total'], width=0.7, zorder=3)
    for i, v in enumerate(cnt.values):
        a1.annotate(f'{int(v)}', (i, v), ha='center', fontsize=6.4, xytext=(0, 2),
                    textcoords='offset points')
    a1.set_xticks(range(7)); a1.set_xticklabels([LAB[d] for d in ORD])
    a1.set_ylabel('Markets operating', fontsize=7.4); grid(a1)
    a1.set_title('a. Days of operation', fontsize=7.4, loc='left', pad=4)
    # plotted as percentages, which is how the manuscript quotes them
    a2.fill_between(st.thr, 100 * st.lo, 100 * st.hi, color=COLOR['ntl_total'], alpha=.22, lw=0,
                    label='Random assignment of days (90% interval)', zorder=2)
    a2.plot(st.thr, 100 * st.obs, '-', color=COLOR['ntl_buffer'], lw=1.8, label='Observed', zorder=3)
    a2.plot(st.thr, 100 * st.null_mean, '--', color='#8f8e8a', lw=1.0, zorder=2)
    grid(a2); a2.set_xlabel('Maximum distance between markets in a pair (km)', fontsize=7.4)
    a2.set_ylabel('Pairs sharing a market day (%)', fontsize=7.4)
    a2.set_title('b. Nearby markets operate on different days', fontsize=7.4, loc='left', pad=4)
    a2.legend(fontsize=6.4, loc='upper right')
    fig.tight_layout(pad=0.4)
    return save(fig, 'fig14_staggering')


# ============================================================ 15. regional change (image26)
def fig15_region_change():
    pa = C.panel(); mm = C.market_year_activity(pa)
    chg = (100 * (mm[2025] / mm[2020] - 1)).rename('chg')
    m = pa.drop_duplicates('mktID').set_index('mktID')[['un_region', 'wp_SUM']].join(chg).dropna()
    g = m.groupby('un_region').apply(lambda s: pd.Series({
        'equal': s.chg.mean(), 'popw': np.average(s.chg, weights=s.wp_SUM), 'n': len(s)}))
    g = g.reindex(REGIONS).sort_values('equal')
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    y = np.arange(len(g)); h = 0.36
    ax.barh(y + h/2, g.equal, height=h, color='#7a7975', label='Equal-weighted (per market)', zorder=3)
    ax.barh(y - h/2, g.popw, height=h, color=COLOR['ntl_total'], label='Population-weighted', zorder=3)
    ax.axvline(0, color='#a8a8a3', lw=0.9, zorder=4)
    ax.set_yticks(y); ax.set_yticklabels([f'{RNAME.get(r, r)} (n={int(g.loc[r, "n"])})' for r in g.index],
                                         fontsize=7)
    ax.set_xlabel('Change in market activity, 2020 to 2025 (%)', fontsize=7.4)
    grid(ax, axis='x'); ax.legend(fontsize=6.8, loc='lower left')
    return save(fig, 'fig15_region_change')


# ================================================ 16. frequency pairs (image19)
def fig16_frequency_pairs(max_km=28, split_min=28):
    """Panel a: within neighbouring once-weekly / more-than-once-weekly pairs.
    Panel b: change 2020-2025 by trading frequency and proximity to a town.
    28 km is the threshold that reproduces the manuscript's 80 pairs."""
    import re
    pr = C.frequency_pairs(max_km)
    idx = C.market_index()
    o = idx.reindex(pr.once).reset_index(drop=True)
    t = idx.reindex(pr.twice).reset_index(drop=True)
    lv = pd.DataFrame({'once': o.mean(), 'twice': t.mean()}).reindex(YEARS)

    acc = C.access_categories().set_index('mktID')
    mk = C.panel().drop_duplicates('mktID').set_index('mktID')
    ndays = mk.marketDays.apply(lambda x: len(set(re.findall(r'\d+', str(x)))))
    chg = (idx[2025] - 100).rename('chg')
    B = pd.DataFrame({'chg': chg, 'ndays': ndays, 'travel': acc.travel_50}).dropna()
    B = B[B.ndays > 0]
    B['freq'] = np.where(B.ndays == 1, 'Once-weekly', 'Twice-weekly')
    B['prox'] = np.where(B.travel > split_min, f'Farther than {split_min} min',
                         f'Within {split_min} min')

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9))
    a1.plot(YEARS, lv.once, '-o', color=COLOR['ntl_total'], lw=1.7, ms=3.2,
            label='Once-weekly market', zorder=3)
    a1.plot(YEARS, lv.twice, '-o', color=COLOR['ntl_buffer'], lw=1.7, ms=3.2,
            label='More-than-once-weekly neighbour', zorder=3)
    a1.fill_between(YEARS, lv.once, lv.twice, color=COLOR['ntl_buffer'], alpha=.10, lw=0, zorder=2)
    gap = float((lv.once - lv.twice).max())
    a1.annotate(f'gap {gap:.0f} pts', (2024, (lv.once.loc[2024] + lv.twice.loc[2024]) / 2),
                fontsize=6.4, color=MUTED, ha='center')
    grid(a1, 100); years(a1)
    a1.set_ylabel('Index, 2020 = 100', fontsize=7.4); a1.set_xlabel('Year', fontsize=7.4)
    a1.set_title(f'a. Within {len(pr)} neighbouring pairs, the more frequent\n'
                 f'    market falls further', fontsize=7.4, loc='left', pad=4)
    a1.legend(fontsize=6.4, loc='lower left')

    ORD = [f'Within {split_min} min', f'Farther than {split_min} min']
    COL = {ORD[0]: COLOR['ntl_total'], ORD[1]: '#8f8e8a'}
    x = 0
    for f_ in ['Once-weekly', 'Twice-weekly']:
        for pxy in ORD:
            s_ = B[(B.freq == f_) & (B.prox == pxy)].chg
            m_ = s_.mean(); ci = 1.96 * s_.std(ddof=1) / np.sqrt(len(s_)) if len(s_) > 1 else 0
            a2.bar(x, m_, 0.72, color=COL[pxy], zorder=3)
            a2.errorbar(x, m_, yerr=ci, color=INK, lw=1.0, capsize=2.5, zorder=4)
            a2.annotate(f'n={len(s_)}', (x, 1.5), ha='center', fontsize=5.8, color=MUTED)
            x += 1
        x += 0.6
    a2.axhline(0, color='#8f8e8a', lw=0.9, zorder=2)
    a2.set_xticks([0.5, 3.1]); a2.set_xticklabels(['Once-weekly', 'Twice-weekly'], fontsize=7)
    a2.set_ylabel('Change in activity 2020-2025, %', fontsize=7.4)
    a2.set_title('b. Proximity protects once-weekly markets\n    and harms more frequent ones',
                 fontsize=7.4, loc='left', pad=4)
    grid(a2)
    h = [plt.Rectangle((0, 0), 1, 1, color=COL[k]) for k in ORD]
    a2.legend(h, ORD, fontsize=6.2, loc='lower left')
    fig.tight_layout(pad=0.4)
    print(f'   pairs {len(pr)} at {max_km} km; once-weekly {pr.once.nunique()}, '
          f'more-than-once {pr.twice.nunique()}; 2025 gap {lv.once.loc[2025]-lv.twice.loc[2025]:.1f} pts')
    return save(fig, 'fig16_frequency_pairs')


# ================================================ 17. non-market days (image22)
def fig17_nonmarket_days(alpha=0.05):
    """Do non-market days behave like market days?

    Sample: the markets active in every year 2018-2025, calendar 2025, one median
    observation per market-date. Top row compares a market's own market days with
    its non-market days. Each weekday row compares that non-market weekday with
    the same market's remaining non-market days. One-sided Welch t-tests; the
    weekday rows carry a Bonferroni correction over the whole family, the
    market-day benchmark is uncorrected.
    """
    from matplotlib.lines import Line2D
    DAY = {0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday',
           4: 'Thursday', 5: 'Friday', 6: 'Saturday'}
    ORD = [6, 0, 1, 2, 3, 4, 5]
    # the derived panel holds market days only, so this figure needs the raw
    # activity file, which carries every image whether or not it is a market day
    src = pd.read_csv(C.PANEL, low_memory=False)
    oc = [c for c in src.columns if c.startswith('open_')]
    flag = src.groupby('mktID')[oc].first()
    always = set(flag.index[(flag[oc] == 1).all(axis=1)])
    d = pd.read_csv(C.ACT_ALL, low_memory=False).rename(columns={'Location': 'mktID'})
    dt = pd.to_datetime(d.date, format='mixed')
    d['year'] = dt.dt.year; d['date_p'] = dt
    d['weekday'] = (dt.dt.dayofweek + 1) % 7                 # 0 = Sunday
    d = d[d[C.TARGET].notna() & (d.year == 2025) & d.mktID.isin(always)]
    g = (d.groupby(['mktID', 'date_p'])
           .agg(act=(C.TARGET, 'median'), mkt=('mktDay', 'max'),
                weekday=('weekday', 'first')).reset_index())

    def welch(x, y, minn=2):
        nx, ny = len(x), len(y)
        if nx < minn or ny < minn: return np.nan, np.nan
        vx, vy = x.var(ddof=1), y.var(ddof=1)
        se = np.sqrt(vx / nx + vy / ny)
        if se == 0 or not np.isfinite(se): return np.nan, np.nan
        t = (x.mean() - y.mean()) / se
        df = (vx / nx + vy / ny) ** 2 / ((vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
        return x.mean() - y.mean(), stats.t.sf(t, df)          # one-sided

    bench = [welch(s[s.mkt == 1].act, s[s.mkt == 0].act) for _, s in g.groupby('mktID')]
    bench = pd.DataFrame(bench, columns=['diff', 'p']).dropna()
    rows = []
    for m, s in g.groupby('mktID'):
        nm = s[s.mkt == 0]
        for wd in sorted(nm.weekday.unique(), key=ORD.index):
            dfe, pv = welch(nm.loc[nm.weekday == wd, 'act'], nm.loc[nm.weekday != wd, 'act'])
            rows.append({'weekday': DAY[wd], 'diff': dfe, 'p': pv})
    W = pd.DataFrame(rows).dropna()
    W['p_bonf'] = np.minimum(W.p * len(W), 1)

    R = [('Market day', bench['diff'].values, len(bench), (bench.p < alpha).mean(), 'head'),
         ('Non-market day tests', None, len(W), (W.p_bonf < alpha).mean(), 'sec')]
    for dd in [DAY[k] for k in ORD]:
        s_ = W[W.weekday == dd]
        R.append((dd, s_['diff'].values, len(s_), (s_.p_bonf < alpha).mean(), 'day'))
    R = R[::-1]                                        # matplotlib y grows upward
    data = {i: r[1] for i, r in enumerate(R, 1) if r[1] is not None}

    L, Wd, B, H = 0.150, 0.560, 0.225, 0.565
    fig = plt.figure(figsize=(6.5, 4.4))
    ax = fig.add_axes([L, B, Wd, H])
    pos = sorted(data)
    ax.boxplot([data[p_] for p_ in pos], positions=pos, vert=False, widths=0.44,
               whis=(5, 95), showfliers=False, patch_artist=True,
               medianprops=dict(color='white', lw=1.5),
               boxprops=dict(facecolor=COLOR['ntl_total'], edgecolor=COLOR['ntl_total'], lw=0),
               whiskerprops=dict(color=COLOR['ntl_total'], lw=1.5),
               capprops=dict(color=COLOR['ntl_total'], lw=1.5))
    ax.axvline(0, color=MUTED, lw=1.0, ls=(0, (4, 3)), alpha=0.5, zorder=0)
    ax.set_yticks(range(1, len(R) + 1)); ax.set_yticklabels([r[0] for r in R], fontsize=9)
    for lbl, r in zip(ax.get_yticklabels(), R):
        if r[4] == 'head': lbl.set_fontweight('bold')
        if r[4] == 'sec': lbl.set_style('italic'); lbl.set_color(MUTED); lbl.set_fontsize(8)
    ax.tick_params(axis='y', length=0, pad=10); ax.tick_params(axis='x', labelsize=8)
    for sp in ('top', 'right', 'left'): ax.spines[sp].set_visible(False)
    grid(ax, axis='x'); ax.set_ylim(0.4, len(R) + 0.6)
    ax.set_xlabel('Difference in mean activity index  (points)', fontsize=9)

    XL, X1, X2, XR = L - 0.078, L + Wd + 0.075, L + Wd + 0.235, L + Wd + 0.305
    row_y = lambda i: B + H * (i - 0.4) / (len(R) + 0.2)
    fig.text(X1, B + H + 0.028, 'No. of\ntests', ha='center', va='bottom',
             fontsize=8, color=MUTED)
    fig.text(X2, B + H + 0.028, 'Share of positive\ntests (5%)', ha='center', va='bottom',
             fontsize=8, color=MUTED)
    for yy in (B + H + 0.020, row_y(len(R) - 0.5)):
        fig.add_artist(Line2D([XL, XR], [yy, yy], color='#c9c8c2', lw=0.9))
    for i, r in enumerate(R, 1):
        fw = 'bold' if r[4] == 'head' else 'normal'
        st_ = 'italic' if r[4] == 'sec' else 'normal'
        col = MUTED if r[4] == 'sec' else INK
        fig.text(X1, row_y(i), f'{r[2]}', ha='center', va='center', fontsize=9,
                 color=col, fontweight=fw, style=st_)
        fig.text(X2, row_y(i), f'{100*r[3]:.1f}%', ha='center', va='center', fontsize=9,
                 color=INK if r[3] > 0.05 else MUTED, fontweight=fw, style=st_)
    print(f'   {len(bench)} markets, {len(W)} weekday tests, '
          f'benchmark {100*(bench.p<alpha).mean():.1f}% positive, '
          f'weekday rows {int((W.p_bonf<alpha).sum())} surviving Bonferroni')
    return save(fig, 'fig17_nonmarket_days')


# ================================================ 18. NTL per capita by control (image18)
def fig18_ntl_by_control():
    """Nighttime emissions in the 10 km market buffers, by the market district's
    control status before January 2021, per person in the market's 30-minute
    catchment. Buffer emissions only; no district-wide lights enter."""
    pa = C.panel(include_herat=False)
    mk = pa.drop_duplicates('mktID')[['mktID', 'marketlat', 'marketlon', 'wp_SUM']]
    ctl = pd.read_csv(C.CONTROL); ctl['date'] = pd.to_datetime(ctl.date, errors='coerce')
    st = ctl[ctl.date < '2021-01-01'].sort_values('date').groupby('district_id').status.last()
    cd = gpd.read_file(C.GEOJSON)[['district_id', 'geometry']]
    gp = gpd.GeoDataFrame(mk, geometry=gpd.points_from_xy(mk.marketlon, mk.marketlat),
                          crs='EPSG:4326')
    j = gpd.sjoin(gp, cd, how='left', predicate='within'); j = j[~j.index.duplicated()]
    G = {'Government Control': 'Government-held', 'Contested': 'Contested',
         'Taliban Control': 'Taliban-held'}
    mk = mk.set_index('mktID')
    mk['grp'] = j.set_index('mktID').district_id.map(st).map(G)
    mk = mk.dropna(subset=['grp'])

    buf = C.buffer_ntl(markets=set(mk.index), stat='mean')       # market x year
    B = buf.join(mk[['grp', 'wp_SUM']])
    g = B.groupby('grp').apply(lambda s: pd.Series(
        {y: s[y].sum() / s.wp_SUM.sum() for y in YEARS}))
    idx = 100 * g.div(g[2020], axis=0)
    n = mk.grp.value_counts()

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9))
    for k, key in [('Government-held', 'gov'), ('Contested', 'contested'),
                   ('Taliban-held', 'taliban')]:
        if k not in g.index: continue
        a1.plot(YEARS, g.loc[k].values, '-o', color=COLOR[key], lw=1.6, ms=3,
                label=f'{k} ({int(n.get(k, 0))} markets)', zorder=3)
        a2.plot(YEARS, idx.loc[k].values, '-o', color=COLOR[key], lw=1.6, ms=3, zorder=3)
    for ax, ttl, yl in [(a1, 'a. Buffer emissions per person in the catchment',
                         'Radiance per person'),
                        (a2, 'b. Indexed to 2020 = 100', 'Index, 2020 = 100')]:
        grid(ax); years(ax)
        ax.set_title(ttl, fontsize=7.2, loc='left', pad=4)
        ax.set_xlabel('Year', fontsize=7.4); ax.set_ylabel(yl, fontsize=7.4)
    a2.axhline(100, color=RULE, lw=0.9, zorder=1)
    a1.legend(fontsize=6.2, loc='upper left')
    fig.tight_layout(pad=0.4)
    print(f'   markets by 2020 status: {n.to_dict()}')
    return save(fig, 'fig18_ntl_by_control')


# ================================================ 19. nightlights per capita by control status
def fig19_ntl_per_capita_by_control(zero_base=True):
    """Civilian nightlights per person by 2020 district control status, in levels
    and indexed. See common.ntl_per_capita_by_control() for the allocation.

    zero_base keeps the levels panel anchored at zero, so the gap between
    government-held districts and the other two reads at true scale. Pass False
    for the truncated axis the original version of this exhibit used.
    """
    pc, popg = C.ntl_per_capita_by_control()
    ORD = ['Government-held', 'Contested', 'Taliban-held']
    KEY = {'Government-held': 'gov', 'Contested': 'contested', 'Taliban-held': 'taliban'}
    idx = 100 * pc / pc.loc[2020]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 3.0))
    for ax, S, ttl, ylab in [(a1, pc, 'a. Nighttime emissions per capita', 'Radiance per person'),
                             (a2, idx, 'b. Indexed to 2020 = 100', 'Index, 2020 = 100')]:
        # nudge end labels apart where two series finish within a hair of each other
        ends = {k: S[k].iloc[-1] for k in ORD}
        span = max(ends.values()) - min(ends.values())
        off = {k: 0.0 for k in ORD}
        for lo, hi in [(a, b) for i, a in enumerate(ORD) for b in ORD[i + 1:]]:
            if abs(ends[lo] - ends[hi]) < 0.05 * span:
                top, bot = (lo, hi) if ends[lo] >= ends[hi] else (hi, lo)
                off[top] += 4.0; off[bot] -= 4.0
        for k in ORD:
            c = COLOR[KEY[k]]
            ax.plot(YEARS, S[k], '-', color=c, lw=1.7, zorder=3)
            ax.plot([YEARS[-1]], [S[k].iloc[-1]], 'o', color=c, ms=3.6, zorder=4)
            ax.annotate(f' {k}', (YEARS[-1], S[k].iloc[-1]), color=c, fontsize=6.6,
                        va='center', ha='left', annotation_clip=False,
                        xytext=(2, off[k]), textcoords='offset points')
        grid(ax); years(ax)
        ax.set_title(ttl, fontsize=7.4, loc='left', pad=4)
        ax.set_ylabel(ylab, fontsize=7.4); ax.set_xlabel('Year', fontsize=7.4)
        ax.set_xlim(2017.7, 2026.9)
    if zero_base:
        a1.set_ylim(0, None)
    a2.axhline(100, color='#a9a8a2', lw=0.9, zorder=2)
    fig.tight_layout(pad=0.4)
    p20 = (popg.loc[2020] / 1e6).round(1)
    print('   2020 population (m): ' + ', '.join(f'{k} {p20[k]}' for k in ORD))
    return save(fig, 'fig19_ntl_per_capita_by_control')


ALL = [fig01_region_map, fig02_days_of_operation, fig03_access_categories,
       fig04_emissions_by_access, fig05_gdp_vs_mai, fig06_ndvi_ntl_mai, fig07_hilmand,
       fig08_mai_by_access, fig09_decline_grid, fig10_region_panels, fig11_control_status,
       fig12_overpass, fig13_poppy, fig14_staggering, fig15_region_change, fig16_frequency_pairs, fig17_nonmarket_days, fig18_ntl_by_control,
       fig19_ntl_per_capita_by_control]
