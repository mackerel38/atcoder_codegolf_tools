#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))
if len(sys.argv) != 2:
    raise SystemExit("usage: manifest_query.py LANGUAGE")
slug = sys.argv[1]
if not re.fullmatch(r"[a-z0-9-]+", slug):
    raise SystemExit("invalid language slug")
try:
    item = manifest["languages"][slug]
except KeyError as exc:
    raise SystemExit(f"unknown language: {slug}") from exc
print(f"slug={slug}")
print(f"spec_url={item['spec_url']}")
