"""Build every figure and every table in the paper.

    python run_all.py            inputs, figures, tables, verification
    python run_all.py figures    just the figures
    python run_all.py tables     just the tables
    python run_all.py verify     just the verification checks

Figures are written to out/ as PNG, tables as CSV. Nothing else is produced and
nothing outside out/ is written.

Exit status is 0 only when every figure and table was produced and every
verification check passed.
"""
import sys, traceback
import common as C

USAGE = 'usage: python run_all.py [all|figures|tables|verify]'


def _run(label, items, after=None):
    """Call each item, reporting failures without stopping the run."""
    ok, bad = [], []
    for f in items:
        print(f'--- {f.__name__}')
        try:
            r = f()
            if after:
                after(f, r)
            ok.append(f.__name__)
        except Exception as e:
            bad.append((f.__name__, f'{type(e).__name__}: {e}'))
            print(f'   FAILED  {type(e).__name__}: {e}')
            traceback.print_exc()
    print(f'\n{len(ok)} of {len(items)} {label} produced')
    for n, e in bad:
        print(f'   FAILED  {n}: {e}')
    return not bad


def main(what='all'):
    if what not in ('all', 'figures', 'tables', 'verify'):
        sys.exit(USAGE)

    print('== inputs')
    if C.check_inputs():
        sys.exit('missing inputs; set MAI_ROOT to the data tree and rerun')

    good = True

    if what in ('all', 'figures'):
        import figures
        print('\n== figures')
        good &= _run('figures', figures.ALL)

    if what in ('all', 'tables'):
        import tables
        print('\n== tables')

        def _save(f, r):
            r[0].to_csv(f'{C.OUT}/{f.__name__}.csv', index=False)
            if f.__name__ in tables.AS_IMAGE:
                tables.render_png(r[0], f'{C.OUT}/{f.__name__}.png')

        good &= _run('tables', tables.ALL, after=_save)

    if what in ('all', 'verify'):
        print('\n== verification')
        import subprocess
        good &= subprocess.call([sys.executable, 'verify.py']) == 0

    print(f'\nout/ holds the figures and tables. {"" if good else "SOMETHING FAILED — see above."}')
    return 0 if good else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'all'))
