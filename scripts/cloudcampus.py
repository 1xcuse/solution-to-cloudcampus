#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cloudcampus.py - multi-browser + CloudCampus (Moodle 4) bridge.

One place for everything the skill needs from a browser:
  * talk to Safari / Chromium / CDP / WebDriver through browser.py
  * open/navigate/find tabs, wait for pages and H5P readiness
  * read the grade report, course index, assignment pages
  * small helpers for submission status and word limits

Every public function raises RuntimeError with a useful message instead of
returning None, so the CLI layer can show a real diagnosis.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Optional

BASE_URL = "https://www.cloudcampus.com.cn"
TMP = os.path.join(tempfile.gettempdir(), "solution-to-cloudcampus")
os.makedirs(TMP, exist_ok=True)

# ---------------------------------------------------------------------------
# Browser layer (Safari / Chromium / CDP / WebDriver via browser.py)
# ---------------------------------------------------------------------------
from browser import (  # noqa: E402
    BrowserSetupError,
    CDPDriver,
    ChromiumAppleScriptDriver,
    SafariDriver,
    Tab,
    WebDriverDriver,
    open_driver,
)


class Browser:
    """Thin controller over whichever browser backend is configured.

    Keeps the original Safari-oriented API (tab indexes, js_file, render,
    poll_js, ...) so every script in the skill works unchanged on any backend.
    """

    def __init__(self, tab: Optional[int] = None, browser: Optional[str] = None,
                 cdp_port: int = 9222, webdriver_url: str = "http://127.0.0.1:4444"):
        self.tab = tab
        self.driver = open_driver(browser, cdp_port=cdp_port, webdriver_url=webdriver_url)

    @property
    def browser_name(self) -> str:
        return getattr(self.driver, "name", "unknown")

    # -- inspection -----------------------------------------------------
    def list_tabs(self) -> list[Tab]:
        return self.driver.list_tabs()

    def window_count(self) -> int:
        return self.driver.window_count()

    def ensure_window(self, url: str = BASE_URL) -> None:
        self.driver.ensure_window(url)

    def ensure_tab(self, url_hint: Optional[str] = None, create_url: Optional[str] = None) -> int:
        """Return a usable tab index; optionally find a tab whose URL contains url_hint."""
        self.ensure_window()
        tabs = self.list_tabs()
        if url_hint:
            for t in tabs:
                if url_hint in t.url:
                    self.tab = t.index
                    return t.index
        if self.tab and any(t.index == self.tab for t in tabs):
            return self.tab
        self.tab = tabs[0].index if tabs else 1
        return self.tab

    # -- navigation -----------------------------------------------------
    def navigate(self, url: str, tab: Optional[int] = None, timeout: int = 45) -> None:
        idx = tab or self.tab
        if not idx:
            raise RuntimeError("navigate called without a tab (call ensure_tab first)")
        self.driver.navigate(idx, url)
        self.tab = idx
        if not self.wait_url(url, timeout=timeout):
            raise RuntimeError(f"page did not reach {url} within {timeout}s (now: {self.current_url()})")

    def current_url(self) -> str:
        if not self.tab:
            try:
                self.ensure_tab()
            except Exception:
                return ""
        return self.driver.current_url(self.tab)

    def wait_url(self, needle: str, timeout: int = 45) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                here = self.current_url()
            except Exception:
                here = ""
            if here and needle in here:
                for _ in range(20):
                    try:
                        if self.js_inline("document.readyState") == "complete":
                            return True
                    except Exception:
                        pass
                    time.sleep(0.25)
                return True
            time.sleep(0.4)
        return False

    # -- JS execution ---------------------------------------------------
    def js_inline(self, code: str) -> str:
        if not self.tab:
            self.ensure_tab()
        return str(self.driver.js(self.tab, code))

    def js_file(self, path: str) -> str:
        if not self.tab:
            self.ensure_tab()
        with open(path, "r", encoding="utf-8") as fh:
            code = fh.read()
        return str(self.driver.js(self.tab, code))

    def render(self, path: str) -> Optional[Any]:
        """Write JS whose last value is JSON and parse it. Returns None when not JSON."""
        raw = self.js_file(path)
        try:
            return json.loads(raw)
        except Exception:
            return None

    # -- waiting helpers -------------------------------------------------
    def poll_js(self, path: str, predicate, timeout: int = 60, interval: float = 1.2) -> Any:
        t0 = time.time()
        last = None
        while time.time() - t0 < timeout:
            try:
                data = self.render(path)
            except Exception:
                data = None
            last = data
            if data is not None and predicate(data):
                return data
            time.sleep(interval)
        raise RuntimeError(f"timeout after {timeout}s waiting on {os.path.basename(path)}; last={last!r}")

    # -- screenshots ----------------------------------------------------
    def screenshot(self, path: str) -> str:
        return self.driver.screenshot(path)

    def close_window(self) -> None:
        try:
            self.driver.close_window()
        except Exception:
            pass


# historical name used by the CLI scripts
Safari = Browser

BROWSER_CHOICES = [
    "auto", "safari", "chrome", "edge", "brave", "arc", "opera", "vivaldi",
    "chromium", "cdp", "chrome-cdp", "edge-cdp", "webdriver",
]


def add_browser_args(ap) -> None:
    """Add the common browser-selection flags to an argparse parser."""
    ap.add_argument("--browser", default="auto", choices=BROWSER_CHOICES,
                    help="which browser backend to drive (default: auto = the browser that has CloudCampus open)")
    ap.add_argument("--cdp-port", type=int, default=9222,
                    help="remote debugging port for CDP mode (default 9222)")
    ap.add_argument("--webdriver-url", default="http://127.0.0.1:4444",
                    help="W3C WebDriver endpoint (geckodriver/chromedriver)")


def make_browser(args) -> Browser:
    return Browser(
        getattr(args, "tab", None) or None,
        browser=getattr(args, "browser", None) or "auto",
        cdp_port=getattr(args, "cdp_port", 9222),
        webdriver_url=getattr(args, "webdriver_url", "http://127.0.0.1:4444"),
    )


# ---------------------------------------------------------------------------
# JS snippet paths
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
JSDIR = os.path.join(HERE, "js")


def js(name: str) -> str:
    p = os.path.join(JSDIR, name)
    if not os.path.exists(p):
        raise FileNotFoundError(f"missing JS snippet: {name}")
    return p


def write_temp_js(name: str, content: str) -> str:
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(content)
    return p


# ---------------------------------------------------------------------------
# Moodle page readers
# ---------------------------------------------------------------------------

class Moodle:
    def __init__(self, safari: Safari, course_id: int):
        self.s = safari
        self.course_id = int(course_id)

    @property
    def grade_url(self) -> str:
        return f"{BASE_URL}/grade/report/user/index.php?id={self.course_id}"

    def open_grade_report(self) -> list[dict]:
        self.s.navigate(self.grade_url, timeout=60)
        # the table may render a moment after readyState=complete; never accept an empty list
        data = self.s.poll_js(js("scan/grade_rows.js"),
                              lambda d: isinstance(d, dict) and bool(d.get("rows")), timeout=45)
        return data["rows"]

    def parse_grade_rows(self) -> list[dict]:
        data = self.s.render(js("scan/grade_rows.js"))
        if not data or "rows" not in data:
            raise RuntimeError("could not parse grade report rows")
        return data["rows"]

    def open_course(self) -> None:
        self.s.navigate(f"{BASE_URL}/course/view.php?id={self.course_id}", timeout=60)

    def parse_course_index(self) -> dict:
        self.s.navigate(f"{BASE_URL}/course/view.php?id={self.course_id}", timeout=60)
        data = self.s.poll_js(js("scan/course_index.js"),
                              lambda d: isinstance(d, dict) and bool(d.get("sections")), timeout=45)
        return data

    # -- assignment pages -----------------------------------------------
    def assignment_url(self, assign_id: int) -> str:
        return f"{BASE_URL}/mod/assign/view.php?id={assign_id}"

    def open_assignment(self, assign_id: int) -> None:
        self.s.navigate(self.assignment_url(assign_id), timeout=60)

    def read_assignment(self) -> dict:
        data = self.s.render(js("scan/assign_view.js"))
        if not data:
            raise RuntimeError("could not read assignment page")
        return data

    def open_submission_form(self) -> dict:
        """Click Add submission / Edit submission and return form details."""
        clicked = self.s.render(js("assignment/open_form.js"))
        time.sleep(3)
        form = self.s.render(js("assignment/form_info.js"))
        if not isinstance(form, dict):
            raise RuntimeError(f"could not open submission form for assignment (click result: {clicked})")
        form["click"] = clicked
        return form

    # -- submission -----------------------------------------------------
    def fill_online_text(self, text: str) -> str:
        esc = json.dumps(text, ensure_ascii=False)
        src = """(function(){
  try {
    var txt = %s;
    function escHtml(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    var html = txt.split(/\\n\\n+/).map(function(p){ return '<p>' + escHtml(p).replace(/\\n/g,'<br>') + '</p>'; }).join('');
    var ed = document.querySelector('#id_onlinetext_editoreditable');
    if (ed) { ed.focus(); ed.innerHTML = html; ed.dispatchEvent(new Event('input',{bubbles:true})); ed.dispatchEvent(new Event('blur',{bubbles:true})); }
    var ta = document.querySelector('#id_onlinetext_editor') || document.querySelector('textarea[name="onlinetext_editor[text]"]');
    if (ta) { ta.value = txt; ta.dispatchEvent(new Event('input',{bubbles:true})); ta.dispatchEvent(new Event('change',{bubbles:true})); }
    return 'filled ed=' + !!ed + ' ta=' + !!ta + ' len=' + txt.length;
  } catch(e) { return 'EXC ' + e.message; }
})()""" % esc
        return self.s.js_file(write_temp_js("fill_online.js", src))

    def save_changes(self) -> str:
        return self.s.js_file(js("assignment/save.js"))

    def read_submission_status(self) -> dict:
        data = self.s.render(js("assignment/status.js"))
        if not isinstance(data, dict):
            raise RuntimeError("could not read submission status")
        return data

    def page_text(self) -> str:
        raw = self.s.js_inline("(document.querySelector('#region-main')||document.body).innerText")
        return re.sub(r"\s+", " ", raw or "")

    def word_limit_error(self) -> Optional[tuple[int, int]]:
        """After a failed save, Moodle shows: word limit ... N words ... attempting M words."""
        txt = self.page_text()
        m = re.search(r"word limit[^.]*?(\d+)\s*words?[^.]*?(\d+)\s*words?", txt, re.I)
        if m:
            return int(m.group(1)), int(m.group(2))
        return None
