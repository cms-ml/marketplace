#!/usr/bin/env python3
"""Write the --samples JSON for nano_to_table.py: QCD HT bins from validation/dijet-2016.

    make_samples.py --n-files 3 -o samples.json            # 3 files per HT bin
    make_samples.py --n-files 8,4,2,2 -o samples.json      # per HT bin, in the order of XSEC_PB

Cross sections (pb) are the ones in validation/dijet-2016/specification.md (GenXsecAnalyzer,
Open Data records 63139, 63078, 63094, 63102). Every sample gets label 0; make_jet_table.py
assigns the per-jet quark/gluon label afterwards. Stdout: N_SAMPLES N_FILES OUTPUT.
"""
import argparse
import json
import os
import sys

XSEC_PB = {"qcd_700to1000": 6425.0, "qcd_1000to1500": 1117.0, "qcd_1500to2000": 108.3, "qcd_2000toInf": 21.94}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input-files", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         "..", "..", "dijet-2016", "input_files.json"))
    p.add_argument("--n-files", default="3", help="files per sample: one number, or one per sample")
    p.add_argument("-o", "--output", required=True)
    a = p.parse_args()
    try:
        d = json.load(open(a.input_files))
        n = [int(x) for x in a.n_files.split(",")]
        n = n * len(XSEC_PB) if len(n) == 1 else n
        if len(n) != len(XSEC_PB):
            raise ValueError(f"--n-files needs 1 or {len(XSEC_PB)} values")
        s = [{"name": k, "label": 0, "xsec_pb": x, "files": d[k][:m]} for (k, x), m in zip(XSEC_PB.items(), n)]
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    with open(a.output, "w") as f:
        json.dump(s, f, indent=1)
    print(f"N_SAMPLES={len(s)}\nN_FILES={sum(len(x['files']) for x in s)}\nOUTPUT={a.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
