"""House style for every figure in the paper: palette, sizes, fonts, saving.

Everything visual that more than one figure shares lives here, so a change made
once shows up everywhere. The look follows the detection team's figure notebook
(afg_figures.ipynb): matplotlib's default sans, no grid, no top or right spine,
frameless legends, one warm accent for the headline series, grey for comparison
series, and a gold for reference lines.

Sizes are the figure's printed size in the paper. The text block is 6.5 inches
wide (Letter, one-inch margins); a panel in one of the paper's two table cells
has HALF = 3.15 inches inside the cell padding, and a full-width figure FULL = 6.4.
Figures are saved
at exactly that size (no tight bounding box), so a 7-point label in one figure is
a 7-point label in every other.

This module imports nothing from common.py, so the notebooks can use it without
switching matplotlib's backend.
"""
import os
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, to_hex, to_rgb

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------- output folder
# Paper exhibits go to config.PAPER_EXHIBITS (output_paper/paper_exhibits); the
# data behind each one goes to its data/ subfolder, so a figure can be redrawn
# without rerunning the analysis that produced it (plots.draw).
sys.path.insert(0, os.path.join(HERE, '..', 'NTL_processing'))
try:
    from config import PAPER_EXHIBITS as PAPER
except Exception:                       # no data tree configured: write beside the code
    PAPER = os.path.join(HERE, 'out')
FIG_DATA = os.path.join(PAPER, 'data')

# --------------------------------------------------------------- sizes (inches)
# The paper sets every figure in a fixed-width Word table: two 3.25-inch columns (or
# one 6.5-inch column) with 0.05 inch of cell padding each side. These are the
# widths left inside the cells, so the images print at 100% and the type at its
# stated size.
FULL = 6.4                              # a full-width cell: 6.5 in less the cell padding
HALF = 3.15                             # one of two side-by-side cells: 3.25 in less padding
DPI = 300

# --------------------------------------------------------------- palette
# Categorical slots, assigned in this order and never cycled. Slots 1-3
# (terracotta, teal, blue) stay distinguishable for every pair under common
# colour-vision deficiencies, so any figure with up to three groups uses them.
# Slots 4-7 extend to the seven-region figures; all seven pass the adjacent-pair
# checks of the dataviz validator, at a 3:1 or better contrast on white.
CAT = ['#e76f51',   # 1 terracotta - the accent (afg_figures color3)
       '#2a9d8f',   # 2 teal (afg_figures color2)
       '#2f6fa3',   # 3 blue
       '#b8892a',   # 4 gold, darkened from afg_figures color1 so it reads as a line
       '#7d4e9e',   # 5 plum
       '#6b9a4d',   # 6 sage
       '#c45f7f']   # 7 rose

ACCENT = CAT[0]          # the headline series: the Market Activity Index, detected markets
REF = '#9f9f9f'          # dividing and reference lines, dashed: Stata's gs10, the colour of the
                         # 2020 line in the original Stata Figures 9 and 10
NEUTRAL = '#7a7a7a'      # comparison series, drawn dashed
LIGHT = '#d4d4d4'        # background bars and tracks, null bands
INK = '#000000'          # text, axes, zero lines
MUTED = '#555555'        # secondary text
GREEN = '#14703a'        # dark green: total nighttime lights (the buffers take the teal, slot 2)
NTL_HUE = '#1f8a4c'      # the green that groups of nighttime-light series are shaded from


def ramp(n, color=None, light=0.30, dark=1.0):
    """n steps of one hue (default: the accent) from light to dark, for ordered
    categories (years, time windows). `light` and `dark` are positions on a
    white-to-color-to-black scale: 0 is white, 0.5 the color itself, 1 near-black."""
    color = color or ACCENT
    cmap = LinearSegmentedColormap.from_list('r', ['#ffffff', color, '#1a1a1a'])
    return [to_hex(cmap(v)) for v in np.linspace(light, dark * 0.85, n)]


def shades(color, n, light=0.36, dark=0.72):
    """n shades of one hue, dark to light, for groups of markets measured on the
    same data (access categories, trading frequency, samples): the hue says which
    data, the shade which group. Same scale as ramp(); the defaults keep the lightest
    step above 2:1 contrast on white."""
    cmap = LinearSegmentedColormap.from_list('s', ['#ffffff', color, '#000000'])
    return [to_hex(cmap(v)) for v in np.linspace(dark, light, n)]


def greys(n, light=0.25, dark=1.0):
    """n greys from light to black, the reference notebook's ordinal scale."""
    return [to_hex((1 - v,) * 3) for v in np.linspace(light, dark, n)]


# The colour vocabulary, kept the same across the paper: orange is market activity
# (the MAI), greens are nighttime lights (dark green total, teal in the market
# buffers), blue is GDP, grey a comparison series. Groups of markets measured on
# one of these (access categories, trading frequency, poppy, validation samples,
# goods, time windows) are shades of that data's hue, dark to light, with markers
# or line styles as a second cue.
#
# Which colour each series takes: an integer is a CAT slot (0 = first), so changing
# CAT carries through; a string names a colour above or is a hex.
SERIES_SLOT = {
    'mai':        'ACCENT',    # Market Activity Index
    'ntl_total':  'GREEN',     # total civilian nighttime lights
    'ntl_buffer': 1,           # nighttime lights in the 10 km market buffers (teal)
    'ag_gdp':     2,           # agricultural real GDP (blue)
    'tot_gdp':    'NEUTRAL',   # total real GDP, a comparison series
}
SERIES_LABEL = {
    'mai':        'Market Activity Index',
    'ntl_total':  'Total nighttime lights',
    'ntl_buffer': 'Nighttime lights, market buffers',
    'ag_gdp':     'Agricultural real GDP',
    'tot_gdp':    'Total real GDP',
}
ACCESS_ORDER = ['High access', 'Intermediate access', 'Remote']      # dark to light
MARKERS = ['o', 's', '^', 'D']           # Stata's O, S, T: the second cue for groups
REGIONS = ['Central', 'East', 'NorthEast', 'NorthWest', 'SouthEast', 'SouthWest', 'West']
REGION_NAME = {'NorthEast': 'North East', 'NorthWest': 'North West',
               'SouthEast': 'South East', 'SouthWest': 'South West'}


def _resolve_color(v):
    if isinstance(v, int):
        return CAT[v]
    return globals().get(v, v)        # 'NEUTRAL', 'REF', ... or a hex


def set_palette(cat=None, **colors):
    """Rebuild every role colour from CAT. Pass a new list of slots as `cat`, and/or
    any of ACCENT, REF, NEUTRAL, LIGHT, INK, MUTED, GREEN as keywords. Drawing functions
    read these at draw time, so the next figure drawn uses them."""
    global CAT, ACCENT, SERIES, ACCESS, NTL_ACCESS, REGION
    if cat is not None:
        CAT = list(cat)
    for k, v in colors.items():
        globals()[k] = v
    ACCENT = colors.get('ACCENT', CAT[0])
    SERIES = {k: _resolve_color(v) for k, v in SERIES_SLOT.items()}
    ACCESS = dict(zip(ACCESS_ORDER, shades(ACCENT, 3)))          # Figures 5a, 9a
    NTL_ACCESS = dict(zip(ACCESS_ORDER, shades(NTL_HUE, 3)))     # Figure 10a
    REGION = dict(zip(REGIONS, CAT))


set_palette()

# --------------------------------------------------------------- type and marks
FONT = 8          # axis labels and general text, points at printed size
FONT_SMALL = 7    # tick labels, legends, annotations
LW = 1.5          # data lines
MS = 3.5          # line markers

def rc():
    """matplotlib settings from the current FONT, FONT_SMALL, LW, MS and colours."""
    return {
        'font.family': 'DejaVu Sans', 'font.size': FONT,
        'axes.labelsize': FONT, 'axes.titlesize': FONT,
        'xtick.labelsize': FONT_SMALL, 'ytick.labelsize': FONT_SMALL,
        'legend.fontsize': FONT_SMALL, 'legend.title_fontsize': FONT_SMALL,
        'legend.frameon': False, 'legend.handlelength': 1.6, 'legend.borderaxespad': 0.3,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': False, 'axes.linewidth': 0.8, 'axes.edgecolor': INK,
        'axes.labelcolor': INK, 'text.color': INK,
        'xtick.color': INK, 'ytick.color': INK,
        'xtick.major.width': 0.8, 'ytick.major.width': 0.8,
        'xtick.major.size': 3, 'ytick.major.size': 3,
        'lines.linewidth': LW, 'lines.markersize': MS,
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'savefig.facecolor': 'white', 'savefig.dpi': DPI,
        'figure.dpi': 100,
        'figure.constrained_layout.use': True,
        'figure.constrained_layout.h_pad': 0.03, 'figure.constrained_layout.w_pad': 0.03,
    }


def use():
    """Apply the house style to matplotlib."""
    mpl.rcParams.update(rc())


def house(fn):
    """Decorator: draw under the house style (an rc_context), whatever the global
    matplotlib settings are, so a notebook's own rcParams cannot leak into a figure."""
    import functools

    @functools.wraps(fn)
    def wrapped(*a, **k):
        with mpl.rc_context(rc()):
            return fn(*a, **k)
    return wrapped


use()


# --------------------------------------------------------------- helpers
def figure(width=HALF, height=None, nrows=1, ncols=1, **kw):
    """A figure at its printed size. `width` is HALF, FULL or inches; height
    defaults to 0.8 of the width for one panel."""
    if height is None:
        height = 0.8 * width
    return plt.subplots(nrows, ncols, figsize=(width, height), **kw)


def axes(ax=None, width=HALF, height=None):
    """(fig, ax): a new figure at its printed size, or the figure of an axes passed
    in, so each panel can be drawn alone or into a shared figure."""
    return figure(width, height) if ax is None else (ax.figure, ax)


def years_axis(ax, years, short=True, label='Year'):
    """Every year as a tick, as '18' ... '25' when short, and the axis label."""
    ax.set_xticks(years)
    ax.set_xticklabels([str(y)[2:] if short else str(y) for y in years])
    if label:
        ax.set_xlabel(label)


BASE_LW = 0.6            # points; Stata's yline default


def baseline(ax, y=100, xmin=None, xmax=None, **kw):
    """The zero line (or an index's base, 100): black and dashed, as Stata draws
    yline(0) in Figures 9 and 10. xmin/xmax (data units) stop it short of labels."""
    kw = dict(color=INK, ls='--', lw=BASE_LW, zorder=1) | kw
    if xmin is None and xmax is None:
        ax.axhline(y, **kw)
    else:
        ax.plot([xmin, xmax], [y, y], **kw)


REF_LW = 0.8             # points; Stata's lwidth(medthin)


def ref_line(ax, x=None, y=None, **kw):
    """A dividing or reference line (thresholds, events, reference values): grey,
    dashed, the same in every figure."""
    kw = dict(color=REF, ls='--', lw=REF_LW, zorder=1) | kw
    if x is not None:
        ax.axvline(x, **kw)
    if y is not None:
        ax.axhline(y, **kw)


def save(fig, name, folder=None):
    """Save at the figure's own size and 300 dpi: no tight bounding box, so the
    printed size is exactly the figsize. Returns the path."""
    p = os.path.join(folder or PAPER, f'{name}.png')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fig.savefig(p, dpi=DPI)
    if 'ipykernel' in sys.modules:      # show it in the notebook before closing
        from IPython.display import display
        display(fig)
    plt.close(fig)
    print(f'   saved {name}.png')
    return p


def save_data(d, name):
    """Write the data a figure draws, as plotted, to paper_exhibits/data/<name>.csv.
    A dict of frames is written as <name>__<key>.csv per entry."""
    os.makedirs(FIG_DATA, exist_ok=True)
    if isinstance(d, dict):
        return {k: save_data(v, f'{name}__{k}') for k, v in d.items()}
    p = os.path.join(FIG_DATA, f'{name}.csv')
    d.to_csv(p, index=False)
    return p


def load_data(name):
    """Read back what save_data wrote: a frame, or a dict of frames."""
    p = os.path.join(FIG_DATA, f'{name}.csv')
    if os.path.exists(p):
        return pd.read_csv(p)
    parts = sorted(f for f in os.listdir(FIG_DATA) if f.startswith(f'{name}__'))
    if not parts:
        raise FileNotFoundError(f'no figure data for {name} in {FIG_DATA}; run the code that makes it')
    return {f[len(name) + 2:-4]: pd.read_csv(os.path.join(FIG_DATA, f)) for f in parts}


def swatch(colors=None, labels=None):
    """A strip of colour chips, for checking the palette."""
    colors = colors or CAT
    labels = labels or [f'{i + 1} {c}' for i, c in enumerate(colors)]
    fig, ax = plt.subplots(figsize=(FULL, 0.55))
    for i, c in enumerate(colors):
        ax.add_patch(plt.Rectangle((i, 0), 0.92, 1, color=c))
        lum = 0.2126 * to_rgb(c)[0] + 0.7152 * to_rgb(c)[1] + 0.0722 * to_rgb(c)[2]
        ax.text(i + 0.46, 0.5, labels[i], ha='center', va='center', fontsize=6.5,
                color='white' if lum < 0.6 else INK)
    ax.set_xlim(0, len(colors)); ax.set_ylim(0, 1); ax.axis('off')
    return fig
