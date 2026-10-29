# CMS Marketplace

Claude Code plugin marketplace for CMS physics analysis. Each skill is
grounded in commands tested on cmslpc against real CMS releases and data
(CMS Open Data where possible), in both CMSSW and plain pip environments.

## Installation

### From Claude Code (chat box)

Type these in the Claude prompt. They are slash commands, not shell commands:

```text
/plugin marketplace add cms-ml/marketplace
/plugin install cms@cms-marketplace
/plugin install hep-python-tools@cms-marketplace
/plugin install af-fnal-lpc@cms-marketplace
```

### From a terminal

```bash
claude plugin marketplace add cms-ml/marketplace          # or a local clone: /path/to/marketplace
claude plugin install cms@cms-marketplace
claude plugin install hep-python-tools@cms-marketplace
claude plugin install af-fnal-lpc@cms-marketplace         # LPC users: condor batch jobs
claude plugin list                                        # each should show "enabled"
```

**VS Code users on cmslpc:** the extension ships its own `claude` binary,
which isn't on `PATH`:

```bash
alias claude="$(ls -d ~/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude | tail -1)"
```

### Updating, and getting new plugins

When new skills or plugins are merged, refresh the marketplace and install
any new plugins:

```bash
claude plugin marketplace update cms-marketplace
claude plugin install <new-plugin>@cms-marketplace
```

A marketplace added from a **local clone** is read from that folder, so its
skills follow the branch you have checked out there.

After installing or updating, **start a new conversation**. Skills are loaded when a
conversation starts. In VS Code, run "Developer: Reload Window" if a new chat
still doesn't see them. `/skills` lists what is loaded.

**Other agents (Codex, etc.):** skills follow the
[Agent Skills specification](https://agentskills.io/specification), so you can
symlink a plugin's `skills/` directory into the agent's skill path, e.g.
`ln -s $PWD/plugins/cms/skills ~/.agents/skills/cms`.

## One-time setup on cmslpc

- **Keep pip packages from shadowing CMSSW:** `export PYTHONNOUSERSITE=1`.
  Packages in `~/.local` from `pip install --user` break CMSSW's Python.
- **uv (for standalone scripts), installed entirely in nobackup** so the 3 GB
  home quota isn't used:

  ```bash
  export UV_INSTALL_DIR=~/nobackup/.local/bin
  curl -LsSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 sh
  cat >> ~/.bashrc <<'EOF'
  export PATH=~/nobackup/.local/bin:$PATH
  export UV_CACHE_DIR=~/nobackup/.cache/uv
  export UV_PYTHON_INSTALL_DIR=~/nobackup/.local/share/uv/python
  EOF
  ```

## Usage

You don't call skills by name. Claude picks them up when your request matches
their description. Describe the physics task and where things should go.
Mentioning a skill ("use the analysis-spec-builder skill…") makes sure it is
used.

Good requests name:

- the **data**: DAS name or Open Data path, era, number of files to start with
- the **output**: working directory, plot directory and format
- the **deliverables**: spec, script, plots, notes

Examples:

- "Set up CMSSW_14_0_15 in ~/nobackup/work and write an EDAnalyzer that
  histograms muon pT from MiniAOD." (`cmssw`)
- "Plot the dimuon mass in this NanoAOD file with CMS style." (`awkward-array`,
  `vector-awkward`, `hist`)
- "Write a spec for a Z→μμ data/MC comparison in 2016H." (`analysis-spec-builder`)
- "Make this check a single-file script I can send to a colleague."
  (`standalone-script`)

See [examples/](examples/) for a complete prompt.

<!-- GENERATED:START -->

## Plugins

### `af-fnal-lpc` (v0.1.0)

Skills for the CMS LPC analysis facility at Fermilab (cmslpc): HTCondor batch jobs on the LPC pool with inputs and outputs over XRootD/EOS.

**Skills:**

| Skill        | Use when                                                                                        |
| ------------ | ----------------------------------------------------------------------------------------------- |
| `lpc-condor` | HTCondor batch jobs on cmslpc with XRootD in, EOS out, check and resubmit (tested on real jobs) |

---

### `cms` (v0.2.0)

Core CMS analysis plugin: CMSSW releases and architectures, OS containers, EDM modules, cmsRun configuration, EDM file inspection, and the Scikit-HEP stack on NanoAOD (Awkward Array, vector, hist), analysis specifications, and CMS Combine: answering Combine questions from its docs, paper, code and forum, and running Combine commands (remote servers need the CERN network).

**Skills:**

| Skill                   | Use when                                                                                            |
| ----------------------- | --------------------------------------------------------------------------------------------------- |
| `analysis-spec-builder` | Turn an analysis request into a structured CMS specification.md (datasets, cuts, histograms, tools) |
| `awkward-array`         | Jagged arrays with Awkward 2 on CMS NanoAOD (records, selection, combinatorics, indices, I/O)       |
| `cmssw`                 | Release areas, architectures and containers, EDM modules, cmsRun configs, EDM file tools            |
| `combine`               | Answer Combine questions from docs, paper, code and forum; run and debug Combine                    |
| `hist`                  | Histograms with hist + mplhep for CMS (weights, normalisation, UHI, CMS-style plots)                |
| `vector-awkward`        | Four-vector kinematics on NanoAOD with vector + Awkward (masses, deltaR, mT, boosts)                |

**MCP servers:**

| Server               | Endpoint                                                  | Purpose                                                                  |
| -------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------ |
| `combine`            | `https://combine-mcp-git-combine-mcp.app.cern.ch/mcp`     | Combine docs, paper, source code and forum retrieval (CERN network only) |
| `combine-run-remote` | `https://combine-run-mcp-git-combine-mcp.app.cern.ch/mcp` | Runs one Combine command in a remote sandbox (CERN network only)         |

---

### `hep-python-tools` (v0.1.0)

Experiment-neutral Python developer tooling for HEP work, with cmslpc notes: PEP 723 standalone scripts run by uv, and Typer command-line tools wired into pyproject.toml.

**Skills:**

| Skill               | Use when                                                                           |
| ------------------- | ---------------------------------------------------------------------------------- |
| `cli-creator`       | Typer CLIs wired into pyproject.toml console scripts (uv + Hatch bootstrap, tests) |
| `standalone-script` | Single-file PEP 723 scripts run by uv, with Typer CLIs (cmslpc-tested)             |

<!-- GENERATED:END -->

## Example: dimuon resonances on CMS Open Data

[examples/dimuon/PROMPT.md](examples/dimuon/PROMPT.md) is a ready-to-paste
request that exercises five skills at once: a spec, a PEP 723 analysis script
and ten CMS-style plots of the J/ψ, ψ(2S), Υ(1S,2S,3S) and Z peaks from 2016H
DoubleMuon NanoAOD. It needs no grid proxy. It ends by writing
`SKILLS_USED.md`, a record of which skill guided each step and where a skill
fell short. Bring that file back as an issue or PR to improve the skills.

## Contributing

See [CLAUDE.md](CLAUDE.md) for the authoring conventions, and run
`python3 scripts/marketplace.py check` before opening a PR. Issues and PRs are
welcome at <https://github.com/cms-ml/marketplace>.

## License

MIT; see [LICENSE](LICENSE). Third-party teaching material is credited in
[CREDITS.md](CREDITS.md).
