#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

mkdir -p reports/generated

python_command="python3"
if [[ -x .venv/bin/python ]]; then
  python_command=".venv/bin/python"
fi
"$python_command" scripts/generate_publication_figures.py

render_figure() {
  local svg_file="$1"
  local png_file="${svg_file%.svg}.png"

  if command -v rsvg-convert >/dev/null 2>&1; then
    rsvg-convert "$svg_file" -o "$png_file"
  elif command -v sips >/dev/null 2>&1; then
    sips -s format png "$svg_file" --out "$png_file" >/dev/null
  elif command -v inkscape >/dev/null 2>&1; then
    inkscape "$svg_file" --export-type=png --export-filename="$png_file"
  elif command -v soffice >/dev/null 2>&1; then
    soffice --headless --convert-to png --outdir "$(dirname "$svg_file")" \
      "$svg_file" >/dev/null
  else
    echo "Install rsvg-convert, sips, Inkscape, or LibreOffice to render figures." >&2
    exit 1
  fi
}

for svg_file in paper/figures/*.svg; do
  render_figure "$svg_file"
done

report_json="reports/generated/preprint-report.json"
docx_output="paper/Edge_Litter_Detection_Preprint.docx"
pdf_output="paper/Edge_Litter_Detection_Preprint.pdf"

node scripts/paper_to_report_json.js \
  paper/edge_litter_detection_preprint.md \
  "$report_json"
node scripts/generate_paper_docx.js "$report_json" "$docx_output"

office_command=""
if command -v soffice >/dev/null 2>&1; then
  office_command="soffice"
elif command -v libreoffice >/dev/null 2>&1; then
  office_command="libreoffice"
else
  echo "LibreOffice is required to render the publication PDF." >&2
  exit 1
fi

paper_build_dir="$(mktemp -d "${TMPDIR:-/tmp}/edge-litter-paper.XXXXXX")"
trap 'rm -rf "$paper_build_dir"' EXIT
"$office_command" --headless --convert-to pdf --outdir "$paper_build_dir" \
  "$docx_output" >/dev/null
cp "$paper_build_dir/Edge_Litter_Detection_Preprint.pdf" "$pdf_output"

echo "Built $docx_output"
echo "Built $pdf_output"
