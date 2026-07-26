# atcoder_codegolf_tools

Reproducible, language-specific Docker images for AtCoder code-golf verification. The repository consumes AtCoder's 2025-10 language TOML files directly rather than maintaining independent installation recipes.

## Included toolchains

APL, GNU awk, A言語, Bash, C++23/GCC 15.2.0, cLay, dc, Octave, Perl, PyPy 3.11-v7.3.20, R, Ruby 3.4.5, Uiua, and Codon 0.19.3.

Ruby means the standard Ruby 3.4 entry. TruffleRuby is intentionally not included.

## Design

Each image is built independently from `ubuntu:24.04`. `tools/spec.py` downloads the selected AtCoder TOML file, validates it, stores a copy in the image, and executes its `install` field. `tools/run_submission.py` then uses the same TOML metadata for the source filename, compile/check command, runtime environment, and execution command.

No toolchain image is built automatically on ordinary pushes or pull requests. Some upstream recipes, especially C++23 and cLay, build large compiler/library stacks and can consume substantial runner time and storage.

## Build an image locally

Docker must already be installed.

```sh
./bootstrap.sh list
./bootstrap.sh build uiua
```

## Run a submission

```sh
./bootstrap.sh run uiua Main.ua input.txt
./bootstrap.sh run awk Main.awk input.txt
```

The container is run with networking disabled. The source is mounted read-only and standard input is forwarded from the optional input file or the terminal.

## Build in GitHub Actions

Open **Actions → Build toolchain image → Run workflow**, select one language, and leave `push_image` enabled to publish:

```text
ghcr.io/mackerel38/atcoder-codegolf-LANGUAGE:2025-10
```

The build workflow is manual by design. Build and publish lightweight languages first; C++23, cLay, Octave, R, and Codon may approach GitHub-hosted runner time or disk limits.

## Validation

`validate.yml` checks the local tooling and fetches every configured TOML file to verify its required metadata. It does not install the toolchains.

## Upstream fidelity and limitations

- Installation and execution metadata come from AtCoder's published 2025-10 TOML files.
- The base image is Ubuntu 24.04, matching the package assumptions visible in those recipes.
- AtCoder may update the content behind a TOML URL. The build stores the fetched TOML in `/opt/atcoder-toolchain/source.toml`, but this repository does not yet pin a SHA-256 digest.
- GitHub-hosted runners are not identical to AtCoder judges. CPU features, kernel, limits, and transient download availability can differ.
- A large all-in-one image is intentionally avoided; failures and rebuilds remain isolated by language.

See `docs/PROJECT_INSTRUCTIONS.md` for the recommended ChatGPT project policy.
