#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tts_gen.py - offline speech-generating helper (macOS only).

Uses `say` for speech and `afconvert` for AAC/.m4a. No network, no voice clone:
the output is a synthetic voice shaped by pitch (pbas) and rate commands, which
is enough for practice recordings but must not be presented as a real recording.

Presets (measured on macOS 14/15 with the Daniel voice):
  clarkson-ish  Daniel, pbas 40, rate 60, pauses 140/300 ms
  neutral-gb    Daniel, default pitch, rate 110
  clear-gb-slow Daniel, pbas 44, rate 60
  natural-us    Samantha, rate 110
The `[[pbas N]]` range is quantised; on this machine 36/38/40/42 give roughly
72/75/85/99 Hz median F0 and values below 36 clamp. See references/06-media.md.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

PRESETS = {
    "clarkson-ish": {"voice": "Daniel", "pbas": 40, "rate": 60, "comma_ms": 140, "stop_ms": 300},
    "neutral-gb": {"voice": "Daniel", "pbas": None, "rate": 110, "comma_ms": 100, "stop_ms": 220},
    "clear-gb-slow": {"voice": "Daniel", "pbas": 44, "rate": 60, "comma_ms": 110, "stop_ms": 240},
    "natural-us": {"voice": "Samantha", "pbas": None, "rate": 110, "comma_ms": 100, "stop_ms": 220},
}


def add_pauses(text: str, comma_ms: int, stop_ms: int) -> str:
    out = []
    for i, ch in enumerate(text):
        out.append(ch)
        if ch in ",;:":
            out.append(f" [[slnc {comma_ms}]] ")
        elif ch in ".!?":
            nxt = text[i + 1] if i + 1 < len(text) else " "
            if nxt.isspace():
                out.append(f" [[slnc {stop_ms}]] ")
    return "".join(out)


def info(path: str) -> tuple[float, int]:
    r = subprocess.run(["afinfo", path], capture_output=True, text=True)
    m = re.search(r"duration: ([0-9.]+)", r.stdout or "")
    return (float(m.group(1)) if m else 0.0), os.path.getsize(path)


def synth(text: str, out_m4a: str, voice: str, pbas, rate, comma_ms: int, stop_ms: int) -> tuple[float, int]:
    body = add_pauses(text, comma_ms, stop_ms)
    header = ""
    if pbas is not None:
        header += f"[[pbas {pbas}]] "
    if rate is not None:
        header += f"[[rate {rate}]] "
    script = header + body
    base = os.path.splitext(out_m4a)[0]
    txt = base + ".txt"
    aiff = base + ".aiff"
    open(txt, "w", encoding="utf-8").write(script)
    subprocess.run(["say", "-v", voice, "-f", txt, "-o", aiff], check=True)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000", "-s", "3", aiff, out_m4a], check=True)
    os.remove(txt)
    os.remove(aiff)
    return info(out_m4a)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate .m4a speech with macOS say")
    ap.add_argument("inputs", nargs="*", help="UTF-8 text files")
    ap.add_argument("--text", help="inline text (alternative to input files)")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="clarkson-ish")
    ap.add_argument("--voice")
    ap.add_argument("--pbas", type=int)
    ap.add_argument("--rate", type=int)
    ap.add_argument("--comma-ms", type=int)
    ap.add_argument("--stop-ms", type=int)
    ap.add_argument("--out", help="output .m4a for a single input")
    ap.add_argument("--outdir", help="directory for batch outputs")
    args = ap.parse_args()

    preset = PRESETS[args.preset]
    voice = args.voice or preset["voice"]
    pbas = preset["pbas"] if args.pbas is None else args.pbas
    rate = preset["rate"] if args.rate is None else args.rate
    comma_ms = preset["comma_ms"] if args.comma_ms is None else args.comma_ms
    stop_ms = preset["stop_ms"] if args.stop_ms is None else args.stop_ms

    jobs = []
    if args.text:
        if not args.out:
            ap.error("--text needs --out")
        jobs.append((args.text, args.out))
    for path in args.inputs:
        stem = os.path.splitext(os.path.basename(path))[0]
        outdir = args.outdir or os.path.dirname(os.path.abspath(path))
        jobs.append((open(path, encoding="utf-8").read(), os.path.join(outdir, stem + ".m4a")))
    if not jobs:
        ap.error("give --text or at least one input file")

    for text, out in jobs:
        dur, size = synth(text, out, voice, pbas, rate, comma_ms, stop_ms)
        print(f"{os.path.basename(out)}: {dur:.1f}s  {size/1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
