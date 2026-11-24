#!/usr/bin/env node
// cdp_bridge.mjs - minimal Chrome DevTools Protocol helper for the skill.
// Usage:
//   node cdp_bridge.mjs --port 9222 eval --target <id> --expr-file file.js
//   node cdp_bridge.mjs --port 9222 navigate --target <id> --url https://...
//   node cdp_bridge.mjs --port 9222 newtab --url https://...
//   node cdp_bridge.mjs --port 9222 closetab --target <id>
//   node cdp_bridge.mjs --port 9222 screenshot --target <id> --out /tmp/a.png
//   node cdp_bridge.mjs --port 9222 list
// Prints exactly one JSON line on stdout: {"ok":true,"value":...} or {"ok":false,"error":"..."}
import fs from "node:fs";

const argv = process.argv.slice(2);
const opts = { port: 9222 };
const positional = [];
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "--port" || a === "--target" || a === "--expr-file" || a === "--url" || a === "--out") {
    opts[a.replace(/^--/, "")] = argv[++i];
  } else {
    positional.push(a);
  }
}
const cmd = positional[0] || "list";

function out(obj) {
  console.log(JSON.stringify(obj));
  process.exit(obj.ok ? 0 : 1);
}

async function main() {
  const port = Number(opts.port || 9222);
  if (cmd === "list") {
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    return out({ ok: true, value: list });
  }
  const version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  const ws = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = (e) => reject(new Error("websocket error"));
  });
  let id = 0;
  const pending = new Map();
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) reject(new Error(JSON.stringify(m.error)));
      else resolve(m.result);
    }
  };
  const send = (method, params = {}, sessionId) =>
    new Promise((resolve, reject) => {
      const msg = { id: ++id, method, params };
      if (sessionId) msg.sessionId = sessionId;
      pending.set(msg.id, { resolve, reject });
      ws.send(JSON.stringify(msg));
    });
  const attach = async (targetId) => {
    const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
    return sessionId;
  };

  if (cmd === "newtab") {
    const { targetId } = await send("Target.createTarget", { url: opts.url || "about:blank" });
    ws.close();
    return out({ ok: true, value: targetId });
  }
  if (cmd === "closetab") {
    await send("Target.closeTarget", { targetId: opts.target });
    ws.close();
    return out({ ok: true, value: true });
  }
  if (cmd === "navigate") {
    const sid = await attach(opts.target);
    const res = await send("Page.navigate", { url: opts.url }, sid);
    ws.close();
    return out({ ok: true, value: res });
  }
  if (cmd === "eval") {
    const sid = await attach(opts.target);
    const expression = fs.readFileSync(opts["expr-file"], "utf8");
    const res = await send(
      "Runtime.evaluate",
      { expression, returnByValue: true, awaitPromise: true, userGesture: true },
      sid
    );
    if (res.exceptionDetails) {
      const desc = res.exceptionDetails.exception?.description || res.exceptionDetails.text || "JS exception";
      ws.close();
      return out({ ok: false, error: desc.slice(0, 500) });
    }
    let value = res.result ? res.result.value : null;
    if (value === undefined) value = res.result?.description ?? null;
    ws.close();
    return out({ ok: true, value });
  }
  if (cmd === "screenshot") {
    const sid = await attach(opts.target);
    const res = await send("Page.captureScreenshot", { format: "png" }, sid);
    fs.writeFileSync(opts.out, Buffer.from(res.data, "base64"));
    ws.close();
    return out({ ok: true, value: opts.out });
  }
  ws.close();
  return out({ ok: false, error: `unknown command: ${cmd}` });
}

main().catch((e) => out({ ok: false, error: String(e && e.message ? e.message : e) }));
