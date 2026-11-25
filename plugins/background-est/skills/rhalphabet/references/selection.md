# Selection that makes rhalphabet work

Loaded from SKILL.md (workflow step 1). The transfer factor is only smooth and
low-order if the selection is built for it. Every number below is yours to
choose and to justify from simulation; none is a recommendation.

## 1. Substructure preselection in BOTH regions (decorrelated)

Two-prong selection (N2, D2, tau21) is applied before the pass/fail split, to
pass **and** fail alike, so that both regions contain the same kind of jets and
the pass/fail ratio only reflects the flavour tagger.

A plain cut on N2 sculpts the QCD mass spectrum (N2 depends on rho). Use a
designed decorrelated tagger (DDT): cut on `N2 - X(rho, pT) < 0`, where
`X` is the N2 quantile in QCD simulation at a fixed QCD efficiency in each
(rho, pT) cell. [scripts/ddt_map.py](../scripts/ddt_map.py) builds and applies
the map:

```bash
python scripts/ddt_map.py build --files skim/qcd_*.parquet --var n2b1 --weight xsec_weight \
    --select "(msd>40)&(pt>400)" --eff <EFF> --direction below \
    --rho-bins -7 -1 30 --pt-bins 400 1200 16 --smooth 1 --parity even --out n2ddt.json
python scripts/ddt_map.py closure --map n2ddt.json --files skim/qcd_*.parquet --parity odd \
    --select "(msd>40)&(pt>400)"
```

- Choose `<EFF>` from a scan (e.g. signal-over-sqrt-background, or top and
  QCD rejection at fixed signal efficiency) and record the scan.
- Closure must be tested on events **not** used to build the map
  (`--parity`, which splits by the `event` column: keep the event number in
  the skim; without it the script falls back to row index and warns).
  `closure` returns `"pass"` (global efficiency within 3% of the target, cell
  pull rms < 1.5 or cell rms < 5%): if it fails, use coarser cells or more
  smoothing, and do not proceed with a 10% cell spread.
- `n2b1 <= 0` or undefined (soft drop failed) jets must be removed or handled
  explicitly; check how many there are inside your rho range.
- The same function makes a **cut map for a tagger score** (`--direction
  above`): use it when the flavour tagger itself is correlated with mass.

## 2. Flavour-tagger working point (pass/fail split)

- Pass = tagger above the working point, fail = below, after the
  preselection. Pick the working point from the QCD mistag rate and signal
  efficiency in simulation, and quote both (the QCD MC pass fraction sets
  the TF normalisation).
- Check the QCD pass fraction against msd in simulation before anything else:
  if it varies strongly, decorrelate (cut map) or expect a higher-order TF.

## 3. Candidate jet

Leading-pT AK8 jet is the simplest choice. Highest-tagger-score jet among the
two leading jets increases signal efficiency but changes the QCD composition
of the fail region; whatever you choose, use it for data, every MC sample and
every region.

## 4. Suppress top and leptons

Hadronic top passes two-prong and b taggers. Without suppression it can be
several percent of the pass region and bends the apparent TF at high mass.

- lepton veto (loose muons and electrons) in the signal region;
- MET cut (semileptonic top and W+jets);
- optional: veto events with a b-tagged AK4 jet in the hemisphere opposite to
  the AK8 jet (dphi > pi/2), which removes much of ttbar. It also removes
  QCD bb pair production (gluon splitting and flavour excitation recoil
  differently), so it changes the QCD flavour mix in pass with an msd- and
  pT-dependent rate and therefore the TF shape. Use it only if top is a
  significant part of pass without it (show the composition both ways), and
  if you compare with a result that did not use it, show the TF without it too;
- show the pass-region composition per process after these cuts.

## 5. Resonant templates: generator matching and flavour

The TF describes QCD only; everything else is subtracted (TF-only study) or
fitted as a template (full fit). For W, Z, H and top:

- **Match** the AK8 jet to the generator boson (dR < 0.8 and, for V and H,
  both daughter quarks inside the jet). Unmatched V+jets events are QCD-like;
  they are a negligible part of QCD and must not sit in the V template where
  they would add a non-peaking component.
- **Split by flavour**: Z(bb) vs Z(qq, cc) and W(cs) vs W(ud). A b tagger
  passes Z(bb) at signal-like rates and the rest at mistag rates; mixing them
  in one template mis-models the pass region (NanoAOD: GenPart daughters of
  the boson, or `FatJet_nBHadrons >= 2` as a proxy).
- Normalise to cross section x luminosity; quote the resonant fraction of
  pass and fail.

## 6. Trigger and pT range

- Measure the trigger efficiency versus jet pT (and msd) with an orthogonal
  reference trigger (`cms:trigger-efficiency` skill). Either start the pT range
  on the plateau, or apply an efficiency correction and its uncertainty.
- Check that every HLT path in the OR exists in every era used (paths change
  between run periods).

## 7. Binning and rho range (from simulation)

- **msd bins**: about the jet mass resolution (a few GeV to ~10 GeV); low edge
  above the region where soft-drop and Sudakov effects dominate.
- **pT bins**: equal statistics roughly, finer at low pT; the last bin wide.
  Compute the QCD-weighted mean pT per bin; the TF is evaluated there.
- **rho range**: plot the fail-region QCD MC msd shape in rho for each pT bin
  (normalised). Keep the rho window where the shapes agree; drop the high-rho
  edge (jet mass near the cone size: rho close to 2 ln(R/2)) and the very low
  rho region where few jets sit and the soft drop is unreliable. Bins outside
  the window are masked in pass and fail alike.
- Write each choice and the plot that justifies it in the report.

## Gotchas

- **Fail region agrees with data by construction** in a fit with one free QCD
  yield per fail bin. A good fail post-fit plot is not a validation.
- **Signal in fail**: a signal at a 1 % mistag-like pass rate still puts most of
  its events in fail; keep it in the fail model or blind it there too.
- **Different selection for data and MC** (e.g. trigger bit applied to data
  only) changes the pass fraction; apply the trigger to MC too, or show the
  pass fraction is independent of it.
