#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_progress.py - audit a CloudCampus course without changing anything.

Two checks:
  1. every graded item in the user grade report: full / zero / ungraded
  2. every assignment listed in --manifest (or a Moodle assignments scan):
     whether its view page says "Submitted for grading"

Exit code 0 = no zero-grade item and no unsubmitted assignment.
Interactive books that stay ungraded are reported as a warning, not a failure,
because they contain no gradable interactions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cloudcampus import Safari, Moodle, BASE_URL, add_browser_args, make_browser


def classify(grade: str) -> str:
    if grade in ("-", ""):
        return "ungraded"
    try:
        val = float(grade)
    except Exception:
        return "other"
    if val == 0:
        return "zero"
    return "graded"


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit CloudCampus grades and assignment submissions")
    ap.add_argument("--course-id", type=int, required=True)
    ap.add_argument("--tab", type=int, default=0)
    add_browser_args(ap)
    ap.add_argument("--manifest", help="submit manifest; its assignment ids are checked for submission status")
    ap.add_argument("--ids", help="comma separated assignment ids to check when no manifest is given")
    ap.add_argument("--out", default="verify_progress.json")
    args = ap.parse_args()

    safari = make_browser(args)
    if not args.tab:
        safari.ensure_window(BASE_URL)
        safari.tab = safari.list_tabs()[0].index
    else:
        safari.tab = args.tab
    moodle = Moodle(safari, args.course_id)

    print("reading grade report ...", flush=True)
    rows = moodle.open_grade_report()
    report = {"course_id": args.course_id, "grade_url": moodle.grade_url, "items": [], "counts": {},
              "course_total": "", "assignments": {}, "warnings": []}
    grade_raw = safari.render(os.path.join(os.path.dirname(__file__), "js", "scan", "grade_rows.js")) or {}
    report["course_total"] = grade_raw.get("total", "")

    counts: dict[str, int] = {}
    for r in rows:
        state = classify(r.get("grade", ""))
        r["state"] = state
        report["items"].append({"id": r["id"], "mod": r["mod"], "name": r.get("name", ""),
                                "grade": r.get("grade", ""), "pct": r.get("pct", ""), "state": state})
        counts[state] = counts.get(state, 0) + 1
    report["counts"] = counts

    ids = []
    if args.manifest:
        manifest = json.load(open(args.manifest, encoding="utf-8"))
        ids = [str(it["id"]) for it in manifest.get("items", [])]
    elif args.ids:
        ids = [x.strip() for x in args.ids.split(",") if x.strip()]

    for aid in ids:
        try:
            moodle.open_assignment(int(aid))
            info = moodle.read_assignment()
            submitted = "Submitted for grading" in (info.get("status") or "")
            report["assignments"][aid] = {"submitted": submitted, "status": info.get("status", "")[:300]}
            print(f"  assignment {aid}: {'submitted' if submitted else 'NOT SUBMITTED'}", flush=True)
        except Exception as exc:
            report["assignments"][aid] = {"submitted": False, "error": str(exc)}
            print(f"  assignment {aid}: ERROR {exc}", flush=True)
        time.sleep(0.4)

    h5p_ungraded = [it for it in report["items"] if it["state"] == "ungraded" and it["mod"] in ("hvp", "h5pactivity")]
    assign_ungraded = [it for it in report["items"] if it["state"] == "ungraded" and it["mod"] == "assign"]
    report["summary"] = {
        "graded": counts.get("graded", 0),
        "zero": counts.get("zero", 0),
        "ungraded": counts.get("ungraded", 0),
        "h5p_ungraded": len(h5p_ungraded),
        "assignment_ungraded_waiting_teacher": len(assign_ungraded),
        "assignments_total": len(ids),
        "assignments_submitted": sum(1 for v in report["assignments"].values() if v.get("submitted")),
    }
    if h5p_ungraded:
        report["warnings"].append("H5P items with no grade: " + ", ".join(it["id"] for it in h5p_ungraded))
    if assign_ungraded:
        print(f"note: {len(assign_ungraded)} assignment items have no grade yet (teacher has not graded them)")
    missing = [k for k, v in report["assignments"].items() if not v.get("submitted")]
    if missing:
        report["warnings"].append(f"assignments without a submission: {missing}")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    print("\n=== grade report ===")
    print(f"items: {len(rows)}  graded: {counts.get('graded',0)}  zero: {counts.get('zero',0)}  ungraded: {counts.get('ungraded',0)}")
    print(f"course total: {report['course_total']}")
    if ids:
        print(f"assignments submitted: {report['summary']['assignments_submitted']}/{len(ids)}")
    for w in report["warnings"]:
        print("warning:", w)
    print(f"saved {args.out}")

    ok = counts.get("zero", 0) == 0 and not missing
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
