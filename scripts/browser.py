#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""browser.py - one interface, several browser backends.

Backends
--------
safari
    AppleScript `do JavaScript` (Safari, needs "Allow JavaScript from Apple Events").
chromium-applescript
    AppleScript `execute ... javascript` for Chrome / Edge / Brave / Arc / Opera /
    Vivaldi / Chromium. Same setting: View > Developer > Allow JavaScript from Apple Events.
cdp
    Chrome DevTools Protocol over HTTP + WebSocket. Works for any Chromium browser
    started with --remote-debugging-port=<port> (the skill ships
    launch_edge_cdp.sh; the profile keeps the CloudCampus login between runs).
webdriver
    Plain W3C WebDriver (geckodriver / chromedriver / msedgedriver / safaridriver).
    This is the path for Firefox and for cross-platform use.

All backends expose the same small driver API, so the rest of the skill does not
care which browser is behind it.  Errors are RuntimeError/BrowserSetupError with
a message that tells the user what to switch on.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

BASE_URL = "https://www.cloudcampus.com.cn"
TMP = os.path.join(tempfile.gettempdir(), "solution-to-cloudcampus")
os.makedirs(TMP, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))

CHROMIUM_APPS = {
    "edge": "Microsoft Edge",
    "chrome": "Google Chrome",
    "brave": "Brave Browser",
    "arc": "Arc",
    "opera": "Opera",
    "vivaldi": "Vivaldi",
    "chromium": "Chromium",
}
CHROMIUM_BUNDLES = {
    "edge": "com.microsoft.edgemac",
    "chrome": "com.google.Chrome",
    "brave": "com.brave.Browser",
    "arc": "company.thebrowser.Browser",
    "opera": "com.operasoftware.Opera",
    "vivaldi": "com.vivaldi.Vivaldi",
    "chromium": "org.chromium.Chromium",
}
# detection order: Edge first (the skill's primary target), then other Chromium browsers
CHROMIUM_PRIORITY = ["edge", "chrome", "brave", "arc", "opera", "vivaldi", "chromium"]

JS_SETTING_HINT = (
    "在 Edge 菜单栏打开：View > Developer > Allow JavaScript from Apple Events\n"
    "（中文界面：檢視/显示方式 > 開發人員 > 允許來自 Apple 事件的 JavaScript）。\n"
    "Windows 或不想改这个设置时，改用 CDP/WebDriver 模式：\n"
    "  macOS：bash scripts/launch_edge_cdp.sh（独立 profile 启动 Edge 并开好调试端口，登录一次即可保留会话）\n"
    "  Windows：msedge.exe --remote-debugging-port=9222 --user-data-dir=%USERPROFILE%\\.dsh\\edge-cdp\n"
    "  或启动 msedgedriver --port 9515 后用 --browser webdriver"
)


class BrowserSetupError(RuntimeError):
    """The browser is there but its automation bridge is not enabled."""


@dataclass
class Tab:
    index: int
    url: str = ""
    title: str = ""
    window: int = 1
    handle: str = ""


# ---------------------------------------------------------------------------
# AppleScript helpers
# ---------------------------------------------------------------------------

def _osa(script: str, timeout: int = 120) -> str:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if r.returncode != 0:
        raise RuntimeError(f"osascript failed: {err or out}")
    return out


def _as_quote(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _applescript(run: str) -> str:
    """True when `osascript` can execute the given script (used for capability probes)."""
    try:
        return _osa(run, timeout=20)
    except Exception:
        return ""


class BaseDriver:
    name = "base"
    supports_js = True
    app = ""            # app name for AppleScript based drivers
    bundle_id = ""

    def list_tabs(self) -> list[Tab]:
        raise NotImplementedError

    def window_count(self) -> int:
        raise NotImplementedError

    def ensure_window(self, url: str = BASE_URL) -> None:
        raise NotImplementedError

    def navigate(self, tab: int, url: str) -> None:
        raise NotImplementedError

    def js(self, tab: int, code: str) -> str:
        raise NotImplementedError

    def current_url(self, tab: int) -> str:
        for t in self.list_tabs():
            if t.index == tab:
                return t.url
        return ""

    def close_window(self) -> None:
        raise NotImplementedError

    def screenshot(self, path: str) -> str:
        r = subprocess.run(["screencapture", "-x", path], capture_output=True)
        if r.returncode != 0 or not os.path.exists(path):
            raise RuntimeError("screencapture failed (screen recording permission?)")
        return path

    def close_tab(self, tab: int) -> None:  # pragma: no cover - optional per driver
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Safari
# ---------------------------------------------------------------------------

class SafariDriver(BaseDriver):
    name = "safari"
    app = "Safari"
    bundle_id = "com.apple.Safari"

    def list_tabs(self) -> list[Tab]:
        out = _applescript(
            'tell application "Safari"\n'
            '  set res to ""\n'
            '  set ti to 0\n'
            '  repeat with t in tabs of front window\n'
            '    set ti to ti + 1\n'
            '    set res to res & ti & "\\t" & (URL of t) & "\\t" & (name of t) & "\\n"\n'
            '  end repeat\n'
            '  return res\n'
            'end tell'
        )
        tabs: list[Tab] = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    idx = int(parts[0])
                except ValueError:
                    continue
                tabs.append(Tab(idx, parts[1], parts[2] if len(parts) > 2 else ""))
        return tabs

    def window_count(self) -> int:
        return int(_applescript('tell application "Safari" to get count of windows') or 0)

    def ensure_window(self, url: str = BASE_URL) -> None:
        if self.window_count() == 0:
            _osa(
                'tell application "Safari"\n'
                '  activate\n'
                f'  make new document with properties {{URL:"{_as_quote(url)}"}}\n'
                'end tell'
            )
            time.sleep(1.0)

    def navigate(self, tab: int, url: str) -> None:
        _osa(
            'tell application "Safari"\n'
            '  activate\n'
            '  tell front window\n'
            f'    set current tab to tab {tab}\n'
            f'    set URL of current tab to "{_as_quote(url)}"\n'
            '  end tell\n'
            'end tell'
        )

    def js(self, tab: int, code: str) -> str:
        path = os.path.join(TMP, "_last.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        script = (
            f'set jsCode to (read POSIX file "{path}" as «class utf8»)\n'
            'tell application "Safari"\n'
            '  tell front window\n'
            f'    set current tab to tab {tab}\n'
            '    set r to do JavaScript jsCode in current tab\n'
            '  end tell\n'
            'end tell\n'
            'return r'
        )
        return _osa(script)

    def close_window(self) -> None:
        try:
            _osa('tell application "Safari" to close front window')
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Chromium family via AppleScript
# ---------------------------------------------------------------------------

class ChromiumAppleScriptDriver(BaseDriver):
    """Chrome / Edge / Brave / Arc / Opera / Vivaldi via the standard Chromium AppleScript API."""

    def __init__(self, app_key: str = "chrome"):
        self.app = CHROMIUM_APPS.get(app_key, app_key)
        self.bundle_id = CHROMIUM_BUNDLES.get(app_key, "")
        self.name = app_key
        self._map: dict[int, tuple[int, int]] = {}

    def _run(self, body: str) -> str:
        return _applescript(f'tell application "{self.app}"\n{body}\nend tell')

    def list_tabs(self) -> list[Tab]:
        out = self._run(
            'set res to ""\n'
            'set wi to 0\n'
            'set gi to 0\n'
            'repeat with w in windows\n'
            '  set wi to wi + 1\n'
            '  set ti to 0\n'
            '  repeat with t in tabs of w\n'
            '    set ti to ti + 1\n'
            '    set gi to gi + 1\n'
            '    set res to res & wi & "\\t" & ti & "\\t" & (URL of t) & "\\t" & (title of t) & "\\n"\n'
            '  end repeat\n'
            'end repeat\n'
            'return res'
        )
        tabs: list[Tab] = []
        self._map = {}
        idx = 0
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            try:
                wi, ti = int(parts[0]), int(parts[1])
            except ValueError:
                continue
            idx += 1
            self._map[idx] = (wi, ti)
            tabs.append(Tab(idx, parts[2], parts[3] if len(parts) > 3 else "", window=wi))
        return tabs

    def window_count(self) -> int:
        return int(self._run('count of windows') or 0)

    def ensure_window(self, url: str = BASE_URL) -> None:
        if self.window_count() == 0:
            _osa(
                f'tell application "{self.app}"\n'
                'activate\n'
                'make new window\n'
                f'set URL of active tab of front window to "{_as_quote(url)}"\n'
                'end tell'
            )
            time.sleep(1.2)

    def _locate(self, tab: int) -> tuple[int, int]:
        if tab not in self._map:
            self.list_tabs()
        return self._map.get(tab, (1, 1))

    def navigate(self, tab: int, url: str) -> None:
        wi, ti = self._locate(tab)
        _osa(
            f'tell application "{self.app}"\n'
            'activate\n'
            f'tell window {wi}\n'
            f'  set active tab index to {ti}\n'
            f'  set URL of tab {ti} to "{_as_quote(url)}"\n'
            'end tell\n'
            'end tell'
        )

    def js(self, tab: int, code: str) -> str:
        wi, ti = self._locate(tab)
        path = os.path.join(TMP, "_last.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        script = (
            f'set jsCode to (read POSIX file "{path}" as «class utf8»)\n'
            f'tell application "{self.app}"\n'
            f'  tell window {wi}\n'
            f'    set r to execute tab {ti} javascript jsCode\n'
            '  end tell\n'
            'end tell\n'
            'return r'
        )
        try:
            return _osa(script)
        except RuntimeError as exc:
            msg = str(exc)
            if "JavaScript" in msg or "12" in msg:
                raise BrowserSetupError(f"{self.app} 的 AppleScript JavaScript 还没打开。\n{JS_SETTING_HINT}") from exc
            raise

    def close_window(self) -> None:
        try:
            self._run('close front window')
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CDP (Chromium with --remote-debugging-port)
# ---------------------------------------------------------------------------

def _node_binary() -> Optional[str]:
    for cand in (
        os.environ.get("SKILL_NODE"),
        shutil.which("node"),
        os.path.expanduser("~/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/node/bin/node"),
    ):
        if cand and os.path.exists(cand):
            return cand
    return None


class CDPDriver(BaseDriver):
    """Chrome DevTools Protocol for Chromium browsers (Edge first); use scripts/launch_edge_cdp.sh."""

    name = "cdp"
    supports_js = True

    def __init__(self, port: int = 9222):
        self.port = port
        self._bridge = os.path.join(HERE, "cdp_bridge.mjs")
        self._node = _node_binary()

    # -- HTTP helpers ---------------------------------------------------
    def _get(self, path: str) -> Any:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=4) as r:
            return json.loads(r.read().decode("utf-8"))

    def probe(self) -> Optional[dict]:
        try:
            return self._get("/json/version")
        except Exception:
            return None

    def list_tabs(self) -> list[Tab]:
        try:
            data = self._get("/json/list")
        except Exception as exc:
            raise BrowserSetupError(
                f"CDP 端口 {self.port} 连不上。先运行：bash scripts/launch_edge_cdp.sh"
                "（macOS Edge/Chromium 系），Windows 见 references/01。也可用 --browser safari。"
            ) from exc
        tabs = []
        idx = 0
        for t in data:
            if t.get("type") != "page":
                continue
            idx += 1
            tabs.append(Tab(idx, t.get("url", ""), t.get("title", ""), handle=t.get("id", "")))
        return tabs

    def _tab_handle(self, tab: int) -> str:
        tabs = self.list_tabs()
        for t in tabs:
            if t.index == tab:
                return t.handle
        raise RuntimeError(f"CDP 浏览器里没有第 {tab} 个标签页")

    def window_count(self) -> int:
        try:
            return len(self.list_tabs())
        except Exception:
            return 0

    def ensure_window(self, url: str = BASE_URL) -> None:
        if self.window_count() == 0:
            self._bridge_call("newtab", url=url)
            time.sleep(1.0)

    def navigate(self, tab: int, url: str) -> None:
        handle = self._tab_handle(tab)
        self._bridge_call("navigate", target=handle, url=url)

    def js(self, tab: int, code: str) -> str:
        handle = self._tab_handle(tab)
        path = os.path.join(TMP, "_last.js")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        return self._bridge_call("eval", target=handle, expr_file=path)

    def close_window(self) -> None:
        try:
            for t in self.list_tabs():
                self._bridge_call("closetab", target=t.handle)
        except Exception:
            pass

    def screenshot(self, path: str) -> str:
        tabs = self.list_tabs()
        if not tabs:
            raise RuntimeError("CDP: no page targets to screenshot")
        self._bridge_call("screenshot", target=tabs[0].handle, out=path)
        return path

    # -- bridge ---------------------------------------------------------
    def _bridge_call(self, cmd: str, **kw: Any) -> Any:
        if not self._node:
            raise BrowserSetupError("CDP 需要 Node.js（DSH 一般自带）；也可以改用 --browser safari")
        args = [self._node, self._bridge, "--port", str(self.port), cmd]
        for key, val in kw.items():
            flag = "--" + key.replace("_", "-")
            args += [flag, str(val)]
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        out = (r.stdout or "").strip().splitlines()
        payload = ""
        for line in reversed(out):
            if line.strip().startswith("{"):
                payload = line.strip()
                break
        if not payload:
            raise RuntimeError(f"cdp_bridge 没有输出: {r.stderr[-500:]}")
        data = json.loads(payload)
        if not data.get("ok"):
            raise RuntimeError(f"CDP {cmd} failed: {data.get('error')}")
        return data.get("value", "")


# ---------------------------------------------------------------------------
# WebDriver (W3C) - Firefox via geckodriver, Chrome via chromedriver, Edge, Safari
# ---------------------------------------------------------------------------

class WebDriverDriver(BaseDriver):
    name = "webdriver"
    supports_js = True

    def __init__(self, url: str = "http://127.0.0.1:4444", capabilities: Optional[dict] = None):
        self.base = url.rstrip("/")
        self.session: Optional[str] = None
        self.capabilities = capabilities or {}

    def _req(self, method: str, path: str, payload: Optional[dict] = None) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.loads(r.read().decode("utf-8"))
        if body.get("value", {}).get("error"):
            raise RuntimeError(f"WebDriver error: {body['value']}")
        return body.get("value")

    def _ensure(self) -> str:
        if not self.session:
            try:
                caps = {"capabilities": {"alwaysMatch": self.capabilities or {}}}
                val = self._req("POST", "/session", caps)
                self.session = val.get("sessionId") or ""
            except Exception as exc:
                raise BrowserSetupError(
                    f"WebDriver 端口 {self.base} 连不上或没有启动 driver。\n"
                    "Firefox：brew install geckodriver && geckodriver --port 4444（然后打开 Firefox 登录 CloudCampus）\n"
                    "Chrome：chromedriver --port 9515（或直接用 launch_edge_cdp.sh）\n"
                    "Edge：msedgedriver --port 9515"
                ) from exc
        if not self.session:
            raise BrowserSetupError("WebDriver 没有创建 session")
        return self.session

    def _path(self, tail: str = "") -> str:
        return f"/session/{self._ensure()}{tail}"

    def _switch(self, handle: str) -> None:
        self._req("POST", self._path("/window"), {"handle": handle})

    def list_tabs(self) -> list[Tab]:
        handles = self._req("GET", self._path("/window/handles")) or []
        tabs = []
        for i, h in enumerate(handles, 1):
            url = title = ""
            try:
                self._switch(h)
                url = self._req("GET", self._path("/url")) or ""
                title = self._req("GET", self._path("/title")) or ""
            except Exception:
                pass
            tabs.append(Tab(i, url, title, handle=h))
        return tabs

    def window_count(self) -> int:
        try:
            return len(self._req("GET", self._path("/window/handles")) or [])
        except Exception:
            return 0

    def ensure_window(self, url: str = BASE_URL) -> None:
        if self.window_count() == 0:
            self._req("POST", self._path("/window/new"), {"type": "tab"})
            self.navigate(1, url)

    def _handle(self, tab: int) -> str:
        tabs = self.list_tabs()
        for t in tabs:
            if t.index == tab:
                return t.handle
        raise RuntimeError(f"WebDriver: 没有第 {tab} 个窗口")

    def navigate(self, tab: int, url: str) -> None:
        self._switch(self._handle(tab))
        self._req("POST", self._path("/url"), {"url": url})

    def js(self, tab: int, code: str) -> str:
        self._switch(self._handle(tab))
        wrapper = (
            "var __r = (function(){\n" + code + "\n})();\n"
            "return (typeof __r === 'string') ? __r : JSON.stringify(__r);"
        )
        return self._req("POST", self._path("/execute/sync"), {"script": wrapper, "args": []}) or ""

    def close_window(self) -> None:
        try:
            self._req("DELETE", self._path("/window"))
        except Exception:
            pass

    def screenshot(self, path: str) -> str:
        b64 = self._req("GET", self._path("/screenshot"))
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(b64))
        return path


# ---------------------------------------------------------------------------
# Factory / auto detection
# ---------------------------------------------------------------------------

def running_apps() -> list[str]:
    try:
        out = _osa(
            'tell application "System Events" to get name of every process whose background only is false'
        )
        return [x.strip() for x in out.split(",") if x.strip()]
    except Exception:
        return []


def installed_bundle_ids() -> dict[str, bool]:
    result = {}
    for key, bundle in CHROMIUM_BUNDLES.items():
        result[key] = os.path.exists(f"/Applications/{CHROMIUM_APPS[key]}.app")
    return result


def safari_js_works() -> bool:
    try:
        out = _osa('tell application "Safari" to do JavaScript "1+1" in current tab of front window')
        return out.strip().startswith("2")
    except Exception:
        return False


def chromium_js_works(app_key: str = "chrome") -> bool:
    app = CHROMIUM_APPS.get(app_key, app_key)
    try:
        out = _osa(f'tell application "{app}" to execute tab 1 of window 1 javascript "1+1"', timeout=20)
        return out.strip().startswith("2")
    except Exception:
        return False


def cdp_alive(port: int = 9222) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def webdriver_alive(url: str = "http://127.0.0.1:4444") -> bool:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/status", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def safari_tab_urls() -> list[str]:
    try:
        out = _osa(
            'tell application "Safari"\n'
            '  set res to ""\n'
            '  repeat with t in tabs of front window\n'
            '    set res to res & (URL of t) & "\\n"\n'
            '  end repeat\n'
            '  return res\n'
            'end tell'
        )
        return [x for x in out.splitlines() if x.strip()]
    except Exception:
        return []


def chromium_tab_urls(app_key: str) -> list[str]:
    app = CHROMIUM_APPS.get(app_key, app_key)
    try:
        out = _osa(
            f'tell application "{app}"\n'
            '  set res to ""\n'
            '  repeat with w in windows\n'
            '    repeat with t in tabs of w\n'
            '      set res to res & (URL of t) & "\\n"\n'
            '    end repeat\n'
            '  end repeat\n'
            '  return res\n'
            'end tell'
        )
        return [x for x in out.splitlines() if x.strip()]
    except Exception:
        return []


def cdp_tab_urls(port: int = 9222) -> list[str]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [t.get("url", "") for t in data if t.get("type") == "page"]
    except Exception:
        return []


def _has_site(urls: list[str], needle: str = "cloudcampus") -> bool:
    return any(needle in (u or "") for u in urls)


def open_driver(preference: Optional[str] = None, cdp_port: int = 9222,
                webdriver_url: str = "http://127.0.0.1:4444") -> BaseDriver:
    """Return a driver. preference: auto|safari|<chromium key>|cdp|webdriver|chrome-cdp|<key>-cdp."""
    pref = (preference or os.environ.get("SKILL_BROWSER") or "auto").strip().lower()

    if pref.endswith("-cdp"):
        pref = pref[: -len("-cdp")]
        if pref in CHROMIUM_APPS or pref == "cdp":
            return CDPDriver(cdp_port)

    if pref == "auto":
        apps = running_apps()
        # 1) prefer a browser that already has CloudCampus open (login lives there)
        if "Safari" in apps and _has_site(safari_tab_urls()) and safari_js_works():
            return SafariDriver()
        if cdp_alive(cdp_port) and _has_site(cdp_tab_urls(cdp_port)):
            return CDPDriver(cdp_port)
        for key in CHROMIUM_PRIORITY:
            if CHROMIUM_APPS[key] in apps and _has_site(chromium_tab_urls(key)) and chromium_js_works(key):
                return ChromiumAppleScriptDriver(key)
        # 2) any browser whose JS bridge works
        if "Safari" in apps and safari_js_works():
            return SafariDriver()
        if cdp_alive(cdp_port):
            return CDPDriver(cdp_port)
        for key in CHROMIUM_PRIORITY:
            if CHROMIUM_APPS[key] in apps and chromium_js_works(key):
                return ChromiumAppleScriptDriver(key)
        if webdriver_alive(webdriver_url):
            return WebDriverDriver(webdriver_url)
        # 3) nothing ready: return Safari so the caller gets a clear setup message
        return SafariDriver()

    if pref == "safari":
        driver = SafariDriver()
        if not safari_js_works():
            raise BrowserSetupError(
                "Safari 的「允许从 Apple 事件执行 JavaScript」没打开：\n"
                "Safari > 设置 > 高级 > 勾选 Allow JavaScript from Apple Events。"
            )
        return driver
    if pref == "cdp":
        return CDPDriver(cdp_port)
    if pref == "webdriver":
        return WebDriverDriver(webdriver_url)
    if pref in CHROMIUM_APPS:
        app_name = CHROMIUM_APPS[pref]
        if app_name not in running_apps():
            raise BrowserSetupError(
                f"{app_name} 没有在运行或没有安装。\n"
                f"装好并登录 CloudCampus 后再试；或直接用 Safari（--browser safari）或用 CDP 模式。"
            )
        driver = ChromiumAppleScriptDriver(pref)
        if not chromium_js_works(pref):
            raise BrowserSetupError(
                f"{app_name} 的 AppleScript JavaScript 还没打开。\n{JS_SETTING_HINT}"
            )
        return driver
    raise ValueError(f"unknown browser preference: {preference!r}")
