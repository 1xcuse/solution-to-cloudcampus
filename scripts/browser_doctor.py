#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""browser_doctor.py - show which browsers the skill can drive right now.

Checks, in Edge-first order:
  * installed / running browsers
  * whether an AppleScript JS bridge is enabled (Edge/Chrome family, Safari)
  * whether a CDP port is listening (launch_edge_cdp.sh / launch_browser_cdp.sh)
  * whether a W3C WebDriver endpoint is listening (msedgedriver/geckodriver/chromedriver)
  * whether CloudCampus is open in that browser
and prints the one-line fix for anything that is missing.

Exit code 0 when at least one full backend is ready.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import browser


def marker(ok: bool) -> str:
    return "OK " if ok else "-- "


def main() -> int:
    ap = argparse.ArgumentParser(description="Check browser automation readiness")
    ap.add_argument("--cdp-port", type=int, default=9222)
    ap.add_argument("--webdriver-url", default="http://127.0.0.1:4444")
    args = ap.parse_args()

    print("CloudCampus skill - browser doctor")
    print("=" * 60)
    apps = browser.running_apps()
    ready = []

    # --- Edge first ----------------------------------------------------
    print("\n[Chromium browsers] (Edge is the primary target)")
    for key in browser.CHROMIUM_PRIORITY:
        app = browser.CHROMIUM_APPS[key]
        installed = os.path.exists(f"/Applications/{app}.app")
        running = app in apps
        if not installed:
            if key == "edge":
                print(f"  {marker(False)} Edge: 未安装（https://www.microsoft.com/edge/download）")
            continue
        js_ok = browser.chromium_js_works(key) if running else False
        site = browser.chromium_tab_urls(key) if running else []
        print(f"  {marker(js_ok)} {app}: installed=yes running={'yes' if running else 'no'} "
              f"apple_script_js={'on' if js_ok else 'off'} cloudcampus_tabs={sum('cloudcampus' in u for u in site)}")
        if running and js_ok:
            ready.append((key, "applescript"))
        elif running and not js_ok and key == "edge":
            print("       → 打开 Edge 菜单：View > Developer > Allow JavaScript from Apple Events")
            print("         （或改用 CDP 模式：bash scripts/launch_edge_cdp.sh）")

    # --- Safari --------------------------------------------------------
    print("\n[Safari]")
    safari_running = "Safari" in apps
    safari_js = browser.safari_js_works() if safari_running else False
    site = browser.safari_tab_urls() if safari_running else []
    print(f"  {marker(safari_js)} Safari: running={'yes' if safari_running else 'no'} "
          f"apple_script_js={'on' if safari_js else 'off'} cloudcampus_tabs={sum('cloudcampus' in u for u in site)}")
    if safari_js:
        ready.append(("safari", "applescript"))
    if safari_running and not safari_js:
        print("       → Safari > 设置 > 高级 > 勾选 Allow JavaScript from Apple Events")

    # --- CDP -----------------------------------------------------------
    print(f"\n[CDP remote debugging :{args.cdp_port}]")
    cdp_ok = browser.cdp_alive(args.cdp_port)
    browser_label = ""
    if cdp_ok:
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://127.0.0.1:{args.cdp_port}/json/version", timeout=2) as r:
                browser_label = json.loads(r.read().decode()).get("Browser", "")
        except Exception:
            pass
        urls = browser.cdp_tab_urls(args.cdp_port)
        print(f"  {marker(True)} CDP alive: {browser_label or 'chromium'} cloudcampus_tabs={sum('cloudcampus' in u for u in urls)}")
        ready.append(("cdp", "cdp"))
    else:
        print("  --  no CDP port. macOS: bash scripts/launch_edge_cdp.sh")
        print("      Windows: msedge.exe --remote-debugging-port=9222 --user-data-dir=%USERPROFILE%\\.dsh\\edge-cdp")

    # --- WebDriver -----------------------------------------------------
    print(f"\n[WebDriver {args.webdriver_url}] (Firefox/Edge/Chrome; good for Windows/Linux)")
    wd_ok = browser.webdriver_alive(args.webdriver_url)
    print(f"  {marker(wd_ok)} WebDriver endpoint")
    if wd_ok:
        ready.append(("webdriver", "webdriver"))
    else:
        print("      Windows Edge:  msedgedriver.exe --port 9515")
        print("      Firefox:       brew install geckodriver && geckodriver --port 4444")
        print("      之后用 --browser webdriver --webdriver-url http://127.0.0.1:9515")

    # --- summary -------------------------------------------------------
    print("\n" + "=" * 60)
    if ready:
        best = ready[0]
        order = ["edge", "chrome", "brave", "arc", "opera", "vivaldi", "chromium", "safari", "cdp", "webdriver"]
        best = sorted(ready, key=lambda x: order.index(x[0]) if x[0] in order else 99)[0]
        print(f"可用后端：{', '.join(f'{k}({v})' for k, v in ready)}")
        print(f"推荐：--browser {best[0] if best[0] != 'cdp' else 'cdp'}"
              + (f" --cdp-port {args.cdp_port}" if best[0] == 'cdp' else ""))
        return 0
    print("还没有可用的浏览器后端。")
    print("最快路径：装 Edge → 打开 CloudCampus 登录 → bash scripts/launch_edge_cdp.sh → --browser cdp")
    print("或者：Safari 设置里允许 Apple 事件 JS → --browser safari")
    return 1


if __name__ == "__main__":
    sys.exit(main())
