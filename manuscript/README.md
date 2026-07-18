# wildtag.ai - MEE Practical Tools skeleton (Overleaf project)

## Upload to Overleaf
New Project > Upload Project > drop in `wildtag_overleaf.zip`.

## Compiler settings
Menu > Settings:
- Compiler: **pdfLaTeX**  (the default)

No further configuration needed. The bibliography uses **BibTeX**, not biber.

## Files
- `main.tex` - the manuscript skeleton
- `mee.sty`  - house style implementing MEE's submission requirements
- `refs.bib` - bibliography (template entries only; add your real references)

## References
This project uses **`besjournals.bst`**, the British Ecological Society's own
author-year BibTeX style. It ships with TeX Live, so it is available on Overleaf
with no extra files and no manual upload.

Cite with natbib commands:

    \citep{key}   ->  (Author, 2024)
    \citet{key}   ->  Author (2024)

`main.tex` currently contains `\nocite{*}` so that the template entries appear
and the skeleton compiles with a visible reference list. **Delete that line** as
soon as you have real citations in the text, or every entry in `refs.bib` will be
printed whether you cited it or not.

## A note on the style file
Methods in Ecology and Evolution does **not** publish an official LaTeX class.
Wiley asks authors to submit a PDF generated from their own source files, and to
supply the .tex/.bib/.bbl on acceptance. `mee.sty` therefore does not imitate the
journal's typeset appearance. It implements what the journal actually requires at
submission: double spacing, continuous line numbers for reviewers, the BES
reference style, a numbered abstract, and generous margins.

## Draft markers (colour-coded in the PDF)
- **(cite)** in green - a citation is needed here
- *[orange italics]* - guidance for the authors; delete before submitting
- **[RED BRACKETS]** - a number, name or decision still outstanding

## Switching to submission mode
In `main.tex`, change:

    \usepackage{mee}      ->   \usepackage[final]{mee}

This strips the line numbers, guidance notes, (cite) markers and [TBD]
placeholders in one move. Add `anonymous` for double-anonymised review:

    \usepackage[final,anonymous]{mee}
