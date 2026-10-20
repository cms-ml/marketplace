---
name: cli-creator
description: >-
  Use when adding a command-line interface to a Python package or project:
  creating a new CLI with Typer, adding a subcommand or command group (e.g.
  "mytool dataset list"), exposing it as a console script through
  [project.scripts] in pyproject.toml, bootstrapping a new package with uv
  and Hatch when the directory is empty, or testing CLI commands with
  pytest.
metadata:
  summary: Typer CLIs wired into pyproject.toml console scripts (uv + Hatch bootstrap, tests)
---

# CLI Creator

## Overview

Build a Typer CLI inside a package and expose it as a console script, so
`pip install -e .` gives users a `mytool` command. Match the existing
project's layout and conventions. Bootstrap a project only when none exists.

## When to Use

- "Make a CLI called X", "add a `status` subcommand", "expose `pkg.cli:main`"
- An analysis repo that has outgrown loose scripts
- **Not** for a one-file tool. Use the `standalone-script` skill for that.

## Key Concepts

| Piece                           | Role                                                            |
| ------------------------------- | --------------------------------------------------------------- |
| `app = typer.Typer()`           | Top-level command                                              |
| `app.add_typer(sub, name="dataset")` | Command group: `mytool dataset …`                           |
| `def main(): app()`             | Entry point referenced by the console script                   |
| `[project.scripts]`             | `mytool = "my_pkg.cli:main"` in `pyproject.toml` (PEP 621)     |
| `typer.testing.CliRunner`       | Run commands in tests without a subprocess                     |

## Canonical Patterns

### 0. Bootstrap (only if there is no package yet)

```bash
uv venv --python 3.13 .venv && source .venv/bin/activate
uv pip install hatch
hatch new my-tool            # -> my-tool/{pyproject.toml, src/my_tool/, tests/}
cd my-tool
```

`hatch new` fills `authors` and the GitHub URLs from your git config, and
sets `requires-python = ">=3.8"`. Review both. On cmslpc, set uv's cache and
Python directories to nobackup first (see the `standalone-script` skill).

### 1. Inspect before writing

Read `pyproject.toml` (PEP 621 `[project]`, Poetry, Hatch), find the layout
(`src/` or flat), and reuse any existing CLI module or Typer patterns.

### 2. CLI module with a command group

```python
# src/my_tool/cli.py
import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)
dataset = typer.Typer(no_args_is_help=True, help="Dataset commands.")
app.add_typer(dataset, name="dataset")


@dataset.command("list")
def dataset_list(pattern: str = typer.Argument("*", help="DAS dataset pattern")) -> None:
    """List datasets matching PATTERN."""
    from my_tool import das          # import heavy code inside the command: fast --help

    for name in das.find(pattern):
        typer.echo(name)


def main() -> None:
    app()
```

Start with placeholder handlers that print `hello from my-tool dataset list`.
Then replace them with real logic, or delegate to another module as above.

### 3. Wire the console script and dependency

```toml
[project]
dependencies = [
  "typer>=0.12",
]

[project.scripts]
my-tool = "my_tool.cli:main"
```

Optionally add `src/my_tool/__main__.py` containing `from my_tool.cli import
main; main()` so `python -m my_tool` works too.

### 4. Install, run, test

```bash
uv pip install -e . pytest
my-tool --help
my-tool dataset list "/DYJets*/*/NANOAODSIM"
```

```python
# tests/test_cli.py
from typer.testing import CliRunner
from my_tool.cli import app

def test_dataset_list():
    result = CliRunner().invoke(app, ["dataset", "list", "/DYJets*/*/NANOAODSIM"])
    assert result.exit_code == 0
```

## Gotchas

- **Keep imports lazy.** Importing uproot/awkward/ROOT at module top makes
  every `--help` slow. Import inside the command function.
- **`no_args_is_help=True` exits with status 2** after printing help. That's
  Typer/Click's usage-error convention, so don't treat it as a crash in tests.
- **Quote glob-like arguments.** DAS patterns such as `/DYJets*/*/NANOAODSIM`
  are expanded by the shell unless quoted.
- **The console script appears only after installing the package**
  (`uv pip install -e .`). Re-install after changing `[project.scripts]`.
- **Side effects at import time** (reading files, network calls) run on every
  invocation, including `--help`. Keep them inside commands.
- **Inside CMSSW (`cmsenv`) the Python is 3.9.** Use a separate uv venv for
  the tool unless it must import CMSSW/PyROOT modules.

## Reference Files

None. Patterns above were run end-to-end on cmslpc with uv 0.12, Hatch, Typer
and pytest (Python 3.13).

## Docs

- Typer: <https://typer.tiangolo.com/>
- Entry points (`[project.scripts]`): <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#creating-executable-scripts>
- Hatch: <https://hatch.pypa.io/latest/>
- Adapted from the IRIS-HEP marketplace `cli-creator` skill (BSD 3-Clause; see
  `plugins/hep-python-tools/VENDORED-LICENSES.md`):
  <https://github.com/iris-hep/marketplace/tree/main/iris-hep/skills/cli-creator>
