#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      if [[ $# -lt 2 ]]; then
        echo "--output requires a directory" >&2
        exit 2
      fi
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: scripts/run_miniclaw_walkthrough.sh [--output DIR]

Runs the MiniClaw learning walkthrough and writes trace/state/report evidence.
EOF
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$ROOT_DIR/walkthrough-output/miniclaw-$(date +%Y%m%d-%H%M%S)"
fi

TMP_DIR="$(mktemp -d)"
WORKSPACE="$TMP_DIR/workspace"
DB="$TMP_DIR/miniclaw.db"
CLI=(python3 "$ROOT_DIR/prototypes/miniclaw_harness/main.py" --db "$DB")
SUBAGENT_CLI=("${CLI[@]}" --runtime subagent --workspace "$WORKSPACE")
SKILL_CLI=("${SUBAGENT_CLI[@]}" --skills-root "$ROOT_DIR/prototypes/minimal_harness_agent/skills")

mkdir -p "$WORKSPACE/tests" "$OUTPUT_DIR"
cat > "$WORKSPACE/README.md" <<'EOF'
# Demo
EOF
cat > "$WORKSPACE/tests/test_smoke.py" <<'EOF'
import unittest

class SmokeTest(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(True)
EOF

latest_task_id() {
  "${CLI[@]}" background-list | awk '{ task_id = $1 } END { sub(/^#/, "", task_id); print task_id }'
}

{
  "${CLI[@]}" send "hello miniclaw"
  "${CLI[@]}" run-once
  "${CLI[@]}" outbox
} > "$OUTPUT_DIR/普通消息.txt" 2>&1

"${SKILL_CLI[@]}" send "subagent-background: analyze repo with repo-reading skill" > "$OUTPUT_DIR/仓库分析-send.txt" 2>&1
"${SKILL_CLI[@]}" run-once > "$OUTPUT_DIR/仓库分析-run.txt" 2>&1
"${CLI[@]}" background-list > "$OUTPUT_DIR/background-list-after-repo.txt" 2>&1
REPO_TASK_ID="$(latest_task_id)"
"${CLI[@]}" trace-show "$REPO_TASK_ID" > "$OUTPUT_DIR/仓库分析-trace.txt" 2>&1
"${CLI[@]}" state-show "$REPO_TASK_ID" > "$OUTPUT_DIR/仓库分析-state.txt" 2>&1
"${CLI[@]}" memory-list repo > "$OUTPUT_DIR/memory.txt" 2>&1

"${SUBAGENT_CLI[@]}" send "subagent-background: codeact count files" > "$OUTPUT_DIR/codeact-send.txt" 2>&1
"${SUBAGENT_CLI[@]}" run-once > "$OUTPUT_DIR/codeact-run.txt" 2>&1
"${CLI[@]}" background-list > "$OUTPUT_DIR/background-list-after-codeact.txt" 2>&1
CODE_TASK_ID="$(latest_task_id)"
"${CLI[@]}" trace-show "$CODE_TASK_ID" > "$OUTPUT_DIR/codeact-trace.txt" 2>&1
"${CLI[@]}" state-show "$CODE_TASK_ID" > "$OUTPUT_DIR/codeact-state.txt" 2>&1

"${SUBAGENT_CLI[@]}" send "subagent-background: run tests with approval" > "$OUTPUT_DIR/approval-send.txt" 2>&1
"${SUBAGENT_CLI[@]}" run-once > "$OUTPUT_DIR/approval-run.txt" 2>&1
"${CLI[@]}" background-list > "$OUTPUT_DIR/background-list-after-approval.txt" 2>&1
APPROVAL_TASK_ID="$(latest_task_id)"
"${SUBAGENT_CLI[@]}" approve-task "$APPROVAL_TASK_ID" > "$OUTPUT_DIR/approval-approve.txt" 2>&1
"${CLI[@]}" trace-show "$APPROVAL_TASK_ID" > "$OUTPUT_DIR/approval-trace.txt" 2>&1

"${CLI[@]}" compact-task "$REPO_TASK_ID" --keep-recent 5 > "$OUTPUT_DIR/compact.txt" 2>&1
"${CLI[@]}" trace-show "$REPO_TASK_ID" > "$OUTPUT_DIR/compact-trace.txt" 2>&1
"${CLI[@]}" state-show "$REPO_TASK_ID" > "$OUTPUT_DIR/compact-state.txt" 2>&1
"${CLI[@]}" task-report "$REPO_TASK_ID" > "$OUTPUT_DIR/task-report.md" 2>&1

cat > "$OUTPUT_DIR/summary.md" <<EOF
# MiniClaw Walkthrough Evidence

- Workspace: \`$WORKSPACE\`
- Database: \`$DB\`
- Repo analysis task: \`$REPO_TASK_ID\`
- CodeAct task: \`$CODE_TASK_ID\`
- Approval task: \`$APPROVAL_TASK_ID\`

## Evidence Files

- \`普通消息.txt\`: local channel, store, orchestrator, runtime, output router.
- \`仓库分析-trace.txt\`: SubAgent Agent Loop, Skill loading, FileTool, BashTool.
- \`仓库分析-state.txt\`: structured task state for context recovery.
- \`memory.txt\`: long-term memory entry from completed repository analysis.
- \`codeact-trace.txt\` and \`codeact-state.txt\`: restricted CodeAct execution evidence.
- \`approval-trace.txt\`: human approval request, approval event, and resumed execution.
- \`compact-trace.txt\` and \`compact-state.txt\`: compacted trace plus durable summary.
- \`task-report.md\`: Markdown report for article or review notes.
EOF

echo "MiniClaw walkthrough complete."
echo "Output: $OUTPUT_DIR"
