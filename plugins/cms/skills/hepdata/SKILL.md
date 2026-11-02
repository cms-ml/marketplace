---
name: hepdata
description: >-
  Use when preparing, writing, validating or reviewing a HEPData record for a
  CMS paper, PAS, or an Open Data study: converting spectra, efficiencies,
  cutflows, fit results, limits or hist/ROOT histograms into HEPData YAML with
  hepdata_lib, filling keywords, qualifiers and asymmetric uncertainties,
  running hepdata-validate, uploading to the HEPData sandbox, following the
  CMS (EXO, B2G) HEPData and reinterpretation requirements, or debugging
  errors such as "Got unexpected extra argument", "takes 2 positional
  arguments", "The tar ball is not valid", "Inconsistent length of 'values'
  list" or .nan values in the YAML.
metadata:
  summary: HEPData records with hepdata_lib, validated offline, following CMS requirements
---

# HEPData

## Overview

A HEPData record is a `submission.yaml`, plus one YAML file per table, plus
optional images. Each table has independent variables (x: bins or labels)
and dependent variables (y: values with uncertainties). Build it in Python
with **hepdata_lib**, check it with **hepdata-validate**, then upload the
archive to the HEPData sandbox for review.

[assets/make_hepdata.py](assets/make_hepdata.py) is a tested template with
helpers for binned spectra, asymmetric errors, efficiencies and per-category
tables. It has NaN and file guards and runs the validator automatically.

## When to Use

- A CMS paper or PAS needs its HEPData record (required for publication)
- Turning analysis outputs (`summary.json`, hist objects, ROOT files) into tables
- Reviewing someone's record before it goes to the HEPData contact
- Packaging an Open Data study's results in a reusable form

## Key Concepts

| Piece                     | What to put there                                                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Table                     | One per figure panel or paper table. Name it after the paper object (`Figure 3a`). The name becomes the file name. |
| `description`, `location` | What is shown, the selection and normalisation, and `Data from Figure 3a`                                          |
| Keywords                  | `observables` (e.g. `N`, `EFF`, `SIG`), `reactions` (`P P --> JET JET`), `cmenergies` (`13000.0`), `phrases`       |
| Independent variable      | Bins `(low, high)` with units, or string labels (categories)                                                       |
| Dependent variable        | Values plus uncertainties, with qualifiers such as `SQRT(S)` and the selection/category                            |
| Uncertainty               | Symmetric `±x`, or asymmetric `(minus, plus)` with **minus negative**. Label `stat`, `syst`, or named sources.     |
| License                   | hepdata_lib 0.20 writes **CC0** by default. Use `table.add_data_license(name, url)` to change it per table.        |

## Canonical Patterns

### Environment

```bash
source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh   # hepdata_lib 0.20.0 + hepdata-validate
# or: python3 -m pip install hepdata_lib   (pulls hepdata-validator)
```

### Build, write, validate

```bash
cp <skill>/assets/make_hepdata.py my_hepdata.py   # fill build(); inputs arrive as args.input
python3 my_hepdata.py -o hepdata --input summary.json --input plots --no-tar   # TABLES=6 OUTDIR=hepdata VALID=1
python3 <skill>/assets/make_hepdata.py --demo -o /tmp/hd_demo   # toy record: shows every helper
```

The core of a table, with hepdata_lib 0.20:

```python
from hepdata_lib import Submission, Table, Variable, Uncertainty
t = Table("Figure 5a"); t.description = "..."; t.location = "Data from Figure 5a."
t.keywords["observables"] = ["N"]; t.keywords["reactions"] = ["P P --> JET JET"]; t.keywords["cmenergies"] = [13000.0]
x = Variable("$m_{jj}$", is_independent=True, is_binned=True, units="GeV")
x.values = list(zip(edges[:-1], edges[1:]))
y = Variable("Events", is_independent=False, is_binned=False, units="Events")   # keywords only in 0.20
y.values = counts
u = Uncertainty("stat", is_symmetric=False); u.values = [(-d, u_) for d, u_ in zip(down, up)]
y.add_uncertainty(u); y.add_qualifier("SQRT(S)", "13000 GeV")
t.add_variable(x); t.add_variable(y); t.add_image("plots/mjj_2b.pdf")
sub = Submission(); sub.add_table(t); sub.create_files("hepdata", remove_old=True)
```

### From `hist` objects

```python
from hepdata_lib.hist_utils import create_hist_base_table, hist_as_variable
t = create_hist_base_table("Figure 5a", h, axes_rename={"mjj": "$m_{jj}$"}, axes_units={"mjj": "GeV"})
t.add_variable(hist_as_variable("Data", h, uncertainty={"stat": "poisson_sym"}))
```

Tested with a `Var`-axis `Weight()` histogram. The result validates.

### Tables without a natural x axis

- One row per category: a string independent variable (`category_x`).
- Category × scan point (e.g. fit quality vs number of parameters): **two**
  independent variables, one row per combination (demo `Table 2`).
- Fit parameters: one table per category, parameters as a string variable,
  values and errors as dependent variables. HEPData has no native place for a
  covariance matrix other than a 2D table.

### Validate and upload

```bash
cd hepdata && hepdata-validate -d .      # "<dir> is valid", exit 0; run from inside: no absolute paths in the log
tar czf ../submission.tar.gz *          # YAML + images; upload this archive
```

Upload the archive at <https://www.hepdata.net/record/sandbox> (CERN or
ORCID login) and check every table renders. For a CMS paper, the HEPData
contact creates the real record. See
[references/cms-procedure.md](references/cms-procedure.md).

## Gotchas

- **`Variable.__init__() takes 2 positional arguments but 4 were given`**:
  hepdata_lib 0.20 takes keyword arguments only. Older scripts with
  `Variable("Data", False, False, "Events")` break. Write
  `is_independent=..., is_binned=..., units=...`.
- **`Error: Got unexpected extra argument (dir)`**: the validator takes
  `hepdata-validate -d <dir>` (or `-a <archive>`), not a positional path.
- **NaN passes validation.** `float("nan")` is written as `.nan` and
  `hepdata-validate` says "valid". Empty-denominator efficiencies are the
  usual source. Drop the bin or explain it; the template's `finite()` guard
  stops the build.
- **`AssertionError: The tar ball is not valid`** from `create_files()`: the
  YAML was written but fails validation. Run `hepdata-validate -d` to see the
  table, e.g. `Inconsistent length of 'values' list: independent_variables
[2], dependent_variables [3]`.
- **`submission.tar.gz` appears in the current directory**, not in the
  output directory. The template `chdir`s to the parent of the output dir.
- **Table names become file names.** `b-tag efficiency vs Z' mass` gives
  `b-tag_efficiency_vs_z'_mass.yaml`. Use ASCII without quotes, and name tables
  after the paper object. Without a paper (Open Data, a note), use short
  descriptive names such as `mjj spectrum 2b`.
- **Images add size**: each `add_image` writes a PNG and a thumbnail (about
  1.2 MB for 6 figures here). Commit them only if the record is meant to be
  browsed from the repository.
- **Zero-content bins** print "bins with zero content should preferably be
  omitted". That's a note, not an error. Keep them in spectra that were
  fitted (they carry information). For variables that legitimately have no
  uncertainty (counts of parameters, χ²), pass `zero_ok=True` to the
  template's `y_var`. That sets hepdata_lib's `zero_uncertainties_warning=False`.
- **Which statistical error.** Use the same errors as the figure: sqrt(N) if
  the plot shows sqrt(N), Garwood (asymmetric Poisson, demo `Figure 1`) if it
  shows those. Say which in the description. For low counts, Garwood is the
  honest choice.
- **`RuntimeError: File plots/x.pdf does not exist!`** from `add_image` with
  a relative path after a `chdir`. The template's `figure_table` makes image
  paths absolute when the table is built. Do the same in your own code.
- **`phrases`** (free-text search terms) is a keyword reviewers expect.
  `figure_table(..., phrases=[...])` sets it.
- **Per-category tables**: use a string independent variable (`["1 b tag",
"2 b tags"]`) rather than an encoded integer index.
- **`add_image` needs ImageMagick** (`convert`) for PDF → PNG and thumbnails.
  The LCG view has it.
- **Default license changed**: hepdata_lib 0.14 wrote CC-BY-4.0, 0.20 writes
  CC0. Check what your group expects.
- **Open Data records are not CMS results.** Say so in `submission.comment`
  and every description. Never claim a CMS paper identity, and never add a
  CMS INSPIRE id to an Open Data study.
- **Never digitise.** Read values from the same files the figures were made
  from, and `require_files()` them so a missing input fails loudly.

## Reference Files

- [assets/make_hepdata.py](assets/make_hepdata.py): template with
  `figure_table`, `binned_x`, `y_var`, `add_sym`, `add_asym`, `category_x`,
  guards (`require_files`, `finite`), `--input`, `--no-tar`, `--demo`,
  `main(argv)` for use from another script, and automatic validation
  (`VALID=1`, exit 0/1/2).
- [references/cms-procedure.md](references/cms-procedure.md): what CMS
  expects in a record (EXO reinterpretation requirements, cutflows, models),
  who reviews it, and where B2G keeps submissions.

## Docs

- hepdata_lib: <https://github.com/HEPData/hepdata_lib>,
  docs <https://hepdata-lib.readthedocs.io/en/latest/>
- HEPData submission format: <https://hepdata-submission.readthedocs.io/en/latest/>
- Validator: <https://github.com/HEPData/hepdata-validator>
- HEPData submission help: <https://www.hepdata.net/submission>
- EXO MC & Interpretation, reinterpretation materials:
  <https://exo-mc-and-i.gitbook.io/exo-mc-and-interpretation/reinterpretationmaterials>
- CMS B2G HEPData submissions (CERN GitLab): <https://gitlab.cern.ch/cms-b2g-hepdata>
- CMS publication procedure (CMS internal twiki):
  <https://twiki.cern.ch/twiki/bin/viewauth/CMS/Internal/Publications>
- Example CMS record (CMS-EXO-20-008): <https://www.hepdata.net/record/ins1920627>
