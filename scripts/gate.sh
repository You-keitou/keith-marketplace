#!/usr/bin/env bash
# Marketplace quality gate: every skill under skills/* must pass SkillEvaluator Tier 1.
# Keyless profile (no LLM credentials needed). Exit 0 = all skills pass.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
command -v skillevaluator >/dev/null || uv tool install --python 3.13 "skillevaluator[all] @ git+https://github.com/NVIDIA/SkillEvaluator.git"
MIN_SCORE="${MIN_SCORE:-80}"
status=0
for skill in skills/*/; do
  [ -f "$skill/SKILL.md" ] || continue
  echo "== $skill"
  skillevaluator validate "$skill" --checks schema,pii,license,quality,unicode,lint --no-dedup \
    --min-score "$MIN_SCORE" -r cli,json -o reports || status=1
done
exit $status
