# I/O and environments for Awkward on CMS data

Read this reference when opening `root://` (XRootD) files with uproot,
choosing which branches or events to read, writing arrays to Parquet or JSON,
or deciding between the awkward shipped in CMSSW and a pip installation.
Tested on cmslpc (EL9), 2026-10-09.

## Contents

1. [Environments](#environments)
2. [Opening files over XRootD](#opening-files-over-xrootd)
3. [Reading only what you need](#reading-only-what-you-need)
4. [Parquet and JSON](#parquet-and-json)

## Environments

| Environment                      | awkward | uproot | vector | XRootD in uproot                          | Parquet               |
| -------------------------------- | ------- | ------ | ------ | ----------------------------------------- | --------------------- |
| `CMSSW_15_0_21` after `cmsenv`   | 2.6.3   | 5.3.3  | 1.4.0  | `handler=uproot.source.xrootd.XRootDSource` | not available (no pyarrow) |
| pip venv (Python 3.9, 2026-10)   | 2.8.12  | 5.6.9  | 1.7.0  | `pip install fsspec-xrootd xrootd`        | `pip install pyarrow pandas` |

- In CMSSW, run `export PYTHONNOUSERSITE=1` so packages you installed with
  `pip install --user` in `~/.local` don't shadow the release's versions.
- Other releases ship other versions: check with
  `python3 -c "import awkward; print(awkward.__version__)"`.
- A plain venv:
  `python3 -m venv ak && ak/bin/pip install awkward uproot vector fsspec-xrootd xrootd`.

## Opening files over XRootD

```python
import uproot

url = "root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/..."  # Open Data: no proxy
try:
    import fsspec_xrootd  # noqa: F401
    f = uproot.open(url)                                               # pip env
except ImportError:
    f = uproot.open(url, handler=uproot.source.xrootd.XRootDSource)    # CMSSW
events = f["Events"]
```

Without either backend, `uproot.open("root://...")` fails with
`ImportError: Install fsspec-xrootd to access xrootd storage system`.

For CMS (non-Open-Data) files, prefix the `/store/...` LFN with a redirector,
e.g. `root://cmsxrootd.fnal.gov//store/...`. This needs a valid grid proxy
(`voms-proxy-init -voms cms`).

## Reading only what you need

NanoAOD files are large (the test file is 2.4 GB with 1.9M events), so read
specific branches and a range:

```python
arr = events.arrays(["Muon_pt", "Muon_eta", "nMuon"], entry_stop=20000)      # explicit list
arr = events.arrays(filter_name="Muon_*", entry_stop=20000)                  # glob
mu  = events.arrays(filter_name="Muon_*", how="zip", entry_stop=5).Muon      # auto-zip by prefix
two = events.arrays(["Muon_pt"], cut="nMuon >= 2", entry_stop=1000)          # event preselection
for chunk in events.iterate(["Muon_pt", "Muon_eta"], step_size=200_000):   # 200k events per chunk
    ...
```

`step_size="100 MB"` also works, but it counts memory of the _selected_
branches only. Two muon branches of the full 1.9M-event test file fit in a
single 100 MB chunk.

- `how="zip"` groups branches sharing a prefix into one record collection
  (`Muon` with fields `pt`, `eta`, …). The counter branch `nMuon` equals
  `ak.num(Muon_pt, axis=1)`.
- `cut=` is evaluated after reading, so it saves memory downstream but not
  I/O.

## Parquet and JSON

```python
import pathlib
ak.to_parquet(selected, "selected.parquet")      # needs pyarrow (and pandas with pyarrow 21 / awkward 2.8)
back = ak.from_parquet("selected.parquet")

ak.to_json(array, "small.json")                  # second positional argument is the file
back = ak.from_json(pathlib.Path("small.json"))  # a str is parsed AS JSON text, not opened
```

- In the pip test, `ak.to_parquet` failed with `No module named 'pandas'`
  until pandas was installed alongside pyarrow.
- CMSSW_15_0_21 has no pyarrow. Write Parquet from a pip environment, or keep
  ROOT output (`uproot.recreate`).
- JSON is for small samples only. Parquet keeps the jagged structure and
  types and is far smaller.
