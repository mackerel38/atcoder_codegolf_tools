#!/usr/bin/env python3
"""Compile/check and run one submission using stored AtCoder TOML metadata."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(os.environ.get("TOOLCHAIN_ROOT", "/opt/atcoder-toolchain"))
SUBMISSION = Path(os.environ.get("SUBMISSION", "/submission"))


def placeholders(value: str) -> str:
    memory_b = int(os.environ.get("ATCODER_MEMORY_BYTES", str(1024**3)))
    return (
        value.replace("{memory:b}", str(memory_b))
        .replace("{memory:kb}", str(memory_b // 1024))
        .replace("{memory:mb}", str(memory_b // 1024**2))
    )


def runtime_environment(spec: dict) -> dict[str, str]:
    env = os.environ.copy()
    for key in ("environment", "execution_environment", "execution_env"):
        values = spec.get(key)
        if isinstance(values, dict):
            env.update({str(k): placeholders(str(v)) for k, v in values.items()})
    return env


def source_path(filename: str) -> Path:
    if SUBMISSION.is_file():
        return SUBMISSION
    candidate = SUBMISSION / filename
    if candidate.is_file():
        return candidate
    files = [path for path in SUBMISSION.iterdir() if path.is_file()] if SUBMISSION.is_dir() else []
    if len(files) == 1:
        return files[0]
    raise SystemExit(f"submission source not found: expected {candidate}")


def main() -> None:
    spec = json.loads((ROOT / "spec.json").read_text(encoding="utf-8"))
    filename = spec["filename"]
    src = source_path(filename)
    dst = ROOT / filename
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)

    env = runtime_environment(spec)
    compile_script = spec.get("compile")
    if compile_script:
        subprocess.run(["bash", "-c", compile_script], cwd=ROOT, env=env, check=True)
        obj = spec.get("object")
        if obj and not (ROOT / obj).exists():
            raise SystemExit(f"compile command succeeded but object is missing: {obj}")

    command = [placeholders(str(value)) for value in spec["execution"]]
    completed = subprocess.run(command, cwd=ROOT, env=env)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
