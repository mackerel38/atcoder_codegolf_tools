#!/usr/bin/env python3
"""Small local frontend for byte counting and code-golf regression tests."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
REMOTE_ONLY = {"codon", "clay", "octave"}


def command_for(language: str, source: Path, build: Path) -> tuple[list[str], dict[str, str]]:
    env = os.environ.copy()
    commands: dict[str, list[str]] = {
        "a-lang": [str(RUNTIME / "a-lang/interpreter"), str(source)],
        "awk": ["gawk", "-f", str(source)],
        "bash": [str(RUNTIME / "bash53/bin/bash"), str(source)],
        "dc": [str(RUNTIME / "bc1082/bin/dc"), "-f", str(source)],
        "perl": ["perl", str(source)],
        "pypy311": [str(RUNTIME / "pypy311/bin/pypy3"), str(source)],
        "ruby": [str(RUNTIME / "ruby345/bin/ruby"), str(source)],
        "uiua": [
            str(RUNTIME / "uiua/uiua"),
            "run",
            "--no-format",
            "--no-color",
            str(source),
        ],
    }
    if language == "r":
        r_home = RUNTIME / "r450/usr/lib/R"
        env["R_HOME"] = str(r_home)
        return [str(r_home / "bin/Rscript"), str(source)], env
    if language == "cpp23-gcc":
        executable = build / "main"
        subprocess.run(
            ["g++", "-std=gnu++23", "-O2", str(source), "-o", str(executable)],
            check=True,
        )
        return [str(executable)], env
    if language in REMOTE_ONLY:
        raise ValueError(
            f"{language} is remote-only; use ./bootstrap.sh remote {language} ..."
        )
    if language not in commands:
        raise ValueError(f"no local runtime configured for {language}")
    command = commands[language]
    if not Path(command[0]).is_absolute() and shutil.which(command[0]) is None:
        raise ValueError(f"command not found: {command[0]}")
    if Path(command[0]).is_absolute() and not Path(command[0]).is_file():
        raise ValueError(f"runtime not installed: {command[0]}")
    return command, env


def compare(actual: bytes, expected: bytes, mode: str) -> bool:
    if mode == "exact":
        return actual == expected
    if mode == "tokens":
        return actual.split() == expected.split()
    raise ValueError(f"unsupported local judge mode: {mode}")


def run_tests(language: str, source: Path, cases: Path, mode: str) -> bool:
    inputs = sorted(cases.glob("*.in"))
    if not inputs:
        raise ValueError(f"no *.in files found in {cases}")
    passed = True
    with tempfile.TemporaryDirectory() as directory:
        command, env = command_for(language, source.resolve(), Path(directory))
        for input_path in inputs:
            result = subprocess.run(
                command,
                input=input_path.read_bytes(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=10,
            )
            expected_path = input_path.with_suffix(".out")
            ok = result.returncode == 0
            if expected_path.is_file():
                ok &= compare(result.stdout, expected_path.read_bytes(), mode)
            passed &= ok
            print(
                f"{'PASS' if ok else 'FAIL'}  {input_path.stem}"
                f"  exit={result.returncode}  stdout={len(result.stdout)}B"
            )
            if not ok:
                sys.stdout.buffer.write(result.stdout)
                sys.stderr.buffer.write(result.stderr)
    return passed


def status() -> None:
    checks = {
        "a-lang": RUNTIME / "a-lang/interpreter",
        "awk": Path(shutil.which("gawk") or ""),
        "bash": RUNTIME / "bash53/bin/bash",
        "cpp23-gcc": Path(shutil.which("g++") or ""),
        "dc": RUNTIME / "bc1082/bin/dc",
        "perl": Path(shutil.which("perl") or ""),
        "pypy311": RUNTIME / "pypy311/bin/pypy3",
        "r": RUNTIME / "r450/usr/lib/R/bin/Rscript",
        "ruby": RUNTIME / "ruby345/bin/ruby",
        "uiua": RUNTIME / "uiua/uiua",
    }
    for language, path in checks.items():
        print(f"{language:12} {'local' if path.is_file() else 'missing':8} {path}")
    for language in sorted(REMOTE_ONLY):
        print(f"{language:12} remote")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    byte_parser = sub.add_parser("bytes")
    byte_parser.add_argument("sources", nargs="+", type=Path)
    test_parser = sub.add_parser("test")
    test_parser.add_argument("language")
    test_parser.add_argument("source", type=Path)
    test_parser.add_argument("cases", type=Path)
    test_parser.add_argument("--mode", choices=("tokens", "exact"), default="tokens")
    args = parser.parse_args()

    try:
        if args.command == "status":
            status()
        elif args.command == "bytes":
            for source in args.sources:
                print(f"{len(source.read_bytes()):5}  {source}")
        elif not run_tests(args.language, args.source, args.cases, args.mode):
            raise SystemExit(1)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
