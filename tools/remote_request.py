#!/usr/bin/env python3
"""Create or post a code-golf runner request from local source and test files."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPOSITORY = "mackerel38/atcoder_codegolf_tools"
DEFAULT_ISSUE = 1


def encoded(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def load_languages() -> set[str]:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    return set(manifest["languages"])


def safe_id(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return value or "candidate"


def build_request(
    language: str,
    source: Path,
    cases_dir: Path,
    mode: str,
    request_id: str | None = None,
) -> dict:
    if language not in load_languages():
        available = ", ".join(sorted(load_languages()))
        raise ValueError(f"unknown language {language!r}; choose one of: {available}")
    if not source.is_file():
        raise ValueError(f"source file not found: {source}")
    if not cases_dir.is_dir():
        raise ValueError(f"cases directory not found: {cases_dir}")

    inputs = sorted(cases_dir.glob("*.in"))
    if not inputs:
        raise ValueError(f"no *.in files found in {cases_dir}")

    tests = []
    for input_path in inputs:
        output_path = input_path.with_suffix(".out")
        test = {
            "name": safe_id(input_path.stem),
            "stdin_base64": encoded(input_path),
        }
        if output_path.is_file():
            test["expected_base64"] = encoded(output_path)
        tests.append(test)

    if request_id is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        request_id = f"{safe_id(source.stem)}-{language}-{stamp}"

    return {
        "request_id": request_id,
        "language": language,
        "candidates": [
            {
                "id": safe_id(source.stem),
                "source_base64": encoded(source),
            }
        ],
        "tests": tests,
        "judge_mode": mode,
    }


def payload(request: dict) -> str:
    return "/run\n" + json.dumps(request, ensure_ascii=False, indent=2) + "\n"


def post(body: str, repository: str, issue: int) -> None:
    try:
        subprocess.run(
            [
                "gh",
                "issue",
                "comment",
                str(issue),
                "--repo",
                repository,
                "--body-file",
                "-",
            ],
            input=body,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "GitHub CLI (gh) was not found; use remote-payload and paste it manually"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"failed to post GitHub runner request (exit {exc.returncode})") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("language")
    parser.add_argument("source", type=Path)
    parser.add_argument("cases_dir", type=Path)
    parser.add_argument("--mode", choices=("tokens", "exact", "float"), default="tokens")
    parser.add_argument("--request-id")
    parser.add_argument("--post", action="store_true")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--issue", type=int, default=DEFAULT_ISSUE)
    args = parser.parse_args()

    try:
        request = build_request(
            args.language,
            args.source,
            args.cases_dir,
            args.mode,
            args.request_id,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    body = payload(request)
    if args.post:
        post(body, args.repository, args.issue)
    else:
        sys.stdout.write(body)


if __name__ == "__main__":
    main()
