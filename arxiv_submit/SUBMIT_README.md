# arXiv Submission Package — D5-033

## Pre-submission Checklist

- [x] LaTeX v0.5 honesty version
- [x] DOI registered (10.5281/zenodo.20537026)
- [x] ORCID linked (0009-0008-2550-130X)
- [x] Simons & de Weger reference added
- [x] Known Limitations section
- [x] Honesty Statement in abstract
- [ ] arXiv account registration
- [ ] License: CC BY 4.0

## Submission Steps

### 1. Register at arXiv
```
https://arxiv.org/register
Category: math.NT (Number Theory)
         or math.GM (General Mathematics)
         or cs.AI  (Artificial Intelligence, if emphasizing MSS framework)
```

### 2. Prepare Submission
```
Compile LaTeX → D5-033_arxiv_draft.pdf
Strip comments/metadata:
  pdflatex D5-033_arxiv_draft.tex
  bibtex D5-033_arxiv_draft
  pdflatex D5-033_arxiv_draft.tex
  pdflatex D5-033_arxiv_draft.tex
```

### 3. Submit
```
https://arxiv.org/submit
- Upload .tex + .bib + any figures
- Title: On the Collatz Conjecture via Meaning Supremacy Axioms
- Authors: MSS-AI Proof Engine
- Abstract: (from v0.5)
- Cross-list: math.NT as primary
```

### 4. After Acceptance
```
- Add arXiv ID to Zenodo record (version update)
- Add arXiv badge to GitHub README
- Create H481 KB entry
```

## Known Issues
- arXiv requires institutional affiliation or endorsement for first submission
- May need to use "Independent Researcher" + endorsement
- Alternative: submit to viXra first, then arXiv

## Alternative: viXra (no endorsement needed)
```
http://vixra.org/submit
- Faster, no endorsement
- Less prestigious but fully open
- Can serve as pathway to arXiv endorsement
```
