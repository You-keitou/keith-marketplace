#!/usr/bin/env bash
# Sakana AI Namazu を reader として使う（claude -p の代替）。Responses API 経由。
# usage: reader-sakana.sh <file> <prompt-file>
set -euo pipefail
FILE="$1"; PROMPT_FILE="$2"

KEY="${SAKANA_AI_API_KEY:-}"
if [ -z "$KEY" ]; then
  KEY="$(aws ssm get-parameter --name /develop/SAKANA_AI_API_KEY --with-decryption \
    --query Parameter.Value --output text \
    --profile "${AWS_PROFILE:-jinyang}" --region "${AWS_REGION:-ap-northeast-1}" 2>/dev/null)" || true
fi
[ -n "$KEY" ] || { echo "(sakana reader をスキップ: SAKANA_AI_API_KEY を取得できません。env か AWS SSM /develop/SAKANA_AI_API_KEY を確認してください)"; exit 0; }

jq -n --rawfile instructions "$PROMPT_FILE" --rawfile input "$FILE" \
  '{model: "sakana-namazu", instructions: $instructions, input: $input}' \
| curl -sS https://api.sakana.ai/v1/responses \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d @- \
| jq -r '
    if .error then "(sakana reader エラー: " + (.error.message // (.error | tostring)) + ")"
    else ([.output[]? | select(.type == "message") | .content[]? | select(.type == "output_text") | .text] | join("\n")) as $t
      | if $t == "" then "(応答なし)" else $t end
    end'
