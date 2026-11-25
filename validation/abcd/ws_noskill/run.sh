#!/usr/bin/env bash
cd "/uscms_data/d3/ashrivas/AGENTS-AI/tests/abcd_official_run3/ws_noskill"
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
date -u +%FT%TZ > logs_agent_start.txt
"/uscms/home/ashrivas/.local/bin/claude" -p --agent cms:cms-analysis-coder --model sonnet \
  --setting-sources project --plugin-dir /uscms_data/d3/ashrivas/AGENTS-AI/cms/marketplace/plugins/cms --plugin-dir /uscms_data/d3/ashrivas/AGENTS-AI/cms/marketplace/plugins/af-fnal-lpc --plugin-dir /uscms_data/d3/ashrivas/AGENTS-AI/cms/marketplace/plugins/hep-python-tools --strict-mcp-config \
  --permission-mode acceptEdits \
  --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
  --disallowedTools "WebFetch WebSearch" \
  --output-format stream-json --verbose \
  < TASK.md > transcript.jsonl 2> agent_stderr.log
echo "EXIT $?" > AGENT_DONE
date -u +%FT%TZ >> AGENT_DONE
