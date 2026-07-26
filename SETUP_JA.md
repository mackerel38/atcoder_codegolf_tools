# 適用手順

このディレクトリの内容は `mackerel38/atcoder_codegolf_tools` のルートへ上書きしてください。

## 方法1: ZIPを展開

```sh
cd atcoder_codegolf_tools
unzip -o /path/to/chatgpt-runner-implementation.zip
python3 -m unittest discover -s tests -v
git add .github/workflows/chatgpt-runner.yml tools/chatgpt_runner.py \
  tests/test_chatgpt_runner.py docs/CHATGPT_RUNNER.md \
  docs/PROJECT_INSTRUCTIONS.md README.md
git commit -m 'Add ChatGPT code-golf execution runner'
git push
```

ZIPには説明ファイルとパッチも含まれるため、`git add`には上記6ファイルだけを指定してください。

## 方法2: パッチを適用

リポジトリのルートで次を実行します。

```sh
git apply /path/to/chatgpt-runner.patch
python3 -m unittest discover -s tests -v
git add .github/workflows/chatgpt-runner.yml tools/chatgpt_runner.py \
  tests/test_chatgpt_runner.py docs/CHATGPT_RUNNER.md \
  docs/PROJECT_INSTRUCTIONS.md README.md
git commit -m 'Add ChatGPT code-golf execution runner'
git push
```

## 専用Issue

push後、リポジトリに次のタイトルを完全一致で作成します。

```text
ChatGPT code-golf execution queue
```

Issueの作成者は `mackerel38` である必要があります。Issueは開いたままにしてください。

## スモークテスト

専用Issueへ次のコメントを投稿します。

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

Actionsの `ChatGPT code-golf runner` が起動し、Issueへ `10` bytes、`PASS`、exit code `0` を含む返信が付けば成功です。
