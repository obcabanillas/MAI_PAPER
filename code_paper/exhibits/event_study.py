"""The event-study regressions behind Figures 9 and 10 (the official version).

Ports stata/run_event_study_ACCESS.do, which it replaces: the same six reghdfe
specifications, estimated with pyfixest (market fixed effects, plus year fixed
effects in regression 2 and its nighttime-light version; standard errors clustered
by province; singleton markets dropped), the same joint tests (F with G - 1
denominator degrees of freedom, G = province clusters, as Stata's `test` after
reghdfe), and 90% intervals from t(G - 1).

    PAPER EXHIBIT        REGRESSION                                   FIGURE DATA
    Figure 9, panel a    1. activity on access x year                fig09a_access_categories
    Figure 9, panel b    2. log catchment pop x year, asinh(travel)  fig09b_population_travel
    Figure 9, panel c    3. two-day markets, both days x year        fig09c_two_day_markets
    Figure 9, panel d    4. single-day x year, multi-day x year      fig09d_single_multi_day
    Figure 10, panel a   asinh(NTL) on access x year, per group      fig10a_ntl_access_categories
    Figure 10, panel b   asinh(NTL), regression 2's terms            fig10b_ntl_population_travel

Writes the figure data to paper_exhibits/data/ (plots.py draws them) and, to
output_paper/event_study/, the regression tables MAI_pooled.csv and NTL_access.csv
(coefficient, stars at 0.1/1/5 percent, standard error below; as outreg2 wrote them)
and event_study_tests.csv (every joint test the do-file printed).

Inputs: processed_data/event_study_panel.dta (build_event_study_panel.ipynb) and
processed_data/event_study_days_panel.dta (data_build/build_event_study_days_panel.py).
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

import style as S

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'NTL_processing'))
from config import OUTPUT, PROCESSED  # noqa: E402

BASE = 2020
YEARS = list(range(2018, 2026))
NOT_BASE = [y for y in YEARS if y != BASE]
CONTROLS = ['ln_deaths_pc', 'ndvi_dev_control']
ACCESS = {'H': 'High access', 'Int': 'Intermediate access', 'R': 'Remote'}
OUT = os.path.join(OUTPUT, 'event_study')


# ------------------------------------------------------------------ data
def market_panel():
    """event_study_panel.dta with the do-file's variables."""
    d = pd.read_stata(os.path.join(PROCESSED, 'event_study_panel.dta'))
    d = d.rename(columns={'log_deaths_pc': 'ln_deaths_pc', 'y_activity': 'activity'})
    d['ndvi_dev_control'] = d.ndvi_ag_anom
    d['asin_ntl'] = np.arcsinh(np.exp(d.log_light_emissions).fillna(0))   # no light -> 0
    d['market_id'] = d.mktID.astype('category').cat.codes
    single = (d.once_a_week == 1).astype(float)
    for k, lab in ACCESS.items():
        d[f'Access_{k}'] = (d.access == lab).astype(float)
    for y in NOT_BASE:
        yr = (d.year == y).astype(float)
        for k in ACCESS:
            d[f'X_Access_{k}_{y}'] = d[f'Access_{k}'] * yr
        d[f'D_dens_{y}'] = d.ln_pop_30mixed * yr
        d[f'D_ASINtrav_{y}'] = np.arcsinh(d.travel_50) * yr
        d[f'D_single_{y}'] = single * yr
        d[f'D_multi_{y}'] = (1 - single) * yr
    return d


def days_panel():
    """event_study_days_panel.dta: one row per two-day market x trading day x year."""
    d = pd.read_stata(os.path.join(PROCESSED, 'event_study_days_panel.dta'))
    d = d.rename(columns={'log_deaths_pc': 'ln_deaths_pc'})
    d['ndvi_dev_control'] = d.ndvi_ag_anom
    d['market_id'] = d.mktID.astype('category').cat.codes
    for y in YEARS:
        yr = (d.year == y).astype(float)
        d[f'D_dayB_{y}'] = d.day_b * yr                  # second day, every year
        if y != BASE:
            d[f'D_dayA_{y}'] = (1 - d.day_b) * yr        # first day, 2020 omitted
    return d


# ------------------------------------------------------------------ estimation
class Fit:
    """One regression: coefficients, clustered covariance and the cluster count."""

    def __init__(self, data, y, x, fe, label):
        import pyfixest as pf
        self.label = label
        self.fe = fe
        cols = [y] + x + ['Prov_ID'] + fe
        self.data = data.dropna(subset=cols)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.m = pf.feols(f'{y} ~ {" + ".join(x)} | {" + ".join(fe)}', self.data,
                              vcov={'CRV1': 'Prov_ID'}, fixef_rm='singleton')
        self.b = self.m.coef()
        self.se = self.m.se()
        self.V = pd.DataFrame(self.m._vcov, index=self.b.index, columns=self.b.index)
        self.G = self.data.Prov_ID.nunique()
        self.N = int(self.m._N)
        self.r2 = float(self.m._r2)
        self.t90 = stats.t.ppf(0.95, self.G - 1)

    def p(self, k):
        return 2 * stats.t.sf(abs(self.b[k] / self.se[k]), self.G - 1)

    def test(self, rows):
        """Joint Wald test of linear restrictions, each {coef: weight} = 0;
        F(k, G - 1) as Stata's `test` after reghdfe with clustered errors."""
        R = np.array([[r.get(c, 0.0) for c in self.b.index] for r in rows])
        Rb = R @ self.b.values
        F = float(Rb @ np.linalg.solve(R @ self.V.values @ R.T, Rb)) / len(rows)
        return F, float(stats.f.sf(F, len(rows), self.G - 1))

    def path(self, prefix, series):
        """Year path of the coefficients named prefix_<year>; years without one are 0."""
        rows = []
        for y in YEARS:
            k = f'{prefix}_{y}'
            if k in self.b.index:
                b, h = self.b[k], self.t90 * self.se[k]
                rows.append((series, y, b, b - h, b + h))
            else:
                rows.append((series, y, 0.0, 0.0, 0.0))
        return pd.DataFrame(rows, columns=['series', 'year', 'coef', 'lo', 'hi'])


def _xs(prefix, years=NOT_BASE):
    return [f'{prefix}_{y}' for y in years]


def estimate():
    """All six regressions and their joint tests, as in the do-file."""
    d, dd = market_panel(), days_panel()
    F, tests = {}, []

    def note(reg, name, ft):
        tests.append({'regression': reg, 'test': name, 'F': ft[0], 'p': ft[1]})

    # 1. activity on access x year (Figure 9a)
    f = F['1'] = Fit(d, 'activity', sum((_xs(f'X_Access_{k}') for k in ACCESS), []) + CONTROLS,
                     ['market_id'], '1. Access x year')
    for y in NOT_BASE:
        note('1', f'H = Int = R in {y}',
             f.test([{f'X_Access_H_{y}': 1, f'X_Access_Int_{y}': -1},
                     {f'X_Access_H_{y}': 1, f'X_Access_R_{y}': -1}]))
    note('1', 'p: same path all groups',
         f.test([r for y in NOT_BASE for r in ({f'X_Access_H_{y}': 1, f'X_Access_Int_{y}': -1},
                                               {f'X_Access_H_{y}': 1, f'X_Access_R_{y}': -1})]))

    # 2. density and travel time x year (Figure 9b)
    f = F['2'] = Fit(d, 'activity', _xs('D_dens') + _xs('D_ASINtrav') + CONTROLS,
                     ['market_id', 'year'], '2. Density, travel')
    note('2', 'p: density x year = 0', f.test([{k: 1} for k in _xs('D_dens')]))
    note('2', 'p: asinh(travel) x year = 0', f.test([{k: 1} for k in _xs('D_ASINtrav')]))

    # 4. single-day and multi-day x year (Figure 9d)
    f = F['4'] = Fit(d, 'activity', _xs('D_single') + _xs('D_multi') + CONTROLS,
                     ['market_id'], '4. Single vs multi-day')
    for y in NOT_BASE:
        note('4', f'single = multi in {y}', f.test([{f'D_single_{y}': 1, f'D_multi_{y}': -1}]))
    note('4', 'p: same path both groups',
         f.test([{f'D_single_{y}': 1, f'D_multi_{y}': -1} for y in NOT_BASE]))

    # 3. the two days of two-day markets (Figure 9c). The access dummies do not vary
    #    within a market, so the market effects absorb them (Stata drops them too).
    f = F['3'] = Fit(dd, 'y_activity_day', _xs('D_dayA') + _xs('D_dayB', YEARS) + CONTROLS,
                     ['market_id'], '3. Two-day markets')
    gap = lambda y: {f'D_dayB_{y}': 1} if y == BASE else {f'D_dayB_{y}': 1, f'D_dayA_{y}': -1}
    for y in YEARS:
        b = sum(w * f.b[k] for k, w in gap(y).items())
        note('3', f'second - first day in {y} (estimate {b:.2f})', f.test([gap(y)]))
    note('3', 'p: no gap any year', f.test([gap(y) for y in YEARS]))
    note('3', 'p: gap same each year',
         f.test([{k: gap(2018).get(k, 0) - gap(y).get(k, 0) for k in set(gap(2018)) | set(gap(y))}
                 for y in YEARS[1:]]))

    # NTL by access, one regression per group (Figure 10a)
    for k in ACCESS:
        F[f'N_{k}'] = Fit(d[d[f'Access_{k}'] == 1], 'asin_ntl', _xs(f'X_Access_{k}') + CONTROLS,
                          ['market_id'], f'NTL Access_{k}')
    # NTL on density and travel time (Figure 10b)
    f = F['N2'] = Fit(d, 'asin_ntl', _xs('D_dens') + _xs('D_ASINtrav') + CONTROLS,
                      ['market_id', 'year'], 'NTL density, travel')
    note('N2', 'p: density x year = 0', f.test([{k: 1} for k in _xs('D_dens')]))
    note('N2', 'p: asinh(travel) x year = 0', f.test([{k: 1} for k in _xs('D_ASINtrav')]))
    for k, f in F.items():
        f.key = k
    return F, pd.DataFrame(tests)


# ------------------------------------------------------------------ outputs
def figure_data(F):
    """The coefficient paths each figure draws, with 90% intervals."""
    return {
        'fig09a_access_categories': pd.concat(
            [F['1'].path(f'X_Access_{k}', lab) for k, lab in ACCESS.items()]),
        'fig09b_population_travel': pd.concat(
            [F['2'].path('D_dens', 'Log catchment population'),
             F['2'].path('D_ASINtrav', 'asinh(travel time)')]),
        'fig09c_two_day_markets': pd.concat(
            [F['3'].path('D_dayA', 'First trading day'),
             F['3'].path('D_dayB', 'Second trading day')]),
        'fig09d_single_multi_day': pd.concat(
            [F['4'].path('D_single', 'Single-day markets'),
             F['4'].path('D_multi', 'Multi-day markets')]),
        'fig10a_ntl_access_categories': pd.concat(
            [F[f'N_{k}'].path(f'X_Access_{k}', lab) for k, lab in ACCESS.items()]),
        'fig10b_ntl_population_travel': pd.concat(
            [F['N2'].path('D_dens', 'Log catchment population'),
             F['N2'].path('D_ASINtrav', 'asinh(travel time)')]),
    }


def _stars(p):
    return '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''


def regression_table(fits, tests):
    """outreg2's layout: a coefficient row (3 decimals, stars) and a standard-error
    row (2 decimals) per regressor, then N, R-squared, fixed effects, clusters and
    the joint-test p-values."""
    names = list(dict.fromkeys(k for f in fits for k in f.b.index))
    rows = []
    for k in names:
        rows.append([k] + [f'{f.b[k]:.3f}{_stars(f.p(k))}' if k in f.b.index else '' for f in fits])
        rows.append([''] + [f'({f.se[k]:.2f})' if k in f.b.index else '' for f in fits])
    rows.append(['Observations'] + [f.N for f in fits])
    rows.append(['R-squared'] + [f'{f.r2:.3f}' for f in fits])
    rows.append(['Mkt FE'] + ['YES' for f in fits])
    rows.append(['Year FE'] + ['YES' if 'year' in f.fe else '' for f in fits])
    rows.append(['Province clusters'] + [f.G for f in fits])
    for name in dict.fromkeys(t for t in tests.test if t.startswith('p:')):
        cells = []
        for f in fits:
            hit = tests[(tests.regression == f.key) & (tests.test == name)]
            cells.append(f'{hit.p.iloc[0]:.3f}' if len(hit) else '')
        if any(cells):
            rows.append([name] + cells)
    return pd.DataFrame(rows, columns=[''] + [f.label for f in fits])


def main():
    F, tests = estimate()
    for name, d in figure_data(F).items():
        S.save_data(d, name)
    os.makedirs(OUT, exist_ok=True)
    regression_table([F['1'], F['2'], F['4'], F['3']], tests).to_csv(
        os.path.join(OUT, 'MAI_pooled.csv'), index=False)
    regression_table([F['N_H'], F['N_Int'], F['N_R'], F['N2']], tests).to_csv(
        os.path.join(OUT, 'NTL_access.csv'), index=False)
    tests.to_csv(os.path.join(OUT, 'event_study_tests.csv'), index=False)
    for k, f in F.items():
        print(f'   {f.label:<24} N={f.N}  provinces={f.G}')
    print(f'   wrote figure data and {OUT}/MAI_pooled.csv, NTL_access.csv, event_study_tests.csv')
    return F, tests


if __name__ == '__main__':
    main()
