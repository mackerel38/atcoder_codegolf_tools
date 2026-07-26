# ChatGPT project instructions

Use `mackerel38/atcoder_codegolf_tools` as the canonical toolchain registry.

1. Read `manifest.json` before selecting a special language runtime.
2. Use only the language slugs listed there.
3. Check whether Docker is already available. Never install Docker, compilers, packages, or alternate runtimes merely to use this repository.
4. When Docker is available, prefer the pinned GHCR image and run it through `bootstrap.sh`.
5. If an image is unavailable or Docker is absent, stop after one failed availability check and treat that language as unavailable for execution.
6. Do not substitute a different language version without explicitly classifying the candidate as compatibility-tested or untested.
7. The AtCoder TOML URL is the source of truth for filename, installation, compile/check command, runtime environment, and execution command.
8. A successful container run is still a compatibility test, not proof that AtCoder itself used the identical host kernel, CPU, or resource limits.
