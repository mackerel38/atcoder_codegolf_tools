from __future__ import annotations

from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)


def test_manifest() -> None:
    out = run("python3", "tools/validate_manifest.py").stdout
    assert "validated 14 languages" in out
    out = run("python3", "tools/manifest_query.py", "uiua").stdout
    assert "spec_url=https://img.atcoder.jp/" in out


def test_local_spec_and_runner() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        spec = tmp / "mock.toml"
        spec.write_text(
            "language='mock'\n"
            "display='Mock 1'\n"
            "filename='Main.mock'\n"
            "install='''printf installed > marker'''\n"
            "compile='''cp Main.mock program'''\n"
            "object='program'\n"
            "environment={LIMIT='{memory:mb}'}\n"
            "execution=['bash','program']\n",
            encoding="utf-8",
        )
        toolchain = tmp / "toolchain"
        run(
            "python3",
            str(ROOT / "tools/spec.py"),
            "install",
            str(spec),
            "--root",
            str(toolchain),
            cwd=tmp,
        )
        assert (toolchain / "marker").read_text() == "installed"
        source = tmp / "Main.mock"
        source.write_text('read x; echo "$((x+1)) $LIMIT"\n', encoding="utf-8")
        result = subprocess.run(
            ["python3", str(ROOT / "tools/run_submission.py")],
            input="41\n",
            text=True,
            capture_output=True,
            env={
                "PATH": os.environ["PATH"],
                "TOOLCHAIN_ROOT": str(toolchain),
                "SUBMISSION": str(source),
                "ATCODER_MEMORY_BYTES": str(256 * 1024**2),
            },
            check=True,
        )
        assert result.stdout == "42 256\n"


if __name__ == "__main__":
    test_manifest()
    test_local_spec_and_runner()
    print("ok")
