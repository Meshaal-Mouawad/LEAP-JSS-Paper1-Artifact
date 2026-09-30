#!/bin/sh
set -eu
cd "$(dirname "$0")"
pdflatex -interaction=nonstopmode -halt-on-error LEAP_JSS_Paper1.tex
pdflatex -interaction=nonstopmode -halt-on-error LEAP_JSS_Paper1.tex
pdflatex -interaction=nonstopmode -halt-on-error LEAP_JSS_Paper1.tex
(cd supplement && pdflatex -interaction=nonstopmode -halt-on-error LEAP_JSS_Method_Supplement.tex && pdflatex -interaction=nonstopmode -halt-on-error LEAP_JSS_Method_Supplement.tex)
