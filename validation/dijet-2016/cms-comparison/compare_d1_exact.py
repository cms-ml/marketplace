#!/usr/bin/env python3
"""D1 (exact): the student's DeepJet working points vs the BTV POG json, and the 2016G+H luminosity vs the CMS Open Data
luminosity records (record 1059: Run2016Glumi.txt, Run2016Hlumi.txt, pp_2016lumibyls.csv; golden JSON record 14220).

Usage: compare_d1_exact.py --cache <cache dir>
"""
import argparse
import json
import re
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *   # noqa

BTV_BASE = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/BTV/{era}/btagging.json.gz"
OD = "https://opendata.cern.ch/record/{rec}/files/{name}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    a = ap.parse_args()
    od = Path(a.cache) / "opendata"
    summ = json.load(open(STUDENT_DIR / "summary.json"))

    # ------------------------------------------------------------------ working points
    import correctionlib
    wp = {}
    for era in ("2016postVFP_UL", "2016preVFP_UL"):
        cs = correctionlib.CorrectionSet.from_file(BTV_BASE.format(era=era))
        wp[era] = {k: float(cs["deepJet_wp_values"].evaluate(k)) for k in "LMT"}
    stu = summ["btag_wp_deepjet_2016postVFP_UL"]
    diff = {k: stu[k] - wp["2016postVFP_UL"][k] for k in "LMT"}
    log("BTV POG 2016postVFP_UL DeepJet WPs:", wp["2016postVFP_UL"], " student:", stu, " diff:", diff)
    log("BTV POG 2016preVFP_UL DeepJet WPs (for reference):", wp["2016preVFP_UL"])
    wp_ok = all(abs(d) < 1e-9 for d in diff.values())
    # the student's data are Run2016G+H = postVFP (APV ended with 2016F-early); the POG era is the correct one
    save_result("D1a", student_result="DeepJet working points L/M/T used for the b-tag categories (2016postVFP_UL)",
                counterpart={"report": "BTV POG correctionlib json", "path": BTV_BASE.format(era="2016postVFP_UL"), "key": "deepJet_wp_values"},
                level="exact (constants)", statistic=max(abs(d) for d in diff.values()), statistic_name="max |student - POG|", ndf=0,
                p_value=None, ratio=None, student=stu, pog=wp["2016postVFP_UL"], pog_preVFP=wp["2016preVFP_UL"],
                verdict="CONSISTENT" if wp_ok else "INCONSISTENT",
                reason="Identical to the POG json for the correct era (Run2016G,H are postVFP); the preVFP values differ, so the era choice matters.")

    # ------------------------------------------------------------------ luminosity
    for name in ("Run2016Glumi.txt", "Run2016Hlumi.txt", "2016lumi.txt"):
        fetch(OD.format(rec=1059, name=name), od / name)
    fetch(OD.format(rec=1059, name="pp_2016lumibyls.csv"), od / "pp_2016lumibyls.csv", timeout=300)
    fetch(OD.format(rec=14220, name="Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"), od / "golden.json")

    def total_row(fn):
        for line in open(od / fn):
            m = re.match(r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", line)
            if m:
                return dict(nruns=int(m[1]), nfills=int(m[2]), nls=int(m[3]), ncms=int(m[4]), delivered=float(m[5]), recorded=float(m[6]))
        raise RuntimeError(fn)
    G, H = total_row("Run2016Glumi.txt"), total_row("Run2016Hlumi.txt")
    pub_rec = G["recorded"] + H["recorded"]
    pub_del = G["delivered"] + H["delivered"]
    # recompute from the by-lumisection csv and the golden json (independent of the student's code)
    gj = json.load(open(od / "golden.json"))
    rec = {}
    for line in open(od / "pp_2016lumibyls.csv"):
        if line.startswith("#"):
            continue
        c = line.split(",")
        run = int(c[0].split(":")[0]); ls = int(c[1].split(":")[0])
        ranges = gj.get(str(run))
        if ranges and any(lo <= ls <= hi for lo, hi in ranges):
            rec[run] = rec.get(run, 0.0) + float(c[6])
    L_G = sum(v for r, v in rec.items() if 278820 <= r <= 280385)
    L_H = sum(v for r, v in rec.items() if 280919 <= r <= 284044)
    L_csv = L_G + L_H
    L_stu = summ["luminosity"]["recorded_fb"]
    log(f"Open Data published recorded: G {G['recorded']:.6f} + H {H['recorded']:.6f} = {pub_rec:.6f} fb-1")
    log(f"recomputed from csv+golden: G {L_G:.6f} + H {L_H:.6f} = {L_csv:.6f} fb-1; student {L_stu:.6f} fb-1")
    rel_pub = L_stu / pub_rec - 1
    rel_csv = L_stu / L_csv - 1
    log(f"student / published - 1 = {rel_pub:+.2e}; student / recomputed - 1 = {rel_csv:+.2e}; record uncertainty 1.2%")
    # number of lumisections
    nls_pub = G["ncms"] + H["ncms"]
    save_result("D1b", student_result="Integrated luminosity of the processed 2016G+H data (recorded, golden JSON), %.4f fb^-1" % L_stu,
                counterpart={"report": "CMS Open Data luminosity record 1059 (Run2016Glumi.txt + Run2016Hlumi.txt), golden JSON record 14220",
                             "hepdata_table": None},
                level="exact (lumi)", statistic=abs(rel_pub) / 0.012, statistic_name="|student/published - 1| in units of the 1.2% lumi uncertainty",
                ndf=0, p_value=None, ratio=L_stu / pub_rec, student_fb=L_stu, published_fb=pub_rec, published_G=G["recorded"],
                published_H=H["recorded"], recomputed_csv_fb=L_csv, delivered_published_fb=pub_del, n_ls_published=nls_pub,
                n_ls_student=summ["luminosity"]["n_lumisections_processed_and_golden"],
                verdict="CONSISTENT" if abs(rel_pub) < 1e-3 else ("TENSION" if abs(rel_pub) < 0.012 else "INCONSISTENT"),
                reason=("Agrees to %.1e with the published G+H total and to %.1e with an independent csv+golden sum. "
                        "Note: pp_2016lumibyls.csv header says 'Norm tag: None' while the Run2016G/H summaries use the composite normtag; "
                        "the sums nevertheless agree to <1e-3." % (abs(rel_pub), abs(rel_csv))))
    # context only: EXO-20-008 quotes 36.3 fb-1 for the whole of 2016
    save_result("D1c_context", student_result="G+H fraction of the full 2016 luminosity", ratio=L_stu / 36.3, verdict="NOT COMPARABLE",
                reason="EXO-20-008 2016 spectra use 36.3 fb^-1 (all of 2016, eras B-H); the student uses G+H only (%.3f of it). Only cross sections (N/L) can be compared, not counts." % (L_stu / 36.3))


if __name__ == "__main__":
    main()
