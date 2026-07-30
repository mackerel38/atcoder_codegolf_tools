#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

usage() {
  cat <<'EOF'
Usage:
  ./bootstrap.sh list
  ./bootstrap.sh status
  ./bootstrap.sh bytes SOURCE...
  ./bootstrap.sh test LANGUAGE SOURCE CASES_DIR [MODE]
  ./bootstrap.sh build LANGUAGE
  ./bootstrap.sh pull LANGUAGE
  ./bootstrap.sh run LANGUAGE SOURCE [INPUT]
  ./bootstrap.sh remote-payload LANGUAGE SOURCE CASES_DIR [MODE]
  ./bootstrap.sh remote LANGUAGE SOURCE CASES_DIR [MODE]

The run command requires Docker. The remote commands require Python 3; posting
also requires an authenticated GitHub CLI. These commands never install runtimes.
EOF
}

query() {
  python3 tools/manifest_query.py "$1"
}

image() {
  printf 'ghcr.io/mackerel38/atcoder-codegolf-%s:2025-10\n' "$1"
}

case "${1:-}" in
  list)
    python3 - <<'PY'
import json
m=json.load(open('manifest.json'))
for k,v in m['languages'].items(): print(f"{k:12} {v['display']}")
PY
    ;;
  status)
    python3 tools/golf.py status
    ;;
  bytes)
    shift
    python3 tools/golf.py bytes "$@"
    ;;
  test)
    lang=${2:?language is required}
    source=${3:?source path is required}
    cases=${4:?cases directory is required}
    mode=${5:-tokens}
    python3 tools/golf.py test "$lang" "$source" "$cases" --mode "$mode"
    ;;
  build)
    lang=${2:?language is required}
    eval "$(query "$lang")"
    docker build -f docker/Dockerfile --build-arg "SPEC_URL=$spec_url" -t "$(image "$lang")" .
    ;;
  pull)
    lang=${2:?language is required}
    query "$lang" >/dev/null
    docker pull "$(image "$lang")"
    ;;
  run)
    lang=${2:?language is required}
    source=${3:?source path is required}
    input=${4:-/dev/stdin}
    query "$lang" >/dev/null
    source=$(realpath "$source")
    args=(--rm --network none -i -v "$source:/submission:ro")
    if [[ -f $input ]]; then
      args+=("$(image "$lang")")
      docker run "${args[@]}" < "$input"
    else
      args+=("$(image "$lang")")
      docker run "${args[@]}"
    fi
    ;;
  remote-payload)
    lang=${2:?language is required}
    source=${3:?source path is required}
    cases=${4:?cases directory is required}
    mode=${5:-tokens}
    python3 tools/remote_request.py "$lang" "$source" "$cases" --mode "$mode"
    ;;
  remote)
    lang=${2:?language is required}
    source=${3:?source path is required}
    cases=${4:?cases directory is required}
    mode=${5:-tokens}
    python3 tools/remote_request.py "$lang" "$source" "$cases" \
      --mode "$mode" --post
    ;;
  *) usage; exit 2;;
esac
