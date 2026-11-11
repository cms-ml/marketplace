#!/usr/bin/env python3
"""Train a small ParticleNet-style (EdgeConv) jet tagger in plain PyTorch, on CPU or GPU.

No weaver, no torch_geometric: the k-nearest-neighbour EdgeConv is written
with torch.topk/gather, so it runs with any PyTorch >= 2 (tested: LCG_109,
torch 2.10.0 CPU). Reads jet constituents directly with uproot (local path or
root:// URL), pads them to --n-const, trains a binary signal-vs-background
classifier, and writes per-jet test scores with the observers needed for
mass-sculpting and closure checks.

Defaults match the CMS Open Data H->bb vs QCD ntuples
(doi:10.7483/OPENDATA.CMS.JGJX.MS7Q, tree deepntuplizer/tree):

    train_pnet_lite.py --train <scratch>/train_10.root --test <scratch>/test_0.root \
        --epochs 3 --out-dir <scratch>/pnet_lite --onnx

Split: --train/--test files (the record's own train/ and test/ directories), or
--split parity with --train only (event_no even = train, odd = test).
10% of the training jets are held out for the best-epoch choice.

Outputs in --out-dir: scores_test.parquet (score, fj_sdmass, fj_pt, is_signal,
event_no), scores_train.parquet (same, training jets, for the overtraining
check), model.pt (best epoch: state dict + feature standardisation), last.pt
(checkpoint after every epoch; --resume continues from it), metrics.json (the
KEY=VALUE results as JSON), model.onnx (--onnx).
Stdout: one "PROGRESS step=<epoch> value=<val AUC>" line per epoch (read by the
hyperparam-scan skill for pruning), then KEY=VALUE (N_TRAIN, N_VAL, N_TEST, N_TEST_BKG, EPOCHS, BEST_EPOCH,
AUC_TRAIN, AUC_VAL, AUC_TEST, SECONDS, OUT_DIR, ONNX_MAX_ABS_DIFF).
Diagnostics on stderr. Exit codes: 0 ok, 1 training failed a sanity check
(NaN loss or AUC_TEST < 0.6), 2 bad input. --dry-run reads the inputs, prints
the shapes and class counts, and writes nothing. Kinematics in GeV.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time

import numpy as np

FLAGS = ["pfcand_charge", "pfcand_isChargedHad", "pfcand_isNeutralHad", "pfcand_isGamma",
         "pfcand_isEl", "pfcand_isMu", "pfcand_puppiw"]
STANDARDISE = ["ptrel_log", "erel_log", "pfcand_dxysig", "pfcand_dzsig"]
GEOM = ["pfcand_etarel", "pfcand_phirel", "pfcand_deltaR"]
FEATURES = STANDARDISE + GEOM + FLAGS


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def read_jets(paths, tree, max_jets, n_const, sig, bkg, pt_min, pt_max):
    """Return dict with points (N,2,P), feats (N,F,P), mask (N,1,P) and per-jet observers."""
    import awkward as ak
    import uproot

    branches = ["event_no", "fj_pt", "fj_sdmass", sig, bkg, "pfcand_ptrel", "pfcand_erel",
                "pfcand_dxysig", "pfcand_dzsig", *GEOM, *FLAGS]
    out, n = [], 0
    for p in paths:
        left = None if max_jets is None else max_jets - n
        if left is not None and left <= 0:
            break
        t = uproot.open(p)[tree]
        a = t.arrays(branches, entry_stop=None if left is None else min(t.num_entries, 4 * left))
        keep = (a["fj_pt"] > pt_min) & (a["fj_pt"] < pt_max) & ((a[sig] == 1) | (a[bkg] == 1))
        a = a[keep]
        if left is not None:
            a = a[:left]
        out.append(a)
        n += len(a)
    a = ak.concatenate(out)
    cols = {"ptrel_log": np.log(np.maximum(a["pfcand_ptrel"], 1e-6)),
            "erel_log": np.log(np.maximum(a["pfcand_erel"], 1e-6))}
    for c in FEATURES:
        if c not in cols:
            cols[c] = a[c]

    def pad(x):
        return ak.to_numpy(ak.fill_none(ak.pad_none(x, n_const, clip=True), 0.0)).astype(np.float32)

    feats = np.stack([pad(cols[c]) for c in FEATURES], axis=1)
    points = np.stack([pad(a["pfcand_etarel"]), pad(a["pfcand_phirel"])], axis=1)
    mask = pad(ak.ones_like(a["pfcand_etarel"]))[:, None, :]
    return {"points": points, "feats": feats, "mask": mask,
            "is_signal": ak.to_numpy(a[sig]).astype(np.int8),
            "fj_pt": ak.to_numpy(a["fj_pt"]).astype(np.float32),
            "fj_sdmass": ak.to_numpy(a["fj_sdmass"]).astype(np.float32),
            "event_no": ak.to_numpy(a["event_no"]).astype(np.int64)}


def subset(d, sel):
    return {k: v[sel] for k, v in d.items()}


def build_model(n_feat, k=16, convs=((32, 32, 32), (64, 64, 64)), fc=128, dropout=0.1):
    """ParticleNet-style dynamic-graph CNN. Inputs (B,2,P), (B,F,P), (B,1,P) as in weaver.

    Internally channels-last with nn.Linear instead of 1x1 Conv2d: in the LCG_109
    torch build (no MKLDNN) the Conv2d backward on CPU was ~40x slower than the forward.
    """
    import torch
    from torch import nn

    def knn(x, k):  # x: (B, P, C); padded points are pushed far away by the caller
        # squared distances via matmul (torch.cdist does not export to ONNX with a dynamic batch)
        xx = (x * x).sum(dim=-1, keepdim=True)
        d = xx - 2 * torch.matmul(x, x.transpose(1, 2)) + xx.transpose(1, 2)
        return d.topk(k=k + 1, dim=-1, largest=False)[1][:, :, 1:]  # (B, P, k), drop self

    def gather(x, idx):  # x (B, P, C), idx (B, P, k) -> (B, P, k, C)
        B, P, C = x.shape
        flat = (idx + torch.arange(B, device=x.device).view(-1, 1, 1) * P).reshape(-1)
        return x.reshape(B * P, C)[flat].view(B, P, idx.shape[-1], C)

    class LinBN(nn.Module):  # Linear + BatchNorm over the last dim + ReLU
        def __init__(self, cin, cout, act=True):
            super().__init__()
            self.lin, self.bn = nn.Linear(cin, cout, bias=False), nn.BatchNorm1d(cout)
            self.act = nn.ReLU() if act else nn.Identity()

        def forward(self, x):
            s = x.shape
            return self.act(self.bn(self.lin(x).reshape(-1, self.lin.out_features))
                            ).reshape(*s[:-1], self.lin.out_features)

    class EdgeConv(nn.Module):
        def __init__(self, k, cin, couts):
            super().__init__()
            self.k = k
            layers, c = [], 2 * cin
            for co in couts:
                layers.append(LinBN(c, co))
                c = co
            self.mlp = nn.Sequential(*layers)
            self.sc = LinBN(cin, couts[-1], act=False)
            self.act = nn.ReLU()

        def forward(self, pts, x, mask):  # (B,P,C), (B,P,C), (B,P,1)
            nb = gather(x, knn(pts, self.k))
            xi = x.unsqueeze(2).expand_as(nb)
            h = self.mlp(torch.cat([xi, nb - xi], dim=-1)).mean(dim=2)
            return self.act(h + self.sc(x)) * mask

    class PNetLite(nn.Module):
        def __init__(self):
            super().__init__()
            self.bn = nn.BatchNorm1d(n_feat)
            blocks, c = [], n_feat
            for co in convs:
                blocks.append(EdgeConv(k, c, co))
                c = co[-1]
            self.blocks = nn.ModuleList(blocks)
            self.head = nn.Sequential(nn.Linear(c, fc), nn.ReLU(), nn.Dropout(dropout), nn.Linear(fc, 2))

        def forward(self, points, feats, mask):
            shift = (1 - mask) * 1e9  # padded constituents far from everything
            x = (self.bn(feats) * mask).transpose(1, 2)  # -> (B, P, F)
            m = mask.transpose(1, 2)
            pts = (points + shift).transpose(1, 2)
            for b in self.blocks:
                x = b(pts, x, m)
                pts = x + (1 - m) * 1e9  # dynamic graph: next kNN in feature space
            pooled = x.sum(dim=1) / m.sum(dim=1).clamp(min=1)
            return self.head(pooled)

    return PNetLite()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--train", nargs="+", required=True, help="training ROOT files (path or root://)")
    p.add_argument("--test", nargs="*", default=[], help="test ROOT files (with --split files)")
    p.add_argument("--split", choices=["files", "parity"], default="files",
                   help="files: --train vs --test; parity: event_no even=train, odd=test (default: files)")
    p.add_argument("--tree", default="deepntuplizer/tree")
    p.add_argument("--signal", default="label_H_bb", help="signal label branch (default: %(default)s)")
    p.add_argument("--background", default="fj_isQCD", help="background label branch (default: %(default)s)")
    p.add_argument("--max-train", type=int, default=40000, help="max training jets after cuts")
    p.add_argument("--max-test", type=int, default=40000, help="max test jets after cuts")
    p.add_argument("--n-const", type=int, default=100, help="constituents per jet (pad/clip)")
    p.add_argument("--pt-min", type=float, default=300.0, help="jet pT min [GeV]")
    p.add_argument("--pt-max", type=float, default=2000.0, help="jet pT max [GeV]")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=2e-3)
    p.add_argument("--threads", type=int, default=4, help="torch CPU threads (default: 4)")
    p.add_argument("--device", default="cpu", help="cpu or cuda (default: cpu)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out-dir", default="pnet_lite_out")
    p.add_argument("--resume", action="store_true", help="continue from <out-dir>/last.pt if it exists")
    p.add_argument("--onnx", action="store_true", help="also export model.onnx and compare with onnxruntime")
    p.add_argument("--dry-run", action="store_true", help="read inputs, print shapes, write nothing")
    a = p.parse_args()
    if a.split == "files" and not a.test:
        log("error: --split files needs --test files")
        return 2

    t0 = time.time()
    try:
        if a.split == "files":
            tr = read_jets(a.train, a.tree, a.max_train, a.n_const, a.signal, a.background, a.pt_min, a.pt_max)
            te = read_jets(a.test, a.tree, a.max_test, a.n_const, a.signal, a.background, a.pt_min, a.pt_max)
        else:
            allj = read_jets(a.train, a.tree, a.max_train + a.max_test, a.n_const, a.signal, a.background,
                             a.pt_min, a.pt_max)
            even = allj["event_no"] % 2 == 0
            tr, te = subset(allj, even), subset(allj, ~even)
    except Exception as e:  # noqa: BLE001
        log(f"error: cannot read inputs: {type(e).__name__}: {e}")
        return 2
    for name, d in (("train", tr), ("test", te)):
        log(f"# {name}: {len(d['is_signal'])} jets, signal {int(d['is_signal'].sum())}, "
            f"feats {d['feats'].shape}, read in {time.time() - t0:.0f} s")
    if len(tr["is_signal"]) == 0 or len(te["is_signal"]) == 0 or tr["is_signal"].min() == tr["is_signal"].max():
        log("error: empty sample or only one class in training")
        return 2
    if a.dry_run:
        print(f"N_TRAIN={len(tr['is_signal'])}\nN_TEST={len(te['is_signal'])}\n"
              f"N_TEST_BKG={int((te['is_signal'] == 0).sum())}\nN_FEATURES={tr['feats'].shape[1]}\nDRY_RUN=1")
        return 0

    import pandas as pd
    import torch
    from sklearn.metrics import roc_auc_score

    torch.manual_seed(a.seed)
    torch.set_num_threads(a.threads)
    rng = np.random.default_rng(a.seed)
    os.makedirs(a.out_dir, exist_ok=True)

    # standardise the log-pt/energy and impact-parameter features on valid constituents of the training set
    ns = len(STANDARDISE)
    m = tr["mask"][:, 0, :].astype(bool)
    centre = np.array([np.median(tr["feats"][:, i, :][m]) for i in range(ns)], dtype=np.float32)
    scale = np.array([np.std(tr["feats"][:, i, :][m]) or 1.0 for i in range(ns)], dtype=np.float32)

    def prep(d):
        f = d["feats"].copy()
        f[:, :ns, :] = np.clip((f[:, :ns, :] - centre[None, :, None]) / scale[None, :, None], -5, 5)
        f *= d["mask"]
        return torch.from_numpy(d["points"]), torch.from_numpy(f), torch.from_numpy(d["mask"])

    perm = rng.permutation(len(tr["is_signal"]))
    nval = max(1, len(perm) // 10)
    va, trn = subset(tr, perm[:nval]), subset(tr, perm[nval:])
    Xtr, Xva, Xte = prep(trn), prep(va), prep(te)
    ytr = torch.from_numpy(trn["is_signal"].astype(np.int64))
    # class balancing: each class gets the same total weight
    frac = ytr.float().mean().item()
    cw = torch.tensor([0.5 / (1 - frac), 0.5 / frac])
    log(f"# signal fraction {frac:.3f}, class weights {cw.tolist()}")

    dev = torch.device(a.device)
    model = build_model(Xtr[1].shape[1]).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, a.epochs))
    lossf = torch.nn.CrossEntropyLoss(weight=cw.to(dev))

    def predict(X, bs=256):  # larger batches raise the peak memory (B*P*k*C activations)
        model.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(X[0]), bs):
                lo = model(*(x[i:i + bs].to(dev) for x in X))
                out.append(torch.softmax(lo, dim=1)[:, 1].cpu().numpy())
        return np.concatenate(out)

    best, best_ep, ntr, ep0 = -1.0, -1, len(ytr), 0
    last = os.path.join(a.out_dir, "last.pt")
    if a.resume and os.path.exists(last):
        ck = torch.load(last, weights_only=False)
        model.load_state_dict(ck["state_dict"])
        opt.load_state_dict(ck["opt"])
        sched.load_state_dict(ck["sched"])
        best, best_ep, ep0 = ck["best"], ck["best_ep"], ck["epoch"] + 1
        log(f"# resumed from {last}: {ep0} epochs done, best val AUC {best:.4f}")
    for ep in range(ep0, a.epochs):
        model.train()
        order = torch.randperm(ntr)
        tot, nb, te0 = 0.0, 0, time.time()
        for i in range(0, ntr, a.batch_size):
            idx = order[i:i + a.batch_size]
            if len(idx) < 2:
                continue
            lo = model(*(x[idx].to(dev) for x in Xtr))
            loss = lossf(lo, ytr[idx].to(dev))
            if not torch.isfinite(loss):
                log(f"error: non-finite loss at epoch {ep}, batch {nb}")
                return 1
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item()
            nb += 1
        sched.step()
        auc_va = roc_auc_score(va["is_signal"], predict(Xva))
        log(f"# epoch {ep}: loss {tot / max(nb, 1):.4f}  val AUC {auc_va:.4f}  ({time.time() - te0:.0f} s)")
        if auc_va > best:
            best, best_ep = auc_va, ep
            torch.save({"state_dict": model.state_dict(), "centre": centre, "scale": scale,
                        "features": FEATURES, "n_const": a.n_const}, os.path.join(a.out_dir, "model.pt"))
        torch.save({"state_dict": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(),
                    "epoch": ep, "best": best, "best_ep": best_ep}, last)
        print(f"PROGRESS step={ep} value={auc_va:.4f}", flush=True)

    model.load_state_dict(torch.load(os.path.join(a.out_dir, "model.pt"), weights_only=False)["state_dict"])
    s_te, s_tr = predict(Xte), predict(Xtr)
    auc_te = roc_auc_score(te["is_signal"], s_te)
    auc_tr = roc_auc_score(trn["is_signal"], s_tr)
    for name, d, s in (("test", te, s_te), ("train", trn, s_tr)):
        pd.DataFrame({"score": s, "fj_sdmass": d["fj_sdmass"], "fj_pt": d["fj_pt"],
                      "is_signal": d["is_signal"], "event_no": d["event_no"]}).to_parquet(
            os.path.join(a.out_dir, f"scores_{name}.parquet"), index=False)

    onnx_diff, onnx_failed = None, False
    if a.onnx:
        try:
            import onnxruntime as ort

            model.eval()
            ex = tuple(x[:8] for x in Xte)
            path = os.path.join(a.out_dir, "model.onnx")
            torch.onnx.export(model.cpu(), ex, path, input_names=["points", "features", "mask"],
                              output_names=["logits"], dynamic_axes={n: {0: "N"} for n in
                                                                     ["points", "features", "mask", "logits"]},
                              opset_version=17, dynamo=False)
            sess = ort.InferenceSession(path)
            n = min(2048, len(Xte[0]))
            lo = sess.run(None, {"points": Xte[0][:n].numpy(), "features": Xte[1][:n].numpy(),
                                 "mask": Xte[2][:n].numpy()})[0]
            e = np.exp(lo - lo.max(axis=1, keepdims=True))
            onnx_diff = float(np.max(np.abs(e[:, 1] / e.sum(axis=1) - s_te[:n])))
        except Exception as e:  # noqa: BLE001 - keep the scores, report the export failure
            log(f"error: ONNX export/check failed: {type(e).__name__}: {e}")
            onnx_failed = True

    res = {"N_TRAIN": len(ytr), "N_VAL": len(va["is_signal"]), "N_TEST": len(te["is_signal"]),
           "N_TEST_BKG": int((te["is_signal"] == 0).sum()), "EPOCHS": a.epochs, "BEST_EPOCH": best_ep,
           "AUC_TRAIN": round(float(auc_tr), 4), "AUC_VAL": round(float(best), 4),
           "AUC_TEST": round(float(auc_te), 4), "SECONDS": round(time.time() - t0), "OUT_DIR": a.out_dir}
    if onnx_diff is not None:
        res["ONNX_MAX_ABS_DIFF"] = float(f"{onnx_diff:.2e}")
    import json

    with open(os.path.join(a.out_dir, "metrics.json"), "w") as f:
        json.dump({**res, "seed": a.seed, "torch": torch.__version__, "args": vars(a)}, f, indent=1)
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    if onnx_failed:
        print("ONNX_EXPORT=failed")
        return 1
    if math.isnan(auc_te) or auc_te < 0.6:
        log("error: AUC_TEST < 0.6: the model did not learn (check labels, features, padding)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
