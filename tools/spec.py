#!/usr/bin/env python3
"""Fetch, validate, and normalize an AtCoder language TOML specification."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path("/opt/atcoder-toolchain")


def read_bytes(location: str) -> bytes:
    parsed = urlparse(location)
    if parsed.scheme in {"http", "https"}:
        req = Request(location, headers={"User-Agent": "atcoder-codegolf-tools/1"})
        with urlopen(req, timeout=60) as response:
            return response.read()
    return Path(location).read_bytes()


def load_spec(location: str) -> tuple[bytes, dict]:
    raw = read_bytes(location)
    try:
        spec = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise SystemExit(f"invalid TOML at {location}: {exc}") from exc
    for key in ("language", "display", "filename", "execution"):
        if key not in spec:
            raise SystemExit(f"missing required key {key!r} in {location}")
    if not isinstance(spec["execution"], list) or not all(
        isinstance(value, str) for value in spec["execution"]
    ):
        raise SystemExit(f"execution must be a string array in {location}")
    return raw, spec


def install(location: str, root: Path) -> None:
    raw, spec = load_spec(location)
    root.mkdir(parents=True, exist_ok=True)
    (root / "source.toml").write_bytes(raw)
    (root / "spec.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    script = spec.get("install", "")
    if not isinstance(script, str):
        raise SystemExit("install must be a string")
    
    script = script.replace("perl=5.38.2-3.2ubuntu0.2", "perl")
    
    if spec.get("language") == "APL":
        # Some GNU mirrors currently fail TLS or no longer expose the old flat URL.
        # Try current GNU mirrors and verify the GNU APL 1.9 release archive.
        script = script.replace(
            "wget https://ftpmirror.gnu.org/gnu/apl/apl-1.9.tar.gz",
            """wget -O apl-1.9.tar.gz https://rsync.nic.funet.fi/pub/gnu/RELEASE/apl/apl-1.9/apl-1.9.tar.gz ||
    wget -O apl-1.9.tar.gz https://gnu.cs.utah.edu/apl/apl-1.9.tar.gz
    echo '291867f1b1937693abb57be7d9a37618b0376e3e2709574854a7bbe52bb28eb8  apl-1.9.tar.gz' | sha256sum -c -""",
        )
        script = (
            "set -Eex\n"
            "trap 's=$?; "
            'echo "::error::APL install failed at line '
            "$LINENO: $BASH_COMMAND (exit $s)\" >&2; "
            "exit $s' ERR\n"
            + script
        )
    
    if spec.get("language") == "Ruby":
        # numo-openblas requires a Fortran compiler to build LAPACK.
        script = "sudo apt-get install -y gfortran\n" + script
    
        # Reproduce the Rice version available when the 2025-10
        # AtCoder Ruby environment was prepared.
        marker = 'export MAKEFLAGS="-j$(nproc)"'
        script = script.replace(
            marker,
            marker + "\ngem install -N rice:4.6.1",
        )
    if "Codon" in spec.get("display", ""):
        script = (
            "set -Eex\n"
            "trap 's=$?; "
            'echo "::error::Codon install failed at line '
            "$LINENO: $BASH_COMMAND (exit $s)\" >&2; "
            "exit $s' ERR\n"
            + script
        )
    if spec.get("language") == "cLay":
        # Follow redirects from repositories that were renamed or transferred.
        script = script.replace(
            "curl -s https://api.github.com/repos/",
            "curl -sL https://api.github.com/repos/",
        )

        # Replace the removed SCIP download URL with the official GitHub asset.
        old_scip = (
            "wget -q -O scip.sh "
            "https://scipopt.org/download/release/"
            "SCIPOptSuite-9.2.3-Linux-ubuntu24.sh"
        )
        new_scip = (
            "wget -q -O scip.sh "
            "https://github.com/scipopt/scip/releases/download/v923/"
            "SCIPOptSuite-9.2.3-Linux-ubuntu24.sh"
        )

        if old_scip not in script:
            raise SystemExit("cLay SCIP patch target not found")

        script = script.replace(old_scip, new_scip)

        # Pin OR-Tools to the version matching the AtCoder dependency set.
        old_ortools = (
            'gh_download_latest "google" "or-tools"\n'
            "pushd google-or-tools/*"
        )

        new_ortools = "\n".join(
            (
                'AC_ORTOOLS_VERSION="9.14"',
                'wget -q -O or-tools.tar.gz '
                '"https://github.com/google/or-tools/releases/download/'
                'v${AC_ORTOOLS_VERSION}/'
                'or-tools-${AC_ORTOOLS_VERSION}.tar.gz"',
                "mkdir google-or-tools",
                "tar -C google-or-tools -xf or-tools.tar.gz",
                'echo "google/or-tools $AC_ORTOOLS_VERSION" '
                '>> "$HOME/library_version"',
                "pushd google-or-tools/*",
            )
        )

        if old_ortools not in script:
            raise SystemExit("cLay OR-Tools patch target not found")

        script = script.replace(old_ortools, new_ortools)

        # Show the exact command when installation fails.
        script = (
            "set -Eex\n"
            "trap 's=$?; "
            'echo "::error::cLay install failed at line '
            "$LINENO: $BASH_COMMAND (exit $s)\" >&2; "
            'echo "::group::Disk usage" >&2; '
            "df -h >&2; "
            'echo "::endgroup::" >&2; '
            "exit $s' ERR\n"
            + script
        )
    if script:
        install_script = root / "install.sh"
        install_script.write_text(
            "#!/usr/bin/env bash\nset -e\n" + script + "\n",
            encoding="utf-8",
        )
        install_script.chmod(0o755)
        env = os.environ.copy()
        env.setdefault("HOME", "/root")
        subprocess.run(["bash", str(install_script)], cwd=root, env=env, check=True)


def validate(location: str) -> None:
    _, spec = load_spec(location)
    print(f"{spec['language']}\t{spec['display']}\t{spec['filename']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_install = sub.add_parser("install")
    p_install.add_argument("location")
    p_install.add_argument("--root", type=Path, default=ROOT)
    p_validate = sub.add_parser("validate")
    p_validate.add_argument("location")
    args = parser.parse_args()
    if args.command == "install":
        install(args.location, args.root)
    else:
        validate(args.location)


if __name__ == "__main__":
    main()
