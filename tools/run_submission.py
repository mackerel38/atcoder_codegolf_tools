#!/usr/bin/env python3
"""Compile/check and run one submission using stored AtCoder TOML metadata."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

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

    files = (
        [path for path in SUBMISSION.iterdir() if path.is_file()]
        if SUBMISSION.is_dir()
        else []
    )
    if len(files) == 1:
        return files[0]

    raise SystemExit(f"submission source not found: expected {candidate}")


def remove_old_object(path: Path) -> None:
    """Remove an object left by a previous compile attempt."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def report_compile_failure(
    completed: subprocess.CompletedProcess[bytes],
) -> None:
    """Expose compiler output only when compilation actually fails."""
    if completed.stdout:
        sys.stderr.buffer.write(completed.stdout)
    if completed.stderr:
        sys.stderr.buffer.write(completed.stderr)


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
        obj = spec.get("object")
        object_path = ROOT / obj if obj else None

        # Do not accept an object left by an earlier candidate or test.
        if object_path:
            remove_old_object(object_path)

        # Compilation output must not be mixed into the submission output.
        completed = subprocess.run(
            ["bash", "-c", compile_script],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if object_path:
            # AtCoder language specifications may intentionally return a
            # nonzero status after creating the object marker. Ruby does this:
            #
            #   ruby -c Main.rb &&
            #   touch syntax_ok &&
            #   ruby --jit Main.rb ONLINE_JUDGE 2>/dev/null
            #
            # Therefore the declared object is the source of truth.
            if not object_path.exists():
                report_compile_failure(completed)
                raise SystemExit(
                    f"compile command did not create expected object: {obj} "
                    f"(exit {completed.returncode})"
                )
        elif completed.returncode:
            # Specifications without an object marker use the exit status.
            report_compile_failure(completed)
            raise SystemExit(completed.returncode)

    command = [placeholders(str(value)) for value in spec["execution"]]
    completed = subprocess.run(command, cwd=ROOT, env=env)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
