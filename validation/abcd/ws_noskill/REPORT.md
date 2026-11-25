# ABCD estimate of the QCD multijet background in m_avg (2016 G+H JetHT, 16.3 fb-1) — Open Data, private work

**What was done.** Pair-produced resonance → 2 boosted AK8 jets; observable m_avg=(m_SD1+m_SD2)/2, 40–440 GeV, 17 bins (20 GeV wide up to 300, then 30/30/40/40; ~13% resolution proxy from VV MC). Data region A was never filled until the prediction was frozen (`fits/blind_results.json`); `scripts/unblind.py` then filled it.

**Trigger.** OR of HLT_PFHT900, HLT_PFJet450, HLT_AK8PFJet450 (present in both eras; HT800 is absent in 2016H; mass-trimmed paths avoided because they bias m_SD). Turn-on vs leading-AK8 pT with reference PFJet260 (cross-checks AK8PFJet260, PFJet320; Clopper–Pearson): plateau 0.998 above **pT1>550 GeV** (target 0.99, 128k ref. events; three references agree), subleading plateau above 275 → **pT2>300 GeV** (`plots/trigger_*`). No trigger on MC (above plateau). Cost: acceptance for light (80 GeV) resonances near threshold is limited by this boosted selection.

**Preselection.** golden JSON, MET filters, tight jetId, |η|<2.5, lepton veto, pT1>550, pT2>300, mass asymmetry |m1−m2|/(m1+m2)<0.2 (equal-mass pair; QCD eff 0.14, VV both-V-matched eff 0.45 — low because many V jets are not fully merged).

**ABCD variables.** N2(β=1) of jet 1 and of jet 2, each <0.30 on the signal side (V-jet eff 0.74, QCD jet eff 0.35 in 60–120 GeV; N2 ≈ τ21 in separation, τ32/N3 useless: `plots/design_substructure_*`, `boundary_*`). A = both pass (SR), B = jet1 pass/jet2 fail, C = jet1 fail/jet2 pass, D = both fail. I scanned alternatives in QCD MC (N2 × |Δη|, N2 × mass asymmetry, cuts 0.25/0.30/0.35); jet-N2 × jet-N2 at 0.30 closes best (ρ within ±12%); asymmetry as ABCD variable gives ρ=0.3–0.7.

**Independence / TF.** Pearson corr(N2_1,N2_2) in QCD MC: 0.015 / 0.009 / −0.006 in m_avg slices (0.035 inclusive). However the TF=C/D rises from 0.28 to ~2 with m_avg (N2 ↔ jet mass), and an inclusive TF mispredicts by 11%. So **TF is per m_avg bin**, TF=N_C/N_D from data (non-QCD MC subtracted), A_pred = TF·B (`plots/tf_vs_mavg`). A pol2 fit to log TF has χ²=320/14 and is only a cross-check.

**Other backgrounds.** W/Z+jets, tt, VV, H from MC×xsec×lumi: 3.5/3.8/2.3% of data in B/C/D, 5.0% of A; subtracted in B,C,D, added back in A; ±50% normalisation varied (syst).

**Uncertainties.** Stat: Poisson of B,C,D (+MC stat of subtraction). Syst per bin: MC non-closure √((ρ_MC−1)²+σ²_ρ+0.05²) (0.05 flat from data-vs-MC ρ differences in VR_asym, fixed before unblinding), ⊕ non-QCD normalisation. Prediction total QCD in A: **80 200 ± 400 (stat) ± 5 500 (syst, linear sum)**.

**Validation.**
| test | ratio obs/pred | χ²/ndf (stat only) | χ²/ndf (with syst) |
|---|---|---|---|
| MC closure SR | 0.991 | 37/17 | – (this defines the syst) |
| MC closure VR_asym / VR_pt1 / VR_n2 | 0.94 / 0.90 / 0.99 | 2050/17, 7/6, 13.5/17 | – |
| Data VR_asym (asym>0.3) | 1.009 | 1560/17 | 20.7/17 |
| Data VR_pt1 (200<pT2<300) | 0.977 | 15/7 | 3.2/7 |
| Data VR_n2 (shifted tag inside D) | 1.018 | 12/17 | 2.7/17 |

Stat-only χ² is large because stats are huge and non-closure is a few %; the systematic covers it. VR_asym needs the flat 5% (which was partly derived from it — not independent evidence).

**Unblinded SR.** observed 85 989 vs expected (QCD+other) 84 403: ratio 1.019, χ²/ndf = 9.3/17, max local |pull| 1.35 (300–330 GeV bin; no significant excess). Data counts: A 85 989, B 175 616, C 118 381, D 277 611.

**Open issues.** No signal MC: signal efficiency and B/C contamination (≈2ε(1−ε) of signal) untested — a real signal would inflate TF-based prediction slightly. No JES/JEC/mass-scale systematics on non-QCD. High-mass bins (>330 GeV) stat-limited (TF error 20–40%). Systematic is dominated by an ad hoc flat 5%.

**Outputs.** `results.json`, `fits/prediction.json`, `plots/`, `SKILLS_USED.md`, code in `scripts/`, condor reduction in `condor/`.

**Reproduce** (from workspace, `set +u; source inputs/py_env.sh; export PYTHONPATH=$PWD/scripts:$PYTHONPATH`):
`cd condor && condor_submit job.jdl` (reduction to EOS) → `python scripts/stage2.py 0 224 5` → `python scripts/build_base.py` → `python scripts/make_slim.py` → `python scripts/trig_counts.py; python scripts/trig_plots.py` → `python scripts/explore_sub.py; python scripts/scan_abcd.py; python scripts/scan2.py; python scripts/design_plots.py` → `python scripts/run_abcd.py` (blind) → `python scripts/unblind.py` → `python scripts/make_results.py`.
