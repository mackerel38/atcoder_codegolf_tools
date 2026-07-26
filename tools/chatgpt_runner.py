#!/usr/bin/env python3
"""Run trusted code-golf requests from a GitHub issue comment."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import tempfile
import time
import uuid
from typing import Any

MAX_CANDIDATES = 20
MAX_TESTS = 100
MAX_SOURCE_BYTES = 1 * 1024 * 1024
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_EXPECTED_BYTES = 4 * 1024 * 1024
MAX_CAPTURE_BYTES = 256 * 1024
MAX_COMMENT_CHARS = 60_000
DEFAULT_TIMEOUT_SECONDS = 10
MAX_TIMEOUT_SECONDS = 60
DEFAULT_MEMORY_MB = 2048
MAX_MEMORY_MB = 4096
CPU_LIMIT = "2"
PIDS_LIMIT = "512"
QUEUE_TITLE = "ChatGPT code-golf execution queue"
ID_RE = re.compile(r"[A-Za-z0-9_.-]{1,64}\Z")


class RequestError(ValueError):
    """The issue comment does not contain a valid runner request."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_b64(value: Any, field: str, limit: int) -> bytes:
    if not isinstance(value, str):
        raise RequestError(f"{field} must be a Base64 string")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RequestError(f"{field} is not valid Base64") from exc
    if len(decoded) > limit:
        raise RequestError(f"{field} exceeds {limit} decoded bytes")
    return decoded


def bounded_int(value: Any, field: str, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise RequestError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise RequestError(f"{field} must be between {minimum} and {maximum}")
    return value


def bounded_float(value: Any, field: str, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RequestError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise RequestError(f"{field} must be a finite non-negative number")
    return result


def clean_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise RequestError(f"{field} must match {ID_RE.pattern}")
    return value


def strip_optional_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) < 3 or not lines[-1].strip().startswith("```"):
        raise RequestError("unterminated Markdown code fence")
    return "\n".join(lines[1:-1]).strip()


def request_from_event(event: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    issue = event.get("issue")
    comment = event.get("comment")
    repository = event.get("repository")
    if not isinstance(issue, dict) or not isinstance(comment, dict) or not isinstance(repository, dict):
        raise RequestError("unsupported GitHub event")

    owner = repository.get("owner", {}).get("login")
    if not isinstance(owner, str) or not owner:
        raise RequestError("repository owner is missing")
    if issue.get("title") != QUEUE_TITLE:
        raise RequestError("comment is not on the execution queue issue")
    if issue.get("user", {}).get("login") != owner:
        raise RequestError("execution queue issue was not created by the repository owner")
    if comment.get("user", {}).get("login") != owner:
        raise RequestError("request author is not the repository owner")

    body = comment.get("body")
    if not isinstance(body, str) or not body.startswith("/run"):
        raise RequestError("comment must start with /run")
    payload_text = strip_optional_fence(body[4:])
    if not payload_text:
        raise RequestError("/run must be followed by a JSON object")
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise RequestError(f"invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(payload, dict):
        raise RequestError("request payload must be a JSON object")

    languages = manifest.get("languages")
    if not isinstance(languages, dict):
        raise RequestError("manifest.json does not contain languages")
    language = payload.get("language")
    if not isinstance(language, str) or language not in languages:
        raise RequestError("language must be one of the slugs in manifest.json")

    candidates_raw = payload.get("candidates")
    if candidates_raw is None and "source_base64" in payload:
        candidates_raw = [{"id": "candidate", "source_base64": payload["source_base64"]}]
    if not isinstance(candidates_raw, list) or not candidates_raw:
        raise RequestError("candidates must be a non-empty array")
    if len(candidates_raw) > MAX_CANDIDATES:
        raise RequestError(f"at most {MAX_CANDIDATES} candidates are allowed")

    candidates: list[dict[str, Any]] = []
    seen_candidate_ids: set[str] = set()
    for index, item in enumerate(candidates_raw):
        if not isinstance(item, dict):
            raise RequestError(f"candidates[{index}] must be an object")
        candidate_id = clean_id(item.get("id", f"candidate-{index + 1}"), f"candidates[{index}].id")
        if candidate_id in seen_candidate_ids:
            raise RequestError(f"duplicate candidate id: {candidate_id}")
        seen_candidate_ids.add(candidate_id)
        source = decode_b64(item.get("source_base64"), f"candidates[{index}].source_base64", MAX_SOURCE_BYTES)
        try:
            source.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RequestError(f"candidates[{index}].source_base64 must decode to UTF-8") from exc
        candidates.append({"id": candidate_id, "source": source})

    tests_raw = payload.get("tests")
    if not isinstance(tests_raw, list) or not tests_raw:
        raise RequestError("tests must be a non-empty array")
    if len(tests_raw) > MAX_TESTS:
        raise RequestError(f"at most {MAX_TESTS} tests are allowed")

    tests: list[dict[str, Any]] = []
    seen_test_names: set[str] = set()
    for index, item in enumerate(tests_raw):
        if not isinstance(item, dict):
            raise RequestError(f"tests[{index}] must be an object")
        name = clean_id(item.get("name", f"test-{index + 1}"), f"tests[{index}].name")
        if name in seen_test_names:
            raise RequestError(f"duplicate test name: {name}")
        seen_test_names.add(name)
        stdin = decode_b64(item.get("stdin_base64", ""), f"tests[{index}].stdin_base64", MAX_INPUT_BYTES)
        expected = None
        if "expected_base64" in item:
            expected = decode_b64(item["expected_base64"], f"tests[{index}].expected_base64", MAX_EXPECTED_BYTES)
        tests.append({"name": name, "stdin": stdin, "expected": expected})

    judge_mode = payload.get("judge_mode", "tokens")
    if judge_mode not in {"exact", "tokens", "float"}:
        raise RequestError("judge_mode must be exact, tokens, or float")

    return {
        "request_id": str(payload.get("request_id", comment.get("id", "unknown")))[:128],
        "language": language,
        "display": str(languages[language].get("display", language)),
        "candidates": candidates,
        "tests": tests,
        "judge_mode": judge_mode,
        "abs_error": bounded_float(payload.get("abs_error"), "abs_error", 1e-9),
        "rel_error": bounded_float(payload.get("rel_error"), "rel_error", 1e-9),
        "timeout_seconds": bounded_int(
            payload.get("timeout_seconds"),
            "timeout_seconds",
            DEFAULT_TIMEOUT_SECONDS,
            1,
            MAX_TIMEOUT_SECONDS,
        ),
        "memory_mb": bounded_int(
            payload.get("memory_mb"),
            "memory_mb",
            DEFAULT_MEMORY_MB,
            64,
            MAX_MEMORY_MB,
        ),
        "issue_number": int(issue["number"]),
        "repository": str(repository.get("full_name", "")),
        "owner": owner,
    }


def set_capture_limit() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_CAPTURE_BYTES, MAX_CAPTURE_BYTES))


def read_capture(path: Path) -> tuple[bytes, bool]:
    data = path.read_bytes() if path.exists() else b""
    truncated = len(data) >= MAX_CAPTURE_BYTES
    return data[:MAX_CAPTURE_BYTES], truncated


def run_command(command: list[str], *, stdin: bytes, timeout: int, cleanup_name: str | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="codegolf-capture-") as capture_dir:
        stdout_path = Path(capture_dir) / "stdout"
        stderr_path = Path(capture_dir) / "stderr"
        started = time.monotonic()
        timed_out = False
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=stdout_file,
                stderr=stderr_file,
                preexec_fn=set_capture_limit,
            )
            try:
                process.communicate(stdin, timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                process.wait()
            finally:
                if cleanup_name:
                    subprocess.run(
                        ["docker", "rm", "-f", cleanup_name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        timeout=15,
                    )
        elapsed = time.monotonic() - started
        stdout, stdout_truncated = read_capture(stdout_path)
        stderr, stderr_truncated = read_capture(stderr_path)
        return {
            "exit_code": 124 if timed_out else process.returncode,
            "timed_out": timed_out,
            "elapsed": elapsed,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }


def compare_float_tokens(actual: bytes, expected: bytes, abs_error: float, rel_error: float) -> bool:
    actual_tokens = actual.split()
    expected_tokens = expected.split()
    if len(actual_tokens) != len(expected_tokens):
        return False
    for actual_token, expected_token in zip(actual_tokens, expected_tokens):
        try:
            actual_value = float(actual_token)
            expected_value = float(expected_token)
        except ValueError:
            if actual_token != expected_token:
                return False
            continue
        if not math.isfinite(actual_value) or not math.isfinite(expected_value):
            if actual_token != expected_token:
                return False
            continue
        if abs(actual_value - expected_value) > max(abs_error, rel_error * abs(expected_value)):
            return False
    return True


def judge(actual: bytes, expected: bytes | None, request: dict[str, Any]) -> str:
    if expected is None:
        return "RUN"
    mode = request["judge_mode"]
    if mode == "exact":
        passed = actual == expected
    elif mode == "tokens":
        passed = actual.split() == expected.split()
    else:
        passed = compare_float_tokens(actual, expected, request["abs_error"], request["rel_error"])
    return "PASS" if passed else "FAIL"


def pull_image(image: str) -> tuple[str, str]:
    completed = subprocess.run(
        ["docker", "pull", image],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=600,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"docker pull failed ({completed.returncode}):\n{completed.stdout[-8000:]}")
    inspected = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{join .RepoDigests \",\"}}", image],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    digest = inspected.stdout.strip() if inspected.returncode == 0 else "unavailable"
    return completed.stdout[-4000:], digest or "unavailable"


def execute_request(request: dict[str, Any]) -> dict[str, Any]:
    image = f"ghcr.io/{request['owner']}/atcoder-codegolf-{request['language']}:2025-10"
    pull_log, image_digest = pull_image(image)
    candidate_reports: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="codegolf-request-") as workspace:
        workspace_path = Path(workspace)
        for candidate_index, candidate in enumerate(request["candidates"]):
            source_path = workspace_path / f"candidate-{candidate_index}"
            source_path.write_bytes(candidate["source"])
            test_reports: list[dict[str, Any]] = []
            for test_index, test in enumerate(request["tests"]):
                container_name = f"codegolf-{uuid.uuid4().hex[:20]}"
                command = [
                    "docker",
                    "run",
                    "--name",
                    container_name,
                    "--rm",
                    "--network",
                    "none",
                    "--memory",
                    f"{request['memory_mb']}m",
                    "--memory-swap",
                    f"{request['memory_mb']}m",
                    "--cpus",
                    CPU_LIMIT,
                    "--pids-limit",
                    PIDS_LIMIT,
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges",
                    "-i",
                    "-v",
                    f"{source_path.resolve()}:/submission:ro",
                    image,
                ]
                result = run_command(
                    command,
                    stdin=test["stdin"],
                    timeout=request["timeout_seconds"],
                    cleanup_name=container_name,
                )
                status = "TIMEOUT" if result["timed_out"] else "RE" if result["exit_code"] != 0 else judge(result["stdout"], test["expected"], request)
                result.update(
                    {
                        "name": test["name"],
                        "status": status,
                        "stdout_sha256": sha256(result["stdout"]),
                        "stderr_sha256": sha256(result["stderr"]),
                    }
                )
                test_reports.append(result)
            candidate_reports.append(
                {
                    "id": candidate["id"],
                    "source_bytes": len(candidate["source"]),
                    "source_sha256": sha256(candidate["source"]),
                    "tests": test_reports,
                }
            )

    return {
        "request": request,
        "image": image,
        "image_digest": image_digest,
        "pull_log": pull_log,
        "candidates": candidate_reports,
    }


def markdown_code(data: bytes, truncated: bool) -> str:
    text = data.decode("utf-8", "backslashreplace").replace("\x00", "\\x00")
    if not text:
        text = "(empty)"
    if truncated:
        text += f"\n[truncated at {MAX_CAPTURE_BYTES} bytes]"
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}"


def make_markdown(report: dict[str, Any]) -> str:
    request = report["request"]
    lines = [
        "## Code-golf execution result",
        "",
        f"- Request: `{request['request_id']}`",
        f"- Language: **{request['display']}** (`{request['language']}`)",
        f"- Image: `{report['image']}`",
        f"- Digest: `{report['image_digest']}`",
        f"- Judge mode: `{request['judge_mode']}`",
        f"- Limits: {request['timeout_seconds']} s/test, {request['memory_mb']} MiB, {CPU_LIMIT} CPUs, {PIDS_LIMIT} processes, network disabled",
        "",
        "| Candidate | UTF-8 bytes | Passed | Failed | Source SHA-256 |",
        "|---|---:|---:|---:|---|",
    ]
    for candidate in report["candidates"]:
        passed = sum(test["status"] in {"PASS", "RUN"} for test in candidate["tests"])
        failed = len(candidate["tests"]) - passed
        lines.append(
            f"| `{candidate['id']}` | {candidate['source_bytes']} | {passed} | {failed} | `{candidate['source_sha256']}` |"
        )

    for candidate in report["candidates"]:
        lines.extend(
            [
                "",
                f"### Candidate `{candidate['id']}`",
                "",
                "| Test | Status | Exit | Time | stdout bytes | stderr bytes |",
                "|---|---|---:|---:|---:|---:|",
            ]
        )
        for test in candidate["tests"]:
            lines.append(
                f"| `{test['name']}` | **{test['status']}** | {test['exit_code']} | {test['elapsed']:.3f}s | {len(test['stdout'])} | {len(test['stderr'])} |"
            )

        details = [test for test in candidate["tests"] if test["status"] not in {"PASS", "RUN"}]
        if not details and len(candidate["tests"]) == 1:
            details = candidate["tests"]
        for test in details[:5]:
            lines.extend(
                [
                    "",
                    f"<details><summary>{test['name']}: {test['status']}</summary>",
                    "",
                    f"stdout SHA-256: `{test['stdout_sha256']}`",
                    "",
                    markdown_code(test["stdout"], test["stdout_truncated"]),
                    "",
                    f"stderr SHA-256: `{test['stderr_sha256']}`",
                    "",
                    markdown_code(test["stderr"], test["stderr_truncated"]),
                    "",
                    "</details>",
                ]
            )

    text = "\n".join(lines) + "\n"
    if len(text) > MAX_COMMENT_CHARS:
        text = text[: MAX_COMMENT_CHARS - 100] + "\n\n[report truncated to fit a GitHub comment]\n"
    return text


def error_markdown(message: str) -> str:
    safe = message.replace("`", "'")
    return f"## Code-golf runner error\n\n```text\n{safe[:20_000]}\n```\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("manifest.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()

    try:
        event = json.loads(args.event.read_text(encoding="utf-8"))
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        request = request_from_event(event, manifest)
        report = execute_request(request)
        args.output.write_text(make_markdown(report), encoding="utf-8")
        if args.report_json:
            serializable = json.loads(json.dumps(report, default=lambda value: base64.b64encode(value).decode() if isinstance(value, bytes) else str(value)))
            args.report_json.write_text(json.dumps(serializable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    except Exception as exc:  # Always leave a useful issue comment.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(error_markdown(f"{type(exc).__name__}: {exc}"), encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
