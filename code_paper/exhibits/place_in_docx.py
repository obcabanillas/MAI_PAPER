"""Put the current paper figures into a copy of the manuscript, to see them in context.

    python place_in_docx.py PAPER.docx [OUT.docx] [--keep-tables]

Writes OUT.docx (default: PAPER_figures.docx beside the input) and never changes
PAPER.docx. Text, tracked changes and comments are left as they are.

Figures. Image slots are found by caption, not by Word's internal image names: the
drawings after a caption paragraph that starts "Figure 5." are that figure's slots, in
reading order. FIGURES says what goes in each: a file name, None to keep the image
already there (the illustrations in Figures 1 and 2), or (file, 2) for a side-by-side pair drawn as one image (plots.py). A pair
takes both slots of its row: the row's two image cells become one full-width cell,
and any "Panel a." / "Panel b." titles that shared those cells move to a row of their
own above it. Each image is set to its printed size and any crop Word stored for the
old image is cleared.

Tables. The paper's data tables are restyled to one house style: the body font (Arial)
at 9 point, three horizontal rules (above and below the header, below the last row),
a light rule above a "Total" row, no shading and no vertical lines. Content, merges and
alignment are untouched. --keep-tables leaves them as they are.
"""
import copy
import os
import re
import sys
import zipfile

from lxml import etree
from PIL import Image

import style as S

FIGURES = {
    'Figure 1': [None],
    'Figure 2': [None, None],
    'Figure 3': ['fig03a_market_map', 'fig03b_days_of_operation'],
    'Figure 4': [('fig04_population_coverage', 2)],
    'Figure 5': [('fig05ab_access_emissions', 2), 'fig05c_ntl_cdf'],
    'Figure 6': [('fig06_seasonality', 2)],
    'Figure 7': [('fig07_mai_indicators', 2)],
    'Figure 8': ['fig08_regions'],
    'Figure 9': [('fig09ab_access_population', 2), ('fig09cd_trading_days', 2)],
    'Figure 10': [('fig10ab_ntl', 2)],
    'Figure A.1': ['figA1_validation_samples'],
    'Figure A.2': ['figA2_poppy'],
    'Figure A.3': [('figA3_signal_timing', 2)],
    'Figure A.4': [('figA4_overpass', 2)],
}

TABLE_FONT, TABLE_PT, NOTE_PT = 'Arial', 9, 8
RULE_HEAVY, RULE_LIGHT = 8, 4             # border widths, eighths of a point

EMU = 914400                              # EMU per inch
CAPTION = re.compile(r'^(Figure (?:A\.)?\d+)\.')
PARA = re.compile(r'<w:p[ >].*?</w:p>', re.S)
MERGED = 'PAPERFIG-MERGED-SLOT'           # marks a slot taken over by a pair's image
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W, 'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def q(tag):
    return f'{{{W}}}{tag}'


# ------------------------------------------------------------------ figures
def _text(p):
    return ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p)).strip()


def _size(name):
    """Printed size in EMU, from the PNG's pixels and its 300 dpi."""
    w, h = Image.open(os.path.join(S.PAPER, name + '.png')).size
    return round(w / S.DPI * EMU), round(h / S.DPI * EMU)


def _slots(entries):
    """FIGURES entry -> one (name, role) per image slot: role 'own', 'pair' (the
    slot that shows a pair) or 'merged' (the slot the pair takes over)."""
    out = []
    for e in entries:
        if isinstance(e, tuple):
            out += [(e[0], 'pair')] + [(e[0], 'merged')] * (e[1] - 1)
        else:
            out.append((e, 'own'))
    return out


def _swap_images(doc, add_media):
    """Point every slot at its new image; returns the document and the new rIds of pairs."""
    pair_rids = set()
    current, slot = None, 0
    pieces, pos = [], 0
    for m in PARA.finditer(doc):
        p = m.group(0)
        cap = CAPTION.match(_text(p))
        if cap and '<w:drawing>' not in p:
            current, slot = cap.group(1), 0
            continue
        if '<w:drawing>' not in p:
            continue
        if current not in FIGURES:
            raise SystemExit(f'image after "{current}" has no entry in FIGURES')
        slots = _slots(FIGURES[current])
        new_p = p
        for d in re.findall(r'<w:drawing>.*?</w:drawing>', p, re.S):
            if slot >= len(slots):
                raise SystemExit(f'{current} has more images than FIGURES lists')
            name, role = slots[slot]; slot += 1
            if name is None:
                continue
            if role == 'merged':
                new_p = new_p.replace(d, f'<w:t>{MERGED}</w:t>', 1)
                continue
            rid = add_media(name)
            cx, cy = _size(name)
            d2 = re.sub(r'r:embed="[^"]+"', f'r:embed="{rid}"', d)
            d2 = re.sub(r'(<wp:extent )cx="\d+" cy="\d+"', rf'\1cx="{cx}" cy="{cy}"', d2)
            d2 = re.sub(r'(<a:ext )cx="\d+" cy="\d+"', rf'\1cx="{cx}" cy="{cy}"', d2)
            d2 = re.sub(r'<a:srcRect[^>]*/>', '<a:srcRect/>', d2)       # no inherited crop
            new_p = new_p.replace(d, d2, 1)
            print(f'   {current:<11} {name}')
            if role == 'pair':
                pair_rids.add(rid)
        pieces += [doc[pos:m.start()], new_p]; pos = m.end()
    pieces.append(doc[pos:])
    return ''.join(pieces), pair_rids


# ------------------------------------------------------------------ lxml helpers
def _texts(el):
    return ''.join(el.itertext()).strip()


def _child(parent, tag, before=()):
    """parent's child `tag`, created if missing and inserted before the first child
    whose tag is in `before`, keeping the element order Word requires."""
    el = parent.find(q(tag))
    if el is None:
        el = etree.Element(q(tag))
        for i, c in enumerate(parent):
            if etree.QName(c).localname in before:
                parent.insert(i, el); break
        else:
            parent.append(el)
    return el


def _tc_width(tc):
    w = tc.find('w:tcPr/w:tcW', NS)
    return int(w.get(q('w'))) if w is not None else 0


def _tc_span(tc):
    g = tc.find('w:tcPr/w:gridSpan', NS)
    return int(g.get(q('val'))) if g is not None else 1


TCPR_AFTER_W = ('gridSpan', 'hMerge', 'vMerge', 'tcBorders', 'shd', 'noWrap', 'tcMar',
                'textDirection', 'tcFitText', 'vAlign', 'hideMark')


def _merge_pair_rows(root, pair_rids):
    """For each row holding a pair's image: titles stay in a row of their own, and the
    image goes in one cell spanning the row."""
    for blip in list(root.iter('{%s}blip' % NS['a'])):
        if blip.get('{%s}embed' % NS['r']) not in pair_rids:
            continue
        tr = next(blip.iterancestors(q('tr')))
        img_p = next(blip.iterancestors(q('p')))
        tcs = tr.findall('w:tc', NS)
        parent, idx = tr.getparent(), tr.getparent().index(tr)

        title = copy.deepcopy(tr)
        for p in list(title.iter(q('p'))):
            if p.find('.//w:drawing', NS) is not None or MERGED in _texts(p):
                p.getparent().remove(p)
        for tc in title.findall('w:tc', NS):
            if tc.find('w:p', NS) is None:
                tc.append(etree.Element(q('p')))

        image = copy.deepcopy(tr)
        for tc in image.findall('w:tc', NS):
            image.remove(tc)
        trpr = image.find('w:trPr', NS)
        if trpr is not None:
            for h in trpr.findall('w:trHeight', NS):
                trpr.remove(h)
        cell = copy.deepcopy(tcs[0])
        for c in list(cell):
            if etree.QName(c).localname != 'tcPr':
                cell.remove(c)
        tcpr = _child(cell, 'tcPr')
        for v in tcpr.findall('w:vMerge', NS):
            tcpr.remove(v)
        tcw = _child(tcpr, 'tcW', before=TCPR_AFTER_W)
        tcw.attrib.update({q('w'): str(sum(_tc_width(t) for t in tcs)), q('type'): 'dxa'})
        _child(tcpr, 'gridSpan', before=TCPR_AFTER_W[1:]).set(
            q('val'), str(sum(_tc_span(t) for t in tcs)))
        cell.append(copy.deepcopy(img_p))
        image.append(cell)

        parent.remove(tr)
        for k, row in enumerate(([title] if _texts(title) else []) + [image]):
            parent.insert(idx + k, row)


def _even_columns(root, new_rids):
    """Two-column figure tables that received new panels get equal columns: the
    manuscript's columns were nudged to fit the old images (3.09 / 3.41 and the like)."""
    for tbl in root.iter(q('tbl')):
        embeds = {b.get('{%s}embed' % NS['r']) for b in tbl.iter('{%s}blip' % NS['a'])}
        cols = tbl.findall('w:tblGrid/w:gridCol', NS)
        if not embeds & new_rids or len(cols) != 2:
            continue
        total = sum(int(c.get(q('w'))) for c in cols)
        half = [total // 2, total - total // 2]
        for c, w in zip(cols, half):
            c.set(q('w'), str(w))
        for tr in tbl.findall('w:tr', NS):
            tcs = tr.findall('w:tc', NS)
            if len(tcs) == 2:
                for tc, w in zip(tcs, half):
                    tw = tc.find('w:tcPr/w:tcW', NS)
                    if tw is not None:
                        tw.set(q('w'), str(w))


# ------------------------------------------------------------------ tables
RPR_AFTER_SZ = ('highlight', 'u', 'effect', 'bdr', 'shd', 'fitText', 'vertAlign', 'rtl', 'cs',
                'em', 'lang', 'eastAsianLayout', 'specVanish', 'oMath')
TCPR_AFTER_BORDERS = ('shd', 'noWrap', 'tcMar', 'textDirection', 'tcFitText', 'vAlign', 'hideMark')
DATA_CELL = re.compile(r'^[−\-–]?\d|^NA$')


def _font(run, pt):
    """Set a run to the table font and size, in the element order Word requires."""
    rpr = run.find('w:rPr', NS)
    if rpr is None:
        rpr = etree.Element(q('rPr')); run.insert(0, rpr)
    for tag in ('rFonts', 'sz', 'szCs'):
        for el in rpr.findall(f'w:{tag}', NS):
            rpr.remove(el)
    f = etree.Element(q('rFonts'))
    for a in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
        f.set(q(a), TABLE_FONT)
    rpr.insert(1 if len(rpr) and etree.QName(rpr[0]).localname == 'rStyle' else 0, f)
    sz = _child(rpr, 'sz', before=RPR_AFTER_SZ)
    sz.set(q('val'), str(int(pt * 2)))
    szcs = etree.Element(q('szCs')); szcs.set(q('val'), str(int(pt * 2)))
    rpr.insert(rpr.index(sz) + 1, szcs)


def _borders(tc, top=0, bottom=0):
    tcpr = _child(tc, 'tcPr')
    for tag in ('tcBorders', 'shd'):
        for el in tcpr.findall(f'w:{tag}', NS):
            tcpr.remove(el)
    b = _child(tcpr, 'tcBorders', before=TCPR_AFTER_BORDERS)
    for side, sz in (('top', top), ('left', 0), ('bottom', bottom), ('right', 0)):
        e = etree.SubElement(b, q(side))
        if sz:
            e.attrib.update({q('val'): 'single', q('sz'): str(sz), q('space'): '0',
                             q('color'): '000000'})
        else:
            e.set(q('val'), 'nil')


def _restyle_table(tbl):
    rows = tbl.findall('w:tr', NS)
    texts = [[_texts(tc) for tc in tr.findall('w:tc', NS)] for tr in rows]
    caption = 1 if texts and texts[0] and texts[0][0].startswith('Table') else 0
    note = next((i for i, t in enumerate(texts) if t and re.match(r'^(Source|Notes?)\b', t[0])),
                len(rows))
    # the header ends at the first row with a number in it, or at a section label
    # (a row where only the first cell has text)
    first_data = next((i for i in range(caption, note)
                       if any(DATA_CELL.match(c) for c in texts[i][1:])
                       or (i > caption and texts[i][0] and not any(texts[i][1:]))), caption + 1)
    last_header = first_data - 1

    tblpr = tbl.find('w:tblPr', NS)
    for el in tblpr.findall('w:tblBorders', NS):
        tblpr.remove(el)
    tb = _child(tblpr, 'tblBorders', before=('shd', 'tblLayout', 'tblCellMar', 'tblLook',
                                             'tblCaption', 'tblDescription'))
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        etree.SubElement(tb, q(side)).set(q('val'), 'nil')

    for i, tr in enumerate(rows):
        top = RULE_HEAVY if i == caption else 0
        if caption < i < note and texts[i] and texts[i][0].lower().startswith('total'):
            top = RULE_LIGHT
        bottom = RULE_HEAVY if i == note - 1 else RULE_LIGHT if i == last_header else 0
        for tc in tr.findall('w:tc', NS):
            _borders(tc, top, bottom)
        if i >= caption:
            for r in tr.iter(q('r')):
                _font(r, NOTE_PT if i >= note else TABLE_PT)
    return (f'{len(rows)} rows; caption row {caption if caption else "none"}, header rows '
            f'{caption}-{last_header}, notes from row {note if note < len(rows) else "none"}; '
            f'starts "{texts[caption][0][:30] if texts[caption] else ""}"')


def _restyle_tables(root):
    """The innermost tables that hold no figure and at least three rows are the
    paper's data tables."""
    n = 0
    for tbl in list(root.iter(q('tbl'))):
        if tbl.find('.//w:tbl', NS) is not None or tbl.find('.//w:drawing', NS) is not None:
            continue
        if len(tbl.findall('w:tr', NS)) < 3:
            continue
        info = _restyle_table(tbl); n += 1
        print(f'   table: {info}')
    print(f'   restyled {n} tables')


# ------------------------------------------------------------------ main
def place(src, out, tables=True):
    with zipfile.ZipFile(src) as z:
        files = {n: z.read(n) for n in z.namelist()}
    doc = files['word/document.xml'].decode('utf-8')
    rels = files['word/_rels/document.xml.rels'].decode('utf-8')
    next_rid = [max(int(i) for i in re.findall(r'Id="rId(\d+)"', rels)) + 1]
    new_rels, new_rids = [], set()

    def add_media(name):
        rid = f'rId{next_rid[0]}'; next_rid[0] += 1
        target = f'media/paperfig_{name}.png'
        files['word/' + target] = open(os.path.join(S.PAPER, name + '.png'), 'rb').read()
        new_rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                        f'officeDocument/2006/relationships/image" Target="{target}"/>')
        new_rids.add(rid)
        return rid

    doc, pair_rids = _swap_images(doc, add_media)
    root = etree.fromstring(doc.encode('utf-8'))
    _merge_pair_rows(root, pair_rids)
    _even_columns(root, new_rids)
    if tables:
        _restyle_tables(root)
    if MERGED in etree.tostring(root, encoding='unicode'):
        raise SystemExit('a merged slot was left behind')

    files['word/document.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8',
                                                standalone=True)
    files['word/_rels/document.xml.rels'] = rels.replace(
        '</Relationships>', ''.join(new_rels) + '</Relationships>').encode('utf-8')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items():
            z.writestr(n, b)
    print(f'placed {len(new_rids)} images; wrote {out}')
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    src = args[0]
    out = args[1] if len(args) > 1 else os.path.splitext(src)[0] + '_figures.docx'
    if os.path.abspath(out) == os.path.abspath(src):
        sys.exit('refusing to overwrite the input document')
    place(src, out, tables='--keep-tables' not in sys.argv)
