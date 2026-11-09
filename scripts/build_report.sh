#!/bin/bash
# Compile the mid-term report, check the 4-page limit, archive this build in report/history/ (every version is kept,
# PROGRESS 39) and copy the PDF to ~/Downloads/midterm_report_draft.pdf.
cd "$(dirname "$0")/../report" || exit 1
../../tools/tectonic.exe -X compile midterm.tex > /dev/null 2>&1 || { echo "compile failed"; exit 1; }
pages=$(../../.venv/Scripts/python -W ignore -c "import fitz; print(fitz.open('midterm.pdf').page_count)")
echo "$pages pages"
[ "$pages" -le 4 ] || { echo "over the 4-page limit, not archived"; exit 1; }
stamp=$(date +%Y-%m-%d_%H%M)
cp midterm.tex history/midterm_${stamp}_build.tex
cp midterm.pdf history/midterm_${stamp}_build.pdf
cp midterm.pdf ~/Downloads/midterm_report_draft.pdf
echo "archived history/midterm_${stamp}_build.pdf"
