#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_h5p_answers.py - check whether H5P items actually recorded an answer.

A full grade (10/10) does not always mean the H5P review page has a stored
attempt: content can be graded through `setFinished` while the answer payload
never reaches the review table. This script opens each item's "Grade analysis"
page (which redirects to mod/hvp/review.php) and classifies it:

  OK        -> review page shows "Score: x out of y / Gradebook score: ..."
  NO_ANSWER -> "This user hasn't submitted an answer to the H5P yet"
  NO_BOOK   -> review page exists but the content has no questions (InteractiveBook)
  NO_LINK   -> no grade-analysis link in the grade report (e.g. mod_h5pactivity)
  UNKNOWN   -> page did not load / unexpected layout

NO_ANSWER items should be solved again: the check/save action posts an xAPI
answered statement that the review page can display.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cloudcampus import Safari, Moodle, BASE_URL, add_browser_args, make_browser, js


def probe(safari: Safari) -> str:
    raw = safari.js_file(js("scan/review_probe.js"))
    try:
        return json.loads(raw).get("text", "")
    except Exception:
        return raw


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit H5P review pages for stored answers")
    ap.add_argument("--course-id", type=int, required=True)
    ap.add_argument("--tab", type=int, default=0)
    add_browser_args(ap)
    ap.add_argument("--out", default="h5p_answer_audit.json")
    ap.add_argument("--ids", help="only these h5p activity ids")
    args = ap.parse_args()

    safari = make_browser(args)
    if not args.tab:
        safari.ensure_window(BASE_URL)
        safari.tab = safari.list_tabs()[0].index
    else:
        safari.tab = args.tab
    moodle = Moodle(safari, args.course_id)
    moodle.open_grade_report()
    links = safari.render(js("scan/h5p_review_links.js"))
    if not isinstance(links, list):
        raise RuntimeError("could not read H5P review links from the grade report")
    want = set(x.strip() for x in args.ids.split(",")) if args.ids else None
    if want:
        links = [x for x in links if str(x["id"]) in want]

    result = {}
    for n, it in enumerate(links, 1):
        aid = str(it["id"])
        analysis = it.get("analysis") or ""
        if not analysis:
            result[aid] = {"name": it.get("name", ""), "status": "NO_LINK"}
            print(f"[{n}/{len(links)}] {aid} NO_LINK", flush=True)
            continue
        safari.navigate(analysis, timeout=60)
        time.sleep(2)
        text = probe(safari)
        if "hasn't submitted an answer" in text:
            status = "NO_ANSWER"
        else:
            m = re.search(r"Score:\s*([0-9]+) out of ([0-9]+).*?Gradebook score:\s*([0-9]+) out of ([0-9]+)", text)
            if m:
                status = "OK"
                result[aid] = {"name": it.get("name", ""), "status": status, "raw": m.group(0)}
                print(f"[{n}/{len(links)}] {aid} OK {m.group(0)}", flush=True)
                continue
            if re.search(r"no (?:questions|interactions)", text, re.I) or len(text.strip()) < 160:
                status = "NO_BOOK"
            else:
                status = "UNKNOWN"
        result[aid] = {"name": it.get("name", ""), "status": status, "text": text[:300]}
        print(f"[{n}/{len(links)}] {aid} {status}", flush=True)
        time.sleep(0.3)

    counts: dict[str, int] = {}
    for v in result.values():
        counts[v["status"]] = counts.get(v["status"], 0) + 1
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"counts": counts, "items": result}, fh, ensure_ascii=False, indent=1)
    print("counts:", counts)
    bad = [k for k, v in result.items() if v["status"] == "NO_ANSWER"]
    if bad:
        print("re-solve these (no stored answer):", ", ".join(bad))
    print(f"saved {args.out}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
