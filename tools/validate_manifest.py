#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

path = Path("manifest.json")
data = json.loads(path.read_text(encoding="utf-8"))
languages = data.get("languages")
if not isinstance(languages, dict) or not languages:
    raise SystemExit("manifest.languages must be a non-empty object")
for slug, item in languages.items():
    if not isinstance(item, dict):
        raise SystemExit(f"{slug}: entry must be an object")
    for key in ("display", "spec_url"):
        if not isinstance(item.get(key), str) or not item[key]:
            raise SystemExit(f"{slug}: missing {key}")
    url = urlparse(item["spec_url"])
    if url.scheme != "https" or url.netloc != "img.atcoder.jp":
        raise SystemExit(f"{slug}: unsupported spec URL {item['spec_url']}")
print(f"validated {len(languages)} languages")
