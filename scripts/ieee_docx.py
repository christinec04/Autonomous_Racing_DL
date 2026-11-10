"""IEEE conference layout for the pandoc-made Word report (called by build_report_docx.py).

pandoc writes a plain single-column document with its own styles. This pass rewrites the styles and the section
layout to match the IEEE conference template (as in IEEEtran [conference]):
- US Letter, margins top 0.75 in, bottom 1 in, left/right 0.625 in; no page numbers
- title (24 pt) across the page, the authors side by side in one column each, then two columns 0.25 in apart
- Times New Roman 10 pt, justified, single spaced, first-line indent
- "Abstract—" run-in, bold 9 pt
- headings "I. INTRODUCTION" (small caps, centred) and "A. Vehicle model" (italic); unnumbered headings centred
- figure captions "Fig. 1. ..." and table captions "TABLE I" above the table, 8 pt; tables and references 8 pt
- figures scaled to the column width
Only the standard library is used (zipfile + regular expressions on the XML).
"""
import re
import shutil
import tempfile
import zipfile

TIMES = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman" w:cs="Times New Roman"/>'
COL_EMU = int(3.5 * 914400)  # column width 3.5 in


def _style(sid, name, ppr="", rpr="", based="Normal", kind="paragraph"):
    return (f'<w:style w:type="{kind}" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{name}"/>'
            f'<w:basedOn w:val="{based}"/><w:qFormat/><w:pPr>{ppr}</w:pPr><w:rPr>{TIMES}<w:color w:val="000000"/>{rpr}</w:rPr></w:style>')


def _sz(pt):
    return f'<w:sz w:val="{int(pt * 2)}"/><w:szCs w:val="{int(pt * 2)}"/>'


BODY_P = '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:firstLine="202"/><w:jc w:val="both"/>'
STYLES = [
    ('Normal', 'Normal', BODY_P, _sz(10), None),
    ('BodyText', 'Body Text', BODY_P, _sz(10), 'Normal'),
    ('FirstParagraph', 'First Paragraph', BODY_P, _sz(10), 'Normal'),
    ('Compact', 'Compact', '<w:spacing w:before="0" w:after="0"/><w:jc w:val="both"/>', _sz(10), 'Normal'),
    ('Title', 'Title', '<w:spacing w:before="0" w:after="240"/><w:ind w:firstLine="0"/><w:jc w:val="center"/>', _sz(24), 'Normal'),
    ('Author', 'Author', '<w:spacing w:before="0" w:after="240"/><w:ind w:firstLine="0"/><w:jc w:val="center"/>', _sz(10), 'Normal'),
    ('Abstract', 'Abstract', '<w:spacing w:before="0" w:after="120"/><w:ind w:firstLine="202"/><w:jc w:val="both"/>', '<w:b/><w:bCs/>' + _sz(9), 'Normal'),
    ('AbstractTitle', 'Abstract Title', '<w:jc w:val="center"/>', '<w:b/>' + _sz(9), 'Normal'),
    ('Heading1', 'heading 1', '<w:keepNext/><w:spacing w:before="160" w:after="80"/><w:ind w:firstLine="0"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/>',
     '<w:smallCaps/>' + _sz(10), 'Normal'),
    ('Heading2', 'heading 2', '<w:keepNext/><w:spacing w:before="120" w:after="60"/><w:ind w:firstLine="0"/><w:jc w:val="left"/><w:outlineLvl w:val="1"/>',
     '<w:i/><w:iCs/>' + _sz(10), 'Normal'),
    ('CaptionedFigure', 'Captioned Figure', '<w:keepNext/><w:spacing w:before="120" w:after="60"/><w:ind w:firstLine="0"/><w:jc w:val="center"/>', _sz(10), 'Normal'),
    ('ImageCaption', 'Image Caption', '<w:spacing w:before="0" w:after="160"/><w:ind w:firstLine="0"/><w:jc w:val="both"/>', _sz(8), 'Normal'),
    ('TableCaption', 'Table Caption', '<w:keepNext/><w:spacing w:before="120" w:after="80"/><w:ind w:firstLine="0"/><w:jc w:val="center"/>',
     '<w:smallCaps/>' + _sz(8), 'Normal'),
    ('TableText', 'Table Text', '<w:spacing w:before="0" w:after="0"/><w:ind w:firstLine="0"/><w:jc w:val="center"/>', _sz(8), 'Normal'),
    ('Reference', 'Reference', '<w:spacing w:before="0" w:after="20"/><w:ind w:left="300" w:hanging="300"/><w:jc w:val="both"/>', _sz(8), 'Normal'),
]


def _roman(n):
    out = ""
    for v, s in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s
            n -= v
    return out


def _sect(cols, space=360, last=False):
    pg = ('<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="900" w:bottom="1440" w:left="900" '
          'w:header="720" w:footer="720" w:gutter="0"/>')
    return (f'<w:sectPr><w:type w:val="continuous"/>{pg}<w:cols w:num="{cols}" w:space="{space}"/>'
            f'<w:docGrid w:linePitch="360"/></w:sectPr>')


def _styles(xml):
    xml = re.sub(r'<w:style[^>]*w:styleId="Hyperlink".*?</w:style>', '', xml, flags=re.S)
    xml = xml.replace('</w:styles>', '<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/>'
                      '<w:rPr><w:color w:val="000000"/></w:rPr></w:style></w:styles>')
    for sid, *_ in STYLES:
        xml = re.sub(rf'<w:style\b[^>]*w:styleId="{sid}".*?</w:style>', '', xml, flags=re.S)
    defs = ''.join(_style(sid, name, ppr, rpr, based) if based else
                   f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/>'
                   f'<w:pPr>{ppr}</w:pPr><w:rPr>{TIMES}<w:color w:val="000000"/>{rpr}</w:rPr></w:style>'
                   for sid, name, ppr, rpr, based in STYLES)
    # document defaults: Times 10 pt everywhere (tables, lists and anything pandoc styles itself)
    xml = re.sub(r'<w:rPrDefault>.*?</w:rPrDefault>',
                 f'<w:rPrDefault><w:rPr>{TIMES}{_sz(10)}<w:lang w:val="en-US"/></w:rPr></w:rPrDefault>', xml, flags=re.S)
    return xml.replace('</w:styles>', defs + '</w:styles>')


def _document(xml):
    body = re.search(r'<w:body>(.*)</w:body>', xml, flags=re.S)
    b = body.group(1)
    b = re.sub(r'<w:sectPr\b.*?</w:sectPr>\s*$', '', b, flags=re.S)  # pandoc's own (if any) is replaced

    # headings: "1<tab>Introduction" -> "I. Introduction" (small caps from the style), "3.1<tab>X" -> "A. X"
    h1 = [0]

    def head(m):
        p, level = m.group(0), m.group(1)
        num = re.search(r'<w:rStyle w:val="SectionNumber"\s*/></w:rPr><w:t[^>]*>([\d.]+)</w:t></w:r><w:r><w:tab\s*/></w:r>', p)
        if not num:
            return p
        parts = num.group(1).split(".")
        label = f"{_roman(int(parts[0]))}." if level == "1" else f"{chr(64 + int(parts[1]))}."
        return p.replace(num.group(0), f'<w:rStyle w:val="SectionNumber"/></w:rPr><w:t xml:space="preserve">{label} </w:t></w:r>')
    b = re.sub(r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="Heading([12])"\s*/>.*?</w:p>', head, b, flags=re.S)

    # abstract: drop the "Abstract" title paragraph, run "Abstract—" into the text (bold italic)
    b = re.sub(r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="AbstractTitle"\s*/>.*?</w:p>', '', b, count=1, flags=re.S)
    b = re.sub(r'(<w:pStyle w:val="Abstract"\s*/></w:pPr>)',
               r'\1<w:r><w:rPr><w:b/><w:i/></w:rPr><w:t xml:space="preserve">Abstract</w:t></w:r>'
               r'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">—</w:t></w:r>', b, count=1)

    # figure and table captions numbered the IEEE way
    fig = [0]

    def figcap(m):
        fig[0] += 1
        return m.group(1) + f'<w:r><w:t xml:space="preserve">Fig. {fig[0]}. </w:t></w:r>'
    b = re.sub(r'(<w:pStyle w:val="ImageCaption"\s*/></w:pPr>)', figcap, b)
    tab = [0]

    def tabcap(m):
        tab[0] += 1
        return (f'<w:p><w:pPr><w:pStyle w:val="TableCaption"/><w:spacing w:after="0"/></w:pPr><w:r>'
                f'<w:t xml:space="preserve">TABLE {_roman(tab[0])}</w:t></w:r></w:p>' + m.group(0))
    b = re.sub(r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="TableCaption"\s*/>.*?</w:p>', tabcap, b, flags=re.S)

    # table text 8 pt, centred, tables as wide as the column
    def table(m):
        t = re.sub(r'<w:pStyle w:val="Compact"\s*/>', '<w:pStyle w:val="TableText"/>', m.group(0))
        t = re.sub(r'<w:p>(?=<w:r>)', '<w:p><w:pPr><w:pStyle w:val="TableText"/></w:pPr>', t)
        t = re.sub(r'<w:tblW [^>]*/>', '<w:tblW w:type="pct" w:w="5000"/><w:jc w:val="center"/>', t, count=1)
        return t
    b = re.sub(r'<w:tbl>.*?</w:tbl>', table, b, flags=re.S)

    # references: every paragraph after the References heading
    i = b.find('>References<')
    if i > 0:
        j = b.find('</w:p>', i) + len('</w:p>')
        refs = re.sub(r'<w:pStyle w:val="(BodyText|FirstParagraph)"\s*/>', '<w:pStyle w:val="Reference"/>', b[j:])
        b = b[:j] + refs

    # in-text table references (pandoc links them to the table, anchor "tab:...") follow the Roman caption numbers
    b = re.sub(r'(<w:hyperlink w:anchor="tab:[^"]*">.*?<w:t[^>]*>)(\d+)(</w:t>)',
               lambda m: m.group(1) + _roman(int(m.group(2))) + m.group(3), b, flags=re.S)

    # figures no wider than the column
    def fit(m):
        cx, cy = int(m.group(2)), int(m.group(3))
        if cx <= COL_EMU:
            return m.group(0)
        return f'{m.group(1)}cx="{COL_EMU}" cy="{int(cy * COL_EMU / cx)}"'
    b = re.sub(r'(<(?:wp:extent|a:ext) )cx="(\d+)" cy="(\d+)"', fit, b)

    # sections: title (1 column) | authors (one column each) | body (2 columns)
    authors = list(re.finditer(r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="Author"\s*/>.*?</w:p>', b, flags=re.S))
    title = re.search(r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="Title"\s*/>.*?</w:p>', b, flags=re.S)
    if authors and title:
        n = len(authors)
        segs, pos = [], 0
        for k, a in enumerate(authors):
            p = a.group(0)
            # author name (first run) 11 pt
            p = re.sub(r'(<w:pStyle w:val="Author"\s*/></w:pPr><w:r>)(<w:t)', r'\1<w:rPr>' + _sz(11) + r'</w:rPr>\2', p, count=1)
            if k > 0:  # each author starts its own column
                p = p.replace('</w:pPr>', '</w:pPr><w:r><w:br w:type="column"/></w:r>', 1)
            if k == n - 1:  # end of the author section (sectPr is the last child of pPr)
                p = p.replace('</w:pPr>', _sect(n, 200) + '</w:pPr>', 1)
            segs.append((a.start(), a.end(), p))
        for s, e, p in reversed(segs):
            b = b[:s] + p + b[e:]
        t = re.search(r'<w:p>(?:(?!</w:p>).)*?<w:pStyle w:val="Title"\s*/>.*?</w:p>', b, flags=re.S)
        tp = re.sub(r'</w:pPr>', _sect(1) + '</w:pPr>', t.group(0), count=1)
        b = b[:t.start()] + tp + b[t.end():]
    b = b + _sect(2, 360, last=True)
    return xml[:body.start(1)] + b + xml[body.end(1):]


def ieee_format(path):
    """Rewrite the .docx at `path` in place with the IEEE conference layout."""
    tmp = tempfile.mktemp(suffix=".docx")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename.endswith("/"):
                continue  # no folder entries (Word through co-editing services refuses them)
            data = zin.read(item.filename)
            if item.filename == "word/styles.xml":
                data = _styles(data.decode("utf-8")).encode("utf-8")
            elif item.filename == "word/document.xml":
                data = _document(data.decode("utf-8")).encode("utf-8")
                # pandoc writes m:mcJc before m:count; the schema wants count first
                data = re.sub(rb'(<m:mcJc [^>]*/>)\s*(<m:count [^>]*/>)', lambda m: m.group(2) + m.group(1), data)
            elif item.filename == "[Content_Types].xml" and b'Extension="png"' not in data:
                data = data.replace(b'<Default Extension="xml"', b'<Default Extension="png" ContentType="image/png" /><Default Extension="xml"', 1)
            zout.writestr(item, data)
    shutil.move(tmp, path)


if __name__ == "__main__":
    import sys
    ieee_format(sys.argv[1])
