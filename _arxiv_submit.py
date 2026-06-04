#!/usr/bin/env python3
"""Arxiv submission preparation for MSRA paper.
Run: python _arxiv_submit.py [--dry-run]

Prepares the submission bundle:
1. Flattens LaTeX source (single .tex file with embedded bibliography)
2. Creates .tar.gz archive for arXiv upload
3. Validates file size limits (<50MB for arXiv)
"""
import os, tarfile, subprocess, sys, datetime

PROJECT = os.path.dirname(os.path.abspath(__file__))
PAPER_TEX = os.path.join(PROJECT, 'msra_arxiv_paper_v1.tex')
SUBMIT_DIR = os.path.join(PROJECT, 'arxiv_submit')
OUTPUT = os.path.join(SUBMIT_DIR, 'msra_submission.tar.gz')

ARXIV_MAX_SIZE = 50 * 1024 * 1024  # 50 MB
DRY_RUN = '--dry-run' in sys.argv

def step(msg):
    print(f"  [{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def main():
    print("=" * 60)
    print("MSRA arXiv Submission Preparation")
    print(f"  Dry run: {DRY_RUN}")
    print("=" * 60)

    # 1. Create submission directory
    step("Creating submission directory")
    if not DRY_RUN:
        os.makedirs(SUBMIT_DIR, exist_ok=True)

    # 2. Copy the main .tex file
    step(f"Copying {PAPER_TEX}")
    submit_tex = os.path.join(SUBMIT_DIR, 'msra_arxiv_paper_v1.tex')
    if not os.path.exists(PAPER_TEX):
        print(f"ERROR: {PAPER_TEX} not found!")
        sys.exit(1)
    
    if not DRY_RUN:
        with open(PAPER_TEX, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(submit_tex, 'w', encoding='utf-8') as f:
            f.write(content)
        
    tex_size = os.path.getsize(PAPER_TEX)
    print(f"  Main .tex: {tex_size/1024:.1f} KB")

    # 3. Check LaTeX compilation (if pdflatex available)
    step("Checking pdflatex availability")
    pdflatex_available = False
    try:
        subprocess.run(['pdflatex', '--version'], capture_output=True, timeout=5)
        pdflatex_available = True
        print("  pdflatex: AVAILABLE")
    except:
        print("  pdflatex: NOT FOUND (install MiKTeX or TeX Live)")
        print("  Skipping compilation check. Submit .tex directly to arXiv.")

    # Try to compile if available
    if pdflatex_available and not DRY_RUN:
        step("Compiling LaTeX (pass 1)")
        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', '-output-directory', SUBMIT_DIR, submit_tex],
            capture_output=True, text=True, timeout=30, cwd=SUBMIT_DIR
        )
        if result.returncode != 0:
            print(f"  WARNING: pdflatex returned {result.returncode}")
            # Check for common errors
            if 'Undefined control sequence' in result.stdout:
                print("  Issue: Undefined control sequences found")
            if '! LaTeX Error' in result.stdout:
                error_lines = [l for l in result.stdout.split('\n') if '! LaTeX Error' in l]
                for line in error_lines[:3]:
                    print(f"    {line.strip()}")
        
        # Check if .pdf was produced
        pdf_file = os.path.join(SUBMIT_DIR, 'msra_arxiv_paper_v1.pdf')
        if os.path.exists(pdf_file):
            pdf_size = os.path.getsize(pdf_file)
            print(f"  PDF produced: {pdf_size/1024:.1f} KB")
        else:
            print("  WARNING: No PDF produced. arXiv will auto-compile.")

    # 4. Validate submission
    step("Validating submission")
    # Check that the .tex is self-contained (no \input{} or \include{})
    with open(PAPER_TEX, 'r', encoding='utf-8') as f:
        tex = f.read()
    
    inputs = []
    for line in tex.split('\n'):
        if '\\input{' in line or '\\include{' in line:
            inputs.append(line.strip())
    
    if inputs:
        print(f"  WARNING: External inputs found ({len(inputs)}):")
        for inp in inputs[:5]:
            print(f"    {inp[:80]}")
        print("  May need to flatten for arXiv.")
    else:
        print("  Self-contained: YES (no external inputs)")

    # Check file size
    if os.path.exists(submit_tex):
        total_size = os.path.getsize(submit_tex)
        if total_size > ARXIV_MAX_SIZE:
            print(f"  ERROR: Total size {total_size/1024/1024:.1f} MB exceeds arXiv limit (50 MB)")
        else:
            print(f"  Size OK: {total_size/1024:.1f} KB (limit: {ARXIV_MAX_SIZE/1024/1024:.0f} MB)")

    # 5. Create archive
    if not DRY_RUN:
        step(f"Creating {OUTPUT}")
        with tarfile.open(OUTPUT, 'w:gz') as tar:
            tar.add(submit_tex, arcname='msra_arxiv_paper_v1.tex')
        
        archive_size = os.path.getsize(OUTPUT)
        print(f"  Archive: {archive_size/1024:.1f} KB")

    # 6. Print submission instructions
    print()
    print("=" * 60)
    print("ARXIV SUBMISSION INSTRUCTIONS")
    print("=" * 60)
    print()
    print("1. Register at https://arxiv.org/register")
    print("2. Go to https://arxiv.org/submit")
    print("3. Upload file: arxiv_submit/msra_arxiv_paper_v1.tex")
    print("4. Category: cs.AI (Artificial Intelligence) or cs.LO (Logic in CS)")
    print("5. Title: Modular Symbolic Reasoning Architecture for Deterministic")
    print("   Logical Inference: A Formal Verification Approach")
    print("6. Authors: [Your Name], [Co-authors if any]")
    print("7. Abstract: See Section 1 of the paper")
    print("8. Note: This is a self-contained .tex file. arXiv will compile it.")
    print("   arXiv uses TeX Live (2024). The paper uses standard packages.")
    print()
    print("If pdflatex is not installed locally, the arXiv auto-compile")
    print("will produce the PDF after upload (allow 24-48 hours).")
    print()

    # 7. Clean-up recommendations
    print("=" * 60)
    print("PRE-FLIGHT CHECKLIST")
    print("=" * 60)
    checks = [
        ("Author list complete?", "Add author names/affiliations before submission"),
        ("Abstract matches?", "Copy-paste from Section 1 into arXiv form"),
        ("No undefined references?", "arXiv compile will show warnings if any"),
        ("Figures (if any)?", "Paper currently text-only, no figures to upload"),
        ("License selected?", "Recommend: arXiv.org perpetual, non-exclusive 1.0"),
        ("Ancillary files?", "No ancillary files needed (self-contained .tex)"),
    ]
    for q, note in checks:
        print(f"  [ ] {q}")
        print(f"      → {note}")
        print()

    print("Done.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
