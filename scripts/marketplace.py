#!/usr/bin/env python3
"""Validate and sync the CMS plugin marketplace.

Each plugin's ``.claude-plugin/plugin.json`` is the single source of truth for
its name, description, version and keywords. ``.claude-plugin/marketplace.json``
plugin entries and the generated block of ``README.md`` are derived from it.

Usage:
    python scripts/marketplace.py check                 # validate everything, no writes
    python scripts/marketplace.py sync                  # regenerate marketplace.json + README
    python scripts/marketplace.py bump <plugin> <ver>   # bump a plugin version, then sync
    python scripts/marketplace.py bump marketplace <ver>   # top-level metadata.version

Exit code 0 when clean, 1 when any error is found (warnings do not fail).
Standard library only; runs on Python >= 3.9 (the cmslpc system python).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"
MARKETPLACE_JSON = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"
START_MARKER = "<!-- GENERATED:START -->"
END_MARKER = "<!-- GENERATED:END -->"

# Agent Skills spec (https://agentskills.io/specification) frontmatter fields.
SKILL_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
AGENT_REQUIRED = {"name", "description", "tools", "model"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?$")
LINK_RE = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
SKILL_WARN_LINES = 300
SKILL_MAX_LINES = 500
SUMMARY_MAX = 90


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: Path | str, msg: str) -> None:
        self.errors.append(f"{_rel(where)}: {msg}")

    def warn(self, where: Path | str, msg: str) -> None:
        self.warnings.append(f"{_rel(where)}: {msg}")


def _rel(p: Path | str) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------
# Minimal YAML frontmatter parser (scalars, quoted strings, folded/literal
# blocks, one level of lists and maps) -- enough for SKILL.md / agent files.
# ---------------------------------------------------------------------------


def split_frontmatter(text: str) -> tuple[str | None, str]:
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def parse_frontmatter(fm: str) -> dict:
    lines = fm.splitlines()
    out: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            raise ValueError(f"cannot parse frontmatter line: {line!r}")
        key, val = m.group(1), m.group(2).rstrip()
        i += 1
        block: list[str] = []
        while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
            block.append(lines[i])
            i += 1
        while block and not block[-1].strip():
            block.pop()
        if val in (">", ">-", "|", "|-"):
            stripped = [b.strip() for b in block]
            out[key] = ("\n" if val.startswith("|") else " ").join(stripped).strip()
        elif val == "" and block and block[0].strip().startswith("- "):
            out[key] = [_unquote(b.strip()[2:]) for b in block if b.strip()]
        elif val == "" and block:
            if all(re.match(r"^\s+[A-Za-z0-9_-]+:\s", b + " ") for b in block if b.strip()):
                sub = {}
                for b in block:
                    if b.strip():
                        k, _, v = b.strip().partition(":")
                        sub[k.strip()] = _unquote(v)
                out[key] = sub
            else:  # plain multi-line scalar
                out[key] = " ".join(b.strip() for b in block)
        else:
            out[key] = " ".join([_unquote(val)] + [b.strip() for b in block]).strip()
    return out


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@dataclass
class Item:
    name: str
    path: Path
    meta: dict
    body: str


@dataclass
class Plugin:
    name: str
    path: Path
    manifest: dict
    skills: list[Item]
    agents: list[Item]
    mcp: dict


def load_item(path: Path, report: Report) -> Item | None:
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        report.error(path, "missing YAML frontmatter")
        return None
    try:
        meta = parse_frontmatter(fm)
    except ValueError as exc:
        report.error(path, str(exc))
        return None
    name = path.parent.name if path.name == "SKILL.md" else path.stem
    return Item(name=name, path=path, meta=meta, body=body)


def load_plugins(report: Report) -> list[Plugin]:
    plugins = []
    for pdir in sorted(p for p in PLUGINS_DIR.iterdir() if p.is_dir()):
        mpath = pdir / ".claude-plugin" / "plugin.json"
        if not mpath.exists():
            report.error(pdir, "missing .claude-plugin/plugin.json")
            continue
        try:
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.error(mpath, f"invalid JSON: {exc}")
            continue
        skills = []
        sdir = pdir / "skills"
        if sdir.is_dir():
            for d in sorted(x for x in sdir.iterdir() if x.is_dir()):
                if not (d / "SKILL.md").exists():
                    report.error(d, "skill directory has no SKILL.md")
                    continue
                item = load_item(d / "SKILL.md", report)
                if item:
                    skills.append(item)
        agents = []
        adir = pdir / "agents"
        if adir.is_dir():
            for f in sorted(adir.glob("*.md")):
                item = load_item(f, report)
                if item:
                    agents.append(item)
        mcp = {}
        mcp_path = pdir / ".mcp.json"
        if mcp_path.exists():
            try:
                mcp = json.loads(mcp_path.read_text(encoding="utf-8")).get("mcpServers", {})
            except json.JSONDecodeError as exc:
                report.error(mcp_path, f"invalid JSON: {exc}")
        plugins.append(Plugin(pdir.name, pdir, manifest, skills, agents, mcp))
    return plugins


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def check_name(where: Path, name, expected: str, report: Report) -> None:
    if not isinstance(name, str) or not name:
        report.error(where, "frontmatter 'name' is required")
    elif name != expected:
        report.error(where, f"name {name!r} must equal {expected!r}")
    elif len(name) > 64 or not NAME_RE.match(name):
        report.error(where, f"name {name!r} must be <=64 chars of lowercase letters, digits, single hyphens")


def check_description(where: Path, desc, report: Report) -> None:
    if not isinstance(desc, str) or not desc:
        report.error(where, "frontmatter 'description' is required")
        return
    if len(desc) > 1024:
        report.error(where, f"description is {len(desc)} chars (max 1024)")
    if not desc.startswith("Use when"):
        report.error(where, "description must start with 'Use when' (triggering conditions only)")


def check_skill(skill: Item, report: Report) -> None:
    p = skill.path
    unknown = set(skill.meta) - SKILL_KEYS
    if unknown:
        report.error(p, f"unknown frontmatter keys {sorted(unknown)}; use 'metadata:' for extras")
    check_name(p, skill.meta.get("name"), skill.name, report)
    check_description(p, skill.meta.get("description"), report)

    n_lines = len(skill.body.splitlines()) + 4
    if n_lines > SKILL_MAX_LINES:
        report.error(p, f"{n_lines} lines (max {SKILL_MAX_LINES}); move detail into references/")
    elif n_lines > SKILL_WARN_LINES:
        report.warn(p, f"{n_lines} lines (target <= {SKILL_WARN_LINES}); consider references/")

    headings = re.findall(r"^## (.+?)\s*$", skill.body, re.MULTILINE)
    if "Gotchas" not in headings:
        report.error(p, "missing '## Gotchas' section")
    if not headings or headings[-1] != "Docs":
        report.error(p, "'## Docs' must be the last level-2 section")

    # Every relative link must resolve; every bundled file must be linked.
    linked = set()
    for target in sorted(set(LINK_RE.findall(skill.body))):
        if re.match(r"^[a-z]+:", target):
            continue
        resolved = (p.parent / target).resolve()
        linked.add(resolved)
        if not resolved.exists():
            report.error(p, f"broken relative link: {target}")
    for sub in ("references", "assets", "scripts"):
        d = p.parent / sub
        if d.is_dir():
            for f in sorted(d.rglob("*")):
                if f.is_file() and f.resolve() not in linked:
                    report.error(f, "not linked from SKILL.md (unreachable to the model)")
    extra = sorted(
        x.name for x in p.parent.iterdir()
        if x.name not in {"SKILL.md", "references", "assets", "scripts"}
    )
    if extra:
        report.error(p.parent, f"unexpected entries {extra}; use references/, assets/ or scripts/")


def check_agent(agent: Item, report: Report) -> None:
    p = agent.path
    missing = AGENT_REQUIRED - set(agent.meta)
    if missing:
        report.error(p, f"missing frontmatter keys {sorted(missing)}")
    check_name(p, agent.meta.get("name"), agent.name, report)
    check_description(p, agent.meta.get("description"), report)


def check_plugin(plugin: Plugin, report: Report) -> None:
    mpath = plugin.path / ".claude-plugin" / "plugin.json"
    m = plugin.manifest
    if m.get("name") != plugin.name:
        report.error(mpath, f"name {m.get('name')!r} must equal directory name {plugin.name!r}")
    if not m.get("description"):
        report.error(mpath, "description is required")
    if not SEMVER_RE.match(str(m.get("version", ""))):
        report.error(mpath, f"version {m.get('version')!r} is not semver")
    if not plugin.skills and not plugin.agents and not plugin.mcp:
        report.error(plugin.path, "plugin has no skills, agents, or MCP servers")
    for s in plugin.skills:
        check_skill(s, report)
    for a in plugin.agents:
        check_agent(a, report)


def check_unique_names(plugins: list[Plugin], report: Report) -> None:
    seen: dict[str, Path] = {}
    for pl in plugins:
        for item in pl.skills + pl.agents:
            if item.name in seen:
                report.error(item.path, f"name {item.name!r} also used by {_rel(seen[item.name])}")
            seen[item.name] = item.path


# ---------------------------------------------------------------------------
# Generation: marketplace.json + README
# ---------------------------------------------------------------------------


def marketplace_entry(plugin: Plugin) -> dict:
    m = plugin.manifest
    entry = {
        "name": plugin.name,
        "description": m.get("description", ""),
        "version": m.get("version", "0.0.0"),
        "source": f"./plugins/{plugin.name}",
    }
    if m.get("keywords"):
        entry["keywords"] = m["keywords"]
    return entry


def render_marketplace(plugins: list[Plugin]) -> str:
    data = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    data["plugins"] = [marketplace_entry(p) for p in plugins]
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def summarize(meta: dict) -> str:
    """Short README summary: metadata.summary / summary, else the first
    clause of the description with the leading 'Use when' removed."""
    explicit = meta.get("summary") or (meta.get("metadata") or {}).get("summary")
    if explicit:
        return explicit
    desc = re.sub(r"^Use when\s+", "", meta.get("description", "")).strip()
    desc = re.split(r"(?<=[a-z0-9)])[.;:](\s|$)", desc, maxsplit=1)[0]
    desc = desc[:1].upper() + desc[1:]
    if len(desc) > SUMMARY_MAX:
        cut = desc[: SUMMARY_MAX - 1].rsplit(" ", 1)[0].rstrip(",;: ")
        desc = cut + "…"
    return desc


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Column-aligned table, matching prettier's Markdown table formatting."""
    widths = [max(len(r[i]) for r in [headers] + rows) for i in range(len(headers))]
    fmt = lambda cells: "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"  # noqa: E731
    lines = [fmt(headers), "| " + " | ".join("-" * w for w in widths) + " |"]
    lines += [fmt(r) for r in rows]
    return "\n".join(lines)


def render_readme_block(plugins: list[Plugin]) -> str:
    parts = ["## Plugins", ""]
    for i, pl in enumerate(plugins):
        if i:
            parts += ["---", ""]
        parts += [f"### `{pl.name}` (v{pl.manifest.get('version')})", "", pl.manifest.get("description", ""), ""]
        if pl.agents:
            parts += ["**Subagents:**", ""]
            parts += [md_table(["Subagent", "Purpose"], [[f"`{a.name}`", summarize(a.meta)] for a in pl.agents]), ""]
        if pl.skills:
            parts += ["**Skills:**", ""]
            parts += [md_table(["Skill", "Use when"], [[f"`{s.name}`", summarize(s.meta)] for s in pl.skills]), ""]
        if pl.mcp:
            rows = [[f"`{k}`", f"`{v.get('url') or v.get('command', '')}`", v.get("description", "")] for k, v in pl.mcp.items()]
            parts += ["**MCP servers:**", "", md_table(["Server", "Endpoint", "Purpose"], rows), ""]
    return "\n".join(parts).rstrip() + "\n"


def render_readme(plugins: list[Plugin]) -> str:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"README.md is missing {START_MARKER} / {END_MARKER} markers")
    block = f"{START_MARKER}\n\n{render_readme_block(plugins)}\n{END_MARKER}"
    return pattern.sub(lambda _: block, text)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_check() -> int:
    report = Report()
    plugins = load_plugins(report)
    for pl in plugins:
        check_plugin(pl, report)
    check_unique_names(plugins, report)
    if MARKETPLACE_JSON.read_text(encoding="utf-8") != render_marketplace(plugins):
        report.error(MARKETPLACE_JSON, "out of date; run `python scripts/marketplace.py sync`")
    if README.read_text(encoding="utf-8") != render_readme(plugins):
        report.error(README, "generated block out of date; run `python scripts/marketplace.py sync`")
    for w in report.warnings:
        print(f"warning: {w}")
    for e in report.errors:
        print(f"error: {e}")
    n_skills = sum(len(p.skills) for p in plugins)
    n_agents = sum(len(p.agents) for p in plugins)
    status = "FAILED" if report.errors else "OK"
    print(f"{status}: {len(plugins)} plugins, {n_skills} skills, {n_agents} agents, "
          f"{len(report.errors)} errors, {len(report.warnings)} warnings")
    return 1 if report.errors else 0


def cmd_sync() -> int:
    report = Report()
    plugins = load_plugins(report)
    MARKETPLACE_JSON.write_text(render_marketplace(plugins), encoding="utf-8")
    README.write_text(render_readme(plugins), encoding="utf-8")
    print(f"synced {_rel(MARKETPLACE_JSON)} and {_rel(README)}")
    return 0


def cmd_bump(target: str, version: str) -> int:
    if not SEMVER_RE.match(version):
        raise SystemExit(f"{version!r} is not a semver version")
    if target == "marketplace":
        path = MARKETPLACE_JSON
        data = json.loads(path.read_text(encoding="utf-8"))
        old = data.setdefault("metadata", {}).get("version")
        data["metadata"]["version"] = version
    else:
        path = PLUGINS_DIR / target / ".claude-plugin" / "plugin.json"
        if not path.exists():
            raise SystemExit(f"no such plugin: {target}")
        data = json.loads(path.read_text(encoding="utf-8"))
        old = data.get("version")
        data["version"] = version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{_rel(path)}: {old} -> {version}")
    return cmd_sync()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="validate plugins/skills/agents; verify generated files are current")
    sub.add_parser("sync", help="regenerate marketplace.json plugin entries and the README block")
    bump = sub.add_parser("bump", help="bump a plugin (or 'marketplace') version, then sync")
    bump.add_argument("target", help="plugin name, or 'marketplace' for metadata.version")
    bump.add_argument("version")
    args = parser.parse_args(argv)
    if args.cmd == "check":
        return cmd_check()
    if args.cmd == "sync":
        return cmd_sync()
    return cmd_bump(args.target, args.version)


if __name__ == "__main__":
    sys.exit(main())
