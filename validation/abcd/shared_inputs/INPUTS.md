# Inputs (prepared by hand; contain no analysis-design choices)

<!-- prettier-ignore-start -->
<!-- kept verbatim: this is the text the agents were given -->

All paths relative to your workspace. inputs/ holds:

skim_files/<sample>.txt  one xrootd URL per line (root://cmseos.fnal.gov//store/...), Parquet files: a pre-made skim of
                         CMS Open Data 2016 UL NanoAODv9 (postVFP, eras G+H). Use these; you do not need to skim NanoAOD.
                         (In the repo copy the directory is written ${SKIM_BASE}; run_students.sh fills it in from the
                         SKIM_BASE environment variable. To rebuild the skim, run skim_payload.py on nanoaod_filelists/.)
  data:   data_JetHT_2016{G,H}            (24 files each)
  MC:     qcd_HT{300to500,500to700,700to1000,1000to1500,1500to2000,2000toInf}
          wqq_HT{400to600,600to800,800toInf}  zqq_HT{400to600,600to800,800toInf}   (W/Z -> qq, all flavours)
          tt_had tt_semilep  ww wz zz  hbb_ggf hbb_vbf
skim_payload.py          the script that made the skim (for reference only; do not rerun it). What it did:
  - only cut: at least one AK8 jet (FatJet) with pT > 250 GeV. No golden JSON, no trigger, no filter cut applied.
  - one row per event. Columns:
      run, luminosityBlock, event, MET_pt, PuppiMET_pt, fixedGridRhoFastjetAll, nFatJet
      filters        AND of the 2016 recommended MET filters (bool)
      HLT_*          27 single-jet, HT and AK8 trigger paths (False if the path is absent in that file);
                     trig_present = number of these paths present in the file
      j{0,1,2}_{pt,eta,phi,mass,msoftdrop,btagHbb,tau1,tau2,tau3,tau4,n2b1,n3b1,jetId}
                     the three leading AK8 jets in pT order (NanoAOD FatJet), -999 if the jet does not exist
      HT             scalar sum of AK4 jets with pT > 30 GeV, |eta| < 2.5
      nMuLoose, nEleLoose   loose muons / electrons with pT > 10 GeV
      MC only: genWeight, nTrueInt, j{i}_{hadronFlavour,nBHadrons,nCHadrons}, j{i}_bosonDR/bosonId (dR and pdgId
               of the nearest generator W, Z, H or top)
sumw.json                sum of genWeight over the FULL (pre-skim) MC samples, per sample. Use it, not the skim's sum.
xsec.csv                 sample,xsec_pb,source. Use lumi = 16.3 fb-1: weight = xsec*lumi*genWeight/sumw.
golden_2016.json         certified-lumi JSON (Legacy 2016); apply to data only (not applied in the skim).
nanoaod_filelists/       the NanoAOD files the skim was made from (records.json: file and event counts), for
                         completeness checks only.
py_env.sh                `set +u; source inputs/py_env.sh` for numpy/scipy/uproot/awkward/hist/mplhep/iminuit/pyarrow
                         (LCG 109). Works on condor workers. No ROOT-based fitting tools (Combine) are provided or needed.

The data skim is about 50 M rows x 78 columns per era: read only the columns you need, in chunks, or on condor.
Note: the LCG 109 pyarrow has no zstd codec; write Parquet with compression="snappy" (or none).
EOS scratch for condor outputs: root://cmseos.fnal.gov//store/user/<USER>/cms-marketplace-tests/abcd-2016/<WSNAME>/
<!-- prettier-ignore-end -->
