#!/usr/bin/env bash
# Follow-ups after run_students.sh and run_validator.sh: resumed with-skill student adds plots
# (STUDENT_PLOTS_PROMPT.md) -> resumed validator adds CMS-comparison plots (VALIDATOR_PLOTS_PROMPT.md) -> README/PUSH.
# Usage: bash run_followups.sh   (in tmux)
set -uo pipefail
V=$(realpath "$(dirname "$0")"); REPO=$(realpath "$V/../.."); A=$V/ws_skill; OUT=$V/cms-comparison
CLAUDE=${CLAUDE:-$(command -v claude || echo ~/.local/bin/claude)}
COMMON=(--setting-sources project --strict-mcp-config --permission-mode acceptEdits
        --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" --output-format stream-json --verbose)
sid() { head -c 4000 "$1" | grep -o '"session_id":"[^"]*"' | head -1 | cut -d'"' -f4; }
log() { echo "$(date -u +%FT%TZ) $*" >> "$V/followups.log"; }

# 1. the same with-skill student, resumed in its own workspace
if [ ! -f "$A/PLOTS_DONE" ]; then
  log "student start"
  sed -n '/^## Task/,$p' "$V/STUDENT_PLOTS_PROMPT.md" | tail -n +2 > "$A/TASK_PLOTS.md"
  cd "$A"
  "$CLAUDE" -p --resume "$(sid "$A/transcript.jsonl")" --agent cms:cms-analysis-coder --model sonnet "${COMMON[@]}" \
    --plugin-dir "$REPO/plugins/cms" --plugin-dir "$REPO/plugins/af-fnal-lpc" --plugin-dir "$REPO/plugins/hep-python-tools" \
    --plugin-dir "$REPO/plugins/background-est" --disallowedTools "WebFetch WebSearch" \
    < TASK_PLOTS.md > transcript_plots.jsonl 2> stderr_plots.log
  log "student exit $?"
fi
# 2. the same validator, resumed from the repo root
if [ ! -f "$OUT/PLOTS_DONE" ]; then
  log "validator start"
  sed -n '/^## Task/,$p' "$V/VALIDATOR_PLOTS_PROMPT.md" | tail -n +2 | sed "s#<OUT>#$OUT#g; s#<A>#$A#g" > "$OUT/TASK_PLOTS.md"
  cd "$REPO"
  "$CLAUDE" -p --resume "$(sid "$OUT/transcript.jsonl")" --agent cms:cms-results-validator --model opus "${COMMON[@]}" \
    --plugin-dir "$REPO/plugins/cms" < "$OUT/TASK_PLOTS.md" > "$OUT/transcript_plots.jsonl" 2> "$OUT/stderr_plots.log"
  log "validator exit $?"
fi
# 3. README / PUSH (fresh Sonnet)
rm -f "$V/README_DONE"
sed -n '/^## Task/,$p' "$V/README_PROMPT.md" | tail -n +2 | sed "s#<REPO>#$REPO#g" > "$V/README_TASK.md"
cd "$REPO"; log "readme start"
"$CLAUDE" -p --model sonnet "${COMMON[@]}" --plugin-dir "$REPO/plugins/cms" --disallowedTools "WebFetch WebSearch" \
  < "$V/README_TASK.md" > "$V/readme_transcript.jsonl" 2> "$V/readme_stderr.log"
log "readme exit $?"; echo done > "$V/FOLLOWUPS_DONE"
