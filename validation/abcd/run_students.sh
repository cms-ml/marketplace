#!/usr/bin/env bash
# Start the with-skill and without-skill ABCD student runs in tmux (see PROMPT.md).
# Usage: [RUNS=ws_skill] bash run_students.sh [tests_dir (default: this directory)] [model]
# <tests_dir> must contain shared_inputs/ (INPUTS.md + input files); ws_skill/ and ws_noskill/ are created from it.
set -euo pipefail
: "${SKIM_BASE:?set SKIM_BASE to the xrootd directory holding the skim, see shared_inputs/INPUTS.md}"
TESTS=$(realpath "${1:-$(dirname "$0")}"); MODEL=${2:-sonnet}
REPO=$(realpath "$(dirname "$0")/../..")
CLAUDE=${CLAUDE:-claude}   # path to the Claude Code CLI if it is not on PATH
TASK=$(sed -n '/^## Task/,$p' "$REPO/validation/abcd/PROMPT.md" | tail -n +2)

for RUN in ${RUNS:-ws_skill ws_noskill}; do
  WS=$TESTS/$RUN
  if [ -e "$WS" ]; then echo "$WS exists: remove it first" >&2; exit 1; fi
  mkdir -p "$WS/inputs"
  cp -r "$TESTS"/shared_inputs/. "$WS/inputs/"
  mv "$WS/inputs/INPUTS.md" "$WS/INPUTS.md"
  sed -i "s#<WSNAME>#$RUN#g; s#<USER>#$USER#g" "$WS/INPUTS.md"
  sed -i "s#\${SKIM_BASE}#$SKIM_BASE#g" "$WS"/inputs/skim_files/*.txt
  PLUGINS=(--plugin-dir "$REPO/plugins/cms" --plugin-dir "$REPO/plugins/af-fnal-lpc" --plugin-dir "$REPO/plugins/hep-python-tools")
  if [ "$RUN" = ws_skill ]; then
    PLUGINS+=(--plugin-dir "$REPO/plugins/background-est")
    printf '%s\n' "$TASK" | sed 's/^\[with skill only\] //' > "$WS/TASK.md"
  else
    printf '%s\n' "$TASK" | grep -v '^\[with skill only\]' > "$WS/TASK.md"
  fi
  sed -i "s#<WS>#$WS#g" "$WS/TASK.md"
  cat > "$WS/run.sh" <<EOS
#!/usr/bin/env bash
cd "$WS"
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
date -u +%FT%TZ > logs_agent_start.txt
"$CLAUDE" -p --agent cms:cms-analysis-coder --model $MODEL \\
  --setting-sources project ${PLUGINS[*]} --strict-mcp-config \\
  --permission-mode acceptEdits \\
  --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \\
  --disallowedTools "WebFetch WebSearch" \\
  --output-format stream-json --verbose \\
  < TASK.md > transcript.jsonl 2> agent_stderr.log
echo "EXIT \$?" > AGENT_DONE
date -u +%FT%TZ >> AGENT_DONE
EOS
  chmod +x "$WS/run.sh"
  tmux new-session -d -s "abcd_$RUN" "bash $WS/run.sh"
  echo "started abcd_$RUN in $WS"
done
