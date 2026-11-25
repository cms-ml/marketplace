"""Read the two frozen source formats and verify their byte-level provenance."""

import csv
import hashlib
import json
from collections import Counter

import hist
import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified(path, checksum):
    if sha256(path) != checksum:
        raise ValueError(f"unexpected SHA-256 for {path.name}")
    return path


def workshop_data(path, config):
    lo, hi, nbins = config["binning_GeV"]
    vectors = []
    charges = Counter()
    with path.open(newline="") as source:
        for e, px, py, pz, charge in csv.reader(source):
            vectors.append((float(e), float(px), float(py), float(pz)))
            charges[charge] += 1
    if len(vectors) != 100_000 or set(charges) != {"pp", "pm", "mm"}:
        raise ValueError("workshop CSV rows or charges disagree with source schema")
    vectors = np.asarray(vectors)
    mass_squared = vectors[:, 0] ** 2 - np.sum(vectors[:, 1:] ** 2, axis=1)
    if not np.all(np.isfinite(mass_squared) & (mass_squared >= 0)):
        raise ValueError("workshop input has nonfinite or spacelike four-vectors")
    mass = np.sqrt(mass_squared)
    edges = np.linspace(lo, hi, nbins + 1)
    h = hist.Hist(hist.axis.Variable(edges), storage=hist.storage.Int64()).fill(mass)
    intervals = config["masked_GeV"]
    window_lo, window_hi = intervals[0]
    left = int(np.sum((mass > lo) & (mass < window_lo)))
    peak = int(np.sum((mass > window_lo) & (mass < window_hi)))
    right = int(np.sum((mass > window_hi) & (mass < hi)))
    return edges, h.values(), intervals, {
        "all_rows": len(mass), "charge_counts": dict(sorted(charges.items())),
        "workshop_strict_counts": {"left": left, "peak": peak, "right": right},
        "workshop_background": (left + right) / 2,
        "workshop_subtraction": peak - (left + right) / 2,
    }


def continuum_data(path, config):
    data = json.loads(path.read_text())
    lo, hi = config["input_edge_slice"]
    edges = np.asarray(data["edges"][lo:hi + 1])
    if not np.allclose(edges, np.geomspace(300, 6000, 151)[lo:hi + 1], rtol=1e-12, atol=0):
        raise ValueError("continuum grid disagrees with frozen analysis snapshot grid")
    intervals = [[float(edges[left]), float(edges[right])] for left, right in config["masks_bin_index"]]
    counts = np.asarray(data["data_counts"][lo:hi])
    return edges, counts, intervals, {"luminosity_fb": data["luminosity_fb"]}
