#!/bin/bash
# Offline smoke test for solution-to-cloudcampus.
# Does not touch Safari, does not submit anything.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/s2c-smoke.XXXXXX")"
PASS=0; FAIL=0; SKIP=0
ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }
skip() { SKIP=$((SKIP+1)); printf '  skip %s\n' "$1"; }

echo "== python syntax =="
for f in "$ROOT"/scripts/*.py; do
  if python3 -m py_compile "$f" 2>"$TMP/pyerr"; then ok "compile $(basename "$f")"; else bad "compile $(basename "$f"): $(cat "$TMP/pyerr")"; fi
done

echo "== javascript syntax =="
NODE="$(command -v node || true)"
if [ -z "$NODE" ] && [ -x "$HOME/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/node/bin/node" ]; then
  NODE="$HOME/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/node/bin/node"
fi
if [ -n "$NODE" ]; then
  while IFS= read -r f; do
    if "$NODE" --check "$f" 2>"$TMP/jserr"; then ok "js $(basename "$f")"; else bad "js $(basename "$f"): $(cat "$TMP/jserr")"; fi
  done < <(find "$ROOT/scripts/js" -name '*.js' | sort)
else
  skip "node not found; js syntax not checked"
fi

echo "== cdp bridge =="
if [ -n "$NODE" ]; then
  if "$NODE" --check "$ROOT/scripts/cdp_bridge.mjs" 2>"$TMP/mjserr"; then ok "cdp_bridge.mjs"; else bad "cdp_bridge.mjs: $(cat "$TMP/mjserr")"; fi
else
  skip "node not found; cdp bridge not checked"
fi
if bash -n "$ROOT/scripts/launch_edge_cdp.sh" 2>"$TMP/lserr"; then ok "launch_edge_cdp.sh"; else bad "launch_edge_cdp.sh: $(cat "$TMP/lserr")"; fi

echo "== JSON assets =="
for f in "$ROOT"/assets/*.json; do
  if python3 -c "import json,sys; json.load(open(sys.argv[1],encoding='utf-8'))" "$f" 2>"$TMP/jserr"; then ok "json $(basename "$f")"; else bad "json $(basename "$f"): $(cat "$TMP/jserr")"; fi
done

echo "== TTS -> m4a =="
if [ -x /usr/bin/say ] && [ -x /usr/bin/afconvert ] && [ -x /usr/bin/afinfo ]; then
  if python3 "$ROOT/scripts/tts_gen.py" --text "Hello. This is a smoke test of the speaking card pipeline." \
      --out "$TMP/tts.m4a" --preset neutral-gb >"$TMP/tts.log" 2>&1; then
    DUR="$(afinfo "$TMP/tts.m4a" 2>/dev/null | awk '/duration:/ {print $3}')"
    SIZE="$(stat -f%z "$TMP/tts.m4a" 2>/dev/null || echo 0)"
    if [ -n "$DUR" ] && [ "$SIZE" -gt 1000 ]; then ok "tts m4a ${DUR}s ${SIZE}B"; else bad "tts output too small (${SIZE}B)"; fi
  else
    bad "tts_gen failed: $(tail -3 "$TMP/tts.log")"
  fi
else
  skip "say/afconvert not available (not macOS?)"
fi

echo "== docx =="
PY="$HOME/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3"
if [ ! -x "$PY" ]; then PY="$(command -v python3)"; fi
if "$PY" -c "import docx" 2>/dev/null; then
  if "$PY" "$ROOT/scripts/gen_docx.py" "$ROOT/assets/text.example.md" --out "$TMP/example.docx" >"$TMP/docx.log" 2>&1 && [ -s "$TMP/example.docx" ]; then
    ok "docx $(stat -f%z "$TMP/example.docx" 2>/dev/null || echo 0)B"
  else
    bad "gen_docx failed: $(cat "$TMP/docx.log")"
  fi
else
  skip "python-docx not available in $PY"
fi

echo "== visuals =="
if python3 -c "import PIL, numpy" 2>/dev/null; then
  for kind in mindmap poster photo; do
    spec="$ROOT/assets/${kind}.example.json"
    case "$kind" in
      mindmap) spec="$ROOT/assets/mindmap.example.json" ;;
      poster)  spec="$ROOT/assets/poster.example.json" ;;
      photo)   spec="$ROOT/assets/photo.example.json" ;;
    esac
    out="$TMP/$kind.$([ "$kind" = photo ] && echo jpg || echo png)"
    if python3 "$ROOT/scripts/gen_visuals.py" "$kind" --spec "$spec" --out "$out" >"$TMP/vis.log" 2>&1 && [ -s "$out" ]; then
      ok "$kind $(stat -f%z "$out" 2>/dev/null || echo 0)B"
    else
      bad "$kind failed: $(tail -3 "$TMP/vis.log")"
    fi
  done
else
  skip "PIL/numpy not available"
fi

echo "== skill metadata =="
if grep -q '^name: solution-to-cloudcampus' "$ROOT/SKILL.md" 2>/dev/null; then ok "SKILL.md frontmatter"; else bad "SKILL.md frontmatter missing"; fi
for ref in "$ROOT"/references/*.md; do [ -s "$ref" ] && ok "reference $(basename "$ref")" || bad "reference $(basename "$ref") empty"; done
for script in cloudcampus.py browser.py scan_course.py solve_h5p.py submit_assignments.py verify_progress.py audit_h5p_answers.py browser_doctor.py tts_gen.py gen_docx.py gen_visuals.py; do
  [ -s "$ROOT/scripts/$script" ] && ok "script $script" || bad "script $script missing"
done

echo
echo "================================="
echo "PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
[ "$FAIL" -eq 0 ] && echo "SMOKE PASSED" || echo "SMOKE FAILED"
rm -rf "$TMP"
[ "$FAIL" -eq 0 ]
