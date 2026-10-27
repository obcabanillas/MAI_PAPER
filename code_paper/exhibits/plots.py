"""One drawing function per figure panel in the paper.

Each function takes the data the panel shows, already computed, and returns a
matplotlib figure at its printed size. The analysis that produces the data stays
where it was (figures.py, the notebooks, figure4_population_coverage.py); each of
those saves the plotted data with style.save_data() and then calls the function
here. draw(name) reloads that data and redraws, so the look of every figure can be
changed without rerunning any analysis.

Colours, sizes and fonts come from style.py. Titles, panel letters and notes are
set in Word, so no function draws them.

    PAPER EXHIBIT        FUNCTION                        DATA (paper_exhibits/data/)
    Figure 3, panel a    fig03a_market_map               fig03a_market_map.csv
    Figure 3, panel b    fig03b_days_of_operation        fig03b_days_of_operation.csv
    Figure 4, panel a    fig04a_population_coverage      fig04a_population_coverage.csv
    Figure 4, panel b    fig04b_osm_coverage             fig04b_osm_coverage.csv
                         (pair: fig04_population_coverage)
    Figure 5, panel a    fig05a_access_categories        fig05a_access_categories.csv
    Figure 5, panel b    fig05b_positive_emissions       fig05b_positive_emissions.csv
    Figure 5, panel c    fig05c_ntl_cdf                  fig05c_ntl_cdf__{values,kabul}.csv
    Figure 6, panel a    fig06a_monthly_activity         fig06a_monthly_activity.csv
    Figure 6, panel b    fig06b_seasonality_by_goods     fig06b_seasonality_by_goods.csv
    Figure 7, panel a    fig07a_mai_gdp                  fig07a_mai_gdp.csv
    Figure 7, panel b    fig07b_mai_ntl                  fig07b_mai_ntl.csv
    Figure 8             fig08_regions                   fig08_regions.csv
    Figure A.1, a and b  figA1a_validation_samples,      figA1_validation_samples.csv
                         figA1b_validation_difference
    Figure A.2           figA2_poppy                     figA2_poppy.csv
    Figure A.3, a and b  figA3a_last_signal,             figA3_signal_timing.csv
                         figA3b_first_signal
    Figure A.4, a and b  figA4a_overpass_composition,    figA4a_overpass_composition.csv,
                         figA4b_overpass_effects         figA4b_overpass_effects.csv

    Figure 9, a to d     fig09a_ ... fig09d_ (pairs fig09ab_, fig09cd_)  from event_study.py
    Figure 10, a and b   fig10a_, fig10b_ (pair fig10ab_ntl)             from event_study.py
"""

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator, PercentFormatter

import style as S

YEARS = list(range(2018, 2026))
WEEKDAYS = ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri']     # the Afghan week


def _lines(ax, x, series, labels=None, dashed=(), markers=True):
    """Draw {key: values} as lines in their SERIES colours; keys in `dashed` are
    comparison series, drawn grey-dashed when their colour is NEUTRAL."""
    for k, y in series.items():
        ls = '--' if k in dashed else '-'
        ax.plot(x, y, ls=ls, color=S.SERIES.get(k, S.NEUTRAL), marker='o' if markers else None,
                ms=S.MS, label=(labels or S.SERIES_LABEL).get(k, k), zorder=3)


# ============================================================ Figure 3
def provinces():
    """Province polygons with their UN region, from the ADM1 file exhibits/ reads."""
    import geopandas as gpd
    import common as C                      # only imported for the map's input path
    a = gpd.read_file(C.ADM1)
    CSO = {'Central': 'Central', 'East': 'East', 'Northeast': 'NorthEast', 'North': 'NorthWest',
           'South': 'SouthEast', 'Southwest': 'SouthWest', 'West': 'West', 'WestCentral': 'West'}
    a['region'] = a.CSO_Region.map(CSO)
    return a


def fig03a_market_map(d, ax=None, prov=None, width=S.HALF, height=2.75, fill_alpha=0.55):
    """Figure 3a. Provinces shaded by UN region; the detected markets as dots.
    d: one row per market (marketlon, marketlat, un_region)."""
    prov = provinces() if prov is None else prov
    fig, ax = S.axes(ax, width, height)
    for r in S.REGIONS:
        prov[prov.region == r].plot(ax=ax, color=S.REGION[r], alpha=fill_alpha,
                                    edgecolor='white', lw=0.3)
    prov.dissolve().boundary.plot(ax=ax, color=S.INK, lw=0.6)
    ax.scatter(d.marketlon, d.marketlat, s=2.0, color=S.INK, zorder=5, linewidths=0)
    ax.set_axis_off(); ax.set_aspect('equal')
    n = d.un_region.value_counts()
    h = [Patch(facecolor=S.REGION[r], alpha=fill_alpha, edgecolor='none') for r in S.REGIONS] + \
        [Line2D([], [], marker='o', ls='', color=S.INK, ms=2.2)]
    lab = [f'{S.REGION_NAME.get(r, r)} ({int(n.get(r, 0))})' for r in S.REGIONS] + \
          [f'Detected market ({len(d)})']
    ax.legend(h, lab, loc='upper center', bbox_to_anchor=(0.5, -0.04), fontsize=6, ncol=3,
              handlelength=1.0, handletextpad=0.4, columnspacing=1.0, labelspacing=0.35)
    return fig


def fig03b_days_of_operation(d, ax=None, width=S.HALF, height=2.4, labels=True):
    """Figure 3b. Share of market days on each weekday, once-a-week markets against
    markets trading more than once a week. d: day, group, share, n."""
    fig, ax = S.axes(ax, width, height)
    groups = list(dict.fromkeys(d.group))
    dark, light = S.shades(S.ACCENT, 2)          # more frequent markets dark, as in Figure 9d
    cols = [light if g.lower().startswith('once') else dark for g in groups]
    x = np.arange(7); w = 0.4
    for j, (g, c) in enumerate(zip(groups, cols)):
        s = d[d.group == g].set_index('day').reindex(WEEKDAYS)
        xs = x + (j - 0.5) * w
        ax.bar(xs, s.share, w * 0.92, color=c, label=f'{g} (n = {int(s.n.iloc[0])})', zorder=3)
        if labels:
            for xi, v in zip(xs, s.share):
                ax.annotate(f'{v:.0f}', (xi, v), xytext=(0, 1.5), textcoords='offset points',
                            ha='center', fontsize=5.5, color=S.MUTED)
    ax.set_xticks(x); ax.set_xticklabels(WEEKDAYS)
    ax.set_ylabel('Share of market days (%)')
    ax.set_ylim(0, d.share.max() * 1.35)
    ax.legend(loc='upper left')
    return fig


# ============================================================ Figure 4
def fig04a_population_coverage(d, ax=None, width=S.HALF, height=2.4,
                               xlabel='Distance from nearest detected market (km)'):
    """Figure 4a. Share of population and area within each distance of a detected
    market, in the reference notebook's outlined bars.
    d: radius_km, population_share, population_share_nocities, area_share."""
    fig, ax = S.axes(ax, width, height)
    x = np.arange(len(d))
    ax.bar(x, d.population_share_nocities, color='none', edgecolor=S.ACCENT, lw=1.0, ls='--',
           label='Population excl. major cities')
    ax.bar(x, d.population_share, color='none', edgecolor=S.ACCENT, lw=1.0, label='Population')
    ax.bar(x, d.area_share, color='none', edgecolor=S.NEUTRAL, lw=1.0, width=0.5, label='Area')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{v:g}' for v in d.radius_km])
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Share within given distance (%)')
    ax.legend(loc='upper left')
    return fig


def fig04b_osm_coverage(d, ax=None, width=S.HALF, height=2.4):
    """Figure 4b. The same shares around OpenStreetMap marketplaces that do not
    coincide with a periodic market."""
    return fig04a_population_coverage(
        d, ax=ax, width=width, height=height,
        xlabel='Distance from nearest OSM market (km),\nexcluding periodic markets')


# ============================================================ Figure 5
def fig05a_access_categories(d, ax=None, width=S.HALF, height=2.6):
    """Figure 5a. Travel time to a 50,000+ settlement against catchment population,
    coloured by access category. d: travel_50, pop_thousands, access."""
    fig, ax = S.axes(ax, width, height)
    for (k, c), m in zip(S.ACCESS.items(), S.MARKERS):
        s = d[d.access == k]
        ax.scatter(s.travel_50, s.pop_thousands, s=10, color=c, marker=m, alpha=0.9, linewidths=0,
                   label=f'{k} ({len(s)})', zorder=3)
    S.ref_line(ax, x=40); S.ref_line(ax, y=250)
    ax.set_yscale('log'); ax.set_yticks([10, 50, 250, 1000, 5000])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{v:,.0f}'))
    ax.yaxis.set_minor_formatter(FuncFormatter(lambda v, p: ''))
    ax.set_xlabel('Travel time to a town of 50,000+ (min)')
    ax.set_ylabel('Population within 30 min (thousands)')
    ax.legend(loc='upper right', handletextpad=0.2)
    return fig


def fig05b_positive_emissions(d, ax=None, width=S.HALF, height=2.6, counts=True):
    """Figure 5b. Share of markets with positive nighttime-light emissions, 2018
    against 2025, by access category and for all markets.
    d: group, year, lit, n, pct."""
    cats = list(dict.fromkeys(d.group))
    years = sorted(d.year.unique())
    col = {years[0]: S.LIGHT, years[-1]: S.SERIES['ntl_buffer']}     # light at the markets: teal
    fig, ax = S.axes(ax, width, height)
    xs = np.array([0, 1, 2, 3.3])[:len(cats)]
    w = 0.38
    for j, y in enumerate(years):
        t = d[d.year == y].set_index('group').reindex(cats)
        x = xs + (j - 0.5) * w
        ax.bar(x, t.pct, w * 0.92, color=col[y], label=str(y), zorder=2)
        for xi, (_, r) in zip(x, t.iterrows()):
            ax.annotate(f'{r.pct:.0f}%', (xi, r.pct), xytext=(0, 1.5), textcoords='offset points',
                        ha='center', fontsize=5.5)
            if counts:
                ax.annotate(f'{int(r.lit)}', (xi, 2), ha='center', va='bottom', fontsize=5,
                            color='white' if y == years[-1] else S.INK)
    ns = d.drop_duplicates('group').set_index('group').n
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{k.replace(' access', '')}\n(n={ns[k]})" for k in cats])
    ax.tick_params(axis='x', length=0)
    ax.set_ylabel('Markets with positive emissions (%)')
    ax.set_ylim(0, 112); ax.set_yticks(range(0, 101, 20))
    ax.legend(loc='upper left', ncol=2, handlelength=1.0)
    return fig


def fig05c_ntl_cdf(d, ax=None, width=S.HALF, height=2.6):
    """Figure 5c. Cumulative distribution of median monthly radiance across the
    markets, earlier year grey-dashed, later year in the buffer-lights teal. One dashed line
    marks the Kabul city-centre reference for the later year (the two years differ
    by less than a line width on this axis).
    d: {'values': year, light; 'kabul': year, kabul_ref}."""
    v, k = d['values'], d['kabul'].set_index('year').kabul_ref
    years = sorted(v.year.unique())
    sty = {years[0]: dict(color=S.NEUTRAL, ls='--'), years[-1]: dict(color=S.SERIES['ntl_buffer'], ls='-')}
    fig, ax = S.axes(ax, width, height)
    top = max(np.log1p(v.light.max()), np.log1p(k.max()))
    for y in years:
        vals = np.sort(v.loc[v.year == y, 'light'].fillna(0).to_numpy())
        n = len(vals); unlit = 100 * (vals <= 0).mean()
        ax.step(np.r_[0.0, np.log1p(vals)], np.r_[0.0, np.arange(1, n + 1) / n], where='post',
                lw=S.LW, label=f'{y} ({unlit:.0f}% unlit)', **sty[y])
    kabul = np.log1p(k[years[-1]])
    S.ref_line(ax, x=kabul)
    ax.text(kabul - 0.25, 0.35, 'Median, Kabul\ncity center', ha='right',
            va='center', fontsize=S.FONT_SMALL, color=S.MUTED)
    ax.set_xlim(-0.3, 2 * np.ceil(top / 2)); ax.set_ylim(0, 1.0)
    ax.xaxis.set_major_locator(MultipleLocator(2))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax.set_xlabel('Median nighttime light, log(1 + radiance)')
    ax.set_ylabel('Cumulative share of markets')
    ax.legend(loc='lower right', bbox_to_anchor=(0.9, 0.02))
    return fig


# ============================================================ Figure 6
def fig06a_monthly_activity(d, ax=None, width=S.HALF, height=2.6):
    """Figure 6a. Mean activity by month, one line per year (light 2018 to dark
    2025); market days solid, non-market days dashed.
    d: mktDay, year, month, mean."""
    years = sorted(d.year.unique())
    cols = S.ramp(len(years), light=0.2, dark=0.92)
    fig, ax = S.axes(ax, width, height)
    for c, y in zip(cols, years):
        for k, ls, lw in [(1, '-', 1.2), (0, '--', 0.9)]:
            s = d[(d.year == y) & (d.mktDay == k)].sort_values('month')
            ax.plot(s.month, s['mean'], color=c, ls=ls, lw=lw, zorder=3)
    S.baseline(ax, 0)
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(list('JFMAMJJASOND'))
    ax.set_xlabel('Month'); ax.set_ylabel('Market activity')
    yr = [Line2D([], [], color=c, lw=1.6) for c in cols]
    leg = ax.legend(yr, [str(y)[2:] if i else str(y) for i, y in enumerate(years)],
                    loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=len(years),
                    handlelength=0.9, columnspacing=0.6, handletextpad=0.25)
    ax.add_artist(leg)
    ax.legend([Line2D([], [], color=S.INK, lw=1.2), Line2D([], [], color=S.INK, lw=0.9, ls='--')],
              ['Market days', 'Non-market days'], loc='upper center', ncol=2,
              bbox_to_anchor=(0.5, -0.3))
    return fig


def fig06b_seasonality_by_goods(d, ax=None, width=S.HALF, height=2.6, z=1.6449, dodge=0.09, label_gap=8,
                                line_alpha=0.45):
    """Figure 6b. Quarter effects by goods sold, each group centred on its own
    mean, with 90% confidence intervals and direct labels at Q4.
    d: group, quarter (1-4), coef (centred), se."""
    groups = list(dict.fromkeys(d.group))
    fig, ax = S.axes(ax, width, height)
    S.baseline(ax, 0, xmin=-0.35, xmax=3.35)        # stops short of the labels
    q4 = d[d.quarter == 4].set_index('group').coef.sort_values()
    label_y, prev = {}, -np.inf               # direct labels, at least label_gap apart
    for g, y in q4.items():
        prev = label_y[g] = max(y, prev + label_gap)
    cols = S.CAT[:len(groups)]     # goods are not ordered: distinct category colours, the one
                                   # exception to shading groups of MAI series
    for i, g in enumerate(groups):
        s = d[d.group == g].sort_values('quarter')
        x = s.quarter.to_numpy() - 1 + (i - (len(groups) - 1) / 2) * dodge
        c = cols[i]
        ax.plot(x, s.coef, '-', color=c, lw=1.0, alpha=line_alpha, zorder=2)
        ax.errorbar(x, s.coef, yerr=z * s.se, fmt=S.MARKERS[i], color=c, ms=3, elinewidth=0.9,
                    capsize=0, zorder=3)
        ax.annotate(g, (3.5, label_y[g]), color=c, fontsize=S.FONT_SMALL - 0.5, va='center')
    ax.set_xticks(range(4)); ax.set_xticklabels(['Q1', 'Q2', 'Q3', 'Q4'])
    ax.set_xlim(-0.35, 5.3)
    ax.spines['bottom'].set_bounds(-0.35, 3.35)
    ax.set_ylabel("Deviation from group mean\n(index points)")
    return fig


# ============================================================ Figure 7
def fig07a_mai_gdp(d, ax=None, width=S.HALF, height=2.4):
    """Figure 7a. The MAI against agricultural and total real GDP, 2020 = 100.
    d: year, mai, ag_gdp, tot_gdp."""
    fig, ax = S.axes(ax, width, height)
    S.baseline(ax)
    _lines(ax, d.year, {k: d[k] for k in ('mai', 'ag_gdp', 'tot_gdp')}, dashed=('tot_gdp',))
    S.years_axis(ax, d.year); ax.set_ylim(70, 150)
    ax.set_ylabel('Index, 2020 = 100')
    ax.legend(loc='upper left')
    return fig


def fig07b_mai_ntl(d, ax=None, width=S.HALF, height=2.4):
    """Figure 7b. The MAI against national nighttime lights and nighttime lights
    in the market buffers, 2020 = 100. d: year, mai, ntl_total, ntl_buffer."""
    fig, ax = S.axes(ax, width, height)
    S.baseline(ax)
    _lines(ax, d.year, {k: d[k] for k in ('mai', 'ntl_total', 'ntl_buffer')})
    S.years_axis(ax, d.year); ax.set_ylim(70, 150)
    ax.set_ylabel('Index, 2020 = 100')
    ax.legend(loc='upper left')
    return fig


# ============================================================ Figure 8
def fig08_regions(d, width=S.FULL, height=3.6):
    """Figure 8. Seven regional panels: total nighttime lights, nighttime lights in
    the market buffers and the MAI, 2020 = 100, with each region's 2025 MAI change.
    d: region, n_markets, year, ntl_total, ntl_buffer, mai."""
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 4, figsize=(width, height), sharex=True, sharey=True)
    keys = ('ntl_total', 'ntl_buffer', 'mai')
    for ax, r in zip(axs.ravel(), S.REGIONS):
        s = d[d.region == r].sort_values('year')
        S.baseline(ax)
        for k in keys:
            ax.plot(s.year, s[k], '-o', color=S.SERIES[k], lw=1.1, ms=2, zorder=3)
        chg = s.loc[s.year == 2025, 'mai'].iloc[0] - 100
        ax.text(0.04, 0.95, f'{S.REGION_NAME.get(r, r)} ({int(s.n_markets.iloc[0])})',
                transform=ax.transAxes, fontsize=S.FONT_SMALL, va='top', fontweight='bold')
        ax.text(0.04, 0.82, f'MAI {chg:+.0f}', transform=ax.transAxes, fontsize=S.FONT_SMALL - 0.5,
                va='top', color=S.SERIES['mai'])
        S.years_axis(ax, YEARS)
        ax.tick_params(labelsize=S.FONT_SMALL - 0.5)
        ax.set_xlabel('')
    for ax in axs[:, 0]:
        ax.set_ylabel('Index, 2020 = 100')
    fig.supxlabel('Year', fontsize=S.FONT)
    axs[1, 3].axis('off')
    axs[0, 3].tick_params(labelbottom=True)      # no panel below it to carry the years
    h = [Line2D([], [], color=S.SERIES[k], lw=1.4, marker='o', ms=2.5) for k in keys]
    axs[1, 3].legend(h, [S.SERIES_LABEL[k] for k in keys], loc='center', labelspacing=0.8)
    return fig


# ============================================================ Figures 9 and 10
# Event-study coefficients (event_study.py): each series' year path relative to 2020
# with 90% intervals, the 2020 divider and the zero line as in every other figure.
def _coefs(ax, d, styles, offset=0.15):
    """styles: [(series, label, colour, marker)], dodged around each year."""
    n = len(styles)
    for i, (series, label, c, m) in enumerate(styles):
        s = d[d.series == series].sort_values('year')
        x = s.year + (i - (n - 1) / 2) * offset
        ax.errorbar(x, s.coef, yerr=[s.coef - s.lo, s.hi - s.coef], fmt=m, color=c, ms=3.5,
                    elinewidth=0.9, capsize=1.5, capthick=0.9, label=label, zorder=3)
    S.baseline(ax, 0)
    S.ref_line(ax, x=BASE_YEAR)
    S.years_axis(ax, YEARS)
    ax.set_xlim(YEARS[0] - 0.6, YEARS[-1] + 0.6)


def _below(ax, handles=None, labels=None, ncol=None):
    h, l = ax.get_legend_handles_labels() if handles is None else (handles, labels)
    ax.legend(h, l, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=ncol or len(h),
              handletextpad=0.3, columnspacing=1.0)


BASE_YEAR = 2020


def fig09a_access_categories(d, ax=None, width=S.HALF, height=2.8):
    """Figure 9a. Market activity by access category, relative to 2020 (regression 1)."""
    fig, ax = S.axes(ax, width, height)
    _coefs(ax, d, [(k, k, S.ACCESS[k], m) for k, m in zip(S.ACCESS_ORDER, S.MARKERS)], 0.2)
    ax.set_ylabel('Index points (2020 = 0)')
    _below(ax)
    return fig


def _scale_ratio(lo1, hi1, lo2, hi2):
    """Stata's rule for the second axis of Figure 9b: units of the right axis per unit
    of the left, the smallest round value that fits the right-hand intervals inside
    the left axis's range; both axes share their zero."""
    ratio = max(abs(lo2), abs(hi2)) / max(abs(lo1), abs(hi1))
    r = 1
    for c in (1, 0.5, 0.25, 0.2, 0.1, 0.05, 0.025, 0.02, 0.01, 0.005, 0.0025, 0.002, 0.001):
        if c >= ratio:
            r = c
    L, U = min(lo1, lo2 / r), max(hi1, hi2 / r)
    step = 10 if U - L > 30 else 5
    return r, np.floor(L / step) * step, np.ceil(U / step) * step, step


def fig09b_population_travel(d, ax=None, width=S.HALF, height=2.8):
    """Figure 9b. Activity per log point of catchment population (left axis) and per
    unit of asinh(travel time) (right axis), relative to 2020 (regression 2)."""
    fig, ax = S.axes(ax, width, height)
    dark, light = S.shades(S.ACCENT, 2)
    dens = d[d.series == 'Log catchment population']
    trav = d[d.series == 'asinh(travel time)']
    r, L, U, step = _scale_ratio(dens.lo.min(), dens.hi.max(), trav.lo.min(), trav.hi.max())
    dens = dens.assign(year=dens.year - 0.15)      # dodged left; travel is dodged right
    _coefs(ax, dens, [('Log catchment population', 'Log catchment population (left axis)',
                       dark, 'o')], 0)
    ax.errorbar([], [], fmt='s', color=light, ms=3.5, label='asinh(travel time) (right axis)')
    ax.set_ylim(L, U); ax.set_yticks(np.arange(L, U + step / 2, step))
    ax.set_ylabel('Index points per log point of population')
    ax2 = ax.twinx()
    ax2.spines['right'].set_visible(True)
    t = trav.sort_values('year')
    ax2.errorbar(t.year + 0.15, t.coef, yerr=[t.coef - t.lo, t.hi - t.coef], fmt='s', color=light,
                 ms=3.5, elinewidth=0.9, capsize=1.5, capthick=0.9, zorder=3)
    ax2.set_ylim(L * r, U * r); ax2.set_yticks(np.arange(L, U + step / 2, step) * r)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{v:.3g}'))
    ax2.set_ylabel('Index points per unit of asinh(travel)')
    _below(ax, ncol=1)
    return fig


def fig09c_two_day_markets(d, ax=None, width=S.HALF, height=2.8):
    """Figure 9c. The two trading days of twice-a-week markets, relative to the first
    day in 2020 (regression 3)."""
    fig, ax = S.axes(ax, width, height)
    dark, light = S.shades(S.ACCENT, 2)
    _coefs(ax, d, [('First trading day', 'First trading day', dark, 'o'),
                   ('Second trading day', 'Second trading day', light, 's')])
    ax.set_ylabel('Index points (first day in 2020 = 0)')
    _below(ax)
    return fig


def fig09d_single_multi_day(d, ax=None, width=S.HALF, height=2.8):
    """Figure 9d. Single-day and multi-day markets, relative to 2020 (regression 4)."""
    fig, ax = S.axes(ax, width, height)
    dark, light = S.shades(S.ACCENT, 2)          # multi-day dark, as in Figure 3b
    _coefs(ax, d, [('Single-day markets', 'Single-day markets', light, 'o'),
                   ('Multi-day markets', 'Multi-day markets', dark, 's')])
    ax.set_ylabel('Index points (2020 = 0)')
    _below(ax)
    return fig


def fig10a_ntl_access_categories(d, ax=None, width=S.HALF, height=2.8):
    """Figure 10a. Nighttime lights by access category, relative to 2020."""
    fig, ax = S.axes(ax, width, height)
    _coefs(ax, d, [(k, k, S.NTL_ACCESS[k], m) for k, m in zip(S.ACCESS_ORDER, S.MARKERS)], 0.2)
    ax.set_ylabel('asinh(NTL), change from 2020')
    _below(ax)
    return fig


def fig10b_ntl_population_travel(d, ax=None, width=S.HALF, height=2.8):
    """Figure 10b. Nighttime lights per log point of catchment population and per unit
    of asinh(travel time), relative to 2020, on one axis."""
    fig, ax = S.axes(ax, width, height)
    dark, light = S.shades(S.NTL_HUE, 2)
    _coefs(ax, d, [('Log catchment population', 'Log catchment population', dark, 'o'),
                   ('asinh(travel time)', 'asinh(travel time)', light, 's')])
    ax.set_ylabel('asinh(NTL) per unit')
    _below(ax)
    return fig


# ============================================================ Figure A.1
A1_STYLE = {'All markets': ('mai', '-', 'o'),
            'Exact schedule match': ('a1_exact', '--', 's'),
            'Exact match + validated MAI day': ('a1_broad', ':', '^')}


def _a1_color(k):
    dark, light = S.shades(S.ACCENT, 2)          # the subsamples: shades of the MAI orange
    return {'mai': S.SERIES['mai'], 'a1_exact': dark, 'a1_broad': light}[k]


def figA1a_validation_samples(d, ax=None, width=S.HALF, height=2.4):
    """Figure A.1a. The MAI for all markets and for the two field-validated
    subsamples, 2020 = 100. d: sample, n, year, index."""
    fig, ax = S.axes(ax, width, height)
    S.baseline(ax)
    for lab, (k, ls, mk) in A1_STYLE.items():
        s = d[d['sample'] == lab].sort_values('year')
        ax.plot(s.year, s['index'], ls=ls, marker=mk, ms=3, color=_a1_color(k),
                label=f'{lab} (n={int(s.n.iloc[0])})', zorder=3)
    S.years_axis(ax, YEARS)
    ax.set_ylabel('Index, 2020 = 100')
    ax.legend(loc='lower left')
    return fig


def figA1b_validation_difference(d, ax=None, width=S.HALF, height=2.4):
    """Figure A.1b. Each subsample minus all markets, in index points."""
    fig, ax = S.axes(ax, width, height)
    S.baseline(ax, 0)
    base = d[d['sample'] == 'All markets'].set_index('year')['index']
    for lab, (k, ls, mk) in list(A1_STYLE.items())[1:]:
        s = d[d['sample'] == lab].set_index('year')['index'].sort_index()
        ax.plot(s.index, s - base.reindex(s.index), ls=ls, marker=mk, ms=3, color=_a1_color(k),
                label=lab, zorder=3)
    S.years_axis(ax, YEARS)
    ax.set_ylim(-5, 5)
    ax.set_ylabel('Difference from all markets (points)')
    ax.legend(loc='lower right')
    return fig


# ============================================================ Figure A.2
def figA2_poppy(d, ax=None, width=S.HALF, height=2.6):
    """Figure A.2. The MAI by provincial poppy cultivation, with the 2022 ban.
    d: group, n, year, index (groups: Non-poppy, Poppy, Poppy excl. Hilmand)."""
    dark, mid, light = S.shades(S.ACCENT, 3)
    sty = {'Poppy': (dark, '-', 'o'), 'Poppy excl. Hilmand': (mid, '-', 's'),
           'Non-poppy': (light, '--', '^')}
    fig, ax = S.axes(ax, width, height)
    S.baseline(ax)
    S.ref_line(ax, x=2022)
    for g, (c, ls, mk) in sty.items():
        s = d[d.group == g].sort_values('year')
        ax.plot(s.year, s['index'], ls=ls, marker=mk, color=c,
                label=f'{g} (n={int(s.n.iloc[0])})', zorder=3)
    S.years_axis(ax, YEARS)
    ax.set_ylabel('Market Activity Index, 2020 = 100')
    ax.legend(loc='lower left')
    return fig


# ============================================================ Figure A.3
A3_CATEGORIES = ['Continuous operating market, no main day', 'Partial day overlap',
                 'Days do not match']
A3_LABEL = {'Continuous operating market, no main day': 'Continuous market, no main day'}


def _signal_timing(d, panel, top, width, height, ax=None):
    s = d[(d.panel == panel) & d.year.notna()]
    fig, ax = S.axes(ax, width, height)
    bottom = np.zeros(len(YEARS))
    cols = S.shades(S.ACCENT, len(A3_CATEGORIES))
    for cat, c in zip(A3_CATEGORIES, cols):
        cnt = s[s.category == cat].year.astype(int).value_counts().reindex(YEARS, fill_value=0).to_numpy()
        has = cnt > 0                              # empty years would leave slivers on the axis
        ax.bar(np.array(YEARS)[has], cnt[has], bottom=bottom[has], width=0.62, color=c,
               edgecolor='white', lw=0.8, zorder=3)
        for x, n_, b in zip(YEARS, cnt, bottom):
            if n_:
                ax.text(x, b + n_ / 2, str(n_), ha='center', va='center',
                        color=S.INK if c == cols[-1] else 'white',
                        fontsize=S.FONT_SMALL - 0.5, fontweight='bold', zorder=4)
        bottom += cnt
    S.years_axis(ax, YEARS); ax.set_xlim(YEARS[0] - 0.6, YEARS[-1] + 0.6)
    ax.set_ylabel('Number of market days')
    ax.set_ylim(0, top + 0.3); ax.set_yticks(range(0, top + 1))
    h = [Patch(color=c) for c in cols]
    ax.legend(h, [A3_LABEL.get(k, k) for k in A3_CATEGORIES], loc='upper left',
              handlelength=1.0)
    return fig


def _a3_top(d):
    c = d.dropna(subset=['year']).groupby(['panel', 'year']).size()
    return max(int(c.max()) if len(c) else 0, 1) + 2          # headroom for the legend


def figA3a_last_signal(d, ax=None, width=S.HALF, height=2.4):
    """Figure A.3a. MAI-predicted days with no signal in 2025, by the last year
    with a signal. d: panel, category, year (the TIMING table)."""
    return _signal_timing(d, 'A', _a3_top(d), width, height, ax)


def figA3b_first_signal(d, ax=None, width=S.HALF, height=2.4):
    """Figure A.3b. Field-reported days with a signal in 2025, by the first year
    with a signal."""
    return _signal_timing(d, 'B', _a3_top(d), width, height, ax)


# ============================================================ Figure A.4
def window_colors(windows):
    """Overpass windows are ordered in time: shades of the MAI orange, light (early)
    to dark (late)."""
    return dict(zip(windows, S.ramp(len(windows), S.ACCENT, light=0.18, dark=0.9)))


def figA4a_overpass_composition(d, ax=None, width=S.HALF, height=2.6):
    """Figure A.4a. Share of market-day images in each one-hour overpass window, by
    year. d: year, window, share."""
    wins = sorted(d.window.unique())
    col = window_colors(wins)
    fig, ax = S.axes(ax, width, height)
    years = sorted(d.year.unique())
    bottom = np.zeros(len(years))
    for w in wins:
        v = d[d.window == w].set_index('year').share.reindex(years).fillna(0).to_numpy()
        ax.bar(years, v, bottom=bottom, width=0.7, color=col[w], label=w, zorder=3)
        bottom += v
    S.years_axis(ax, years)
    ax.set_ylabel('Share of market-day images (%)'); ax.set_ylim(0, 100)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.24), ncol=len(wins),
              handlelength=1.0, columnspacing=0.8, handletextpad=0.3)
    return fig


def figA4b_overpass_effects(d, ax=None, width=S.HALF, height=2.6, z=1.96):
    """Figure A.4b. Difference in measured activity by overpass window, relative to
    the base window, with 95% confidence intervals. d: window, coef, se, base."""
    d = d.sort_values('window')
    col = window_colors(list(d.window))
    base = d.loc[d.base == 1, 'window'].iloc[0]
    fig, ax = S.axes(ax, width, height)
    S.baseline(ax, 0)
    x = np.arange(len(d))
    ax.bar(x, d.coef, 0.6, color=[col[w] for w in d.window], zorder=2)
    ax.errorbar(x, d.coef, yerr=z * d.se, fmt='none', ecolor=S.INK, elinewidth=0.8, capsize=2,
                zorder=3)
    ax.set_xticks(x); ax.set_xticklabels(d.window)
    ax.set_xlabel('Overpass window (local time)')
    ax.set_ylabel(f'Index points vs the {base} window')
    return fig


# ============================================================ side-by-side pairs
# Where the paper sets two panels side by side, they are drawn as one image: the two
# axes share a height and a baseline, and a shared y axis is labelled once. Word
# keeps the "Panel a." / "Panel b." titles above each half.
def _pair(width, height, sharey=False):
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(width, height), sharey=sharey)
    return fig, a1, a2


def fig04_population_coverage(d, width=S.FULL, height=2.7):
    """Figure 4, panels a and b, on one y axis so the coverage compares directly."""
    fig, a1, a2 = _pair(width, height, sharey=True)
    fig04a_population_coverage(d['a'], ax=a1)
    fig04b_osm_coverage(d['b'], ax=a2)
    a2.set_ylabel('')
    a2.get_legend().remove()                      # one legend serves both panels
    return fig


def fig05ab_access_emissions(d, width=S.FULL, height=2.7):
    """Figure 5, panels a and b. d: {'a': fig05a data, 'b': fig05b data}."""
    fig, a1, a2 = _pair(width, height)
    fig05a_access_categories(d['a'], ax=a1)
    fig05b_positive_emissions(d['b'], ax=a2)
    return fig


def fig06_seasonality(d, width=S.FULL, height=2.75):
    """Figure 6, panels a and b. d: {'a': fig06a data, 'b': fig06b data}."""
    fig, a1, a2 = _pair(width, height)
    fig06a_monthly_activity(d['a'], ax=a1)
    fig06b_seasonality_by_goods(d['b'], ax=a2)
    a2.set_xlabel('Quarter')
    return fig


def fig07_mai_indicators(d, width=S.FULL, height=2.5):
    """Figure 7, panels a and b, on one y axis. d: {'a': fig07a data, 'b': fig07b data}."""
    fig, a1, a2 = _pair(width, height, sharey=True)
    fig07a_mai_gdp(d['a'], ax=a1)
    fig07b_mai_ntl(d['b'], ax=a2)
    a2.set_ylabel('')
    return fig


def fig09ab_access_population(d, width=S.FULL, height=3.0):
    """Figure 9, panels a and b. d: {'a': fig09a data, 'b': fig09b data}."""
    fig, a1, a2 = _pair(width, height)
    fig09a_access_categories(d['a'], ax=a1)
    fig09b_population_travel(d['b'], ax=a2)
    return fig


def fig09cd_trading_days(d, width=S.FULL, height=3.0):
    """Figure 9, panels c and d. d: {'c': fig09c data, 'd': fig09d data}."""
    fig, a1, a2 = _pair(width, height)
    fig09c_two_day_markets(d['c'], ax=a1)
    fig09d_single_multi_day(d['d'], ax=a2)
    return fig


def fig10ab_ntl(d, width=S.FULL, height=3.0):
    """Figure 10, panels a and b. d: {'a': fig10a data, 'b': fig10b data}."""
    fig, a1, a2 = _pair(width, height)
    fig10a_ntl_access_categories(d['a'], ax=a1)
    fig10b_ntl_population_travel(d['b'], ax=a2)
    return fig


def figA1_validation_samples(d, width=S.FULL, height=2.5):
    """Figure A.1, panels a and b. d: the validation-sample series."""
    fig, a1, a2 = _pair(width, height)
    figA1a_validation_samples(d, ax=a1)
    figA1b_validation_difference(d, ax=a2)
    return fig


def figA3_signal_timing(d, width=S.FULL, height=2.5):
    """Figure A.3, panels a and b, on one y axis. d: the TIMING table."""
    fig, a1, a2 = _pair(width, height, sharey=True)
    figA3a_last_signal(d, ax=a1)
    figA3b_first_signal(d, ax=a2)
    a2.set_ylabel('')
    a2.get_legend().remove()                      # one legend serves both panels
    return fig


def figA4_overpass(d, width=S.FULL, height=2.7):
    """Figure A.4, panels a and b. d: {'a': fig A.4a data, 'b': fig A.4b data}."""
    fig, a1, a2 = _pair(width, height)
    figA4a_overpass_composition(d['a'], ax=a1)
    figA4b_overpass_effects(d['b'], ax=a2)
    return fig


# Paper order: name -> drawing function. Names are the output files.
PANELS = {
    'fig03a_market_map': fig03a_market_map,
    'fig03b_days_of_operation': fig03b_days_of_operation,
    'fig04a_population_coverage': fig04a_population_coverage,
    'fig04b_osm_coverage': fig04b_osm_coverage,
    'fig05a_access_categories': fig05a_access_categories,
    'fig05b_positive_emissions': fig05b_positive_emissions,
    'fig05c_ntl_cdf': fig05c_ntl_cdf,
    'fig06a_monthly_activity': fig06a_monthly_activity,
    'fig06b_seasonality_by_goods': fig06b_seasonality_by_goods,
    'fig07a_mai_gdp': fig07a_mai_gdp,
    'fig07b_mai_ntl': fig07b_mai_ntl,
    'fig08_regions': fig08_regions,
    'fig09a_access_categories': fig09a_access_categories,
    'fig09b_population_travel': fig09b_population_travel,
    'fig09c_two_day_markets': fig09c_two_day_markets,
    'fig09d_single_multi_day': fig09d_single_multi_day,
    'fig10a_ntl_access_categories': fig10a_ntl_access_categories,
    'fig10b_ntl_population_travel': fig10b_ntl_population_travel,
    'figA1a_validation_samples': figA1a_validation_samples,
    'figA1b_validation_difference': figA1b_validation_difference,
    'figA2_poppy': figA2_poppy,
    'figA3a_last_signal': figA3a_last_signal,
    'figA3b_first_signal': figA3b_first_signal,
    'figA4a_overpass_composition': figA4a_overpass_composition,
    'figA4b_overpass_effects': figA4b_overpass_effects,
}

PANELS.update({
    'fig04_population_coverage': fig04_population_coverage,
    'fig05ab_access_emissions': fig05ab_access_emissions,
    'fig06_seasonality': fig06_seasonality,
    'fig07_mai_indicators': fig07_mai_indicators,
    'fig09ab_access_population': fig09ab_access_population,
    'fig09cd_trading_days': fig09cd_trading_days,
    'fig10ab_ntl': fig10ab_ntl,
    'figA1_validation_samples': figA1_validation_samples,
    'figA3_signal_timing': figA3_signal_timing,
    'figA4_overpass': figA4_overpass,
})

# The data file each panel reads, where it differs from the panel name; a dict
# reads several (the side-by-side pairs, whose data come from different producers).
DATA_NAME = {'figA1a_validation_samples': 'figA1_validation_samples',
             'figA1b_validation_difference': 'figA1_validation_samples',
             'figA3a_last_signal': 'figA3_signal_timing',
             'figA3b_first_signal': 'figA3_signal_timing',
             'fig04_population_coverage': {'a': 'fig04a_population_coverage',
                                           'b': 'fig04b_osm_coverage'},
             'fig05ab_access_emissions': {'a': 'fig05a_access_categories',
                                          'b': 'fig05b_positive_emissions'},
             'fig06_seasonality': {'a': 'fig06a_monthly_activity',
                                   'b': 'fig06b_seasonality_by_goods'},
             'fig07_mai_indicators': {'a': 'fig07a_mai_gdp', 'b': 'fig07b_mai_ntl'},
             'fig09ab_access_population': {'a': 'fig09a_access_categories',
                                           'b': 'fig09b_population_travel'},
             'fig09cd_trading_days': {'c': 'fig09c_two_day_markets', 'd': 'fig09d_single_multi_day'},
             'fig10ab_ntl': {'a': 'fig10a_ntl_access_categories',
                             'b': 'fig10b_ntl_population_travel'},
             'figA4_overpass': {'a': 'figA4a_overpass_composition',
                                'b': 'figA4b_overpass_effects'}}

# The images the paper uses, in order (place_in_docx.py puts these in the manuscript).
PAPER = ['fig03a_market_map', 'fig03b_days_of_operation', 'fig04_population_coverage',
         'fig05ab_access_emissions',
         'fig05c_ntl_cdf', 'fig06_seasonality', 'fig07_mai_indicators', 'fig08_regions',
         'fig09ab_access_population', 'fig09cd_trading_days', 'fig10ab_ntl',
         'figA1_validation_samples', 'figA2_poppy', 'figA3_signal_timing', 'figA4_overpass']


# Every drawing function draws under the house style, whatever matplotlib settings
# the caller has (the notebooks set their own for their diagnostic plots).
for _name, _fn in list(PANELS.items()):
    globals()[_fn.__name__] = PANELS[_name] = S.house(_fn)


def _load(name):
    src = DATA_NAME.get(name, name)
    if isinstance(src, dict):
        return {k: S.load_data(v) for k, v in src.items()}
    return S.load_data(src)


def draw(name, **kw):
    """Redraw one panel (or side-by-side pair) from its saved data."""
    return PANELS[name](_load(name), **kw)


def save(name, **kw):
    """Redraw one panel from its saved data and write it to paper_exhibits."""
    return S.save(draw(name, **kw), name)


def save_paper():
    """Draw every image the paper uses from the saved data. The producers (figures.py,
    the notebooks, figure4_population_coverage.py) save the data; the pairs combine
    data from more than one of them, so they are drawn here."""
    return [save(n) for n in PAPER]


if __name__ == '__main__':
    save_paper()
