#!/usr/bin/env bash
cd <REPO>/validation/abcd/ws_noskill
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
date -u +%FT%TZ >> logs_agent_resume_node.txt
"claude" -p --resume f86c89fa-4523-4612-8892-cb1eef8e4f51 --agent cms:cms-analysis-coder --model sonnet --setting-sources project --plugin-dir <REPO>/plugins/cms --plugin-dir <REPO>/plugins/af-fnal-lpc --plugin-dir <REPO>/plugins/hep-python-tools --strict-mcp-config \
  --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" --disallowedTools "WebFetch WebSearch" \
  --output-format stream-json --verbose < <TESTS>/RESUME_NOTE.md >> transcript.jsonl 2>> agent_stderr.log
echo "EXIT $?" > AGENT_DONE; date -u +%FT%TZ >> AGENT_DONE
