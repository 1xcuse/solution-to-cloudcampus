#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_course.py - inventory a CloudCampus course.

Reads the grade report (every graded item, its weight and current grade) and the
course index (sections/weeks and activity names). With --deep it also visits each
assignment page and records the prompt plus how it accepts work (online text vs
file upload), which is what you need to plan content.

Outputs inventory.json and inventory.md in --out (default: ./cloudcampus_scan).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cloudcampus import Safari, Moodle, BASE_URL, add_browser_args, make_browser


def classify(row: dict) -> str:
    mod = row.get("mod", "")
    if mod == "hvp":
        return "h5p"
    if mod == "h5pactivity":
        return "h5p-activity"
    if mod == "assign":
        return "assignment"
    return mod or "other"


def main() -> int:
    ap = argparse.ArgumentParser(description="Inventory a CloudCampus course via Safari")
    ap.add_argument("--course-id", type=int, required=True)
    ap.add_argument("--tab", type=int, default=0, help="Safari tab index; 0 = auto/new window")
    add_browser_args(ap)
    ap.add_argument("--out", default="cloudcampus_scan")
    ap.add_argument("--deep", action="store_true", help="visit each assignment page to read the prompt and form type")
    ap.add_argument("--keep-window", action="store_true", help="leave the Safari window open afterwards")
    args = ap.parse_args()

    safari = make_browser(args)
    if not args.tab:
        safari.ensure_window(BASE_URL)
        safari.tab = safari.list_tabs()[0].index
    else:
        safari.tab = args.tab
    m = Moodle(safari, args.course_id)

    print("[1/3] grade report ...", flush=True)
    rows = m.open_grade_report()
    items = []
    for r in rows:
        r["kind"] = classify(r)
        items.append(r)
    # fetch the "Course total" row from the same page
    grade_raw = safari.render(os.path.join(os.path.dirname(__file__), "js", "scan", "grade_rows.js"))
    total = grade_raw.get("total", "") if isinstance(grade_raw, dict) else ""

    print("[2/3] course index ...", flush=True)
    m.open_course()
    index = m.parse_course_index()
    sections = index.get("sections", [])
    # map cm id -> section title for convenience
    section_of = {}
    for sec in sections:
        for it in sec.get("items", []):
            if it.get("cmid"):
                section_of[str(it["cmid"])] = sec.get("title", "")
    for it in items:
        it["section"] = section_of.get(str(it.get("id")), "")

    counts = {}
    for it in items:
        counts[it["kind"]] = counts.get(it["kind"], 0) + 1

    print("[3/3] writing inventory ...", flush=True)
    os.makedirs(args.out, exist_ok=True)
    raw_title = index.get("title", "") or ""
    parts = [p.strip() for p in raw_title.split(" | ")]
    course_title = parts[-2] if len(parts) >= 2 else raw_title
    inv = {
        "course_id": args.course_id,
        "course_title": course_title,
        "course_url": f"{BASE_URL}/course/view.php?id={args.course_id}",
        "grade_url": m.grade_url,
        "course_total": total,
        "counts": counts,
        "sections": sections,
        "items": items,
        "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    if args.deep:
        assignments = [it for it in items if it["kind"] == "assignment"]
        for i, it in enumerate(assignments, 1):
            aid = int(it["id"])
            print(f"  assignment {i}/{len(assignments)}: {aid} ...", flush=True)
            try:
                m.open_assignment(aid)
                info = m.read_assignment()
                it.update({"task": info.get("task", ""), "status_text": info.get("status", ""), "view_buttons": info.get("buttons", [])})
                form = m.open_submission_form()
                it["form"] = {
                    "online_text": bool(form.get("online_editor") or form.get("online_textarea")),
                    "file_manager": bool(form.get("filemanager")),
                    "save_buttons": form.get("save_buttons", []),
                }
            except Exception as exc:  # keep scanning even if one page fails
                it["error"] = str(exc)
            time.sleep(0.5)

    with open(os.path.join(args.out, "inventory.json"), "w", encoding="utf-8") as fh:
        json.dump(inv, fh, ensure_ascii=False, indent=1)

    lines = [f"# CloudCampus 课程清单：{inv['course_title']}", ""]
    lines.append(f"- course id: {args.course_id}")
    lines.append(f"- grade report: {m.grade_url}")
    lines.append(f"- course total: {total}")
    lines.append(f"- item counts: {counts}")
    lines.append("")
    lines.append("| id | kind | section | name | weight | grade |")
    lines.append("|---|---|---|---|---|---|")
    for it in items:
        lines.append(f"| {it.get('id')} | {it.get('kind')} | {it.get('section','')} | {it.get('name','')[:70]} | {it.get('weight','')} | {it.get('grade','')} |")
    if args.deep:
        lines.append("")
        lines.append("## Assignment prompts")
        for it in items:
            if it["kind"] != "assignment" or "task" not in it:
                continue
            lines.append(f"\n### {it['id']}")
            lines.append("```")
            lines.append(it.get("task", "")[:1500])
            lines.append("```")
            lines.append(f"- form: {it.get('form')}")
    with open(os.path.join(args.out, "inventory.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    # leave Safari on the grade report, which is the least surprising place
    try:
        m.open_grade_report()
    except Exception:
        pass
    print(f"saved {args.out}/inventory.json and inventory.md")
    print(f"items: {len(items)} | counts: {counts}")
    if not args.keep_window:
        pass  # keep the window; closing is the operator's call
    return 0


if __name__ == "__main__":
    sys.exit(main())
