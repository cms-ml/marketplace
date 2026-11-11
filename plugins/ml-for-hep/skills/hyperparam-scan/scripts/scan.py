#!/usr/bin/env python3
"""Hyperparameter scans around ANY trainer that prints KEY=VALUE: grid, random, TPE with
pruning; resumable; parallel workers on one node or on HTCondor.

    scan.py run --study-dir scan1 --space space.json --mode quick|random|tpe \
        --cmd "python3 train_bdt.py table.parquet --out-dir {out_dir} --params-json '{params_json}' --progress-every 25" \
        --metric AUC_VAL [--n-trials 30] [--timeout 1800] [--prune] [--kfold 4] [--worker-id 0]
    scan.py merge scan1 [more study dirs or leaderboard.json files] -o leaderboard.json
    scan.py condor --study-dir scan1 --workers 20 --transfer table.parquet,train_bdt.py -- <run options>

run     Each trial runs --cmd in a shell with placeholders replaced: {out_dir} (trial directory),
        {params_json} (the sampled parameters as JSON), {seed}, {<parameter name>}, and with
        --kfold also {train_folds} {val_folds} (comma lists). The trial value is --metric from
        the command's KEY=VALUE stdout (mean over folds with --kfold K: fold k is validation,
        --test-fold is never used, the rest train). Lines "PROGRESS step=N value=V" are
        reported to Optuna; with --prune (median rule after --prune-warmup steps and 5 trials)
        a hopeless trial is killed. A trial whose command exits with 2, times out
        (--trial-timeout) or prints no metric is FAILED; STATUS=FAIL in its output (e.g.
        overtrained) keeps the value but excludes the trial from BEST.
        Modes: quick = full grid over each parameter's "choices" (or low/high if none);
        random = random search; tpe = Optuna TPE (Bayesian). Space JSON:
        {"name": {"type": "float"|"int"|"categorical", "low":, "high":, "log": bool, "choices": []}}
        State lives in <study-dir>/journal.log (Optuna journal storage: safe on NFS, shared by
        parallel workers). Re-running the same command resumes: finished trials are kept and
        --n-trials counts the total number of finished trials of the study.
        Stop rules: --n-trials, --timeout seconds (no new trial starts after it).
merge   Combine studies (e.g. one per Condor worker) into one leaderboard.
condor  Write <study-dir>/condor/{scan.jdl,worker.sh}: --workers jobs, each running `scan.py run`
        with --worker-id $(Process) in its own study and returning scan_w<id>.tar.gz
        (journal + leaderboard; merge them afterwards). --gpus N adds request_GPUs.
        Submit with condor_submit yourself (see the skill). Nothing is submitted here.

Outputs of run/merge: leaderboard.json ({"summary":..., "trials":[...]} sorted best first) and
leaderboard.csv. Stdout KEY=VALUE: N_COMPLETE N_PRUNED N_FAILED N_STATUS_FAIL BEST_VALUE
BEST_TRIAL BEST_PARAMS BEST_OUT_DIR SPREAD_TOP5 [BASELINE IMPROVEMENT SIGNIFICANT] SECONDS
LEADERBOARD STATUS. With --baseline V --noise E (the default-parameter value and its
statistical error, e.g. AUC_ERR from evaluate.py), SIGNIFICANT=1 only if
BEST_VALUE - BASELINE > 2 x NOISE in the right direction.
Exit codes: 0 ok, 1 no trial completed with STATUS != FAIL, 2 bad arguments.
--dry-run prints the first trial's command and the grid size and runs nothing.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import subprocess
import sys
import time

KV = re.compile(r"^([A-Z][A-Z0-9_.]*)=(.*)$")
PROG = re.compile(r"^PROGRESS step=(\d+) value=([-+0-9.eE]+|nan)")


def log(m):
    print(m, file=sys.stderr, flush=True)


def load_study(study_dir, name, direction, sampler=None, pruner=None):
    import optuna
    from optuna.storages import JournalStorage
    from optuna.storages.journal import JournalFileBackend

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    os.makedirs(study_dir, exist_ok=True)
    storage = JournalStorage(JournalFileBackend(os.path.join(study_dir, "journal.log")))
    return optuna.create_study(study_name=name, storage=storage, direction=direction, sampler=sampler,
                               pruner=pruner, load_if_exists=True)


def suggest(trial, space):
    out = {}
    for k, s in space.items():
        if s["type"] == "categorical":
            out[k] = trial.suggest_categorical(k, s["choices"])
        elif s["type"] == "int":
            out[k] = trial.suggest_int(k, int(s["low"]), int(s["high"]), log=bool(s.get("log")))
        else:
            out[k] = trial.suggest_float(k, float(s["low"]), float(s["high"]), log=bool(s.get("log")))
    return out


def run_cmd(cmd, trial, metric, timeout, prune):
    """Run one training command; return (value, kv dict). Raises on failure or pruning."""
    import optuna

    t0 = time.time()
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    kv = {}
    try:
        for line in proc.stdout:
            m = PROG.match(line)
            if m and trial is not None:
                trial.report(float(m.group(2)), int(m.group(1)))
                if prune and trial.should_prune():
                    proc.kill()
                    raise optuna.TrialPruned()
            m = KV.match(line.strip())
            if m:
                kv[m.group(1)] = m.group(2)
            if timeout and time.time() - t0 > timeout:
                proc.kill()
                raise RuntimeError(f"trial timeout after {timeout} s")
    finally:
        proc.stdout.close()
        rc = proc.wait()
    if rc not in (0, 1) or metric not in kv:
        raise RuntimeError(f"command exit {rc}, {metric} {'missing' if metric not in kv else 'present'}")
    return float(kv[metric]), kv


def leaderboard(trials, direction, a, t0, out_json):
    """trials: list of dicts (number, state, value, params, out_dir, status, worker)."""
    sign = -1 if direction == "maximize" else 1
    done = [t for t in trials if t["state"] == "COMPLETE"]
    good = sorted((t for t in done if t.get("status") != "FAIL"), key=lambda t: sign * t["value"])
    rest = sorted((t for t in done if t.get("status") == "FAIL"), key=lambda t: sign * t["value"])
    res = {"N_COMPLETE": len(done), "N_PRUNED": sum(t["state"] == "PRUNED" for t in trials),
           "N_FAILED": sum(t["state"] == "FAIL" for t in trials), "N_STATUS_FAIL": len(rest)}
    if good:
        b = good[0]
        top = [t["value"] for t in good[:5]]
        res.update({"BEST_VALUE": b["value"], "BEST_TRIAL": b["number"], "BEST_PARAMS": json.dumps(b["params"]),
                    "BEST_OUT_DIR": b.get("out_dir", ""), "SPREAD_TOP5": round(max(top) - min(top), 6)})
        if a.baseline is not None:
            imp = (b["value"] - a.baseline) * -sign
            res.update({"BASELINE": a.baseline, "IMPROVEMENT": round(imp, 6),
                        "SIGNIFICANT": int(a.noise is not None and imp > 2 * a.noise)})
    res.update({"SECONDS": round(time.time() - t0, 1), "LEADERBOARD": out_json, "STATUS": "PASS" if good else "FAIL"})
    with open(out_json, "w") as f:
        json.dump({"summary": res, "direction": direction, "trials": good + rest}, f, indent=1)
    with open(os.path.splitext(out_json)[0] + ".csv", "w", newline="") as f:
        keys = sorted({k for t in done for k in t["params"]})
        wr = csv.writer(f)
        wr.writerow(["rank", "trial", "worker", "value", "status"] + keys)
        for i, t in enumerate(good + rest):
            wr.writerow([i + 1, t["number"], t.get("worker", ""), t["value"], t.get("status", "")] + [t["params"].get(k, "") for k in keys])
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    return 0 if good else 1


def trial_rows(study):
    return [{"number": t.number, "state": t.state.name, "value": t.value, "params": t.params,
             "out_dir": t.user_attrs.get("out_dir", ""), "status": t.user_attrs.get("status", ""),
             "worker": t.user_attrs.get("worker", "")} for t in study.trials if t.state.name != "RUNNING"]


def cmd_run(a) -> int:
    t0 = time.time()
    try:
        import optuna

        space = json.load(open(a.space))
        if not space:
            raise ValueError("empty search space")
        for ph in ("{out_dir}",):
            if ph not in a.cmd:
                raise ValueError(f"--cmd must contain {ph}")
        if a.kfold and ("{train_folds}" not in a.cmd or "{val_folds}" not in a.cmd):
            raise ValueError("--kfold needs {train_folds} and {val_folds} in --cmd")
    except Exception as e:  # noqa: BLE001
        log(f"error: {type(e).__name__}: {e}")
        return 2
    seed = a.seed + 1000 * a.worker_id
    if a.mode == "quick":
        grid = {k: (s.get("choices") or [s["low"], s["high"]]) for k, s in space.items()}
        space = {k: {"type": "categorical", "choices": v} for k, v in grid.items()}
        sampler = optuna.samplers.GridSampler(grid, seed=seed)
        ngrid = 1
        for v in grid.values():
            ngrid *= len(v)
        a.n_trials = min(a.n_trials or ngrid, ngrid)
    elif a.mode == "random":
        sampler = optuna.samplers.RandomSampler(seed=seed)
    else:
        sampler = optuna.samplers.TPESampler(seed=seed, n_startup_trials=a.startup_trials)
    pruner = optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=a.prune_warmup) if a.prune else optuna.pruners.NopPruner()

    def fill(cmd, params, out_dir, extra=None):
        rep = {"{out_dir}": shlex.quote(out_dir), "{params_json}": json.dumps(params), "{seed}": str(seed)}
        rep.update({"{" + k + "}": str(v) for k, v in params.items()})
        rep.update(extra or {})
        for k, v in rep.items():
            cmd = cmd.replace(k, v)
        return cmd

    if a.dry_run:
        first = {k: (s["choices"][0] if s["type"] == "categorical" else s["low"]) for k, s in space.items()}
        ex = {"{train_folds}": "1,2,3", "{val_folds}": "0"} if a.kfold else None
        print(f"N_TRIALS={a.n_trials}\nMODE={a.mode}\nFIRST_CMD={fill(a.cmd, first, os.path.join(a.study_dir, 'trials', 't0'), ex)}\nDRY_RUN=1")
        return 0
    study = load_study(a.study_dir, a.study_name, a.direction, sampler, pruner)

    def objective(trial):
        params = suggest(trial, space)
        out_dir = os.path.join(a.study_dir, "trials", f"w{a.worker_id}_t{trial.number}")
        trial.set_user_attr("out_dir", out_dir)
        trial.set_user_attr("worker", a.worker_id)
        if a.kfold:
            folds = [k for k in range(a.kfold + 1) if k != a.test_fold][: a.kfold]
            vals, status = [], "PASS"
            for k in folds:
                ex = {"{train_folds}": ",".join(str(j) for j in folds if j != k), "{val_folds}": str(k)}
                v, kv = run_cmd(fill(a.cmd, params, f"{out_dir}_f{k}", ex), None, a.metric, a.trial_timeout, False)
                vals.append(v)
                status = "FAIL" if kv.get("STATUS") == "FAIL" else status
            trial.set_user_attr("fold_values", vals)
            value = sum(vals) / len(vals)
        else:
            value, kv = run_cmd(fill(a.cmd, params, out_dir), trial, a.metric, a.trial_timeout, a.prune)
            status = kv.get("STATUS", "")
        trial.set_user_attr("status", status)
        log(f"# trial {trial.number}: {a.metric}={value:.5f} {status} {json.dumps(params)}")
        return value

    def n_done():
        return sum(t.state.name in ("COMPLETE", "PRUNED") for t in study.trials)

    def stop(study, trial):
        if (a.n_trials and n_done() >= a.n_trials) or (a.timeout and time.time() - t0 > a.timeout):
            study.stop()

    if not a.n_trials or n_done() < a.n_trials:
        study.optimize(objective, callbacks=[stop], catch=(RuntimeError,))
    else:
        log(f"# study already has {n_done()} finished trials (>= --n-trials): nothing to run")
    return leaderboard(trial_rows(study), a.direction, a, t0, os.path.join(a.study_dir, "leaderboard.json"))


def cmd_merge(a) -> int:
    t0 = time.time()
    rows, direction = [], None
    try:
        for src in a.sources:
            if os.path.isdir(src):
                lb = os.path.join(src, "leaderboard.json")
                src = lb if os.path.exists(lb) else src
            if os.path.isdir(src):
                st = load_study(src, a.study_name, a.direction)
                rows += trial_rows(st)
                direction = direction or st.direction.name.lower()
            else:
                d = json.load(open(src))
                rows += [dict(t, state="COMPLETE") for t in d["trials"]]
                direction = direction or d["direction"]
        if not rows:
            raise ValueError("no trials found")
    except Exception as e:  # noqa: BLE001
        log(f"error: {type(e).__name__}: {e}")
        return 2
    return leaderboard(rows, direction, a, t0, a.output)


def cmd_condor(a) -> int:
    d = os.path.join(a.study_dir, "condor")
    files = [os.path.abspath(f) for f in a.transfer.split(",") if f] + [os.path.abspath(__file__), os.path.abspath(a.space)]
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        log(f"error: missing transfer files: {missing}")
        return 2
    run_args = [x for x in a.run_args if x != "--"]

    def cq(x):  # HTCondor "new" arguments syntax: double the quotes, wrap in '...' if needed
        y = x.replace('"', '""').replace("'", "''")
        return f"'{y}'" if (y != x or " " in x or not x) else x

    worker = f"""#!/bin/bash
# worker for scan.py: one independent study per job, results returned as scan_w<id>.tar.gz
ID=$1; shift
set +u
source {a.env}
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS={a.cpus}
python3 scan.py run --study-dir scan_w$ID --worker-id $ID --space {os.path.basename(a.space)} "$@"
RC=$?
tar czf scan_w$ID.tar.gz --exclude='*.parquet' --exclude='model.*' scan_w$ID
exit $RC
"""
    jdl = f"""universe = vanilla
executable = worker.sh
arguments = "$(Process) {' '.join(cq(x) for x in run_args)}"
transfer_input_files = {','.join(files)}
should_transfer_files = YES
when_to_transfer_output = ON_EXIT
transfer_output_files = scan_w$(Process).tar.gz
request_cpus = {a.cpus}
request_memory = {a.memory}
{f'request_GPUs = {a.gpus}' if a.gpus else '# request_GPUs = 1   (only after condor_status shows GPU slots)'}
output = w$(Process).out
error = w$(Process).err
log = scan.log
queue {a.workers}
"""
    print(f"WORKERS={a.workers}\nJDL={os.path.join(d, 'scan.jdl')}\nSUBMIT=cd {d} && condor_submit scan.jdl")
    if a.dry_run:
        print("DRY_RUN=1")
        return 0
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "worker.sh"), "w") as f:
        f.write(worker)
    os.chmod(os.path.join(d, "worker.sh"), 0o755)
    with open(os.path.join(d, "scan.jdl"), "w") as f:
        f.write(jdl)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="sub", required=True)
    r = sub.add_parser("run", help="run or resume a study")
    r.add_argument("--study-dir", required=True)
    r.add_argument("--study-name", default="scan")
    r.add_argument("--space", required=True, help="search-space JSON")
    r.add_argument("--cmd", required=True, help="training command template")
    r.add_argument("--mode", choices=["quick", "random", "tpe"], default="tpe")
    r.add_argument("--metric", default="AUC_VAL")
    r.add_argument("--direction", choices=["maximize", "minimize"], default="maximize")
    r.add_argument("--n-trials", type=int, default=0, help="total finished trials of the study (0: no limit)")
    r.add_argument("--timeout", type=float, default=0, help="seconds; no new trial after this (0: none)")
    r.add_argument("--trial-timeout", type=float, default=0, help="seconds per training command")
    r.add_argument("--startup-trials", type=int, default=10, help="random trials before TPE starts")
    r.add_argument("--prune", action="store_true", help="kill trials below the median (needs PROGRESS lines)")
    r.add_argument("--prune-warmup", type=int, default=0, help="steps before a trial may be pruned")
    r.add_argument("--kfold", type=int, default=0, help="K-fold CV over folds != --test-fold")
    r.add_argument("--test-fold", type=int, default=4)
    r.add_argument("--worker-id", type=int, default=0)
    r.add_argument("--seed", type=int, default=1)
    r.add_argument("--baseline", type=float)
    r.add_argument("--noise", type=float)
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(fn=cmd_run)
    m = sub.add_parser("merge", help="merge studies or leaderboards")
    m.add_argument("sources", nargs="+")
    m.add_argument("-o", "--output", default="leaderboard.json")
    m.add_argument("--study-name", default="scan")
    m.add_argument("--direction", choices=["maximize", "minimize"], default="maximize")
    m.add_argument("--baseline", type=float)
    m.add_argument("--noise", type=float)
    m.set_defaults(fn=cmd_merge)
    c = sub.add_parser("condor", help="write an HTCondor submit file and worker script")
    c.add_argument("--study-dir", required=True)
    c.add_argument("--space", required=True)
    c.add_argument("--workers", type=int, required=True)
    c.add_argument("--transfer", default="", help="comma-separated files each job needs (table, trainer)")
    c.add_argument("--env", default="/cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh",
                   help="environment script sourced on the worker (default: %(default)s)")
    c.add_argument("--cpus", type=int, default=4)
    c.add_argument("--memory", default="4000", help="MB")
    c.add_argument("--gpus", type=int, default=0)
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("run_args", nargs=argparse.REMAINDER, help="-- then options passed to `scan.py run`")
    c.set_defaults(fn=cmd_condor)
    a = p.parse_args()
    if a.sub == "run" and a.mode == "quick" and a.prune:
        log("error: --prune has no use in quick mode")
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
