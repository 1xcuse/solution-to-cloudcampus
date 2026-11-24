#!/bin/bash
# Launch a Chromium browser (Edge by default) with a dedicated profile and a CDP port.
# The profile keeps the CloudCampus login between runs, so you only log in once.
#
# usage:
#   bash scripts/launch_edge_cdp.sh                     # Edge, port 9222, opens CloudCampus
#   bash scripts/launch_edge_cdp.sh --port 9333 --app chrome
#   bash scripts/launch_edge_cdp.sh --url https://www.cloudcampus.com.cn/
set -u
PORT=9222
APP=edge
URL="https://www.cloudcampus.com.cn/"
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --app)  APP="$2"; shift 2 ;;
    --url)  URL="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1"; exit 1 ;;
  esac
done

case "$APP" in
  edge)    BIN="/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" ;;
  chrome)  BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ;;
  brave)   BIN="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" ;;
  chromium) BIN="/Applications/Chromium.app/Contents/MacOS/Chromium" ;;
  arc)     BIN="/Applications/Arc.app/Contents/MacOS/Arc" ;;
  *) echo "unsupported app: $APP (edge|chrome|brave|chromium|arc)"; exit 1 ;;
esac

if [ ! -x "$BIN" ]; then
  echo "找不到 $APP 的可执行文件：$BIN"
  echo
  echo "macOS 安装 Edge：https://www.microsoft.com/edge/download （下载 .pkg 后双击安装）"
  echo "Windows 用法（PowerShell）："
  echo '  & "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 `'
  echo '      --user-data-dir="$env:USERPROFILE\.dsh\edge-cdp" --new-window https://www.cloudcampus.com.cn'
  echo
  echo "也可以继续用 Safari：python3 scripts/scan_course.py --course-id 12345 --browser safari"
  exit 2
fi

PROFILE="$HOME/.dsh/browser-profiles/$APP-cdp"
mkdir -p "$PROFILE"
echo "启动 $APP（profile: $PROFILE, CDP 端口: $PORT）..."
"$BIN" --remote-debugging-port="$PORT" --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check --new-window "$URL" >/dev/null 2>&1 &

for i in $(seq 1 20); do
  if curl -s --max-time 1 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if ! curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "启动后 CDP 端口 $PORT 仍不可用，检查是否有弹窗/权限提示。"
  exit 3
fi

echo "CDP 已就绪："
curl -s "http://127.0.0.1:$PORT/json/version" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("  Browser:", d.get("Browser"))' 2>/dev/null || true
echo
echo "下一步：在打开的 $APP 窗口里登录 CloudCampus（只需一次，profile 会记住会话）。"
echo "然后用 CDP 模式跑技能脚本，例如："
echo "  python3 scripts/scan_course.py --course-id 12345 --browser cdp --cdp-port $PORT"
echo "  python3 scripts/solve_h5p.py --course-id 12345 --browser cdp --cdp-port $PORT --from-scan scan/inventory.json"
