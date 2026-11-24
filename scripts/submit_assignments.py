#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""submit_assignments.py - submit CloudCampus/Moodle assignments from a manifest.

Two submission modes:
  online : paste prepared text into the Moodle online-text editor (Atto)
  file   : upload one local file through the file manager (DataTransfer injection;
           the OS file dialog is not used because Safari's panel is out-of-process)

Manifest JSON:
{
  "course_id": 12345,
  "items": [
    {"id": 666033, "mode": "online", "text_path": "content/666033.md"},
    {"id": 668591, "mode": "file",   "file_path": "artifacts/668591.docx"}
  ]
}

The script never trims text silently. If Moodle rejects a submission for a word
limit it stores the limit and the attempted count (status WORD_LIMIT) so the
operator can shorten the text and rerun with the same manifest.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cloudcampus import Safari, Moodle, BASE_URL, add_browser_args, make_browser, js, write_temp_js

MIME = {
    ".m4a": "audio/mp4", ".mp3": "audio/mpeg", ".wav": "audio/wav",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword", ".pdf": "application/pdf",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain", ".md": "text/plain",
}


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read().strip()


def inject_file(safari: Safari, path: str) -> str:
    fname = os.path.basename(path)
    mime = MIME.get(os.path.splitext(fname)[1].lower(), "application/octet-stream")
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    src = """(function(){
  try {
    var b64 = "%s";
    var bin = atob(b64);
    var arr = new Uint8Array(bin.length);
    for (var k = 0; k < bin.length; k++) arr[k] = bin.charCodeAt(k);
    var file = new File([arr], "%s", {type: "%s"});
    var fi = document.querySelector('input[name=repo_upload_file]');
    if (!fi) return 'NO_INPUT';
    var dt = new DataTransfer();
    dt.items.add(file);
    fi.files = dt.files;
    fi.dispatchEvent(new Event('change', {bubbles: true}));
    return 'SET ' + fi.files[0].name + ' ' + fi.files[0].size;
  } catch(e) { return 'EXC ' + e.message; }
})()""" % (b64, fname, mime)
    return safari.js_file(write_temp_js("inject_file.js", src))


def draft_check(safari: Safari, itemid: str, filename: str, timeout: int = 30) -> bool:
    src = """(function(){
  try {
    var itemid = "%s";
    if (!itemid) return;
    var sesskey = (window.M && M.cfg) ? M.cfg.sesskey : '';
    window.__draft = 'PENDING';
    fetch('/repository/draftfiles_ajax.php?action=list&itemid=' + itemid + '&sesskey=' + sesskey + '&filepath=%%2F', {credentials: 'same-origin'})
      .then(function(r){ return r.json(); })
      .then(function(j){ window.__draft = JSON.stringify({files: (j.list || []).map(function(f){ return f.filename + '|' + f.filesize; })}); })
      .catch(function(e){ window.__draft = 'ERR ' + e.message; });
    return;
  } catch(e) { window.__draft = 'ERR ' + e.message; return; }
})()""" % itemid
    p = write_temp_js("draft_check.js", src)
    read = write_temp_js("read_draft.js", "(function(){ return window.__draft || 'none'; })()")
    t0 = time.time()
    while time.time() - t0 < timeout:
        safari.js_file(p)
        time.sleep(1.6)
        raw = safari.js_file(read)
        if filename in raw:
            return True
        print(f"   draft: {raw[:160]}", flush=True)
    return False


def submit_online(moodle: Moodle, text: str) -> dict:
    form = moodle.open_submission_form()
    if not (form.get("online_editor") or form.get("online_textarea")):
        return {"status": "FORM_MISMATCH", "form": form}
    print("   fill:", moodle.fill_online_text(text), flush=True)
    time.sleep(2)
    print("   save:", moodle.save_changes(), flush=True)
    time.sleep(7)
    return settle(moodle)


def submit_file(moodle: Moodle, path: str) -> dict:
    form = moodle.open_submission_form()
    if not form.get("filemanager"):
        return {"status": "FORM_MISMATCH", "form": form}
    s = moodle.s
    print("   picker:", s.js_file(js("assignment/open_picker.js")), flush=True)
    time.sleep(3)
    print("   repo:", s.js_file(js("assignment/pick_repo.js")), flush=True)
    time.sleep(3)
    print("   inject:", inject_file(s, path), flush=True)
    info = s.render(js("assignment/get_itemid.js")) or {}
    itemid = str(info.get("itemid") or "")
    print("   itemid:", info, flush=True)
    print("   upload:", s.js_file(js("assignment/upload.js")), flush=True)
    time.sleep(6)
    ok = draft_check(s, itemid, os.path.basename(path))
    if not ok:
        return {"status": "UPLOAD_UNCONFIRMED", "itemid": itemid}
    print("   close:", s.js_file(js("assignment/close_picker.js")), flush=True)
    time.sleep(2)
    print("   save:", moodle.save_changes(), flush=True)
    time.sleep(8)
    return settle(moodle)


def settle(moodle: Moodle) -> dict:
    """Read the page after clicking save; classify result."""
    try:
        st = moodle.read_submission_status()
    except Exception as exc:
        st = {"error": str(exc), "url": "", "submitted": False, "status": ""}
    if st.get("submitted"):
        st["status_kind"] = "SUBMITTED"
        return st
    if "id=" not in (st.get("url") or ""):
        limit = moodle.word_limit_error()
        if limit:
            st["status_kind"] = "WORD_LIMIT"
            st["limit"], st["attempted"] = limit
            return st
    st["status_kind"] = st.get("status_kind") or "FAILED"
    st["page_snippet"] = moodle.page_text()[:400]
    return st


def main() -> int:
    ap = argparse.ArgumentParser(description="Submit CloudCampus assignments from a manifest")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--tab", type=int, default=0)
    add_browser_args(ap)
    ap.add_argument("--only", help="comma separated assignment ids")
    ap.add_argument("--inspect", action="store_true", help="only inspect the submission form, do not submit")
    ap.add_argument("--out", default="submit_results.json")
    args = ap.parse_args()

    manifest = json.load(open(args.manifest, encoding="utf-8"))
    course_id = int(manifest.get("course_id") or 0)
    items = manifest.get("items") or []
    only = {x.strip() for x in args.only.split(",")} if args.only else None
    if only:
        items = [it for it in items if str(it.get("id")) in only]
    if not items:
        print("manifest has no matching items")
        return 2

    safari = make_browser(args)
    if not args.tab:
        safari.ensure_window(BASE_URL)
        safari.tab = safari.list_tabs()[0].index
    else:
        safari.tab = args.tab
    moodle = Moodle(safari, course_id)

    results = {"items": {}, "updated": ""}
    exit_code = 0
    for n, item in enumerate(items, 1):
        aid = int(item["id"])
        mode = item.get("mode", "online")
        print(f"[{n}/{len(items)}] {aid} mode={mode} ...", flush=True)
        try:
            moodle.open_assignment(aid)
            if args.inspect:
                form = moodle.open_submission_form()
                results["items"][str(aid)] = {"status": "INSPECT", "form": form}
                print("   form:", json.dumps(form, ensure_ascii=False)[:500], flush=True)
                time.sleep(0.5)
                continue
            if mode == "online":
                text = read_text(item["text_path"])
                res = submit_online(moodle, text)
            elif mode == "file":
                res = submit_file(moodle, item["file_path"])
            else:
                raise RuntimeError(f"unknown mode: {mode}")
            results["items"][str(aid)] = res
            print(f"   result: {res.get('status_kind')} limits={res.get('limit')}", flush=True)
            if res.get("status_kind") != "SUBMITTED":
                exit_code = 3 if res.get("status_kind") == "WORD_LIMIT" else 1
        except Exception as exc:
            results["items"][str(aid)] = {"status": "EXCEPTION", "error": str(exc)}
            print(f"   FAILED: {exc}", flush=True)
            exit_code = 1
        results["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=1)
        time.sleep(0.6)

    submitted = sum(1 for v in results["items"].values() if v.get("status_kind") == "SUBMITTED")
    print(f"\nsubmitted {submitted}/{len(items)}; results -> {args.out}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
