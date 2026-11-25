#!/usr/bin/env bash
cd /uscms/home/ashrivas/nobackup/AGENTS-AI/tests/abcd_official_run3/ws_noskill
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
date -u +%FT%TZ >> logs_agent_resume_node.txt
"/uscms/home/ashrivas/.local/bin/claude" -p --resume f86c89fa-4523-4612-8892-cb1eef8e4f51 --agent cms:cms-analysis-coder --model sonnet --setting-sources project --plugin-dir /uscms/home/ashrivas/nobackup/AGENTS-AI/cms/marketplace/plugins/cms --plugin-dir /uscms/home/ashrivas/nobackup/AGENTS-AI/cms/marketplace/plugins/af-fnal-lpc --plugin-dir /uscms/home/ashrivas/nobackup/AGENTS-AI/cms/marketplace/plugins/hep-python-tools --strict-mcp-config \
  --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" --disallowedTools "WebFetch WebSearch" \
  --output-format stream-json --verbose < /uscms/home/ashrivas/nobackup/AGENTS-AI/tests/RESUME_NOTE.md >> transcript.jsonl 2>> agent_stderr.log
echo "EXIT $?" > AGENT_DONE; date -u +%FT%TZ >> AGENT_DONE
