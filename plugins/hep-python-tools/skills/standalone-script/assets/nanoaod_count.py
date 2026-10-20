#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "typer>=0.12",
#   "uproot>=5",
#   "awkward>=2",
#   "fsspec-xrootd",
#   "xrootd",
# ]
# ///
"""Count NanoAOD events with >= N good muons."""
import awkward as ak
import typer
import uproot

app = typer.Typer(add_completion=False)


@app.command()
def main(
    url: str = typer.Argument(..., help="NanoAOD file (local path or root:// URL)"),
    min_muons: int = typer.Option(2, "--min-muons", "-n", help="Minimum muons with pT > 20 GeV"),
    entries: int = typer.Option(10000, "--entries", help="Events to read"),
) -> None:
    """Count events with at least N muons above 20 GeV in a NanoAOD file."""
    arr = uproot.open(url)["Events"].arrays(["Muon_pt"], entry_stop=entries)
    n = int(ak.sum(ak.sum(arr.Muon_pt > 20, axis=1) >= min_muons))
    typer.echo(f"{n} / {len(arr)} events with >= {min_muons} muons (pT > 20 GeV)")


if __name__ == "__main__":
    app()
