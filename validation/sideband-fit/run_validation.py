"""Recreate the predeclared CMS Open Data sideband benchmarks and toy ensemble."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "plugins/background-est/skills/sideband-fit/scripts"))

from fit_sidebands import (
    Spectrum,
    fit_histogram,
    fit_sideband,
    json_text,
    window_masks,
)
from inputs import continuum_data, sha256, verified, workshop_data
from plots import fit_plot, toy_plot
from toys import run_ensembles


def load_json(path):
    return json.loads(path.read_text())


def fit_case(edges, counts, intervals, config):
    windows = window_masks(edges, intervals)
    sideband = ~np.any(windows, axis=0)
    blind_counts = np.array([n if keep else None for n, keep in zip(counts, sideband)])
    report = fit_histogram(edges, blind_counts, intervals, config["coordinate"], config["orders"])
    if report["selected_order"] is None:
        raise RuntimeError("no usable sideband model")
    return report


def assess_case(edges, counts, report, meta):
    windows = report["window_masks"]
    masked_counts = windows @ counts
    candidates = []
    for fit in report["candidates"]:
        candidate = {key: value for key, value in fit.items() if key != "prediction_covariance"}
        if fit["valid"]:
            variance = fit["window_covariance"].diagonal()
            candidate["window_heldout_residual"] = (
                (masked_counts - fit["window_expected"]) / np.sqrt(variance + fit["window_expected"])
            )
            candidate["prediction_std"] = np.sqrt(np.diag(fit["prediction_covariance"]))
        candidates.append(candidate)
    return {**{key: value for key, value in report.items() if key != "candidates"},
            "counts": counts, "nbins": len(edges) - 1, "metadata": meta,
            "masked_observed": masked_counts, "candidates": candidates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True, help="external input directory")
    parser.add_argument("--output", type=Path, required=True, help="directory for full fits and results")
    parser.add_argument("--smoke", action="store_true", help="12 toys per scenario with a distinct seed")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=1,
                        help="local toy worker processes; set BLAS to one thread each")
    args = parser.parse_args()
    settings = load_json(HERE / "frozen.json")
    manifest = load_json(HERE / "input_manifest.json")
    input_paths = {name: verified(args.inputs / spec["path_from_inputs"], spec["sha256"])
                   for name, spec in manifest.items()}
    crosscheck_path = verified(args.inputs / manifest["continuum"]["crosscheck_input"],
                               manifest["continuum"]["crosscheck_sha256"])
    primary, crosscheck = load_json(input_paths["continuum"]), load_json(crosscheck_path)
    if any(primary[key] != crosscheck[key] for key in ("data_counts", "edges")):
        raise ValueError("snapshot raw inputs disagree between templates and fit export")

    samples = {
        "jpsi": workshop_data(input_paths["jpsi_csv"], settings["jpsi"]),
        "continuum": continuum_data(input_paths["continuum"], settings["continuum"]),
    }
    reports = {name: fit_case(*sample[:3], settings[name]) for name, sample in samples.items()}
    edges, counts, _, _ = samples["continuum"]
    windows = reports["continuum"]["window_masks"]
    sideband = reports["continuum"]["sideband_mask"]
    spectrum = Spectrum(edges, settings["continuum"]["coordinate"])
    fits = [fit_sideband(spectrum, sideband, counts[sideband], order)
            for order in settings["continuum"]["orders"]]
    config = settings["toys"]
    seed = config["master_seed"] + 1 if args.smoke else config["master_seed"]
    attempts = 12 if args.smoke else config["attempts_per_scenario"]
    print(f"TOYS={attempts} per truth and strength (seed {seed})", flush=True)
    ensembles, pulls = run_ensembles(spectrum, windows, fits, config, attempts, seed,
                                     settings["rules"]["fixed_order"], args.workers)

    args.output.mkdir(parents=True, exist_ok=True)
    plots_dir = args.output / "plots"
    plots_dir.mkdir(exist_ok=True)
    summary = {"configuration_sha256": sha256(HERE / "frozen.json"), "toys": ensembles}
    for name, (edges, counts, intervals, meta) in samples.items():
        report = reports[name]
        selected = next(fit for fit in report["candidates"] if fit["order"] == report["selected_order"])
        (args.output / f"{name}_fit.json").write_text(json_text(report))
        summary[name] = assess_case(edges, counts, report, meta)
        if name == "jpsi":
            summary[name]["window_subtraction"] = summary[name]["masked_observed"] - selected["window_expected"]
            summary[name]["window_subtraction_stat_std"] = np.sqrt(
                summary[name]["masked_observed"] + selected["window_covariance"].diagonal()
            )
        fit_plot(name, edges, counts, selected, intervals, meta, plots_dir / name)
    toy_plot(pulls, plots_dir / "toy_pulls")
    (args.output / "summary.json").write_text(json_text(summary))
    (args.output / "toy_pulls.json").write_text(json_text(pulls))
    print(f"SUMMARY_JSON={args.output / 'summary.json'}")


if __name__ == "__main__":
    sys.exit(main())
