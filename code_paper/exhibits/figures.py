"""Paper figures made by the exhibits package. One function per figure file.

Every function writes to the shared paper_exhibits folder (config.PAPER_EXHIBITS),
under the paper's exhibit number. Where the paper shows panels as separate images,
each panel is its own function and file, drawn without an in-figure title (the
paper's caption carries the panel title).

    PAPER EXHIBIT        FUNCTION                       FILE
    Figure 5, panel a    fig05a_access_categories       fig05a_access_categories.png
    Figure 8             fig08_regions                  fig08_regions.png
    Figure A.1           figA1_validation_samples       figA1_validation_samples.png
    Figure A.2           figA2_poppy                    figA2_poppy.png
    Figure A.4, panel a  figA4a_overpass_composition    figA4a_overpass_composition.png
    Figure A.4, panel b  figA4b_overpass_effects        figA4b_overpass_effects.png

The rest of the paper's figures are made elsewhere; EXHIBITS.md at the repository
root lists every exhibit and where it is made. Figures that are not in the final
paper are in archive/exhibits/figures_full.py.
"""
import common as C
from common import (plt, pd, np, COLOR, LABEL, MUTED, YEARS, REGIONS, RNAME,
                    grid, years, save_paper)
from matplotlib.ticker import FuncFormatter


# ============================================================ Figure 5, panel a
def fig05a_access_categories():
    """Figure 5a. Access categories defined by proximity and catchment population:
    travel time to a 50,000+ settlement against population within 30 minutes."""
    m = C.access_categories()
    AC = {'High access': COLOR['high'], 'Intermediate access': COLOR['inter'], 'Remote': COLOR['remote']}
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    for k, c in AC.items():
        s = m[m.access == k]
        ax.scatter(s.travel_50, s.wp_SUM / 1000, s=11, color=c, alpha=0.75,
                   edgecolor='none', label=f'{k} ({len(s)})', zorder=3)
    ax.axvline(40, color='#999995', ls='--', lw=0.9, zorder=2)
    ax.axhline(250, color='#999995', ls='--', lw=0.9, zorder=2)
    ax.set_yscale('log'); ax.set_yticks([10, 50, 250, 1000, 5000])
    ax.get_yaxis().set_major_formatter(FuncFormatter(lambda v, p: f'{v:,.0f}'))
    ax.set_xlabel('Travel time to a settlement of\n50,000 or more (minutes)', fontsize=7)
    ax.set_ylabel('Catchment population within\n30 minutes (thousands)', fontsize=7)
    grid(ax, axis='both'); ax.legend(fontsize=5.9, loc='upper right')
    fig.tight_layout(pad=0.4)
    return save_paper(fig, 'fig05a_access_categories')


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
    return save_paper(fig, 'fig08_regions')


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
    a. the three series; b. each subsample minus the full sample."""
    A1, N = validation_series()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 2.9))
    STY = {'All markets': (C.INK, '-', 'o'), 'Exact schedule match': (COLOR['mai'], '--', 's'),
           'Exact match + validated MAI day': (COLOR['ntl_total'], ':', '^')}
    for lab, (col, ls, mkr) in STY.items():
        a1.plot(A1.index, A1[lab], ls=ls, marker=mkr, ms=3, lw=1.6, color=col,
                label=f'{lab} (n={N[lab]})', zorder=3)
        if lab != 'All markets':
            a2.plot(A1.index, A1[lab] - A1['All markets'], ls=ls, marker=mkr, ms=3, lw=1.6,
                    color=col, zorder=3)
    grid(a1, 100); years(a1); grid(a2, 0); years(a2)
    a1.set_ylabel('Index, 2020 = 100', fontsize=7.4)
    a2.set_ylabel('Difference from all markets (points)', fontsize=7.4)
    a1.set_title('a. Market activity by sample', fontsize=7.4, loc='left', pad=4)
    a2.set_title('b. Restricted sample minus full sample', fontsize=7.4, loc='left', pad=4)
    a2.set_ylim(-5, 5)
    a1.legend(fontsize=6.2, loc='lower left')
    fig.tight_layout(pad=0.4)
    return save_paper(fig, 'figA1_validation_samples')


# ============================================================ Figure A.2
POPPY = {'Hilmand', 'Kandahar', 'Uruzgan', 'Faryab', 'Nangarhar', 'Badakhshan',
         'Zabul', 'Farah', 'Nimroz'}     # provinces with UNODC-recorded poppy area in 2022


def figA2_poppy():
    """Figure A.2. Market activity by provincial poppy cultivation before the 2022
    ban: non-poppy, poppy, and poppy excluding Hilmand."""
    pa = C.panel(); pa['poppy'] = pa.admLvl1.isin(POPPY)
    S = pd.concat([C.mai_series(pa[~pa.poppy], 'Non-poppy'),
                   C.mai_series(pa[pa.poppy], 'Poppy'),
                   C.mai_series(pa[pa.poppy & (pa.admLvl1 != 'Hilmand')], 'Poppy excl. Hilmand')],
                  axis=1).reindex(YEARS)
    n = pa.drop_duplicates('mktID').poppy.value_counts()
    n_xh = pa[pa.poppy & (pa.admLvl1 != 'Hilmand')].mktID.nunique()
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    for col, key, lab in [('Non-poppy', 'ntl_total', f'Non-poppy (n={n[False]})'),
                          ('Poppy', 'ntl_buffer', f'Poppy (n={n[True]})'),
                          ('Poppy excl. Hilmand', 'mai', f'Poppy excl. Hilmand (n={n_xh})')]:
        ax.plot(YEARS, S[col], '-o', color=COLOR[key], lw=1.6, ms=3, label=lab, zorder=3)
    ax.axvline(2022, color='#bdbdb8', ls='--', lw=0.9, zorder=1)
    grid(ax, 100); years(ax)
    ax.set_ylabel('MAI, 2020 = 100', fontsize=7.4); ax.set_xlabel('Year', fontsize=7.4)
    ax.legend(fontsize=6.4, loc='lower left')
    fig.tight_layout(pad=0.4)
    return save_paper(fig, 'figA2_poppy')


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


def _window_colors(cols):
    return dict(zip(cols, ['#b9b9b3', COLOR['mai'], COLOR['ntl_total'], COLOR['ndvi'], COLOR['ntl_buffer']]))


def figA4a_overpass_composition():
    """Figure A.4a. Distribution of market-day images by one-hour overpass window."""
    ct, _, _ = overpass_windows()
    WIN = _window_colors(ct.columns)
    fig, ax = plt.subplots(figsize=(3.3, 2.9))
    bot = np.zeros(len(ct))
    for c in ct.columns:
        ax.bar(range(len(ct)), ct[c], bottom=bot, color=WIN[c], label=c, width=0.74, zorder=3)
        bot += ct[c].values
    ax.set_xticks(range(len(ct))); ax.set_xticklabels([str(y)[2:] for y in ct.index])
    ax.set_ylabel('Share of market-day images, %', fontsize=7.4); ax.set_xlabel('Year', fontsize=7.4)
    ax.set_ylim(0, 104)
    ax.legend(fontsize=6, ncol=5, loc='upper left', bbox_to_anchor=(0, -0.18),
              columnspacing=0.9, handlelength=1.1, title='Overpass window', title_fontsize=6)
    fig.tight_layout(pad=0.4)
    return save_paper(fig, 'figA4a_overpass_composition')


def figA4b_overpass_effects():
    """Figure A.4b. Estimated differences in measured activity by overpass window,
    relative to the 10:00 window, with 95% confidence intervals."""
    ct, eff, BASE = overpass_windows()
    WIN = _window_colors(ct.columns)
    fig, ax = plt.subplots(figsize=(3.3, 2.9))
    ax.bar(range(len(eff)), eff.coef, yerr=1.96 * eff.se, capsize=2.5,
           color=[WIN[l] for l in eff.index], width=0.6, zorder=3,
           error_kw=dict(lw=0.9, ecolor=MUTED))
    grid(ax, 0); ax.set_xticks(range(len(eff))); ax.set_xticklabels(eff.index, rotation=45, ha='right')
    ax.set_ylabel(f'Index points vs the {BASE} window', fontsize=7.4)
    ax.set_xlabel('Overpass window (local time)', fontsize=7.4)
    fig.tight_layout(pad=0.4)
    return save_paper(fig, 'figA4b_overpass_effects')


ALL = [fig05a_access_categories, fig08_regions, figA1_validation_samples, figA2_poppy,
       figA4a_overpass_composition, figA4b_overpass_effects]


if __name__ == '__main__':
    for f in ALL:
        print('---', f.__name__); f()
