from __future__ import annotations

from pathlib import Path
import base64
import importlib.util
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

REMOTE_SPEC = importlib.util.spec_from_file_location(
    "remote_request", ROOT / "tools/remote_request.py"
)
assert REMOTE_SPEC and REMOTE_SPEC.loader
remote_request = importlib.util.module_from_spec(REMOTE_SPEC)
REMOTE_SPEC.loader.exec_module(remote_request)

GOLF_SPEC = importlib.util.spec_from_file_location("golf", ROOT / "tools/golf.py")
assert GOLF_SPEC and GOLF_SPEC.loader
golf = importlib.util.module_from_spec(GOLF_SPEC)
GOLF_SPEC.loader.exec_module(golf)


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


def test_remote_request() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        source = tmp / "Main.awk"
        source.write_bytes(b"{print $1}")
        cases = tmp / "cases"
        cases.mkdir()
        (cases / "sample.in").write_bytes(b"123\n")
        (cases / "sample.out").write_bytes(b"123\n")
        (cases / "run-only.in").write_bytes(b"456\n")

        request = remote_request.build_request(
            "awk", source, cases, "tokens", "test-request"
        )
        assert request["request_id"] == "test-request"
        assert request["language"] == "awk"
        assert len(request["tests"]) == 2
        assert base64.b64decode(
            request["candidates"][0]["source_base64"]
        ) == b"{print $1}"
        sample = next(test for test in request["tests"] if test["name"] == "sample")
        assert base64.b64decode(sample["expected_base64"]) == b"123\n"
        run_only = next(
            test for test in request["tests"] if test["name"] == "run-only"
        )
        assert "expected_base64" not in run_only
        assert json.loads(remote_request.payload(request).split("\n", 1)[1]) == request


def test_local_judge_comparison() -> None:
    assert golf.compare(b"1  2\n", b"1\n2\n", "tokens")
    assert not golf.compare(b"1 2\n", b"1 3\n", "tokens")
    assert golf.compare(b"exact\n", b"exact\n", "exact")
    assert not golf.compare(b"exact", b"exact\n", "exact")


if __name__ == "__main__":
    test_manifest()
    test_local_spec_and_runner()
    test_remote_request()
    test_local_judge_comparison()
    print("ok")
