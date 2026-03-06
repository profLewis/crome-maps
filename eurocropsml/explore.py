#!/usr/bin/env python3
"""Explore EuroCropsML dataset: class distributions, sample time series.

Usage:
    python3 eurocropsml/explore.py --data-dir eurocropsml/data
    python3 eurocropsml/explore.py --data-dir eurocropsml/data --country latvia --plot

Requirements:
    pip install numpy matplotlib (matplotlib only needed for --plot)
"""
import argparse
import os
import sys
from collections import Counter

import numpy as np


SENTINEL2_BANDS = [
    "B02 (Blue)", "B03 (Green)", "B04 (Red)", "B05 (RE1)",
    "B06 (RE2)", "B07 (RE3)", "B08 (NIR)", "B08A (NIR2)",
    "B11 (SWIR1)", "B12 (SWIR2)"
]


def load_dataset(data_dir, country, split="train"):
    """Load an .npz dataset file."""
    filename = f"{country}_{split}.npz"
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        print(f"File not found: {path}")
        print(f"Run: python3 eurocropsml/download.py --download --country {country}")
        sys.exit(1)

    print(f"Loading {path}...")
    data = np.load(path, allow_pickle=True)
    print(f"  Keys: {list(data.keys())}")
    for key in data.keys():
        arr = data[key]
        print(f"  {key}: shape={arr.shape}, dtype={arr.dtype}")
    return data


def show_class_distribution(data, top_n=20):
    """Show crop class distribution."""
    if "labels" in data:
        labels = data["labels"]
    elif "y" in data:
        labels = data["y"]
    else:
        print("No labels found in dataset")
        return

    counts = Counter(labels)
    total = len(labels)
    print(f"\nClass distribution ({len(counts)} classes, {total} parcels):")
    print(f"{'Class':>6s}  {'Count':>8s}  {'%':>6s}  Bar")
    print("-" * 60)
    for cls, count in counts.most_common(top_n):
        pct = count / total * 100
        bar = "#" * int(pct * 2)
        print(f"{cls:>6}  {count:>8d}  {pct:5.1f}%  {bar}")

    if len(counts) > top_n:
        rest = sum(c for _, c in counts.most_common()[top_n:])
        print(f"{'...':>6}  {rest:>8d}  {rest/total*100:5.1f}%  (remaining {len(counts)-top_n} classes)")


def plot_sample_timeseries(data, n_samples=5, output_path=None):
    """Plot sample Sentinel-2 time series."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib required for plotting. Install with: pip install matplotlib")
        return

    if "X" in data:
        X = data["X"]
    elif "features" in data:
        X = data["features"]
    else:
        print("No feature data found")
        return

    labels = data.get("labels", data.get("y", None))

    fig, axes = plt.subplots(n_samples, 1, figsize=(12, 3 * n_samples))
    if n_samples == 1:
        axes = [axes]

    indices = np.random.choice(len(X), min(n_samples, len(X)), replace=False)

    for ax, idx in zip(axes, indices):
        ts = X[idx]  # shape: (timesteps, bands)
        if ts.ndim == 1:
            ax.plot(ts)
            ax.set_ylabel("Value")
        else:
            # Plot NDVI-like (NIR - Red) / (NIR + Red)
            if ts.shape[1] >= 7:
                red = ts[:, 2].astype(float)   # B04
                nir = ts[:, 6].astype(float)   # B08
                ndvi = np.where((nir + red) > 0, (nir - red) / (nir + red), 0)
                ax.plot(ndvi, "g-", linewidth=2, label="NDVI")
                ax.set_ylabel("NDVI")
                ax.legend()
            else:
                for b in range(ts.shape[1]):
                    ax.plot(ts[:, b], label=f"Band {b}")
                ax.legend(fontsize=7)

        label = labels[idx] if labels is not None else "?"
        ax.set_title(f"Parcel {idx} — Class: {label}")
        ax.set_xlabel("Timestep")

    plt.tight_layout()
    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Plot saved to {output_path}")
    else:
        plt.show()


def load_metadata(data_dir, country):
    """Load metadata CSV if available."""
    path = os.path.join(data_dir, f"{country}_metadata.csv")
    if not os.path.exists(path):
        return None
    try:
        import csv
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"\nMetadata: {len(rows)} rows, columns: {list(rows[0].keys()) if rows else []}")
        return rows
    except Exception as e:
        print(f"Could not read metadata: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Explore EuroCropsML dataset")
    parser.add_argument("--data-dir", default="eurocropsml/data", help="Data directory")
    parser.add_argument("--country", default="latvia",
                        help="Country (latvia, estonia, portugal)")
    parser.add_argument("--split", default="train", help="Split (train, test)")
    parser.add_argument("--plot", action="store_true", help="Plot sample time series")
    parser.add_argument("--plot-output", help="Save plot to file instead of showing")
    parser.add_argument("--top-n", type=int, default=20, help="Top N classes to show")
    args = parser.parse_args()

    data = load_dataset(args.data_dir, args.country, args.split)
    show_class_distribution(data, top_n=args.top_n)
    load_metadata(args.data_dir, args.country)

    if args.plot:
        plot_sample_timeseries(data, output_path=args.plot_output)


if __name__ == "__main__":
    main()
