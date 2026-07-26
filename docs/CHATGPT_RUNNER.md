# ChatGPT code-golf execution runner

This repository can use one owner-controlled GitHub issue as a remote execution queue for ChatGPT-assisted code-golf verification. GitHub Actions pulls the pinned GHCR toolchain image, restores candidate source bytes from Base64, compiles or checks the source through the image entrypoint, executes tests without network access, and posts the result back to the issue.

## One-time setup

1. Ensure the required language image already exists in GHCR.
2. Create one open issue in this repository with the exact title:

   ```text
   ChatGPT code-golf execution queue
   ```

   The issue must be created by the repository owner. Keep it open and use it only for runner requests and results.
3. In the repository settings, leave **Actions → General → Workflow permissions** able to write issues. The workflow declares `issues: write`, `packages: read`, and `contents: read`.
4. If GHCR returns `403` or `pull access denied`, open the package settings and grant this repository Actions access to that package.

The workflow accepts only newly created comments satisfying all of these conditions:

- the target is an issue, not a pull request;
- the issue title exactly matches the queue title;
- the issue was created by the repository owner;
- the comment was created by the repository owner;
- the comment begins with `/run`.

## Request format

Post `/run` followed by a JSON object. An optional Markdown code fence around the JSON is accepted.

```text
/run
{
  "request_id": "awk-smoke-1",
  "language": "awk",
  "candidates": [
    {
      "id": "a",
      "source_base64": "e3ByaW50ICQxfQ=="
    }
  ],
  "tests": [
    {
      "name": "basic",
      "stdin_base64": "MTIzCg==",
      "expected_base64": "MTIzCg=="
    }
  ],
  "judge_mode": "tokens"
}
```

The example source is `{print $1}` and the test input and expected output are both `123` followed by a newline.

### Required fields

- `language`: a slug from `manifest.json`.
- `candidates`: one or more candidate objects.
  - `id`: a unique identifier containing only ASCII letters, digits, `.`, `_`, or `-`.
  - `source_base64`: Base64-encoded UTF-8 source bytes.
- `tests`: one or more test objects.
  - `name`: a unique identifier with the same restrictions as candidate IDs.
  - `stdin_base64`: Base64-encoded standard input. It may be an empty string.
  - `expected_base64`: optional Base64-encoded expected output.

For a single candidate, `source_base64` may be supplied at the top level instead of `candidates`.

### Optional fields

- `request_id`: shown in the result comment.
- `judge_mode`: `tokens` (default), `exact`, or `float`.
- `abs_error`: non-negative absolute tolerance for `float`; default `1e-9`.
- `rel_error`: non-negative relative tolerance for `float`; default `1e-9`.
- `timeout_seconds`: per-test limit from 1 to 60; default 10.
- `memory_mb`: container memory limit from 64 to 4096; default 2048.

`tokens` compares byte tokens separated by ASCII/Unicode whitespace as interpreted by Python byte splitting. `exact` compares the full output byte sequence. `float` compares numeric tokens with the requested tolerances and requires non-numeric tokens to match exactly.

## Limits and isolation

Each request is limited to:

- 20 candidates;
- 100 tests;
- 1 MiB decoded source per candidate;
- 4 MiB decoded input or expected output per test;
- 256 KiB captured stdout and stderr per run;
- 2 CPUs and 512 processes per container;
- no container network;
- no Linux capabilities;
- `no-new-privileges` enabled;
- one workflow request at a time through a repository-wide concurrency group.

Candidate output is treated as untrusted data and is placed in Markdown code fences. Containers are removed after every test, including timeout cleanup.

## Result interpretation

The issue reply reports:

- language display and slug;
- GHCR image and digest;
- decoded UTF-8 source byte count and SHA-256;
- PASS, FAIL, RE, TIMEOUT, or RUN for each test;
- process exit code and elapsed time;
- captured stdout and stderr for failures, or for a single successful test.

A successful GHCR run is a compatibility test against the stored AtCoder TOML environment. It is not proof that the production AtCoder judge used an identical kernel, CPU, filesystem, or resource configuration.

## ChatGPT connector workflow

A ChatGPT session with access to the repository can:

1. read `manifest.json` and select available language slugs;
2. generate candidate and test byte strings locally;
3. Base64-encode those bytes;
4. add a `/run` comment to the queue issue;
5. read the workflow result comment;
6. revise and submit another batch when necessary.

If the GitHub connector cannot create issue comments, the repository owner must paste the generated `/run` payload into the queue issue manually.
