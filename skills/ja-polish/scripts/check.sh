#!/usr/bin/env bash
# ja-polish 機械検査: textlint（表記・書式）+ rhythm.py（リズム・定型句）+ Haiku 読者（構成）。
# usage: check.sh <file> [--fix] [--no-reader] [--reader-model <model>]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/ja-polish"
FIX=0; READER=1; MODEL="haiku"; FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --fix) FIX=1 ;;
    --no-reader) READER=0 ;;
    --reader-model) MODEL="$2"; shift ;;
    *) FILE="$1" ;;
  esac; shift
done
[ -f "$FILE" ] || { echo "usage: check.sh <file> [--fix] [--no-reader] [--reader-model <model>]" >&2; exit 2; }
FILE="$(cd "$(dirname "$FILE")" && pwd)/$(basename "$FILE")"

# 1. textlint（初回だけ ~/.cache/ja-polish に npm install、以後はオフライン）
if [ ! -x "$CACHE/node_modules/.bin/textlint" ]; then
  echo "== textlint を $CACHE に導入中（初回のみ）" >&2
  mkdir -p "$CACHE" && cd "$CACHE"
  [ -f package.json ] || npm init -y >/dev/null
  npm i --no-audit --no-fund --silent textlint textlint-rule-preset-ja-technical-writing \
    textlint-rule-preset-ja-spacing textlint-rule-prh @textlint-ja/textlint-rule-preset-ai-writing
fi
cp "$HERE/textlintrc.json" "$HERE/prh-hiraku.yml" "$CACHE/"
echo "== textlint（表記・書式）"
cd "$CACHE"
if [ "$FIX" = 1 ]; then ./node_modules/.bin/textlint -c textlintrc.json --fix "$FILE" || true; fi
./node_modules/.bin/textlint -c textlintrc.json "$FILE" 2>&1 | grep -v '^解説:' || true

# 2. リズム・定型句
echo; echo "== rhythm（リズム・定型句）"
python3 "$HERE/rhythm.py" "$FILE"

# 3. Haiku 読者（tool/MCP/設定を全部剥がした素の一読者）
if [ "$READER" = 1 ] && command -v claude >/dev/null; then
  echo; echo "== reader（$MODEL による一読者の指摘）"
  claude -p --model "$MODEL" --tools "" --strict-mcp-config --setting-sources "" --no-session-persistence \
    --system-prompt "$(cat "$HERE/reader-prompt.txt")" < "$FILE" 2>/dev/null || echo "(reader をスキップ: claude -p が失敗)"
fi
