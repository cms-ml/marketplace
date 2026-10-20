# Vendored Content Licenses

## IRIS-HEP Marketplace

The following skills were adapted from the
[IRIS-HEP marketplace](https://github.com/iris-hep/marketplace) (upstream
commit `ca69e49`, 2026-09-27):

- `skills/standalone-script/`, from `iris-hep/skills/standalone-script/`
- `skills/cli-creator/`, from `iris-hep/skills/cli-creator/`

**Original authors:** Gordon Watts, Ben Galewsky

**What was kept:**

- `standalone-script`: the workflow (PEP 723 block, `uv run --script`
  shebang, Typer CLI, `chmod +x`), and `assets/pep723_typer_script.py`, which
  is copied unchanged.
- `cli-creator`: the workflow (uv + Hatch bootstrap, inspect the project,
  Typer module with `main()`, `[project.scripts]` wiring, validation).

**What changed:**

- Tested end-to-end on cmslpc (EL9) with uv 0.12, Typer, Hatch and pytest.
  Added cmslpc/lxplus notes: installing uv with its binary, cache and managed
  Pythons in nobackup, outside the 3 GB home quota, `env -S` failing in `cmssw-el7`
  containers (coreutils 8.22), and PEP 723 environments being isolated from
  CMSSW/PyROOT.
- `standalone-script`: added a CMS example, `assets/nanoaod_count.py`
  (NanoAOD over XRootD).
- `cli-creator`: added a command-group example, a `CliRunner` test, and
  notes on `hatch new` metadata, lazy imports, exit code 2 for
  `no_args_is_help`, and quoting DAS patterns.

**License:** BSD 3-Clause License

```text
BSD 3-Clause License

Copyright (c) 2025, IRIS-HEP

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
