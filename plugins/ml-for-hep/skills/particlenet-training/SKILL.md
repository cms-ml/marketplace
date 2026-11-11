---
name: particlenet-training
description: >-
  Use when training or evaluating a ParticleNet-style (EdgeConv / dynamic
  graph CNN) or other point-cloud jet tagger on jet constituents (PF
  candidates, tracks, secondary vertices): setting up weaver-core (data
  config YAML, network config, `weaver` train and `--predict` commands),
  writing a minimal PyTorch EdgeConv instead, padding constituents to a fixed
  length with a mask, choosing points and features, flattening pT and mass
  with weaver reweighting, exporting to ONNX, finding torch on cvmfs (LCG
  views, /cvmfs/unpacked.cern.ch images) or a GPU on the LPC, or debugging
  "Need to specify `treename`", weaver finding no input files with root://
  paths, a DataLoader that hangs with --num-workers, or training that is far
  too slow on CPU.
metadata:
  summary: ParticleNet jet taggers with weaver-core or plain PyTorch, tested on CPU with the CMS Open Data H->bb sample
---

# ParticleNet training

## Overview

ParticleNet treats a jet as an unordered set of constituents. Each
constituent has **points** (coordinates for the k-nearest-neighbour graph,
usually Δη and Δφ to the jet axis) and **features** (log pT, log E, charge,
particle type, impact parameters ...). EdgeConv blocks build the kNN graph,
update every constituent from its neighbours, rebuild the graph in feature
space, and a global average over the real (masked) constituents feeds a
small classifier. Jets have different multiplicities, so constituents are
padded or clipped to a fixed length with a **mask**.

**Status: CPU smoke test only.** Both routes below were run on a cmslpc
interactive node on 10–50k jets for 1–3 epochs to prove that the commands,
inputs and outputs work. A full training (millions of jets, tens of epochs)
and the GPU route are **untested** here.

| Route                                          | When                                                                | Files                                                                                                                |
| ---------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **weaver-core** (the reference ParticleNet)    | Real trainings, GPU, many files, standard CMS tagger configs        | [assets/hbb_particlenet.yaml](assets/hbb_particlenet.yaml), [assets/particlenet_lite.py](assets/particlenet_lite.py) |
| **plain PyTorch** EdgeConv (`train_pnet_lite`) | Quick studies, no extra install, reading root:// directly, teaching | [scripts/train_pnet_lite.py](scripts/train_pnet_lite.py)                                                             |

The worked example is the CMS Open Data H→bb vs QCD AK8-jet sample with PF
candidates ([references/hbb-open-data-example.md](references/hbb-open-data-example.md)).
Kinematics are in **GeV**.

## When to Use

- Training a constituent-based jet tagger (H→bb, top, W/Z, quark/gluon)
- Converting ntuples with `pfcand_*` vectors into weaver inputs
- Producing per-jet scores with observers (soft-drop mass, pT, event number)
  for the `mass-sculpting-check` and `closure-tests` skills
- **Not** for flat per-event features (use `bdt-training`), and not for
  inference inside CMSSW (ONNX/SONIC; out of scope here)

## Key Concepts

| Term                    | Meaning                                                                                                         |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| `pf_points`             | (N, 2, P) coordinates for the first kNN: Δη, Δφ to the jet axis                                                 |
| `pf_features`           | (N, F, P) per-constituent features, standardised (weaver `auto` or fixed centre/scale), clipped to [−5, 5]      |
| `pf_mask`               | (N, 1, P) 1 for real constituents, 0 for padding; padding must not join any neighbourhood                       |
| P (`length`)            | Constituents kept per jet (sorted by pT in most ntuples); 100 covers AK8 jets in the Open Data sample (mean 45) |
| `pad_mode: wrap`        | weaver repeats the jet's own constituents instead of zero-padding (`constant` is required for the mask)         |
| Observers               | Columns copied unchanged into the prediction output (fj_sdmass, fj_pt, event_no) for the HEP checks             |
| `reweight_method: flat` | Per-class weights that flatten the (pT, m_SD) distribution: the net cannot learn the mass/pT prior              |
| `labels: type: simple`  | One-hot list of boolean branches; weaver writes `score_<label>` per class                                       |

**Split.** The Open Data record already ships `train/` and `test/`
directories; use them. When you make your own split, split by
`event_no` parity (`--extra-selection-train "event_no % 2 == 0"` in weaver,
`--split parity` in the script), never by random jets, so jets of one event
never sit on both sides.

## Canonical Patterns

### 1. Environment

```bash
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
python3 -c "import torch, torch_geometric, onnxruntime; print(torch.__version__, torch.cuda.is_available())"
# 2.10.0 False    (cmslpc interactive node, 2026-11; also torch_geometric 2.6.1, onnxruntime 1.23.2)
```

LCG_109 has torch (CPU build), so the plain-PyTorch route needs nothing else. For weaver:

```bash
python3 -m venv --system-site-packages <scratch>/venv-weaver
. <scratch>/venv-weaver/bin/activate
pip install weaver-core          # 0.5.4 tested; 86 s
```

This upgrades numba, pyarrow and lz4 inside the venv (weaver-core 0.5.4
pins numba ≥ 0.63.1, pyarrow ≥ 22, lz4 ≥ 4.3.3, above LCG_109's) and pip
warns about LCG packages it does not use; harmless inside a venv. The
lighter `pip install --no-deps weaver-core` (12 s) fails `pip check`
(awkward0 missing, older numba/pyarrow/lz4) but training, `--predict` and
`--export-onnx` on ROOT inputs all ran with it (awkward0 is only for `.awkd`).

Containers on `/cvmfs/unpacked.cern.ch/registry.hub.docker.com/` (listed
2026-11, not tested here): `fnallpc/fnallpc-docker:pytorch-2.0.0-cuda11.7-cudnn8-runtime-singularity`
(and older pytorch/tensorflow GPU images), `cmsml/cmsml:3.11-cuda`,
`coffeateam/coffea-almalinux9:*`. Run them with `apptainer exec`.

### 2. Make the input local and small

weaver expands `--data-train` with `glob.glob`, so root:// URLs are not
read. Copy a branch-reduced subset:

```bash
D=root://eospublic.cern.ch//eos/opendata/cms/datascience/HiggsToBBNtupleProducerTool/HiggsToBBNTuple_HiggsToBB_QCD_RunII_13TeV_MC
<skill>/scripts/make_jet_subset.py $D/train/ntuple_merged_10.root -o <scratch>/train_10.root --entries 50000
# N_JETS=50000  N_BRANCHES=53  SIZE_MB=113.7     (23 s, 0.77 GB RSS)
<skill>/scripts/make_jet_subset.py $D/test/ntuple_merged_0.root -o <scratch>/test_0.root --entries 50000
```

### 3. weaver: data config, network, train, predict

[assets/hbb_particlenet.yaml](assets/hbb_particlenet.yaml) is a complete
data config for this sample: `treename`, `new_variables` (mask, log pT/E,
labels), 14 `pf_features`, `labels`, `observers` (event_no, fj_pt, fj_eta,
fj_sdmass) and flat (pT, m_SD) reweighting.
[assets/particlenet_lite.py](assets/particlenet_lite.py) wraps
`weaver.nn.model.ParticleNet` (a CPU-sized default; the docstring has the
full ParticleNet parameters).

```bash
cp <skill>/assets/{hbb_particlenet.yaml,particlenet_lite.py} <scratch>/ && cd <scratch>
export OMP_NUM_THREADS=4
weaver --data-train train_10.root --data-config hbb_particlenet.yaml \
  --network-config particlenet_lite.py --model-prefix models/pnet_lite \
  --num-epochs 2 --samples-per-epoch 20000 --samples-per-epoch-val 5000 \
  --batch-size 256 --start-lr 5e-3 --optimizer ranger --gpus "" --num-workers 0 \
  --fetch-step 1 --in-memory --train-val-split 0.8 --log-file logs/train.log
weaver --predict --data-test test_0.root --data-config hbb_particlenet.yaml \
  --network-config particlenet_lite.py --model-prefix models/pnet_lite_best_epoch_state.pt \
  --batch-size 512 --gpus "" --num-workers 0 --predict-output pred/test_0.root
```

| Flag                                      | Meaning                                                                                                |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `--gpus ""`                               | CPU. On a GPU node: `--gpus 0`                                                                         |
| `--samples-per-epoch`                     | Jets per epoch (sampled); keep small for tests                                                         |
| `--fetch-step 1 --in-memory`              | Load the whole (small) file once and keep it                                                           |
| `--train-val-split 0.8`                   | Validation from the training files                                                                     |
| `--extra-selection-train "event_no%2==0"` | Your own parity split (with `--extra-selection-test "event_no%2==1"`)                                  |
| `--predict-output x.root`                 | Tree `Events`: `score_is_qcd`, `score_is_hbb`, labels, observers; one row per jet                      |
| `--predict-output x.parquet`              | One array column `scores` (per class) plus `_label_` and the observers                                 |
| `--export-onnx m.onnx`                    | With `--model-prefix <dir>/<x>_best_epoch_state.pt`; writes `<dir>/m.onnx` and `<dir>/preprocess.json` |

On the first run weaver computes the `auto` standardisation and writes
`hbb_particlenet.<hash>.auto.yaml`. Keep it with the model: prediction must
use the same numbers.

### 4. Plain PyTorch (no weaver)

```bash
<skill>/scripts/train_pnet_lite.py --train <scratch>/train_10.root --test <scratch>/test_0.root \
    --max-train 12000 --max-test 12000 --epochs 2 --batch-size 128 --threads 3 \
    --out-dir <scratch>/lite_run --onnx [--resume]
# PROGRESS step=1 value=0.9581
# N_TRAIN=10800 N_VAL=1200 N_TEST=12000 BEST_EPOCH=1 AUC_TRAIN=0.9541 AUC_VAL=0.9581 AUC_TEST=0.955 ONNX_MAX_ABS_DIFF=1.77e-05
```

That is the smoke test: 12 000 jets, 2 epochs, about 5 minutes per epoch on
3 threads of a busy shared node, 3.5 GB RSS. The second epoch was run with
`--resume` from `last.pt` (written after every epoch), which is how a
killed or time-limited job continues. `metrics.json` holds the same
KEY=VALUE results; the `PROGRESS` lines let the `hyperparam-scan` skill
prune trials.

It reads root:// URLs directly, pads to `--n-const` (default 100), balances
the classes, keeps the best epoch on a 10% validation split, and writes
`scores_test.parquet` and `scores_train.parquet` (score, fj_sdmass, fj_pt,
is_signal, event_no). `--dry-run` reads and reports class counts only.
Exit codes: 0 ok, 1 not learning (NaN loss, AUC_TEST < 0.6) or ONNX export
failed, 2 bad input.

### 5. Evaluate (always)

The scores files feed the model-agnostic checks (label column is
`is_signal`, mass is `fj_sdmass`):

```bash
<model-evaluation>/scripts/evaluate.py <run>/scores_test.parquet --train <run>/scores_train.parquet \
    --label is_signal --bkg-effs 0.1,0.01 --out-dir <run>/eval
# AUC_TEST=0.95497 AUC_ERR=0.00213 KS_P_SIG=0.439 KS_P_BKG=0.25 OVERTRAINED=0 SIG_EFF_AT_BKG_0.01=0.5005 STATUS=PASS
<mass-sculpting-check>/scripts/sculpting.py <run>/scores_test.parquet --label is_signal \
    --mass fj_sdmass --mass-range 40,200 --bkg-effs 0.1,0.01 --out-dir <run>/sculpt
# DCOR=0.2098 CHI2_NDF_0.1=5.39 VERDICT_0.1=SCULPTED VERDICT_0.01=LOW_STAT STATUS=FAIL   (exit 1)
```

The smoke-test tagger **sculpts the QCD soft-drop mass** (no mass
flattening in the plain script), as expected. Signal efficiency at fixed
background efficiency is the number to compare, not the AUC.

### 6. GPU (not tested here)

The interactive nodes have no GPU (`nvidia-smi` missing). On 2026-11-09,
`condor_status -constraint 'CUDACapability =!= undefined'` from cmslpc
returned **no** GPU slots in the LPC pool, so `request_GPUs = 1` in a submit
file could not be tested. Ask the LPC (or use lxplus-gpu / a university
cluster) and check with that `condor_status` command first. weaver then
needs `--gpus 0`; the script needs `--device cuda`.

## Gotchas

- **Training on CPU is slow.** The lite network (2 EdgeConv blocks, k=16,
  P=100) trained at 26–29 jets/s in weaver (3 threads) and took about
  5 minutes per 10.8k-jet epoch in the plain script (3 threads, busy node). Tens of thousands
  of jets and 1–3 epochs is a smoke test, not a tagger. Scale on a GPU.
- **1x1 `Conv2d` on a permuted neighbour tensor**: the backward was ~40×
  slower than the forward (profiler: `aten::convolution_backward` 97% of the
  time; LCG_109 torch is built without MKLDNN). `train_pnet_lite.py` uses
  `nn.Linear` on channels-last tensors instead (~15× faster per jet).
- **`AssertionError` in `symbolic_opset9.py ... cdist`** on ONNX export:
  `torch.cdist` does not export with a dynamic batch axis. Compute the
  distances with a matmul (as the script does).
- **weaver prints `Cannot compute metric roc_auc_score: y should be a 1d
array, got an array of shape (N, 2)`** (scikit-learn 1.8): its
  "validation metric" is then the accuracy. Compute the AUC from the
  `--predict` output.
- **Peak memory comes from activations** of size batch × P × k × channels:
  4.3 GB RSS when scoring in batches of 1024; the script now scores in
  batches of 256.
- **weaver hung with `--num-workers 1`** on CPU: the progress bar never
  moved and both processes sat at 0% CPU for 9 minutes. `--num-workers 0`
  worked.
- **`Need to specify treename as more than one trees are found`**: the Open
  Data files have `deepntuplizer/tree` and an extra cycle. Set
  `treename: deepntuplizer/tree` in the data config.
- **root:// inputs** are silently empty in weaver (glob). Copy a subset with
  `make_jet_subset.py` or xrdcp the file.
- **Reweighting drops jets.** With `reweight_vars`, jets outside the bin
  edges are discarded in training (`reweight_discard_under_overflow`
  defaults to true). Make the training `selection` match the edges, and use
  a looser `test_time_selection` so the sculpting check sees the full mass
  range.
- **Labels must be exclusive.** `type: simple` takes the argmax of the
  label list; in this sample `label_H_bb == fj_isH` and `fj_isQCD` is its
  complement (checked on 20k jets). Some H-sample jets are QCD-labelled
  (`sample_isQCD == 0` but `fj_isQCD == 1`): label by truth, not by sample.
- **`event_no` is not unique** across the H and QCD samples (values repeat):
  fine for a parity split, useless as a jet ID.
- **Legacy ONNX exporter**: `torch.onnx.export(..., dynamo=False)` warns
  "You are using the legacy TorchScript-based ONNX export" on torch 2.10
  but works; onnxruntime agreed to 7e-5 on the smoke test.

## Reference Files

- [scripts/make_jet_subset.py](scripts/make_jet_subset.py): first N jets,
  selected branches, written locally with uproot (`--dry-run`).
- [scripts/train_pnet_lite.py](scripts/train_pnet_lite.py): plain-PyTorch
  ParticleNet-lite: read, pad, train (`--resume`), scores parquet,
  `metrics.json`, ONNX check.
- [assets/hbb_particlenet.yaml](assets/hbb_particlenet.yaml): weaver data
  config for the Open Data H→bb sample.
- [assets/particlenet_lite.py](assets/particlenet_lite.py): weaver network
  config around `weaver.nn.model.ParticleNet`.
- [references/hbb-open-data-example.md](references/hbb-open-data-example.md):
  the tested runs, with timings, memory and AUCs.

## Docs

- H. Qu, L. Gouskos, "ParticleNet: Jet Tagging via Particle Clouds",
  Phys. Rev. D 101 (2020) 056019, <https://arxiv.org/abs/1902.08570>
- Y. Wang et al., "Dynamic Graph CNN for Learning on Point Clouds" (EdgeConv),
  <https://arxiv.org/abs/1801.07829>
- weaver-core: <https://github.com/hqucms/weaver-core> (ParticleNet model:
  `weaver/nn/model/ParticleNet.py`)
- Example network configs: <https://github.com/jet-universe/particle_transformer/blob/main/networks/example_ParticleNet.py>
- CMS Open Data, "Sample with jet, track and secondary vertex properties for
  Hbb tagging ML studies", doi:10.7483/OPENDATA.CMS.JGJX.MS7Q,
  <https://opendata.cern.ch/record/12102>
- CMS, "Identification of heavy, energetic, hadronically decaying particles
  using machine-learning techniques", JINST 15 (2020) P06005,
  <https://arxiv.org/abs/2004.08262>
