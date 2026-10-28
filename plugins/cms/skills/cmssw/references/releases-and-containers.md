# Releases, SCRAM_ARCH and OS containers

Read this reference when choosing a CMSSW release for a dataset or data-taking
era, when `cmsrel` says a release is not available for your architecture, or
when a release must run on a different OS than the host (e.g. a `slc7` release
on an EL9 node such as cmslpc or lxplus).

## Contents

1. [Find the release a dataset was made with](#find-the-release-a-dataset-was-made-with)
2. [Latest releases and what changed: release notes](#latest-releases-and-what-changed-release-notes)
3. [Example eras](#example-eras)
4. [Find the architectures of a release](#find-the-architectures-of-a-release)
5. [OS containers: cmssw-elX](#os-containers-cmssw-elx)
6. [Release naming](#release-naming)

## Find the release a dataset was made with

Don't guess. Ask DAS (needs a grid proxy) or read the file's provenance:

```bash
voms-proxy-init -voms cms
dasgoclient -query="release dataset=/Muon0/Run2024A-PromptReco-v1/MINIAOD"
# CMSSW_14_0_4
edmProvDump <file> | head -5     # releases of each processing step
```

To _read_ MiniAOD you can generally use the production release cycle or a
newer one. To _re-run_ or extend NanoAOD production, use the same release
cycle (`X_Y`) the campaign used.

## Latest releases and what changed: release notes

The CMSSW release notes at <https://cmssdt.cern.ch/SDT/ReleaseNotes/> are
updated with every release. Check them before relying on any release number
in this file. The index lists every cycle (`CMSSW 15_0`, `15_1`, …) and its
releases, newest first. Each release has its own page:

```text
https://cmssdt.cern.ch/SDT/ReleaseNotes/CMSSW_<major>/CMSSW_<X>_<Y>_<Z>.html
e.g. https://cmssdt.cern.ch/SDT/ReleaseNotes/CMSSW_15/CMSSW_15_0_21.html
```

A release page gives:

- the **release date**
- every **cms-sw/cmssw PR merged since the previous release**, with number,
  author, title and the categories it touched (e.g. `xpog`, `reconstruction`)
- **CMSDIST changes**, meaning updates to externals such as ROOT, Python
  packages and generator tags, plus a "compare to previous" link

Use it to:

- pick the **newest patch in a cycle** (e.g. the latest `CMSSW_15_0_*`) for
  bug fixes, then confirm it exists for your arch with
  `ls -d /cvmfs/cms.cern.ch/*/cms/cmssw*/CMSSW_15_0_<N>`
- check whether a **fix or backport** you need (search the PR number or title)
  has reached a release before upgrading
- see why results changed between two releases: read every page between them

From the shell, `scram list -c CMSSW_15_0` shows what is installed on CVMFS
for the current `SCRAM_ARCH`. The release notes show what was _released_ and
why.

## Example eras

These were checked with `dasgoclient` and `/cvmfs` on 2026-10-06. Newer patch
releases appear frequently, so confirm with the commands above for your exact
dataset, and check the
[release notes](https://cmssdt.cern.ch/SDT/ReleaseNotes/) for the latest
release in each cycle.

| Data                                      | Release (from DAS) | Arch(es) on CVMFS                        | On an EL9 host |
| ----------------------------------------- | ------------------ | ---------------------------------------- | -------------- |
| CMS Open Data 2011/2012 (Run 1)           | `CMSSW_5_3_32`     | `slc6_amd64_gcc472`                      | `cmssw-el6`    |
| CMS Open Data 2015 MiniAOD                | `CMSSW_7_6_7`      | `slc6_amd64_gcc493`, `slc7_amd64_gcc493` | `cmssw-el7`    |
| Run 2 Ultra-Legacy (`RunIISummer20UL*`)   | `CMSSW_10_6_X`     | `slc7_amd64_gcc700`                      | `cmssw-el7`    |
| Run 3 2022 (`Run3Summer22MiniAODv4`)      | `CMSSW_13_0_13`    | `el8_amd64_gcc11`, `el9_amd64_gcc11`, …  | native         |
| Run 3 2024 prompt (`Run2024A-PromptReco`) | `CMSSW_14_0_4`     | `el8_amd64_gcc12`, `el9_amd64_gcc12`, …  | native         |

## Find the architectures of a release

```bash
ls -d /cvmfs/cms.cern.ch/*/cms/cmssw*/CMSSW_12_4_25
# /cvmfs/cms.cern.ch/el8_amd64_gcc10/...   /cvmfs/cms.cern.ch/slc7_amd64_gcc10/...
scram list -c CMSSW_13_0     # only lists releases for the *current* SCRAM_ARCH
```

Patch releases (`CMSSW_X_Y_Z_patchN`) live under `cms/cmssw-patch/` rather
than `cms/cmssw/`.

Then select the arch before `cmsrel`:

```bash
export SCRAM_ARCH=el8_amd64_gcc10
cmsrel CMSSW_12_4_25
```

An `el8_*` release on an EL9 host needs the `cmssw-el8` container.

## OS containers: cmssw-elX

Wrappers in `/cvmfs/cms.cern.ch/common`: `cmssw-el6`, `cmssw-el7`,
`cmssw-el8`, `cmssw-el9` (plus aliases such as `cmssw-cc7`). They run
apptainer on an image from `/cvmfs/unpacked.cern.ch`. What is visible inside
depends on apptainer's site defaults. On cmslpc, `/cvmfs`, your home and
`/eos/uscms` are visible but **`/uscms_data` (nobackup) is not**, so add
`-B /uscms_data` when your area lives there.

```bash
cmssw-el7                                   # interactive shell in CentOS 7
cmssw-el7 -B /uscms_data -- 'cmd1 && cmd2'  # bind an extra path; run commands and exit
cmssw-el7 --show-command -- true            # print the underlying apptainer call
```

Inside the container, when the OS differs from the host, the wrapper
**unsets `SCRAM_ARCH`** and re-sources `cmsset_default.sh`, so the default
becomes the container OS's newest compiler (e.g. `slc7_amd64_gcc12`). Export
the release's arch explicitly before `cmsrel` or `cmsenv`:

```bash
cmssw-el7 -- 'export SCRAM_ARCH=slc7_amd64_gcc700 && cd CMSSW_10_6_30/src && cmsenv && cmsRun cfg.py'
```

Notes:

- Check visibility with `cmssw-el7 -- 'ls -d /path'`. Bind anything missing
  with `-B /path`.
- Condor/CRAB jobs for a container release must also start the container. For
  CRAB, the release's arch selects the right worker OS automatically.
- Build and run the area with the same container. Objects built on EL9 against
  an `slc7` release will not load.

## Release naming

| Form                           | Meaning                                                        |
| ------------------------------ | -------------------------------------------------------------- |
| `CMSSW_15_0_21`                | Production release: cycle `15_0`, patch-level 21               |
| `CMSSW_15_0_X`                 | The GitHub branch for that cycle; browse code here             |
| `CMSSW_14_0_15_patch1`         | Patch release on top of `CMSSW_14_0_15`                        |
| `CMSSW_15_1_0_pre3`            | Pre-release (development; not for analysis)                    |
| `CMSSW_15_0_X_2026-10-05-2300` | Integration build (IB) on `/cvmfs/cms-ib.cern.ch`; short-lived |
