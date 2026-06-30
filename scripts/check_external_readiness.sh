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

credential_helper="$(git config --get credential.helper 2>/dev/null || true)"
if [[ -z "$credential_helper" ]]; then
  credential_helper="missing"
fi

credential_helper_available="unknown"
if [[ "$credential_helper" == "missing" ]]; then
  credential_helper_available="missing"
elif command -v "git-credential-${credential_helper}" >/dev/null 2>&1; then
  credential_helper_available="available"
else
  credential_helper_available="missing"
fi

ssh_github_auth="unknown"
ssh_output="$(ssh -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new git@github.com 2>&1 || true)"
if [[ "$ssh_output" == *"successfully authenticated"* ]]; then
  ssh_github_auth="available"
elif [[ "$ssh_output" == *"Permission denied"* ]]; then
  ssh_github_auth="denied"
else
  ssh_github_auth="unknown"
fi

credential_action=""
if [[ "$remote" == https://github.com/* && "$credential_helper_available" != "available" ]]; then
  credential_action="- Fix git credential helper or switch to SSH before pushing."
fi

ssh_action=""
if [[ "$ssh_github_auth" == "denied" ]]; then
  ssh_action="- Authorize an SSH key with GitHub if using SSH remote."
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
credential_helper: $credential_helper
credential_helper_available: $credential_helper_available
ssh_github_auth: $ssh_github_auth

next_actions:
- Run scripts/verify_offline.sh before pushing.
- If openai_api_key is set, run scripts/verify_real_model.sh.
$credential_action
$ssh_action
- If working_tree is clean and behind_origin is 0, push with git push origin ${branch:-main}.
EOF
