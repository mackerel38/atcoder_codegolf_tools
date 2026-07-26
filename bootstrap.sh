#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

usage() {
  cat <<'EOF'
Usage:
  ./bootstrap.sh list
  ./bootstrap.sh build LANGUAGE
  ./bootstrap.sh pull LANGUAGE
  ./bootstrap.sh run LANGUAGE SOURCE [INPUT]

The run command requires Docker. It never installs Docker or another runtime.
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
  *) usage; exit 2;;
esac
