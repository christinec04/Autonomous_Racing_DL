"""Word version of the mid-term report, made from report/midterm.tex and the compiled report/midterm.pdf.

Figures: the PDF figures become PNGs, the TikZ architecture diagram is cropped from the compiled PDF (page 1, above
the Fig. 1 caption). Then pandoc (pypandoc_binary) converts the LaTeX to report/midterm.docx and scripts/ieee_docx.py gives it the IEEE
conference layout (two columns, Times 10 pt, IEEE headings and captions), a copy is archived in
report/history/ next to the PDF builds and one goes to ~/Downloads/midterm_report_draft.docx.
Run after scripts/build_report.sh:  python scripts/build_report_docx.py
"""
import datetime
import pathlib
import re
import shutil

import fitz
import pypandoc

from ieee_docx import ieee_format

REP = pathlib.Path(__file__).resolve().parent.parent / "report"
TMP = REP / "docx_build"


def main(name="midterm", downloads="midterm_report_draft.docx"):
    TMP.mkdir(exist_ok=True)
    for f in (REP / "figs").glob("*.pdf"):
        fitz.open(f)[0].get_pixmap(dpi=220).save(TMP / f"{f.stem}.png")
    pdf = fitz.open(REP / f"{name}.pdf")
    cap = pdf[0].search_for("Fig. 1.")[0]
    pdf[0].get_pixmap(clip=fitz.Rect(cap.x0 - 1, 212, 568, cap.y0 - 2), dpi=250).save(TMP / "architecture.png")

    tex = (REP / f"{name}.tex").read_text(encoding="utf-8")
    tex = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
                 lambda m: r"\includegraphics[width=\columnwidth]{architecture.png}", tex, flags=re.S)
    tex = re.sub(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\.pdf\}", r"\\includegraphics\1{\2.png}", tex)
    tex = re.sub(r"\\IEEEauthorblockN\{([^}]*)\}", lambda m: m.group(1) + r"\\", tex).replace(r"\IEEEauthorblockA", "")
    # numbered citations and a plain reference list (pandoc drops \cite without a .bib file)
    bib = re.search(r"\\begin\{thebibliography\}\{\d+\}(.*?)\\end\{thebibliography\}", tex, flags=re.S)
    items = re.findall(r"\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|\Z)", bib.group(1), flags=re.S)
    num = {k: i + 1 for i, (k, _) in enumerate(items)}
    tex = re.sub(r"~?\\cite\{([^}]+)\}", lambda m: " [" + ", ".join(str(num[k.strip()]) for k in m.group(1).split(",")) + "]", tex)
    refs = "\\section*{References}\n" + "\n\n".join(f"[{i + 1}] {t.strip()}" for i, (_, t) in enumerate(items))
    bib = re.search(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", tex, flags=re.S)  # after the \cite edits
    tex = tex[:bib.start()] + refs + "\n" + tex[bib.end():]
    (TMP / "midterm_docx.tex").write_text(tex, encoding="utf-8")

    out = REP / f"{name}.docx"
    pypandoc.convert_file(str(TMP / "midterm_docx.tex"), "docx", outputfile=str(out),
                          extra_args=[f"--resource-path={TMP}", "--number-sections"])
    ieee_format(out)  # two columns, Times 10 pt, IEEE headings and captions (scripts/ieee_docx.py)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    shutil.copy(out, REP / "history" / f"{name}_{stamp}_build.docx")
    shutil.copy(out, pathlib.Path.home() / "Downloads" / downloads)
    shutil.rmtree(TMP)
    print(out, f"archived history/{name}_{stamp}_build.docx")


if __name__ == "__main__":
    import sys
    main(*sys.argv[1:3])  # e.g. reduced_scope_draft reduced_scope_draft.docx
