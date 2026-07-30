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

## 軽量なローカル作業環境

このチェックアウトでは、頻繁に使う処理系だけを `.runtime/`（Git管理外）へ
分離して置けます。現在の構成は A言語、GNU awk、Bash 5.3、
C++23/GCC、GNU dc、Perl、PyPy 3.11-v7.3.20、R 4.5.0、Ruby 3.4.5、
Uiua 0.16.2 をローカルで使い、Codon、cLay、Octaveをリモートへ回します。

```sh
./bootstrap.sh status
./bootstrap.sh bytes challenges/abc468/*/main.*
./bootstrap.sh test uiua challenges/abc468/b/main.ua \
  challenges/abc468/b/cases
```

各処理系をシステム領域へ入れないため、WSLの通常環境を壊さず、`.runtime/`
だけで約500MBに収まります。cLayは巨大な付属ライブラリを入れず、変換器だけを
任意で手元に置き、最終確認にはリモートの正確なイメージを使います。

## 容量を使わずリモートで試す

Dockerや各言語処理系をローカルへ入れず、GitHub Actions上の既存イメージで
実行できます。テストは同じディレクトリに `名前.in` と、必要なら期待出力の
`名前.out` を置きます。

```text
cases/
├── sample.in
├── sample.out
└── edge.in
```

送信内容だけを確認する場合:

```sh
./bootstrap.sh remote-payload awk Main.awk cases
```

認証済みの GitHub CLI から専用Issueへ送信する場合:

```sh
./bootstrap.sh remote awk Main.awk cases
```

第5引数で比較方法を `tokens`（既定）、`exact`、`float` から選べます。
結果は専用Issueへ返信されます。ローカルに増えるのはこの小さなリポジトリと
ソース・テストだけで、言語イメージは増えません。

## Build in GitHub Actions

Open **Actions → Build toolchain image → Run workflow**, select one language, and leave `push_image` enabled to publish:

```text
ghcr.io/mackerel38/atcoder-codegolf-LANGUAGE:2025-10
```

The build workflow is manual by design. Build and publish lightweight languages first; C++23, cLay, Octave, R, and Codon may approach GitHub-hosted runner time or disk limits.

## ChatGPT remote runner

When ChatGPT cannot access Docker directly, `.github/workflows/chatgpt-runner.yml` can execute Base64-preserved candidate sources and tests through the pinned GHCR images. Create one owner-controlled issue titled exactly:

```text
ChatGPT code-golf execution queue
```

Post `/run` JSON requests to that issue. The workflow accepts owner-created requests only, disables container networking, applies CPU, memory, process, capability, and timeout limits, and replies with source byte counts, SHA-256 values, per-test status, stdout, and stderr.

See `docs/CHATGPT_RUNNER.md` for setup, request schema, limits, and result interpretation.

## Validation

`validate.yml` checks the local tooling and fetches every configured TOML file to verify its required metadata. It does not install the toolchains.

Run the remote-runner unit tests with:

```sh
python3 -m unittest discover -s tests -v
```

## Upstream fidelity and limitations

- Installation and execution metadata come from AtCoder's published 2025-10 TOML files.
- The base image is Ubuntu 24.04, matching the package assumptions visible in those recipes.
- AtCoder may update the content behind a TOML URL. The build stores the fetched TOML in `/opt/atcoder-toolchain/source.toml`, but this repository does not yet pin a SHA-256 digest.
- GitHub-hosted runners are not identical to AtCoder judges. CPU features, kernel, limits, and transient download availability can differ.
- A large all-in-one image is intentionally avoided; failures and rebuilds remain isolated by language.

See `docs/PROJECT_INSTRUCTIONS.md` for the recommended ChatGPT project policy.
