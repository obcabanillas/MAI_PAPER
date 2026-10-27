"""Paper figures made by the exhibits package. One function per figure file.

Every function writes to the shared paper_exhibits folder (config.PAPER_EXHIBITS),
under the paper's exhibit number. Where the paper shows panels as separate images,
each panel is its own function and file, drawn without an in-figure title (the
paper's caption carries the panel title).

    PAPER EXHIBIT        FUNCTION                       FILE
    Figure 5, panel a    fig05a_access_categories       fig05a_access_categories.png
    Figure 8             fig08_regions                  fig08_regions.png
    Figure A.1, a and b  figA1_validation_samples       figA1a_validation_samples.png,
                                                        figA1b_validation_difference.png
    Figure A.2           figA2_poppy                    figA2_poppy.png
    Figure A.4, panel a  figA4a_overpass_composition    figA4a_overpass_composition.png
    Figure A.4, panel b  figA4b_overpass_effects        figA4b_overpass_effects.png

Each function computes the data its figure shows, saves it to
paper_exhibits/data/ (style.save_data) and draws it with the matching function in
plots.py, where all the drawing and styling lives.

The rest of the paper's figures are made elsewhere; EXHIBITS.md at the repository
root lists every exhibit and where it is made. Figures that are not in the final
paper are in archive/exhibits/figures_full.py.
"""
import common as C
from common import pd, np, YEARS
import plots as P
import style as S


def _out(d, name, *panels):
    """Save the figure data under `name` and draw and save each panel from it."""
    S.save_data(d, name)
    return [S.save(P.PANELS[p](d), p) for p in (panels or (name,))]


# ============================================================ Figure 5, panel a
def fig05a_access_categories():
    """Figure 5a. Access categories defined by proximity and catchment population:
    travel time to a 50,000+ settlement against population within 30 minutes."""
    m = C.access_categories()
    d = pd.DataFrame({'mktID': m.mktID, 'travel_50': m.travel_50,
                      'pop_thousands': m.wp_SUM / 1000, 'access': m.access})
    return _out(d, 'fig05a_access_categories')


# ============================================================ Figure 8
def fig08_regions():
    """Figure 8. Market activity and civilian nighttime-light emissions by region:
    seven panels (a-g), total NTL, NTL in 10 km market buffers and the MAI."""
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
    d = pd.concat([pd.DataFrame({'region': r, 'n_markets': int(MK[r]), 'year': YEARS,
                                 'ntl_total': tot[r].reindex(YEARS).values,
                                 'ntl_buffer': buf[r].reindex(YEARS).values,
                                 'mai': mai[r].reindex(YEARS).values}) for r in C.REGIONS])
    return _out(d, 'fig08_regions')


# ============================================================ Figure A.1
def validation_samples():
    """The two field-validation subsamples of Figure A.1, from the WFP classification.
      exact : exact schedule match, or a daily bazaar whose main day matches (94)
      broad : exact plus partial overlaps where the field adds a day the MAI does
              not detect, i.e. the MAI-predicted day is corroborated (107)"""
    w = C.wfp_validation()
    exact = w.mktID[w.day_match.isin(['Exact match', 'Continuous bazaar, main day correct'])]
    extra = w.mktID[(w.day_match == 'Partial overlap') &
                    (w.partial_type == 'Field reports an extra day the MAI does not detect')]
    return exact, pd.concat([exact, extra])


def validation_series():
    """Annual MAI for all markets and for the two subsamples, 2020 = 100."""
    pa = C.panel()
    exact, broad = validation_samples()
    S = {'All markets': C.mai_series(pa)}
    for lab, ids in [('Exact schedule match', exact), ('Exact match + validated MAI day', broad)]:
        s = C.mai_series(pa[pa.mktID.isin(ids)])
        S[lab] = 100 * s / s.loc[2020]
    return pd.DataFrame(S).loc[2018:2025], {'All markets': pa.mktID.nunique(),
                                            'Exact schedule match': len(exact),
                                            'Exact match + validated MAI day': len(broad)}


def figA1_validation_samples():
    """Figure A.1. Market activity under alternative field-validation samples:
    panel a the three series; panel b each subsample minus the full sample."""
    A1, N = validation_series()
    d = A1.rename_axis('year').reset_index().melt('year', var_name='sample', value_name='index')
    d.insert(1, 'n', d['sample'].map(N))
    return _out(d, 'figA1_validation_samples',
                'figA1a_validation_samples', 'figA1b_validation_difference')


# ============================================================ Figure A.2
POPPY = {'Hilmand', 'Kandahar', 'Uruzgan', 'Faryab', 'Nangarhar', 'Badakhshan',
         'Zabul', 'Farah', 'Nimroz'}     # provinces with UNODC-recorded poppy area in 2022


def figA2_poppy():
    """Figure A.2. Market activity by provincial poppy cultivation before the 2022
    ban: non-poppy, poppy, and poppy excluding Hilmand."""
    pa = C.panel(); pa['poppy'] = pa.admLvl1.isin(POPPY)
    S_ = pd.concat([C.mai_series(pa[~pa.poppy], 'Non-poppy'),
                   C.mai_series(pa[pa.poppy], 'Poppy'),
                   C.mai_series(pa[pa.poppy & (pa.admLvl1 != 'Hilmand')], 'Poppy excl. Hilmand')],
                  axis=1).reindex(YEARS)
    n = pa.drop_duplicates('mktID').poppy.value_counts()
    n_xh = pa[pa.poppy & (pa.admLvl1 != 'Hilmand')].mktID.nunique()
    N = {'Non-poppy': int(n[False]), 'Poppy': int(n[True]), 'Poppy excl. Hilmand': n_xh}
    d = S_.rename_axis('year').reset_index().melt('year', var_name='group', value_name='index')
    d.insert(1, 'n', d.group.map(N))
    return _out(d, 'figA2_poppy')


# ============================================================ Figure A.4
def overpass_windows():
    """Image share by one-hour overpass window and year, and the time-window effects.

    Regression (Figure A.4 panel b): market-day activity on window dummies (the
    modal 10:00 window omitted), quarter and year dummies, with market fixed effects
    (within transformation) and standard errors clustered by market. Windows with
    fewer than 200 images are dropped. Local time is UTC + 4:30."""
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
    lab = [c.replace('T_', '') for c in X.columns if c.startswith('T_')]
    eff = pd.DataFrame({'coef': [bb[f'T_{l}'] for l in lab], 'se': [se[f'T_{l}'] for l in lab]}, index=lab)
    eff.loc[BASE] = [0.0, 0.0]
    return ct, eff.sort_index(), BASE


def figA4a_overpass_composition():
    """Figure A.4a. Distribution of market-day images by one-hour overpass window."""
    ct, _, _ = overpass_windows()
    d = ct.rename_axis('year').reset_index().melt('year', var_name='window', value_name='share')
    return _out(d, 'figA4a_overpass_composition')


def figA4b_overpass_effects():
    """Figure A.4b. Estimated differences in measured activity by overpass window,
    relative to the 10:00 window, with 95% confidence intervals."""
    _, eff, BASE = overpass_windows()
    d = eff.rename_axis('window').reset_index()
    d['base'] = (d.window == BASE).astype(int)
    return _out(d, 'figA4b_overpass_effects')


ALL = [fig05a_access_categories, fig08_regions, figA1_validation_samples, figA2_poppy,
       figA4a_overpass_composition, figA4b_overpass_effects]


if __name__ == '__main__':
    for f in ALL:
        print('---', f.__name__); f()
