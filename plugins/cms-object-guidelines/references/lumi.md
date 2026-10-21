# luminosity — CMS POG recommendations (NanoAOD)

Source: https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun2, https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun3 (LUM POG) and https://twiki.cern.ch/twiki/bin/view/CMS/PdmVRun3Analysis (PdmV/DQM-DC), retrieved 24 Sep 2026 | Campaigns: Run2 pp 13 TeV 2015/2016/2017/2018 (Legacy/UL JSONs) plus special runs (5.02 TeV pp, PbPb, pPb, XeXe, 900 GeV); Run3 2022 (Summer22/Summer22EE), 2023 (Summer23/Summer23BPix), 2024, 2025, 2026 (prompt).

brilcalc installation/usage: `BrilcalcQuickStart` twiki. **The brilcalc command differs by year**, so always use the one for your year (Section 2).

## 1. NanoAOD branches (`run`, `luminosityBlock`) and certification JSONs
Branch source: https://cms-xpog.docs.cern.ch/autoDoc/ (event-level `run`, `luminosityBlock`, `event`). A lumimask keeps a data event only if its (`run`, `luminosityBlock`) pair appears in the certification JSON. Apply it to data only.

Use the **Golden JSON**, and compute the luminosity with brilcalc on **that same JSON**.

**Prefer the CVMFS copies**, which are readable wherever CVMFS is mounted: `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/CollisionsYY/latest/…`. These are the same files as on AFS/EOS. The CVMFS path is the AFS/EOS relative path with `latest/` inserted after `CollisionsYY/`. The CVMFS paths come from a CVMFS listing, not from the LUM/PdmV twikis.

### Run 2 Golden JSONs (pp 13 TeV)
AFS base: `/afs/cern.ch/cms/CAF/CMSCOMM/COMM_DQM/certification/`. Use **Legacy** for UL analyses; the 2017 Legacy file is named `UL2017`. 2015 has no Legacy JSON, on AFS or on CVMFS.

| Year | Type | AFS (relative to base) | CVMFS |
| --- | --- | --- | --- |
| 2016 | **Legacy** | `Collisions16/13TeV/Legacy_2016/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions16/latest/13TeV/Legacy_2016/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt` |
| 2017 | **Legacy** | `Collisions17/13TeV/Legacy_2017/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions17/latest/13TeV/Legacy_2017/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt` |
| 2018 | **Legacy** | `Collisions18/13TeV/Legacy_2018/Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions18/latest/13TeV/Legacy_2018/Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt` |
| 2015 | PreLegacy | `Collisions15/13TeV/Reprocessing/Cert_13TeV_16Dec2015ReReco_Collisions15_25ns_JSON_v2.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions15/latest/13TeV/Reprocessing/Cert_13TeV_16Dec2015ReReco_Collisions15_25ns_JSON_v2.txt` |
| 2016 | PreLegacy | `Collisions16/13TeV/ReReco/Final/Cert_271036-284044_13TeV_ReReco_07Aug2017_Collisions16_JSON.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions16/latest/13TeV/ReReco/Final/Cert_271036-284044_13TeV_ReReco_07Aug2017_Collisions16_JSON.txt` |
| 2017 | PreLegacy | `Collisions17/13TeV/ReReco/Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON_v1.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions17/latest/13TeV/ReReco/Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON_v1.txt` |
| 2017 LowPU (runs 306896–307082) | PreLegacy | `Collisions17/13TeV/ReReco/Cert_306896-307082_13TeV_EOY2017ReReco_Collisions17_JSON_LowPU.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions17/latest/13TeV/ReReco/Cert_306896-307082_13TeV_EOY2017ReReco_Collisions17_JSON_LowPU.txt` (identical copies also in `13TeV/Final/` and `13TeV/PromptReco/`) |
| 2018 | PreLegacy | `Collisions18/13TeV/ReReco/Cert_314472-325175_13TeV_17SeptEarlyReReco2018ABC_PromptEraD_Collisions18_JSON.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions18/latest/13TeV/ReReco/Cert_314472-325175_13TeV_17SeptEarlyReReco2018ABC_PromptEraD_Collisions18_JSON.txt` |

The Run 2 source gives **no 2016 preVFP/postVFP split and no per-era values**. Compute these with brilcalc on your JSON, restricted to the runs you analyse.

### Run 2 special-run Golden JSONs
Web base: `https://cms-service-dqmdc.web.cern.ch/CAF/certification/`

| Run | Web (relative to base) | CVMFS |
| --- | --- | --- |
| pp 5.02 TeV 2017 | `Collisions17/5TeV/ReReco/Cert_306546-306826_5TeV_EOY2017ReReco_Collisions17_JSON.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions17/latest/5TeV/ReReco/Cert_306546-306826_5TeV_EOY2017ReReco_Collisions17_JSON.txt` |
| PbPb 5.02 TeV 2018 | `Collisions18/HI/PromptReco/Cert_326381-327564_HI_PromptReco_Collisions18_JSON.txt` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions18/latest/HI/PromptReco/Cert_326381-327564_HI_PromptReco_Collisions18_JSON.txt` |

### Run 3 Golden JSONs (13.6 TeV, from the DQM-DC team)
EOS base: `/eos/user/c/cmsdqm/www/CAF/certification/` = `https://cms-service-dqmdc.web.cern.ch/CAF/certification/`

| Year | EOS (relative to base) | CVMFS |
| --- | --- | --- |
| 2022 | `Collisions22/Cert_Collisions2022_355100_362760_Golden.json` (call 7-23) | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions22/latest/Cert_Collisions2022_355100_362760_Golden.json` |
| 2023 | `Collisions23/Cert_Collisions2023_366442_370790_Golden.json` (call 1-12) | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions23/latest/Cert_Collisions2023_366442_370790_Golden.json` |
| 2024 | `Collisions24/Cert_Collisions2024_378981_386951_Golden.json` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions24/latest/Cert_Collisions2024_378981_386951_Golden.json` |
| 2025 | `Collisions25/Cert_Collisions2025_391658_398903_Golden.json` | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions25/latest/Cert_Collisions2025_391658_398903_Golden.json` |
| 2026 | not listed on the PdmV page | `/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions26/latest/Cert_Collisions2026_401624_403937_golden.json`: **preliminary/partial**. Runs 401624–403937 end inside era D (403423–404067). There is no lumi uncertainty for 2026, and newer versions may appear under `latest/` |

### Run 3 pp 13.6 TeV physics eras → run ranges and MC campaigns
Run ranges follow Tier0 PromptReco era/procVersion changes.

| Year | Era | Runs | MC campaign | Note |
| --- | --- | --- | --- | --- |
| 2022 | B | 355065–355793 | – | commissioning |
| 2022 | C | 355794–357486 | Run3Summer22 | PDs good for physics from here |
| 2022 | D (v1–v3) | 357487–359021 | Run3Summer22 | |
| 2022 | E | 359022–360331 | Run3Summer22EE | |
| 2022 | F | 360332–362180 | Run3Summer22EE | |
| 2022 | G | 362350–362760 | Run3Summer22EE | |
| 2023 | B | 366365–367079 | – | |
| 2023 | C (v1–v4) | 367080–369802 | Run3Summer23 | pre-BPix |
| 2023 | D (v1–v2) | 369803–372415 | Run3Summer23BPix | post-BPix |
| 2024 | B–I | 378971–387121 | not given in source | A = 900 GeV; J = ppRef |
| 2025 | B–G | 391531–398903 | not given | pO/OO/NeNe runs 393610–394285 excluded |
| 2026 | A–D | 401600–404067 | not given | C (402514–403422) = low-PU era |

## 2. Integrated luminosity (brilcalc) and uncertainties
`NT=/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags`. Replace `[your json]` with your JSON.

### Run 2, pp 13 TeV (2015–2018)
Command for all years: `brilcalc lumi --normtag $NT/normtag_PHYSICS.json -u /fb -i [your json]`

Cite **CMS-LUM-17-003** for 2015–2016 and **CMS-PAS-LUM-20-001** for 2017–2018 and the combinations.

Totals in /fb, stable beams:

| | 2015 | 2016 | 2017 | 2017 LowPU | 2018 | 2015–2018 | 2016–2018 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Delivered | 4.13 | 41.56 | 50.51 | 0.2624 | 67.56 | 163.76 | 159.63 |
| Golden PreLegacy | 2.27 | 36.31 | 42.12 | 0.22768 | 59.47 | 140.17 | 137.90 |
| **Golden Legacy** | – | 36.31 | 42.07 | – | 59.56 | 140.22 | 137.94 |
| **Uncertainty** | **1.6%** | **1.2%** | **0.82%** | **0.90%** | **0.84%** | **0.73%** | **0.73%** |

- The uncertainty applies to every row of its column, meaning the full datasets. **If you compute lumi for a special dataset, consult LUM POG.**
- Delivered-lumi cross-checks use `-b "STABLE BEAMS" --amodetag PROTPHYS --beamenergy 6500` with `--begin/--end` dates. For 2017 low PU, use runs `--begin 306896 --end 307082` and `-u /pb`.
- If something is missing, the source points to revision 10 of the Run 2 twiki (https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun2?rev=10).

### Run 2 special runs
| Run | Command (normtag) | Uncertainty | Reference / totals |
| --- | --- | --- | --- |
| pp 5.02 TeV 2017 | `normtag_PHYSICS.json`, `-u /pb` | 1.9% | LUM-19-001. Golden 302.29 /pb; recorded 322.94; delivered 341.29. Golden JSON: Section 1 |
| pp 5.02 TeV 2015 | `normtag_PHYSICS.json`, `-u /pb` | 2.3% | LUM-16-001. The brilcalc warning about missing offline lumi is negligible |
| PbPb 5.02 TeV 2018 | `normtag_PHYSICS.json`, `-u /nb` | 1.5% | LUM-18-001. Golden 1700.20 /μb (607.30 with HLT_HIMinimumBias). Golden JSON: Section 1 |
| PbPb 5.02 TeV 2015 | – | final estimate in progress (LUM-20-002) | contact experts |
| pPb/Pbp 2016 (8.16 TeV/nucleon only) | `normtag_PHYSICS.json`, `-u /nb` | Pbp 3.2%, pPb 3.7%, combined 3.5% | LUM-17-002. For the 5.02 TeV/nucleon part, contact lumi experts |
| XeXe 2017 (fill 6295) | `brilcalc lumi -f 6295 -b "STABLE BEAMS" --normtag $NT/normtag_BRIL.json -u /ub` | not estimated | 2.48 /μb; AN-2022-025, CMS-DP-2024-015 |
| 900 GeV 2018 (fills 7299/7300, 7406/7407) | `normtag_BRIL.json`, `-u /nb` (preliminary) | ~30% (13 TeV calibration scaled by σ_inel) | – |
| High-β* 2018 (fills 6877–6892) | regular pp 13 TeV calibration | – | – |

### Run 3, pp 13.6 TeV
| Year | Command | Uncertainty | Status / reference |
| --- | --- | --- | --- |
| 2022 | `brilcalc lumi --normtag $NT/normtag_PHYSICS.json -u /fb -i [your json]` | **1.4%** | final, LUM-22-001 |
| 2023 | `brilcalc lumi --normtag $NT/normtag_PHYSICS.json -u /fb -i [your json]` | **1.3%** | CMS-DP-2024-068 (https://cds.cern.ch/record/2904808) |
| 2024 | `brilcalc lumi --normtag $NT/normtag_PHYSICS.json -u /fb -i [your json]` | **1.6%** (preliminary) | CMS-DP-2026-003 (https://cds.cern.ch/record/2952191) |
| 2025 | `brilcalc lumi -u /fb -b "STABLE BEAMS" --normtag $NT/normtag_BRIL.json -i [your json]` | **5%**, uncorrelated with previous years | preliminary (Feb 2026); tension between Z counting and a partial vdM calibration |
| 2026 | `brilcalc lumi -b "STABLE BEAMS" --datatag online -u /fb -i [your json]` | **none available** (Use same as 2025) | prompt/online; no normtag |

Reference totals in /fb (2022–2024 with normtag_PHYSICS):

| Year | Era | Delivered | Recorded | Golden JSON | MC campaign |
| --- | --- | --- | --- | --- | --- |
| 2022 | B | 0.13 | 0.11 | 0.10 | – |
| 2022 | C | 7.01 | 6.38 | 5.02 | Run3Summer22 |
| 2022 | D | 3.80 | 3.38 | 2.97 | Run3Summer22 |
| 2022 | E | 6.75 | 6.26 | 5.81 | Run3Summer22EE |
| 2022 | F | 20.16 | 18.60 | 17.78 | Run3Summer22EE |
| 2022 | G | 3.62 | 3.27 | 3.09 | Run3Summer22EE |
| 2022 | **Total** | 41.47 | 38.01 | 34.76 | |
| 2023 | B | 1.33 | 1.19 | 0.64 | – |
| 2023 | C | 20.38 | 18.76 | 17.96 | Run3Summer23 |
| 2023 | D | 11.03 | 10.15 | 9.68 | Run3Summer23BPix |
| 2023 | **Total** | 32.74 | 30.10 | 28.28 | |
| 2024 | B / C / D / E | 0.74 / 7.96 / 8.94 / 12.38 | 0.66 / 7.45 / 8.34 / 11.56 | 0.13 / 7.26 / 7.98 / 11.42 | – |
| 2024 | F / G / H / I | 30.81 / 43.27 / 6.89 / 13.04 | 28.43 / 39.78 / 6.26 / 11.95 | 28.04 / 38.07 / 5.49 / 11.56 | – |
| 2024 | **Total** | 124.04 | 114.44 | 109.95 | |
| 2025 | B / C / D | 0.33 / 24.12 / 29.21 | 0.30 / 22.66 / 26.53 | 0.25 / 21.56 / 25.82 | – |
| 2025 | E / F / G | 15.85 / 30.45 / 25.12 | 14.24 / 27.53 / 23.00 | 14.05 / 26.69 / 22.25 | – |
| 2025 | **Total** | 125.07 | 114.25 | 110.63 | preliminary (DC Ops) |
| 2026 | A / B / C / D | 0.87 / 17.64 / 2.56 / 12.04 | 0.81 / 16.32 / 2.42 / 10.80 | 0.64 / 15.28 / 2.11 / 10.03 | C = low-PU |
| 2026 | **Total** | 33.10 | 30.36 | 28.06 | preliminary; all 13.6 TeV runs regardless of PU |

LUM's delivered-lumi cross-checks (no JSON):
- 2023: `--begin 366442 --end 370790`
- 2024: `--begin 378981 --end 386951 -b "STABLE BEAMS"`
- 2025: `--begin 10491 --end 11245 -b 'STABLE BEAMS' --normtag $NT/normtag_BRIL.json --amodetag PROTPHYS` (note: fill numbers, not run numbers). `PROTPHYS` excludes the pO/OO/NeNe fills.

These tables are for cross-checking only. **Normalise with brilcalc on your own JSON.** The LUM combination (Section 4) uses slightly different golden values: 34.75 / 28.40 / 110.11 /fb for 2022 / 2023 / 2024.

## 3. Corrections
### Where to get inputs
- Normtags: `/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/`:
  - `normtag_PHYSICS.json` for Run 2 (all approved pp/HI/pA results) and Run 3 2022–2024.
  - `normtag_BRIL.json` for 2025 and for the Run 2 preliminary cases (XeXe, 900 GeV).
- Certification JSONs: Section 1.
- Pileup reweighting (ROOT histograms and correctionlib): `PileupJSONFileforData` twiki. Details are in `pileup.md`.
- Inelastic cross-section for pileup reweighting: the Run 3 page recommends **69.2 mb**. This is the fiducial value, and LUM POG does not measure it. The 80 mb value (TOTEM, 13.6 TeV) is for pileup public plots and comparisons only. For cross-sections, ask the SMP PAG. The Run 2 lumi page does not state a value.

### How to apply
1. **Data**: apply the lumimask from the JSON you chose.
   - **Run 3:** use every split PD of the same flavour, e.g. `Muon0` + `Muon1`, `EGamma0` + `EGamma1`, `JetMET0` + `JetMET1`; for 2023D+ also `ParkingVBF[0-7]` etc. Otherwise part of the luminosity is missing.
   - From 2022C: JetHT + MET → `JetMET`, SingleMuon + DoubleMuon → `Muon`. Look up the PDs for a trigger path with CMS HLT Info (https://cmshltinfo.app.cern.ch/summary).
2. **MC normalisation**: scale each MC sample to the brilcalc luminosity of the eras that sample represents. For example, 2022 CD ↔ Run3Summer22 and 2022 EFG ↔ Run3Summer22EE, each with its own lumi. The source does not give a normalisation formula; the usual practice is σ × L / Σ genWeight.
3. **Pileup**: reweight MC to the data pileup profile (see `pileup.md`).

```python
from coffea.lumi_tools import LumiMask   # tooling choice, not from the LUM/PdmV source

golden = {
    "2018": "/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions18/latest/13TeV/Legacy_2018/"
            "Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt",
    "2023": "/cvmfs/cms-griddata.cern.ch/cat/metadata/DC/Collisions23/latest/Cert_Collisions2023_366442_370790_Golden.json",
}[year]
if is_data:
    events = events[LumiMask(golden)(events.run, events.luminosityBlock)]

# Luminosity for this JSON (shell); Run2 and Run3 2022–2024 → normtag_PHYSICS:
# brilcalc lumi --normtag /cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_PHYSICS.json -u /fb -i <golden>
lumi_fb = {"2023C": 17.96, "2023D": 9.68}   # replace with YOUR brilcalc output for YOUR JSON/run range
w_mc = xsec_pb * 1000 * lumi_fb["2023C"] / sum_genweight   # Run3Summer23 ↔ 2023C
```

## 4. Systematics
All nuisances are `lnN` in combine datacards. Combination study: https://indico.cern.ch/event/1617597/.

### Run 2, pp 13 TeV: new scheme (Cholesky minimal decomposition, RECOMMENDED)
The old "Uncorrelated/Correlated" component scheme is imprecise: it gives 0.74% on the total, where the correct value is 0.73%.

| Nuisance | 2015 | 2016 | 2017 | 2018 |
| --- | --- | --- | --- | --- |
| `lumi_13TeV_15_l` | 1.0122 | – | – | – |
| `lumi_13TeV_1516_l` | 1.0096 | 1.0118 | – | – |
| `lumi_13TeV_151617_l` | 1.0002 | 1.0004 | 1.0055 | – |
| `lumi_13TeV_15161718_l` | 1.0042 | 1.0035 | 1.0061 | 1.0084 |

- **2016+2017+2018:** use the same rows without the 2015 column, and drop `lumi_13TeV_15_l`.
- **Single year:** use **every nuisance whose name contains the year**. For example, 2017 = `lumi_13TeV_151617_l` 1.0055 + `lumi_13TeV_15161718_l` 1.0061.
- **Years integrated into one bin:**

| Nuisance | 2016+2017+2018 | 2015+2016+2017+2018 |
| --- | --- | --- |
| `lumi_13TeV_15_l` | – | 1.0002 |
| `lumi_13TeV_1516_l` | 1.0031 | 1.0032 |
| `lumi_13TeV_151617_l` | 1.0018 | 1.0018 |
| `lumi_13TeV_15161718_l` | 1.0064 | 1.0063 |

Old scheme (**discouraged**; for backwards compatibility only):
- 2015–2018, 7 parameters, values for 2015 / 2016 / 2017 / 2018:
  - `lumi_1` = 1.01005 / – / – / –
  - `lumi_2` = – / 1.006 / – / –
  - `lumi_3` = – / – / 1.00378 / –
  - `lumi_4` = – / – / – / 1.00439
  - `lumi_5` = 1.008 / 1.00781 / – / –
  - `lumi_6` = – / – / 1.00626 / 1.00582
  - `lumi_7` = 1.0097 / 1.00742 / 1.00369 / 1.00414
- 2016–2018, 5 parameters, values for 2016 / 2017 / 2018:
  - `lumi_1` = 1.00985 / – / –
  - `lumi_2` = – / 1.00378 / –
  - `lumi_3` = – / – / 1.00439
  - `lumi_4` = – / 1.00626 / 1.00582
  - `lumi_5` = 1.00742 / 1.00369 / 1.00414

Run 2 covariance in fb² (%² in parentheses). It was computed with the **PreLegacy** lumi values.

| | 2015 | 2016 | 2017 | 2018 |
| --- | --- | --- | --- | --- |
| 2015 | 0.0013346 (2.59) | 0.0105502 (1.28) | 0.00251461 (0.263) | 0.0047106 (0.349) |
| 2016 | 0.0105502 (1.28) | 0.200399 (1.52) | 0.0360933 (0.236) | 0.0630426 (0.292) |
| 2017 | 0.00251461 (0.263) | 0.0360933 (0.236) | 0.118847 (0.6699) | 0.127301 (0.5083) |
| 2018 | 0.0047106 (0.349) | 0.0630426 (0.292) | 0.127301 (0.5083) | 0.248156 (0.7019) |

2017G (pp 5.02 TeV) + 2017H (pp 13 TeV low PU), minimal correlations (RECOMMENDED), in %:
- Uncorrelated: 2017G 1.7, 2017H 1.5.
- Correlated: 0.8 (G), 0.9 (H).

The full breakdown (reference only) is in `CMS-LUMI-POG/Normtags` `Scripts/luminosity_lowPU_periods.txt` with `combineYears.py -r`.

### Run 3
| Analysis years | Treatment |
| --- | --- |
| Single year | lnN of that year: 2022 1.014, 2023 1.013, 2024 1.016 (prelim), 2025 1.05 |
| 2022 + 2023 + 2024 | `lumi_1` = 1.0138 / 1.0017 / 1.0020; `lumi_2` = – / 1.0127 / 1.0068; `lumi_3` = – / – / 1.0144 (total 1.20%) |
| 2022 + 2023 | `lumi_1` = 1.0138 / 1.0017; `lumi_2` = – / 1.0127 (total 1.01%) |
| 2023 + 2024 | `lumi_1` = 1.0115 / –; `lumi_2` = 1.0056 / 1.0161 (total 1.41%) |
| 2022 + 2024 (without 2023) | **not provided** in the source; ask LUM POG or build it from the covariance below |
| Any year combined with 2025 | 2025's 5% goes in as a **separate, uncorrelated** nuisance |
| 2026 | no uncertainty available yet |
| Run 2 + Run 3 combined | **correlation not given** in either source; ask LUM POG |

The Run 3 page says these nuisances come from a new reduction method, "unlike the Run 2 method".

Covariance for 2022/2023/2024, in fb² (values in parentheses are in %², i.e. 100² · cov_ij / (L_i L_j)). Combination: 34.75 ± 0.48 + 28.40 ± 0.36 + 110.11 ± 1.77 = **173.26 ± 2.07 /fb (1.2%)**.

| | 2022 | 2023 | 2024 |
| --- | --- | --- | --- |
| 2022 | 0.2297 (1.9023) | 0.0231 (0.2336) | 0.1049 (0.2742) |
| 2023 | 0.0231 (0.2336) | 0.1323 (1.6403) | 0.2802 (0.8959) |
| 2024 | 0.1049 (0.2742) | 0.2802 (0.8959) | 3.1270 (2.5791) |

## 5. Pitfalls / do NOT use
### Run 2
- The old Run 2 `lumi_1…lumi_7` scheme: it is discouraged. Use the `lumi_13TeV_*_l` Cholesky nuisances.
- In a single-year Run 2 analysis, using only one nuisance. Every nuisance whose name contains the year must go in.
- Assigning the full-dataset uncertainty to a special dataset or trigger subset without asking LUM POG.
- PreLegacy JSONs or PreLegacy totals in a UL analysis. Use the Legacy JSONs. (The Run 2 covariance matrix itself comes from the PreLegacy values.)
- The 900 GeV 2018 calibration as a precision number (only ~30%). pPb uncertainties for the 5.02 TeV/nucleon part: none exist, so ask the experts.
- `-u /fb` for small datasets: the source uses `/pb` for 2017 low PU and 5 TeV pp, `/nb` or `/μb` for HI, and `/ub` for XeXe.

### Run 3
- The same brilcalc command for every year. 2022–2024 use `normtag_PHYSICS.json`, 2025 uses `normtag_BRIL.json` with `-b "STABLE BEAMS"`, and 2026 uses `--datatag online` with no normtag.
- 2025 delivered lumi without `--amodetag PROTPHYS`. This counts the pO/OO/NeNe fills.
- Treating the 2025 5% or the 2024 1.6% as final. Both are preliminary. 2026 has no uncertainty, and its numbers are prompt.
- Computing 2026 (online) lumi once and never again. Calibrations are applied retroactively, so redo the calculation from time to time. Normtag/cvmfs updates arrive once per day, so recent fills can be missing for a few days.
- Numbers from the PdmV "without normtag" tables. Use only the normtag values.
- Correlating Run 3 years with the Run 2 recipe, or correlating 2025 with earlier years.
- Using 80 mb (total inelastic) in pileup reweighting. Use 69.2 mb.
- Analysing only one PD of a split flavour (e.g. only `Muon0`).
- Normalising one MC campaign to the whole year: 2022 is split C–D / E–G and 2023 is split C / D (BPix). Also, 2022B and 2023B have no MC campaign in the tables.
- 2022 ReReco: use the `27Jun2023` MINIAOD / `22Sep2023` NANOAOD tag. **Do not use `10Dec2022`**. If your dataset isn't in the newest tag, use PromptReco.
- 2023C prompt NanoAOD switches version at run 367472 (v11p9 up to and including it, v12 after). The v12 datasets are split into v2/v3/v4 processing versions, so include every run in the era.
- NanoAOD v12 changed branch types (Int_t → Short_t/UChar_t). Old `MakeClass` code can break silently.
- 2024 lost MINIAOD/NANOAOD files for collision runs 384935, 384951, 384963, 384981, 385142. If lumisections in your JSON weren't processed, the brilcalc lumi is too high. Consider computing lumi only on the lumisections you actually processed. (This consequence is an inference; the source only lists the runs.)
- The 2026 PdmV totals **include** the low-PU era C.

### Both runs
- Copying table totals into the normalisation instead of running brilcalc on your own JSON. Also, the Run 3 tables and the LUM combination differ slightly (e.g. 2023: 28.28 vs 28.40 /fb).
