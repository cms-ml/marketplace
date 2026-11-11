# Worked example: H→bb vs QCD on CMS Open Data, CPU only

Read this reference when you want the exact commands, timings, memory and
results of the tested runs behind the `particlenet-training` skill, or need a
baseline to compare your own small training with.

Contents:

1. Sample
2. Environment
3. Input subsets
4. weaver-core run
5. Plain-PyTorch run
6. What these numbers do and do not show

All runs: cmslpc interactive node (el9, 8 cores, ~7 GB free memory, shared
with other users: load average 6–13 during the runs), 2026-11-09, no GPU.

## 1. Sample

CMS Open Data, "Sample with jet, track and secondary vertex properties for
Hbb tagging ML studies" (doi:10.7483/OPENDATA.CMS.JGJX.MS7Q, record 12102).
AK8 jets with pT > 200 GeV from H→bb and QCD simulation, 200 000 jets per
file, 1.2 GB per ROOT file, tree `deepntuplizer/tree`:

```text
root://eospublic.cern.ch//eos/opendata/cms/datascience/HiggsToBBNtupleProducerTool/HiggsToBBNTuple_HiggsToBB_QCD_RunII_13TeV_MC/
  train/ntuple_merged_{9..90}.root    (82 files; .h5 copies next to them)
  test/ntuple_merged_{0..8}.root      (9 files)
```

Branches used: `fj_pt`, `fj_sdmass`, `fj_isQCD`, `label_H_bb` (equal to
`fj_isH` in the first 20k jets checked), `event_no`, and the `pfcand_*`
vectors (`ptrel`, `erel`, `etarel`, `phirel`, `deltaR`, `charge`,
`isChargedHad`, `isNeutralHad`, `isGamma`, `isEl`, `isMu`, `dxysig`, `dzsig`,
`puppiw`). `n_pfcands` has mean 45, max 189 in the first 20k jets. About 13%
of jets are H→bb.

## 2. Environment

| Item            | Version                                                       |
| --------------- | ------------------------------------------------------------- |
| LCG view        | LCG_109 x86_64-el9-gcc15-opt (Python 3.13.11)                 |
| torch           | 2.10.0 (CPU; `torch.backends.mkldnn.is_available()` is False) |
| torch_geometric | 2.6.1 (not needed by either route)                            |
| onnxruntime     | 1.23.2                                                        |
| uproot/awkward  | 5.6.0 / 2.8.9                                                 |
| weaver-core     | 0.5.4 (venv, `--system-site-packages`)                        |

`pip install weaver-core` (full deps, 86 s) upgraded numba to 0.68.1,
pyarrow to 26.0.1 and added awkward0 0.15.5 and lz4 in the venv.
`pip install --no-deps weaver-core` (12 s) leaves `pip check` complaining
(awkward0 missing; numba 0.62.0, pyarrow 20.0.0, lz4 4.0.0 below the pins),
but **training, `--predict` to parquet and `--export-onnx` all ran** on ROOT
input with it. awkward0 is only imported for `.awkd` files.

## 3. Input subsets

```bash
D=root://eospublic.cern.ch//eos/opendata/cms/datascience/HiggsToBBNtupleProducerTool/HiggsToBBNTuple_HiggsToBB_QCD_RunII_13TeV_MC
make_jet_subset.py $D/train/ntuple_merged_10.root -o train_10.root --entries 50000
make_jet_subset.py $D/test/ntuple_merged_0.root  -o test_0.root  --entries 50000
# N_JETS=50000 N_BRANCHES=53 SIZE_MB=113.7   22.9 s, 0.77 GB max RSS (train)
```

After `300 < fj_pt < 2000` GeV: 39 217 training jets, 39 145 test jets (6003
H→bb, 33 142 QCD).

## 4. weaver-core run

Data config [../assets/hbb_particlenet.yaml](../assets/hbb_particlenet.yaml),
network [../assets/particlenet_lite.py](../assets/particlenet_lite.py)
(2 EdgeConv blocks (32,32,32), (64,64,64), k=16, fc 128; weaver reports
49.94 M FLOPs per jet).

```bash
export OMP_NUM_THREADS=3
weaver --data-train train_10.root --data-config hbb_particlenet.yaml \
  --network-config particlenet_lite.py --model-prefix models/pnet_lite \
  --num-epochs 2 --samples-per-epoch 20000 --samples-per-epoch-val 5000 \
  --batch-size 256 --start-lr 5e-3 --optimizer ranger --gpus "" --num-workers 0 \
  --fetch-step 1 --in-memory --train-val-split 0.8 --log-file logs/train.log
```

- Training 25.8 and 29.2 jets/s (epochs 0, 1), validation ~120–150 jets/s.
  Wall time 25 min 50 s, max RSS 2.45 GB.
- weaver's own validation AUC failed: `WARNING: Cannot compute metric
roc_auc_score: y should be a 1d array, got an array of shape (4864, 2)
instead.` (scikit-learn 1.8). The "validation metric" it then prints is
  the accuracy (0.772 epoch 0, 0.761 epoch 1). Compute the AUC yourself from
  the predict output.
- With `--num-workers 1` the same command hung (0% CPU for 9 minutes,
  progress bar at 0 steps). `--num-workers 0` is the CPU setting that worked.

```bash
weaver --predict --data-test test_0.root --data-config hbb_particlenet.yaml \
  --network-config particlenet_lite.py --model-prefix models/pnet_lite_best_epoch_state.pt \
  --batch-size 512 --gpus "" --num-workers 0 --predict-output pred/test_0.root
```

ROOT output: tree `Events` with `is_qcd`, `score_is_qcd`, `is_hbb`,
`score_is_hbb`, `_label_`, `event_no`, `fj_pt`, `fj_eta`, `fj_sdmass`, one
row per jet (39 145). A `.parquet` output instead has a single array column
`scores` plus `_label_` and the observers.

Result on the 39 145 test jets: AUC 0.757 (0.880 inside the training window
40 < m_SD < 200 GeV); signal efficiency 4.3% at 1% QCD efficiency. This
network saw only 40k (pT, m_SD)-flattened jets and is **undertrained**: it
tests the commands, not the architecture.

`--export-onnx t.onnx` writes `models/t.onnx` next to `--model-prefix`
(not in the working directory) plus `models/preprocess.json`; onnxruntime
sees inputs `pf_points (N,2,n_pf)`, `pf_features (N,14,n_pf)`,
`pf_mask (N,1,n_pf)` and output `softmax (N,2)`.

## 5. Plain-PyTorch run

```bash
train_pnet_lite.py --train train_10.root --test test_0.root \
  --max-train 12000 --max-test 12000 --epochs 1 --batch-size 128 --threads 3 --out-dir run
train_pnet_lite.py ... --epochs 2 --resume --onnx --out-dir run     # same arguments, continues from run/last.pt
```

CPU smoke test (2026-11-10, node load ~20 on 8 cores): 10 800 training,
1 200 validation and 12 000 test jets (1 866 signal, 10 134 QCD).

| Stage                       | Wall time | Result                                                                       |
| --------------------------- | --------- | ---------------------------------------------------------------------------- |
| epoch 0                     | 583 s     | val AUC 0.9549, test AUC 0.9497                                              |
| epoch 1 (`--resume`)        | 294 s     | val AUC 0.9581, test AUC 0.9550, train AUC 0.9541; 3.5 GB peak RSS           |
| ONNX vs PyTorch             |           | max abs score difference 1.77e-05 on 2 048 jets                              |
| `evaluate.py`               |           | AUC 0.9550 ± 0.0021; signal eff. 0.50 at 1% QCD eff.; KS p 0.44 / 0.25; PASS |
| `sculpting.py` (40–200 GeV) |           | dCor 0.21; 10% WP χ²/ndf 5.4 (SCULPTED); 1% WP LOW_STAT; FAIL                |

An earlier interrupted run (27 000 training jets, 4 threads, idle node)
reached val AUC 0.953 and 0.970 after epochs 0 and 1 at 321 s per epoch.
Nothing larger was run: a full training and any GPU run are untested.

No mass flattening and only class balancing here, so the network may use
the jet mass: run the `mass-sculpting-check` skill on `scores_test.parquet`
before trusting a cut on it.

## 6. What these numbers do and do not show

- They show that the commands run, the input pipeline is right (labels,
  padding, mask, observers), and the scores files have what the HEP checks
  need.
- They are not a tagger performance: tens of thousands of jets and a few
  epochs on a shared CPU. The CMS ParticleNet trainings use millions of jets
  on GPUs.
- The weaver and plain-PyTorch numbers are not comparable: different
  weighting (flat (pT, m_SD) vs class balance only), training size, epochs
  and optimiser.
