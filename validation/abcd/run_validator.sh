#!/usr/bin/env bash
# Wait for both student runs, audit their reads, then run the cms-results-validator (opus) per CMS_COMPARISON_PROMPT.md (ABCD vs EXO-17-021).
# Usage: bash run_validator.sh [tests_dir (default: this directory)] [out_dir_name (default cms-comparison)]
set -uo pipefail
TESTS=$(realpath "${1:-$(dirname "$0")}")
REPO=$(realpath "$(dirname "$0")/../..")
OUT=$REPO/validation/abcd/${2:-cms-comparison}
CLAUDE=${CLAUDE:-$(command -v claude || echo "$(ls -d ~/nobackup/.vscode-server/extensions/anthropic.claude-code-*-linux-x64 | sort -V | tail -1)/resources/native-binary/claude")}
until [ -f "$TESTS/ws_skill/AGENT_DONE" ] && [ -f "$TESTS/ws_noskill/AGENT_DONE" ]; do sleep 300; done
mkdir -p "$OUT"
python3 "$REPO/validation/abcd/audit_reads.py" "$TESTS" > "$OUT/audit_reads.txt" 2>&1
echo "audit exit $?" >> "$OUT/audit_reads.txt"
sed -n '/^## Task/,$p' "$REPO/validation/abcd/CMS_COMPARISON_PROMPT.md" | tail -n +2 | \
  sed "s#<TESTS>#$TESTS#g; s#<OUT>#$OUT#g" > "$OUT/TASK.md"
cd "$REPO"
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
date -u +%FT%TZ > "$OUT/validator_start.txt"
"$CLAUDE" -p --agent cms:cms-results-validator --model opus --setting-sources project \
  --plugin-dir "$REPO/plugins/cms" --strict-mcp-config --permission-mode acceptEdits \
  --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
  --output-format stream-json --verbose < "$OUT/TASK.md" > "$OUT/transcript.jsonl" 2> "$OUT/validator_stderr.log"
echo "EXIT $?" > "$OUT/VALIDATOR_DONE"; date -u +%FT%TZ >> "$OUT/VALIDATOR_DONE"
