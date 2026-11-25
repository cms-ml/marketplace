#!/usr/bin/env python3
"""Audit the student transcripts: skills loaded, and any file access outside the workspace.

Usage: python3 audit_reads.py <tests_dir>   (reads <tests_dir>/ws_*/transcript.jsonl)
Prints, per run: skills invoked, tool-call counts, and every path outside the
workspace, /cvmfs, /tmp, EOS and the background-est skill directory that a
tool call touched. Exit 1 if the run without the skill touched ABCD
skill files or earlier test directories.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ALLOWED = ("/cvmfs/", "/tmp/", "/dev/", "/proc/", "/usr/", "/etc/", "/bin/", "/store/", "root://", "/eos/")
PATH_RE = re.compile(r"(/(?:uscms|uscms_data|uscmst1b_scratch|eos|store|tmp|cvmfs|home)[^\s'\"`;|&><)]*)")


def calls(path):
    for line in path.open():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        if m.get("type") != "assistant":
            continue
        for c in m.get("message", {}).get("content", []):
            if c.get("type") == "tool_use":
                yield c["name"], c.get("input", {})


def main(tests):
    bad = False
    for ws in sorted(Path(tests).glob("ws_*")):
        t = ws / "transcript.jsonl"
        if not t.exists():
            print(f"{ws.name}: no transcript")
            continue
        wsr = str(ws.resolve())
        alts = {wsr, wsr.replace("/uscms_data/d3/", "/uscms/home/").replace("/ashrivas/", "/ashrivas/nobackup/", 1),
                str(ws)}
        n, skills, outside = Counter(), [], Counter()
        for name, inp in calls(t):
            n[name] += 1
            if name == "Skill":
                skills.append(inp.get("skill"))
            text = " ".join(str(v) for v in inp.values())
            for p in PATH_RE.findall(text):
                p = p.rstrip(".,:")
                if any(p.startswith(a) for a in alts) or p.startswith(ALLOWED):
                    continue
                outside[p] += 1
        print(f"== {ws.name}: tool calls {dict(n)}")
        print(f"   skills invoked: {skills}")
        for p, k in outside.most_common():
            flag = ""
            if "abcd" in p or "rhalphabet" in p or "background-est" in p or "/tests/" in p:
                flag = "   <-- SKILL/TEST PATH"
                if ws.name == "ws_noskill":
                    bad = True
            print(f"   outside: {p} (x{k}){flag}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
