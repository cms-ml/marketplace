---
name: standalone-script
description: >-
  Use when writing a single-file, runnable Python script (not a package)
  whose dependencies should travel with it: a quick NanoAOD check, a
  dataset or file utility, an automation helper, or a one-off tool to share,
  using PEP 723 inline metadata and uv. Also use when such a script fails on
  cmslpc or lxplus because uv is missing, the home quota fills up, or the
  shebang errors with "env: invalid option -- 'S'".
metadata:
  summary: Single-file PEP 723 scripts run by uv, with Typer CLIs (cmslpc-tested)
---

# Standalone Script

## Overview

A PEP 723 script declares its own Python version and dependencies in a
comment block. `uv run --script` builds a cached, isolated environment for it
on demand. With a `#!/usr/bin/env -S uv run --script` shebang, the file is
directly executable and needs no virtualenv, package or `pyproject.toml`.

Use Typer for the command line, even for a single command, so options and
`--help` come for free and the script can grow.

## When to Use

- One-file tools: inspect a NanoAOD file, count events, list branches, tidy
  outputs, call an API
- Sharing a script that must "just run" for a colleague
- **Not** for code needing PyROOT/FWLite or CMSSW libraries. Those are not on
  PyPI, so run such scripts with CMSSW's `python3` after `cmsenv` instead.
- **Not** for multi-module code or importable libraries. Use the `cli-creator`
  skill or a real package for those.

## Key Concepts

| Piece                               | Meaning                                                             |
| ----------------------------------- | ------------------------------------------------------------------- |
| `# /// script` … `# ///`            | PEP 723 block: `requires-python`, `dependencies` (TOML in comments) |
| `#!/usr/bin/env -S uv run --script` | First line; makes `./script.py` work (needs coreutils ≥ 8.30)       |
| `uv run --script script.py`         | Explicit form; works everywhere uv runs                             |
| uv cache / managed Pythons          | Where environments and downloaded interpreters live (see Gotchas)   |

## Canonical Patterns

### Workflow

1. Copy [assets/pep723_typer_script.py](assets/pep723_typer_script.py) to the
   new script name.
2. Fill in `dependencies` (keep `typer`). Keep `requires-python = ">=3.13"`
   unless a dependency needs otherwise, since uv downloads a matching Python.
3. Write the logic in Typer command(s) and replace the docstring (it becomes
   `--help`).
4. Keep the shebang as line 1, then `chmod +x script.py`.
5. Run it: `./script.py --help`, then a real invocation.

### CMS example: count NanoAOD events over XRootD

[assets/nanoaod_count.py](assets/nanoaod_count.py) declares `uproot`,
`awkward`, `fsspec-xrootd` and `xrootd`. It reads a `root://` NanoAOD file and
counts events with ≥ N muons above 20 GeV:

```bash
./nanoaod_count.py root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/30000/0082C29D-E74C-024A-BE9B-97B29EE7A4A2.root -n 2
# 1375 / 10000 events with >= 2 muons (pT > 20 GeV)
```

The first run downloads Python and the packages (~6 s here). Later runs reuse
the cache.

### Get uv on cmslpc / lxplus

uv is not installed system-wide. Install it once, entirely in nobackup so
the small home area isn't touched:

```bash
export UV_INSTALL_DIR=~/nobackup/.local/bin
curl -LsSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 sh   # don't edit ~/.bashrc for us
```

Then add these lines to `~/.bashrc` (tcsh users: `setenv VAR value`):

```bash
export PATH=~/nobackup/.local/bin:$PATH
export UV_CACHE_DIR=~/nobackup/.cache/uv
export UV_PYTHON_INSTALL_DIR=~/nobackup/.local/share/uv/python
```

After this, the only file uv writes under home is a small install receipt
(`~/.config/uv/uv-receipt.json`). Tested: binary 37 MB, cache and one
managed Python ~125 MB, all in nobackup.

## Gotchas

- **Home quota.** On cmslpc the home area has a 3 GB hard limit. By default
  uv puts its binary in `~/.local/bin`, its cache in `~/.cache/uv` and managed
  Pythons in `~/.local/share/uv/python`. One managed Python is ~115 MB, and the
  cache grows with every new dependency set. Use the nobackup install above
  (`UV_INSTALL_DIR`, `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`).
- **`env: invalid option -- 'S'`.** `env -S` needs coreutils ≥ 8.30. EL9
  hosts have 8.32, but `cmssw-el7` containers have 8.22, so `./script.py`
  fails there. Use `uv run --script script.py`, which works in both.
- **No PyROOT / CMSSW inside the script env.** uv builds an isolated
  environment from PyPI. It runs fine from a `cmsenv` shell (tested) but cannot
  import `ROOT` or CMSSW modules. Use uproot, or run with CMSSW's `python3`
  without PEP 723.
- **Quote DAS/XRootD patterns.** Arguments like `/DYJets*/*/NANOAODSIM` are
  shell globs. Quote them so the script receives the pattern itself.
- **`requires-python = ">=3.13"`** makes uv pick the newest installed or
  downloadable Python (3.14 in testing). Binary wheels such as `xrootd` must
  exist for it. If an install tries to compile, pin a lower bound that has
  wheels (e.g. `">=3.12,<3.14"`).
- **Typer `count=True` options** take a short flag (`-v`, `-vv`). Typer shows
  them as `<int>` in `--help`.

## Reference Files

- [assets/pep723_typer_script.py](assets/pep723_typer_script.py): the
  starting template (PEP 723 block + Typer command + `-v` logging levels).
- [assets/nanoaod_count.py](assets/nanoaod_count.py): a complete CMS example
  reading NanoAOD over XRootD.

## Docs

- PEP 723: <https://peps.python.org/pep-0723/>
- uv scripts guide: <https://docs.astral.sh/uv/guides/scripts/>
- Typer: <https://typer.tiangolo.com/>
- Adapted from the IRIS-HEP marketplace `standalone-script` skill
  (BSD 3-Clause; see `plugins/hep-python-tools/VENDORED-LICENSES.md`):
  <https://github.com/iris-hep/marketplace/tree/main/iris-hep/skills/standalone-script>
