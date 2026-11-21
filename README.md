# CMS Marketplace

Skills for CMS physics analysis in Claude Code and Codex. Use them to set up
CMSSW, skim NanoAOD, measure efficiencies, run batch jobs at Fermilab or CERN,
and package results for HEPData. The `cms` plugin also includes two Claude Code
subagents for implementing an analysis and reviewing it against published CMS results.

Browse the [plugin catalog](#plugins) to choose skills or jump to the
[validation results](#validations) for worked analyses and batch runs.

## Installation

### From Claude Code (chat box)

Type these in the Claude prompt. They are slash commands, not shell commands:

```text
/plugin marketplace add cms-ml/marketplace
/plugin install cms@cms-marketplace
/plugin install hep-python-tools@cms-marketplace
/plugin install af-fnal-lpc@cms-marketplace
/plugin install af-cern-lxplus@cms-marketplace
```

### From a terminal with Claude Code

```bash
claude plugin marketplace add cms-ml/marketplace          # or a local clone: /path/to/marketplace
claude plugin install cms@cms-marketplace
claude plugin install hep-python-tools@cms-marketplace
claude plugin install af-fnal-lpc@cms-marketplace         # LPC users: condor batch jobs
claude plugin install af-cern-lxplus@cms-marketplace      # lxplus users: lxbatch, EOS, CRAB
claude plugin list                                        # each should show "enabled"
```

**VS Code users on cmslpc:** the extension ships its own `claude` binary,
which isn't on `PATH`:

```bash
alias claude="$(ls -d ~/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude | tail -1)"
```

### Updating Claude Code plugins

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

### From a terminal with Codex

Register the marketplace and list its plugins:

```bash
codex plugin marketplace add cms-ml/marketplace
codex plugin list --marketplace cms-marketplace --available --json
```

For a local checkout, use `codex plugin marketplace add /path/to/marketplace`
in the first step. Install the plugins you need, then start a new Codex session
in your analysis directory:

```bash
codex plugin add cms@cms-marketplace               # CMSSW and NanoAOD analysis
codex plugin add af-fnal-lpc@cms-marketplace       # Fermilab LPC and CMS Connect
codex plugin add af-cern-lxplus@cms-marketplace    # CERN lxplus, EOS and CRAB
codex plugin add hep-python-tools@cms-marketplace  # standalone Python scripts and CLIs
```

For example, ask Codex to “use the `nanoaod-skimming` skill to skim these DY
files and check that the merged output preserves the sum of generator weights.”

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

Claude Code and Codex can select skills from the task description. Describe the
physics task, name the skill if you want a particular workflow, and say where
to write the outputs.

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
- "List the jet and HT triggers in one 2016G and one 2016H JetHT file, then
  measure the turn-on of their OR vs m_jj with HLT_PFJet260 as reference and
  tell me where it plateaus." (`trigger-efficiency`)
- "Turn the spectra and efficiencies in summary.json into a HEPData record in
  hepdata/, with the plots attached, and validate it." (`hepdata`)
- "Split these 142 Open Data files into 10 condor jobs, write the outputs to
  my EOS area, and resubmit any that fail." (`lpc-condor`)
- "Use the cms-analysis-coder agent to implement specification.md: start on
  2 files, then run everything, and write summary.json and SKILLS_USED.md."
  (Claude Code agent `cms-analysis-coder`)

See [examples/](examples/) for a complete prompt, and
[validation/dijet-2016/PROMPT.md](validation/dijet-2016/PROMPT.md) for a
full analysis task given to the agent.

### Running the agent on a long task

In Claude Code, ask for the agent by name: "Use the cms-analysis-coder agent to …".
For tasks that take hours (condor jobs, full datasets), run it headless
inside `tmux`, so a closed laptop or a VS Code reconnect doesn't kill it:

```bash
tmux new -s agent                       # reattach later with: tmux attach -t agent
cd marketplace                          # or your analysis directory
sed -n '/^## Task/,$p' validation/dijet-2016/PROMPT.md | \
  claude -p --agent cms:cms-analysis-coder \
    --permission-mode acceptEdits \
    --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
    > agent_report.md 2>&1
```

The prompt goes on **stdin**: `--allowedTools` takes a list and would
swallow a prompt given as an argument. Without `--allowedTools`, a headless
agent cannot run shell commands. Allowing `Bash` lets it run any command in
your account, so give it a clear working directory and limits in the prompt.

Check progress without interrupting it:

```bash
ls -lt <workdir> <workdir>/plots | head                    # newest outputs first
condor_q                                                   # its batch jobs
eos root://cmseos.fnal.gov ls /store/user/$USER/<area>     # its EOS outputs
```

If it stops (for example, the node was rebooted), start a new run that
resumes from what exists:

> Use the cms-analysis-coder agent to resume `<workdir>`. These steps are
> done: `<list, e.g. condor skims in /store/user/$USER/...>`; don't redo
> them. Read `specification.md` and `SKILLS_USED.md` first, then finish
> `<remaining deliverables>`. If an earlier run failed, find out why first
> (memory: `/usr/bin/time -v`). Append new notes to `SKILLS_USED.md`.

<!-- GENERATED:START -->

## Plugins

### `af-cern-lxplus` (v0.1.1)

Skills for CMS work on CERN lxplus: driving lxplus over ssh, HTCondor batch (lxbatch, CPU and GPU, EosSubmit), EOS and xrootd storage, and CRAB grid submission.

**Skills:**

| Skill             | Use when                                                                                                       |
| ----------------- | -------------------------------------------------------------------------------------------------------------- |
| `crab`            | CRAB on EL9: setup, sizing, sites, exit codes, recovery tasks, CRAB as a backend for law/combine fits          |
| `eos-xrootd`      | EOS and xrootd at CERN and FNAL: URLs, verified copies, FUSE pitfalls, quotas, recycle-bin etiquette           |
| `lxplus-access`   | Reaching lxplus from agents: Kerberos, node pinning, node-local /tmp, killed background processes, shell traps |
| `lxplus-htcondor` | CERN lxbatch HTCondor: where to submit, memory/CPU/GPU sizing, flavours, holds, EosSubmit, robust stage-out    |

---

### `af-fnal-lpc` (v0.2.0)

Skills for the CMS LPC analysis facility at Fermilab (cmslpc): HTCondor batch jobs on the LPC pool with inputs and outputs over XRootD/EOS, plus field notes for large productions on the LPC pool and CMS Connect.

**Skills:**

| Skill            | Use when                                                                                                            |
| ---------------- | ------------------------------------------------------------------------------------------------------------------- |
| `cmsconnect-lpc` | CMS Connect and FNAL LPC condor field notes: wrapper traps, microarch, site vetoes, large GEN productions, FNAL EOS |
| `lpc-condor`     | HTCondor batch jobs on cmslpc with XRootD in, EOS out, check and resubmit (tested on real jobs)                     |

---

### `cms` (v0.5.0)

Core CMS analysis plugin: CMSSW releases and architectures, OS containers, EDM modules, cmsRun configuration, EDM file inspection, and the Scikit-HEP stack on NanoAOD (Awkward Array, vector, hist), NanoAOD skimming with luminosity and normalisation bookkeeping, plus analysis specifications.

**Subagents:**

| Subagent                | Purpose                                                                             |
| ----------------------- | ----------------------------------------------------------------------------------- |
| `cms-analysis-coder`    | Senior CMS PhD student that implements an analysis spec with the marketplace skills |
| `cms-results-validator` | ARC-style reviewer that compares an analysis with published CMS results on HEPData  |

**Skills:**

| Skill                   | Use when                                                                                                                                       |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `analysis-spec-builder` | Turn an analysis request into a structured CMS specification.md (datasets, cuts, histograms, tools)                                            |
| `awkward-array`         | Jagged arrays with Awkward 2 on CMS NanoAOD (records, selection, combinatorics, indices, I/O)                                                  |
| `cmssw`                 | Release areas, architectures and containers, EDM modules, cmsRun configs, EDM file tools                                                       |
| `hepdata`               | HEPData records with hepdata_lib, validated offline, following CMS requirements                                                                |
| `hist`                  | Histograms with hist + mplhep for CMS (weights, normalisation, UHI, CMS-style plots)                                                           |
| `muon-tag-and-probe`    | Muon ID, isolation and trigger efficiencies and scale factors from Z → μμ tag and probe in NanoAOD, with the Muon POG correctionlib comparison |
| `nanoaod-skimming`      | Skim and slim NanoAOD (uproot or RDataFrame) with golden JSON, genEventSumw bookkeeping and luminosity accounting                              |
| `trigger-efficiency`    | Trigger turn-ons and offline thresholds from NanoAOD (reference method, Clopper-Pearson, plateau rule)                                         |
| `vector-awkward`        | Four-vector kinematics on NanoAOD with vector + Awkward (masses, deltaR, mT, boosts)                                                           |

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

## Validations

These runs show what the skills and agents produced on CMS Open Data and on
the two batch facilities. Follow each report for the inputs, results and limits
of the comparison.

| Workflow                                                                                    | What the run demonstrates                                                                                                                                           |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [NanoAOD skimming](validation/nanoaod-skimming/README.md)                                   | Skims 2016G SingleMuon and DY to 2–3% of their input size, preserves the MC sum of generator weights, and checks the luminosity normalization with the Z peak.      |
| [Muon tag and probe](validation/muon-tnp/README.md)                                         | Compares tight ID, isolation and trigger scale factors with the Muon POG. Tight ID agrees. A roughly 1.2% IsoMu24 offset remains in the barrel with bit-2 matching. |
| [b-tagged dijet search](validation/dijet-2016/README.md)                                    | Runs the analysis on 142 Open Data files, from trigger turn-ons and mass fits to CMS-style plots and HEPData tables.                                                |
| [Comparison with published CMS results](validation/dijet-2016/cms-comparison/COMPARISON.md) | The results validator compares the dijet and dimuon analyses with six HEPData records and explains where the selections or normalizations differ.                   |
| [Fermilab LPC batch](validation/lpc-condor/RESULTS.md)                                      | Splits JetHT inputs across HTCondor jobs and checks the outputs on EOS. All jobs exited successfully in both runs.                                                  |
| [CERN lxplus batch](validation/lxplus-condor/RESULTS.md)                                    | Runs the same JetHT selection on lxbatch and stages the outputs to FNAL EOS. The successful run matches the LPC counts job by job.                                  |

To check the committed results locally, run the checker from the repository
root for a validation that provides one. For example:

```bash
python3 validation/nanoaod-skimming/check_results.py
```

To reproduce a full run, follow its report for the environment, input data
and commands. The [dijet prompt](validation/dijet-2016/PROMPT.md) and the
[CMS comparison prompt](validation/dijet-2016/CMS_COMPARISON_PROMPT.md)
show how to give the implementation and review tasks to the Claude Code agents.

To add one for your own skill or agent, see
[CONTRIBUTING.md](CONTRIBUTING.md#7-the-validation).

## Contributing

New skills, agents and plugins are welcome. **[CONTRIBUTING.md](CONTRIBUTING.md)**
explains the pieces (skill, agent, plugin), which one to write, and how to
make a PR step by step. Every skill or agent PR comes with a validation: an
analysis that uses it, run by an agent, in `validation/<name>/`.
[validation/dijet-2016](validation/dijet-2016) (a b-tagged dijet search on
2016 Open Data, using the `cms-analysis-coder` agent and the
`trigger-efficiency` and `hepdata` skills) is the reference example.
[CLAUDE.md](CLAUDE.md) has the authoring rules that
`python3 scripts/marketplace.py check` enforces.

Issues and PRs are welcome at <https://github.com/cms-ml/marketplace>.

## License

MIT; see [LICENSE](LICENSE). Third-party teaching material is credited in
[CREDITS.md](CREDITS.md).
