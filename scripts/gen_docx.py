#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_docx.py - turn a UTF-8 text file into a clean .docx for an assignment.

Paragraphs are split on blank lines. Requires python-docx; on DSH that is the
bundled runtime python:
  ~/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="Text file -> .docx")
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title")
    ap.add_argument("--font", default="Calibri")
    ap.add_argument("--size", type=int, default=12)
    args = ap.parse_args()

    from docx import Document
    from docx.shared import Pt, Inches

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = args.font
    style.font.size = Pt(args.size)
    for sec in doc.sections:
        sec.top_margin = Inches(1)
        sec.bottom_margin = Inches(1)
        sec.left_margin = Inches(1)
        sec.right_margin = Inches(1)
    if args.title:
        p = doc.add_paragraph()
        run = p.add_run(args.title)
        run.bold = True
        run.font.size = Pt(args.size + 2)
    text = open(args.input, encoding="utf-8").read()
    for para in text.split("\n\n"):
        para = para.strip()
        if para:
            doc.add_paragraph(para)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    doc.save(args.out)
    print(f"saved {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
