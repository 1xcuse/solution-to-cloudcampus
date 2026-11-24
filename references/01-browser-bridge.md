# 浏览器桥（Edge 优先，Safari / Chromium / Firefox 都可）

这个 skill 不绑定 Safari：所有脚本都通过 `scripts/browser.py` 的后端接口操作浏览器。
`--browser` 参数（或环境变量 `SKILL_BROWSER`）选择后端，默认 `auto`。

## 支持矩阵

| 浏览器 | 方式 | 平台 | 状态 |
|---|---|---|---|
| **Microsoft Edge** | AppleScript `execute javascript`（现有 profile，已登录即可） | macOS | 代码就绪；需在 Edge 里打开菜单开关 |
| **Microsoft Edge** | CDP（`launch_edge_cdp.sh` + 独立 profile） | macOS / Windows | 代码就绪；协议与 Chrome 相同，已用 Chromium 实测 |
| **Microsoft Edge** | W3C WebDriver（`msedgedriver --port 9515`） | Windows / macOS | 代码就绪；Windows 推荐 |
| Safari | AppleScript `do JavaScript` | macOS | ✅ 全流程实测（本机 48 项 H5P + 24 作业） |
| Chrome / Brave / Arc / Opera / Vivaldi / Chromium | AppleScript `execute javascript` | macOS | 代码就绪（与 Edge 同 API） |
| 任意 Chromium | CDP（`--remote-debugging-port`） | macOS / Windows / Linux | ✅ 基础操作实测（导航/执行 JS/截图/开新标签） |
| Firefox | W3C WebDriver（`geckodriver --port 4444`） | macOS / Windows / Linux | 代码就绪（需装 geckodriver） |

`auto` 的挑选顺序：**已打开 CloudCampus 且 JS 桥可用的 Edge → 其他 Chromium → Safari → CDP 端口 → WebDriver 端口**。
在本机测试时哪个浏览器里登录了 CloudCampus，auto 就会选它。

## 方式一：Edge/Chromium 的 AppleScript JS（macOS，用现有登录）

Edge 默认关闭 AppleScript 执行 JS。打开：菜单栏 **View → Developer → Allow JavaScript from Apple Events**
（中文界面：檢視/显示方式 → 開發人員 → 允許來自 Apple 事件的 JavaScript）。

验证：

```bash
osascript -e 'tell application "Microsoft Edge" to execute tab 1 of window 1 javascript "1+1"'
# 输出 2 就算通
```

然后直接用：

```bash
python3 scripts/scan_course.py --course-id 12345 --browser edge
python3 scripts/solve_h5p.py --course-id 12345 --browser edge --from-scan scan/inventory.json
```

Safari 同理，开关在 Safari > 设置 > 高级 > Allow JavaScript from Apple Events。

## 方式二：CDP（macOS / Windows，最稳，不依赖菜单开关）

用独立 profile 启动浏览器并打开调试端口；登录一次 CloudCampus，会话会保存在该 profile 里。

macOS：

```bash
bash scripts/launch_edge_cdp.sh                 # Edge，端口 9222，自动打开 CloudCampus
bash scripts/launch_edge_cdp.sh --port 9333     # 自定义端口
bash scripts/launch_edge_cdp.sh --app chrome --port 9334
```

Windows（PowerShell）：

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
    --remote-debugging-port=9222 `
    --user-data-dir="$env:USERPROFILE\.dsh\edge-cdp" `
    --new-window https://www.cloudcampus.com.cn
```

然后用：

```bash
python3 scripts/solve_h5p.py --course-id 12345 --browser cdp --cdp-port 9222 --from-scan scan/inventory.json
```

原理：`scripts/cdp_bridge.mjs`（Node，DSH 自带）通过 `http://127.0.0.1:9222` + WebSocket 发
`Runtime.evaluate` / `Page.navigate` / `Page.captureScreenshot` / `Target.createTarget`，
等价于 Chrome DevTools 的 Console 里执行代码。

注意：Edge/Chrome 从 136 版起，用默认 profile 开远程调试会被拒绝；**必须**用 `--user-data-dir` 指向独立目录，
所以第一次要在这个窗口里重新登录 CloudCampus。

## 方式三：WebDriver（Windows/Linux 通用，Firefox 也走这条路）

W3C WebDriver 是标准协议，Edge/Chrome/Firefox/Safari 都有 driver：

```powershell
# Windows Edge
msedgedriver.exe --port 9515
# 然后
python scripts\scan_course.py --course-id 12345 --browser webdriver --webdriver-url http://127.0.0.1:9515
```

```bash
# macOS Firefox
brew install geckodriver
geckodriver --port 4444
python3 scripts/scan_course.py --course-id 12345 --browser webdriver --webdriver-url http://127.0.0.1:4444
```

注意：WebDriver 默认使用临时 profile，登录状态不保留。要让 CloudCampus 免登录，把
`--webdriver-url` 指向的 driver 配置成固定 profile（Firefox: `--profile`；Edge/Chrome:
`--user-data-dir` 通过 capabilities 传入）。脚本里可以用环境变量传 capabilities：

```bash
export SKILL_WD_CAPABILITIES='{"ms:edgeOptions":{"args":["--user-data-dir=C:\\edge-profile"]}}'
```

（当前 `WebDriverDriver` 会读取该 JSON 作为 `alwaysMatch` 能力。）

## 浏览器医生（先跑这个）

```bash
python3 scripts/browser_doctor.py
```

输出每个后端的 installed / running / JS 开关 / CloudCampus 标签数 / CDP / WebDriver 状态，
并给出下一步该敲的命令。缺什么它直接告诉你。

## 常见问题

| 现象 | 处理 |
|---|---|
| `execute ... javascript` 报 “功能已关闭” | 打开菜单 View > Developer > Allow JavaScript from Apple Events，或改用 `--browser cdp` |
| `窗口索引错误 (-1719)` | 浏览器没有窗口：先打开一个窗口/标签再跑 |
| CDP 端口连不上 | 确认浏览器是用 `--remote-debugging-port` 启动的；Edge 需要 `--user-data-dir` 独立 profile |
| CDP 打开的是登录页 | 在这个独立 profile 的窗口里登录一次 CloudCampus，之后会话保留 |
| WebDriver 报 session 创建失败 | driver 没启动或端口不对；`msedgedriver --port 9515` / `geckodriver --port 4444` |
| 脚本跑在错误的标签页 | 用 `--tab N` 固定工作标签；导航后脚本会轮询 URL 确认 |
| 原生文件对话框点不到 | 正常：文件上传走 DataTransfer 注入页面控件，不依赖系统对话框 |

## 本机实测状态（2026-11-24）

- Safari：全流程实测通过（48 项 H5P 满分、24 份作业提交、评分审计）。
- CDP（Chrome 157，`--browser cdp`）：导航、执行 JS、截图、新开/关闭标签实测通过。
- Edge：本机未安装，未做真机验证；AppleScript 与 CDP 两条路与 Chrome 共用同一套 Chromium API，
  安装 Edge 后 `browser_doctor.py` 会显示 `apple_script_js=on/off`。
- Firefox/WebDriver：本机没有 geckodriver，未做真机验证。
