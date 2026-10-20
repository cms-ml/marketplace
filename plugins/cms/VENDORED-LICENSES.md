# Vendored Content Licenses

## IRIS-HEP Marketplace

The following skill was adapted from the
[IRIS-HEP marketplace](https://github.com/iris-hep/marketplace) (upstream
commit `ca69e49`, 2026-09-27):

- `skills/awkward-array/`, from `iris-hep/skills/awkward-array/`

**Original authors:** Gordon Watts, Ben Galewsky

**What was kept:** the skill name, the five-step workflow (build records →
filter early → combinatorics → add fields → repeat), the topic coverage
(records, filtering/aggregation, sorting, combinatorics, argmin/argmax,
flattening, NumPy interop, pitfalls, file I/O), and the `argmax(...,
keepdims=True)` example.

**What changed:**

- Rewritten for CMS: NanoAOD examples (uproot `Events` tree, `Muon_*`/`Jet_*`
  branches, index branches such as `Jet_muonIdx1`, `genWeight`), GeV units, and
  CMSSW vs pip environments. Added a runnable worked example
  (`assets/nanoaod_dimuon.py`).
- Ten reference notes merged into `references/operations.md` and
  `references/io-and-environments.md`.
- Every example re-tested on cmslpc with awkward 2.6.3 (CMSSW_15_0_21) and
  2.8.12 (pip). Upstream statements found incorrect and corrected here:
  - "There is no `ak.max` or `ak.min`": both exist.
  - `ak.fill_like`: does not exist (use `ak.full_like` / `ak.zeros_like`).
  - `ak.count` "counts non-empty elements": it counts non-`None` values.
  - `ak.from_json("data.json")`: parses the string as JSON; a file needs
    `pathlib.Path`.
  - "Avoid `axis=None`": valid and useful for `ak.sum` / `ak.flatten`; the
    skill asks for a deliberate choice of axis instead.

### Additional skills from the same source

The following skills were also adapted from the IRIS-HEP marketplace (upstream
commit `ca69e49`, same authors and license as above):

- `skills/vector-awkward/`, from `iris-hep/skills/vector-awkward/`
  - **Kept:** skill name; register behaviours → zip with `with_name` → use
    `deltaR`, `+`/`.mass`, `boostCM_of_p4`.
  - **Changed:** NanoAOD examples (muons, jets, MET as `Momentum2D`, nearest
    jet, transverse mass, sums, boosts), tested with vector 1.4.0 (CMSSW) and
    1.7.0 (pip). Corrected upstream statements: `Vector4D` with `px/py/pz/E`
    fields has no `.pt` (use `Momentum4D`), and vector also works without
    Awkward (`vector.array`, `vector.obj`). Added: records zipped before
    `register_awkward()` never gain vector methods, and arithmetic drops extra
    fields.
- `skills/hist/`, from `iris-hep/skills/hist/`
  - **Kept:** skill name, `Hist.new` axis/storage patterns, UHI indexing, the
    categorical-axes example, and the plotting/labelling advice.
  - **Changed:** CMS NanoAOD examples with `genWeight` (including negative
    weights) and normalisation from `Runs/genEventSumw`, the CMS style and
    `hep.cms.label` instead of the ATLAS style, ratio panels, and measured
    NanoAOD ranges replacing ATLAS guesses. Tested with hist 2.7.2 / mplhep
    0.3.47 (CMSSW) and hist 2.9.2 / mplhep 1.1.3 (pip). Corrected upstream
    statements: `.fill` returns the histogram (not `None`), `histtype="bar"`
    and `"barstep"` exist only in newer mplhep, the 2D example's
    `mplhep.hist2dplot` after `import mplhep as hep`, the W mass (80.4 GeV, not
    82), and the b-tag range (CMS scores are 0–1).
- `skills/analysis-spec-builder/`, from `iris-hep/skills/analysis-spec-builder/`
  - **Kept:** skill name, the draft → ask → iterate → write `specification.md`
    workflow, the drafting rules, and the template's section structure.
  - **Changed:** CMS template (DAS names, tier, era, Golden JSON, triggers,
    MC normalisation, a new Corrections and Systematics section). Defaults are
    NanoAOD, uproot/awkward/vector/hist, correctionlib and Combine, instead of
    PHYSLITE, ServiceX and pyhf. The three examples were rewritten with real
    CMS datasets, checked in DAS and against NanoAOD branches.

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
