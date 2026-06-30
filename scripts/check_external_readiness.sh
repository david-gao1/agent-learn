#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

branch="$(git branch --show-current 2>/dev/null || true)"
remote="$(git config --get remote.origin.url 2>/dev/null || true)"
status="$(git status --short 2>/dev/null || true)"

ahead="unknown"
behind="unknown"
if git rev-parse --verify origin/main >/dev/null 2>&1; then
  counts="$(git rev-list --left-right --count origin/main...HEAD)"
  behind="${counts%%[[:space:]]*}"
  ahead="${counts##*[[:space:]]}"
fi

if [[ -z "$status" ]]; then
  working_tree="clean"
else
  working_tree="dirty"
fi

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  openai_api_key="set"
else
  openai_api_key="missing"
fi

if [[ -x "$ROOT_DIR/scripts/verify_offline.sh" ]]; then
  offline_verifier="available"
else
  offline_verifier="missing"
fi

cat <<EOF
# External Readiness

branch: ${branch:-unknown}
remote: ${remote:-missing}
working_tree: $working_tree
behind_origin: $behind
ahead_of_origin: $ahead
openai_api_key: $openai_api_key
offline_verifier: $offline_verifier

next_actions:
- Run scripts/verify_offline.sh before pushing.
- If openai_api_key is set, run scripts/verify_real_model.sh.
- If working_tree is clean and behind_origin is 0, push with git push origin ${branch:-main}.
EOF
