#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).parents[1] / "tools" / "chatgpt_runner.py"
SPEC = importlib.util.spec_from_file_location("chatgpt_runner", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = {"languages": {"awk": {"display": "AWK"}}}
        self.event = {
            "repository": {
                "full_name": "mackerel38/atcoder_codegolf_tools",
                "owner": {"login": "mackerel38"},
            },
            "issue": {
                "number": 1,
                "title": runner.QUEUE_TITLE,
                "user": {"login": "mackerel38"},
            },
            "comment": {
                "id": 123,
                "user": {"login": "mackerel38"},
                "body": "/run\n" + json.dumps(
                    {
                        "language": "awk",
                        "candidates": [{"id": "a", "source_base64": b64(b"{print $1}")}],
                        "tests": [
                            {
                                "name": "sample",
                                "stdin_base64": b64(b"123\n"),
                                "expected_base64": b64(b"123\n"),
                            }
                        ],
                    }
                ),
            },
        }

    def test_request_parsing(self) -> None:
        request = runner.request_from_event(self.event, self.manifest)
        self.assertEqual(request["language"], "awk")
        self.assertEqual(request["candidates"][0]["source"], b"{print $1}")
        self.assertEqual(request["tests"][0]["stdin"], b"123\n")

    def test_owner_only(self) -> None:
        self.event["comment"]["user"]["login"] = "someone-else"
        with self.assertRaises(runner.RequestError):
            runner.request_from_event(self.event, self.manifest)

    def test_tokens_judge(self) -> None:
        request = {"judge_mode": "tokens", "abs_error": 0.0, "rel_error": 0.0}
        self.assertEqual(runner.judge(b"1  2\n", b"1\n2", request), "PASS")

    def test_exact_judge(self) -> None:
        request = {"judge_mode": "exact", "abs_error": 0.0, "rel_error": 0.0}
        self.assertEqual(runner.judge(b"1\n", b"1", request), "FAIL")

    def test_float_judge(self) -> None:
        request = {"judge_mode": "float", "abs_error": 1e-6, "rel_error": 1e-6}
        self.assertEqual(runner.judge(b"1.0000001", b"1", request), "PASS")


if __name__ == "__main__":
    unittest.main()
