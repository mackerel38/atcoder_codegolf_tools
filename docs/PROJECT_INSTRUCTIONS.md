# ChatGPT project instructions

Use `mackerel38/atcoder_codegolf_tools` as the canonical toolchain registry.

1. Read `manifest.json` before selecting a special language runtime.
2. Use only the language slugs listed there.
3. Check whether Docker is already available. Never install Docker, compilers, packages, or alternate runtimes merely to use this repository.
4. When Docker is available, prefer the pinned GHCR image and run it through `bootstrap.sh`.
5. When Docker is unavailable, use the owner-controlled GitHub Actions execution queue documented in `docs/CHATGPT_RUNNER.md`.
6. Post runner requests only to the issue titled exactly `ChatGPT code-golf execution queue`, created by the repository owner.
7. Preserve candidate source, test input, and expected output as Base64. Measure the decoded source with UTF-8 byte length, not character count.
8. Batch multiple candidates and tests into one request when practical.
9. Use `tokens` for ordinary whitespace-token comparison, `exact` for strict output, and `float` only with explicit tolerances appropriate to the problem.
10. Treat PASS as compatibility-tested in the pinned GHCR image, not as proof of execution on the production AtCoder judge.
11. If an image is unavailable, Docker is absent, or the remote runner cannot be triggered, stop after one failed availability check and classify that language as unavailable for execution.
12. Do not substitute another language version without explicitly classifying the candidate as compatibility-tested or untested.
13. The AtCoder TOML URL is the source of truth for filename, installation, compile/check command, runtime environment, and execution command.
14. Preserve raw stdout and stderr when checking scientific notation, decorations, whitespace behavior, and negative-number formatting.
