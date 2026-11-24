#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""solve_h5p.py - complete H5P interactive exercises on CloudCampus.

Supports the content types seen in an EAP course and typical CloudCampus courses:
  DragText, Blanks, FindTheWords, SortParagraphs, QuestionSet,
  Flashcards, InteractiveBook, and the mod_h5pactivity wrapper (embedded book).

The script drives the page's own H5P instance APIs and DOM instead of guessing
coordinates, then (optionally) re-reads the grade report to prove each exercise
was recorded. Grading rules in Moodle's mod_hvp: the best captured attempt
wins, so one clean run is enough.

Examples
  python3 solve_h5p.py --course-id 12345 --ids 664639,664644 --tab 3
  python3 solve_h5p.py --course-id 12345 --from-scan cloudcampus_scan/inventory.json --types DragText,Blanks
  python3 solve_h5p.py --course-id 12345 --from-scan ... --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cloudcampus import Safari, Moodle, BASE_URL, add_browser_args, make_browser, js, write_temp_js

READY_TEMPLATE = r"""(function(){
  try {
    var ID = %s;
    if (location.href.indexOf('id=' + ID) < 0) return JSON.stringify({ready:false, why:'wrong_page', url: location.href.slice(-40)});
    if (document.readyState !== 'complete') return JSON.stringify({ready:false, why:'loading'});
    function markers(ins, doc) {
      var lib = ins.libraryInfo ? ins.libraryInfo.machineName : '';
      if (lib === 'H5P.DragText') return !!(ins.droppables && ins.droppables.length);
      if (lib === 'H5P.Blanks') return (doc.querySelectorAll('input').length > 0) && !!(ins.params && ins.params.questions);
      if (lib === 'H5P.FindTheWords') return !!(ins.grid && ins.grid.elementSize && ins.vocabulary && ins.vocabulary.words && ins.vocabulary.words.length);
      if (lib === 'H5P.SortParagraphs') return !!(ins.content && ins.content.getDraggables && ins.params && ins.params.paragraphs);
      if (lib === 'H5P.QuestionSet') { var q = ins.getQuestions ? ins.getQuestions() : null; return !!(q && q.length); }
      if (lib === 'H5P.Flashcards') return doc.querySelectorAll('.h5p-textinput').length > 0;
      if (lib === 'H5P.InteractiveBook') return !!(doc.querySelector('.h5p-interactive-book'));
      return true;
    }
    var f = document.querySelector('iframe.h5p-iframe');
    if (f && f.contentWindow && f.contentWindow.H5P && f.contentWindow.H5P.instances && f.contentWindow.H5P.instances.length) {
      var ins = f.contentWindow.H5P.instances[0];
      if (!markers(ins, f.contentDocument)) return JSON.stringify({ready:false, why:'not_attached', lib: ins.libraryInfo.machineName});
      return JSON.stringify({ready:true, lib: ins.libraryInfo.machineName, mode:'hvp'});
    }
    var player = document.querySelector('iframe.h5p-player');
    if (player) {
      var n = player.contentDocument ? player.contentDocument.querySelector('iframe') : null;
      if (n && n.contentWindow && n.contentWindow.H5P && n.contentWindow.H5P.instances && n.contentWindow.H5P.instances.length) {
        var ins2 = n.contentWindow.H5P.instances[0];
        return JSON.stringify({ready:true, lib: ins2.libraryInfo.machineName, mode:'h5pactivity'});
      }
    }
    return JSON.stringify({ready:false, why:'no_instance'});
  } catch(e) { return JSON.stringify({ready:false, why:'exc:' + e.message}); }
})()
"""


def make_ready(aid: int) -> str:
    return write_temp_js(f"ready_{aid}.js", READY_TEMPLATE % aid)


def wait_ready(safari: Safari, aid: int, timeout: int = 45) -> dict:
    p = make_ready(aid)
    seen = None
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            d = safari.render(p)
        except Exception:
            d = None
        seen = d
        if isinstance(d, dict) and d.get("ready"):
            return d
        time.sleep(1.2)
    raise RuntimeError(f"page {aid} not ready: {seen!r}")


def results_init(path: str) -> dict:
    if path and os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    return {"items": {}, "updated": ""}


def save_results(path: str, data: dict) -> None:
    data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def _json(raw: str) -> dict:
    try:
        d = json.loads(raw)
        return d if isinstance(d, dict) else {"raw": raw}
    except Exception:
        return {"raw": raw}


def solve_dragtext(s: Safari) -> dict:
    return _json(s.js_file(js("h5p/solve_drag.js")))


def solve_blanks(s: Safari) -> dict:
    return _json(s.js_file(js("h5p/solve_blanks.js")))


def solve_ftw(s: Safari) -> dict:
    return _json(s.js_file(js("h5p/solve_ftw.js")))


def solve_sortpara(s: Safari, max_steps: int = 40) -> dict:
    last = {}
    for _ in range(max_steps):
        last = _json(s.js_file(js("h5p/sp_step.js")))
        if last.get("status") in ("SORTED_AND_CHECKED", "ERROR", "NOMATCH", "NO_PARAMS"):
            return last
        time.sleep(1.0)
    return {"status": "TIMEOUT", "last": last}


def solve_questionset(s: Safari, max_steps: int = 140) -> dict:
    s.js_file(js("h5p/qs_reset.js"))
    time.sleep(1.5)
    plan = _json(s.js_file(js("h5p/qs_plan.js")))
    if plan.get("error"):
        return {"status": "PLAN_FAIL", "plan": plan}
    last = {}
    for _ in range(max_steps):
        last = _json(s.js_file(js("h5p/qs_step4.js")))
        st = last.get("status")
        if st == "FINISHED":
            break
        if st == "CLICKED_FINISH":
            time.sleep(1.6)
            break
        if st in ("ERROR", "NO_PLAN", "NO_ENTRY", "OPT_NOT_FOUND", "NO_VISIBLE", "UNHANDLED"):
            return {"status": "STEP_FAIL", "last": last, "plan_types": plan.get("types")}
        if st == "SHOW_BUTTONS":
            time.sleep(0.6)
            continue
        time.sleep(0.7)
    final = _json(s.js_file(js("h5p/qs_final.js")))
    final.setdefault("status", "DONE")
    final["plan"] = plan
    return final


def solve_flashcards(s: Safari) -> dict:
    res = _json(s.js_file(js("h5p/fc_solve.js")))
    time.sleep(1.2)
    s.js_file(js("h5p/fc_post.js"))
    time.sleep(2.0)
    post = _json(s.js_file(js("h5p/read_post.js")))
    res["post"] = post
    return res


def solve_interactive_book(s: Safari, max_steps: int = 70) -> dict:
    last = {}
    finished = False
    for _ in range(max_steps):
        last = _json(s.js_file(js("h5p/ib_step2.js")))
        st = last.get("status")
        if st in ("AT_LAST_PAGE", "CLICKED_FINISH"):
            finished = True
            break
        if st in ("UNKNOWN", "ERROR", "NO_IFRAME", "NO_INSTANCE", "NO_PLAYER_IFRAME", "NO_NESTED_IFRAME"):
            return {"status": "STEP_FAIL", "last": last}
        time.sleep(1.2)
    final = _json(s.js_file(js("h5p/ib_final.js")))
    if not final.get("completed"):
        # single-chapter books never advance past page 1, so mark the chapter read
        marked = _json(s.js_file(js("h5p/ib_mark_read.js")))
        final["marked_read"] = marked
    # a reading-only book has no score of its own; make the gradebook record it
    final["finish"] = _json(s.js_file(js("h5p/finish_ib.js")))
    final["finished"] = finished
    final.setdefault("status", "DONE")
    return final


def solve_h5pactivity(s: Safari, max_steps: int = 90) -> dict:
    last = {}
    for _ in range(max_steps):
        last = _json(s.js_file(js("h5p/h5pa_step2.js")))
        st = last.get("status")
        if st in ("END_OR_UNKNOWN", "CLICKED_SUBMIT"):
            break
        if st in ("ERROR", "NO_PLAYER_IFRAME", "NO_NESTED_IFRAME", "NO_INSTANCE"):
            return {"status": "STEP_FAIL", "last": last}
        time.sleep(1.4)
    final = _json(s.js_file(js("h5p/h5pa_final.js")))
    final.setdefault("status", "DONE")
    final["last_step"] = last.get("status")
    return final


def dispatch(safari: Safari, lib: str, mode: str) -> dict:
    if mode == "h5pactivity":
        return solve_h5pactivity(safari)
    if lib == "H5P.DragText":
        return solve_dragtext(safari)
    if lib == "H5P.Blanks":
        return solve_blanks(safari)
    if lib == "H5P.FindTheWords":
        return solve_ftw(safari)
    if lib == "H5P.SortParagraphs":
        return solve_sortpara(safari)
    if lib == "H5P.QuestionSet":
        return solve_questionset(safari)
    if lib == "H5P.Flashcards":
        return solve_flashcards(safari)
    if lib == "H5P.InteractiveBook":
        return solve_interactive_book(safari)
    return {"status": "UNSUPPORTED", "lib": lib}


def score_ok(d: dict) -> bool:
    if d.get("status") in ("UNSUPPORTED", "STEP_FAIL", "PLAN_FAIL", "TIMEOUT"):
        return False
    if d.get("error"):
        return False
    s, mx = d.get("score"), d.get("max")
    if isinstance(s, (int, float)) and isinstance(mx, (int, float)):
        return mx == 0 or s >= mx
    return bool(d.get("post", {}).get("post", "").startswith("OK") if isinstance(d.get("post"), dict) else False) or d.get("status") in ("DONE", "FINISHED") or d.get("completed") is not None


def collect_ids(args) -> list[tuple[int, str]]:
    """Return [(activity_id, kind)] where kind is 'hvp' or 'h5pactivity'."""
    out: list[tuple[int, str]] = []
    if args.ids:
        for x in args.ids.split(","):
            x = x.strip()
            if x:
                out.append((int(x), "hvp"))
    if args.from_scan:
        inv = json.load(open(args.from_scan, encoding="utf-8"))
        want = set(t.strip() for t in args.types.split(",")) if args.types else None
        for it in inv.get("items", []):
            kind = "hvp" if it.get("mod") == "hvp" else "h5pactivity" if it.get("mod") == "h5pactivity" else None
            if not kind:
                continue
            if want and it.get("mod") not in want:
                continue
            out.append((int(it["id"]), kind))
    # de-duplicate while keeping order
    seen = set()
    uniq = []
    for aid, kind in out:
        if aid in seen:
            continue
        seen.add(aid)
        uniq.append((aid, kind))
    return uniq[: args.limit] if args.limit else uniq


def main() -> int:
    ap = argparse.ArgumentParser(description="Complete H5P exercises on CloudCampus")
    ap.add_argument("--course-id", type=int, required=True, help="Moodle course id (id= in course URLs)")
    ap.add_argument("--ids", help="comma separated mod_hvp activity ids")
    ap.add_argument("--from-scan", help="inventory.json produced by scan_course.py")
    ap.add_argument("--types", help="filter --from-scan by mod type: hvp,h5pactivity")
    ap.add_argument("--tab", type=int, default=0)
    add_browser_args(ap)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--out", default="h5p_results.json")
    args = ap.parse_args()

    targets = collect_ids(args)
    if not targets:
        print("nothing to do: pass --ids or --from-scan")
        return 2

    safari = make_browser(args)
    if not args.tab:
        safari.ensure_window(BASE_URL)
        safari.tab = safari.list_tabs()[0].index
    else:
        safari.tab = args.tab
    moodle = Moodle(safari, args.course_id)

    results = results_init(args.out)
    print(f"targets: {len(targets)}  tab={safari.tab}  dry_run={args.dry_run}", flush=True)

    for n, (aid, kind) in enumerate(targets, 1):
        url = (f"{BASE_URL}/mod/hvp/view.php?id={aid}" if kind == "hvp"
               else f"{BASE_URL}/mod/h5pactivity/view.php?id={aid}")
        print(f"[{n}/{len(targets)}] {aid} ({kind}) ...", flush=True)
        try:
            safari.navigate(url, timeout=60)
            ready = wait_ready(safari, aid, timeout=45)
            lib = ready.get("lib", "")
            mode = ready.get("mode", "hvp")
            print(f"   ready lib={lib} mode={mode}", flush=True)
            if args.dry_run:
                results["items"][str(aid)] = {"status": "DRY", "lib": lib, "mode": mode}
                save_results(args.out, results)
                continue
            res = dispatch(safari, lib, mode)
            res["lib"] = lib
            res["mode"] = mode
            ok = score_ok(res)
            res["status_ok"] = ok
            results["items"][str(aid)] = res
            print(f"   done status={res.get('status')} score={res.get('score')}/{res.get('max')} ok={ok}", flush=True)
        except Exception as exc:
            results["items"][str(aid)] = {"status": "EXCEPTION", "error": str(exc), "mode": kind}
            print(f"   FAILED: {exc}", flush=True)
        save_results(args.out, results)
        time.sleep(0.6)

    if not args.skip_verify:
        print("verifying grades ...", flush=True)
        try:
            rows = moodle.open_grade_report()
            by_id = {str(r["id"]): r for r in rows}
            for aid, kind in targets:
                r = by_id.get(str(aid))
                rec = results["items"].setdefault(str(aid), {})
                if not r:
                    rec["grade"] = "NOT_IN_GRADEBOOK"
                    continue
                rec["grade"] = r.get("grade")
                rec["pct"] = r.get("pct")
                rec["name"] = r.get("name")
                lib = rec.get("lib", "")
                g = r.get("grade", "")
                expected_ungraded = lib.endswith("InteractiveBook") and g in ("-", "")
                rec["grade_ok"] = expected_ungraded or (g not in ("-", "") and float(g or 0) > 0)
            print("grade report refreshed", flush=True)
        except Exception as exc:
            print(f"grade verification failed: {exc}", flush=True)
        # books with no interactive content stay "ungraded" until H5P.setFinished is sent
        repairs = 0
        for aid, kind in targets:
            rec = results["items"].get(str(aid), {})
            if not rec.get("lib", "").endswith("InteractiveBook"):
                continue
            if rec.get("grade") not in ("-", "", None) or rec.get("grade_ok"):
                continue
            print(f"   repairing ungraded InteractiveBook {aid} ...", flush=True)
            try:
                safari.navigate(f"{BASE_URL}/mod/hvp/view.php?id={aid}", timeout=60)
                wait_ready(safari, aid, timeout=45)
                rec["finish_retry"] = _json(safari.js_file(js("h5p/finish_ib.js")))
                repairs += 1
                time.sleep(1.5)
            except Exception as exc:
                rec["finish_retry_error"] = str(exc)
        if repairs:
            time.sleep(2)
            try:
                rows = moodle.open_grade_report()
                by_id = {str(r["id"]): r for r in rows}
                for aid, kind in targets:
                    rec = results["items"].get(str(aid), {})
                    if not rec.get("lib", "").endswith("InteractiveBook"):
                        continue
                    r = by_id.get(str(aid))
                    if r:
                        rec["grade"] = r.get("grade")
                        rec["pct"] = r.get("pct")
                        rec["grade_ok"] = r.get("grade") not in ("-", "") and float(r.get("grade") or 0) > 0
            except Exception as exc:
                print(f"repair verification failed: {exc}", flush=True)
        save_results(args.out, results)

    if args.dry_run:
        print(f"\ndry-run finished for {len(results['items'])} items; nothing was submitted")
        print(f"results: {args.out}")
        return 0
    ok_count = sum(1 for v in results["items"].values() if v.get("grade_ok") or v.get("status_ok"))
    print(f"\nfinished {len(results['items'])} items, ok-ish: {ok_count}")
    print(f"results: {args.out}")
    return 0 if ok_count >= len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())
