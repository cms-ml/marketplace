#!/usr/bin/env bash
cd "<REPO>/validation/abcd/run3/ws_skill"
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
date -u +%FT%TZ > logs_agent_start.txt
"claude" -p --agent cms:cms-analysis-coder --model sonnet \
  --setting-sources project --plugin-dir <REPO>/plugins/cms --plugin-dir <REPO>/plugins/af-fnal-lpc --plugin-dir <REPO>/plugins/hep-python-tools --plugin-dir <REPO>/plugins/background-est --strict-mcp-config \
  --permission-mode acceptEdits \
  --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
  --disallowedTools "WebFetch WebSearch" \
  --output-format stream-json --verbose \
  < TASK.md > transcript.jsonl 2> agent_stderr.log
echo "EXIT $?" > AGENT_DONE
date -u +%FT%TZ >> AGENT_DONE
