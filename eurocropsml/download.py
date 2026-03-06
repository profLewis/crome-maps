#!/usr/bin/env python3
"""Download EuroCropsML benchmark dataset from Zenodo.

EuroCropsML is a machine learning benchmark for crop classification using
Sentinel-2 time series. It provides 706,683 parcels across Latvia, Estonia,
and Portugal with 176 crop classes.

The dataset contains .npz files with Sentinel-2 reflectance time series
(10 bands at 10m) per parcel, along with parcel geometries and labels.

Source: https://zenodo.org/records/15095445

Usage:
    python3 eurocropsml/download.py --list
    python3 eurocropsml/download.py --download
    python3 eurocropsml/download.py --download --country latvia
"""
import argparse
import json
import os
import sys
import urllib.request

ZENODO_RECORD = "15095445"
ZENODO_API = f"https://zenodo.org/api/records/{ZENODO_RECORD}"

# Known dataset files from the Zenodo record
COUNTRY_FILES = {
    "latvia": {
        "train": "latvia_train.npz",
        "test": "latvia_test.npz",
        "metadata": "latvia_metadata.csv",
    },
    "estonia": {
        "train": "estonia_train.npz",
        "test": "estonia_test.npz",
        "metadata": "estonia_metadata.csv",
    },
    "portugal": {
        "train": "portugal_train.npz",
        "test": "portugal_test.npz",
        "metadata": "portugal_metadata.csv",
    },
}


def get_file_list():
    """Fetch the file list from Zenodo API."""
    print("Fetching file list from Zenodo...")
    req = urllib.request.Request(ZENODO_API)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    files = []
    for f in data.get("files", []):
        files.append({
            "filename": f["key"],
            "size": f["size"],
            "url": f["links"]["self"],
            "checksum": f.get("checksum", ""),
        })

    return files, data.get("metadata", {})


def download_file(url, output_path, expected_size=None):
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        if expected_size and size == expected_size:
            print(f"  Already downloaded: {os.path.basename(output_path)} ({size / 1e6:.1f} MB)")
            return True
        else:
            print(f"  Incomplete, re-downloading: {os.path.basename(output_path)}")

    print(f"  Downloading: {os.path.basename(output_path)}")

    def progress(block, block_size, total):
        done = block * block_size
        if total > 0:
            pct = min(100, done * 100 // total)
            print(f"\r  {pct}% ({done / 1e6:.1f} MB)", end="", flush=True)

    urllib.request.urlretrieve(url, output_path, reporthook=progress)
    print()
    return True


def main():
    parser = argparse.ArgumentParser(description="Download EuroCropsML from Zenodo")
    parser.add_argument("--list", action="store_true", help="List available files")
    parser.add_argument("--download", action="store_true", help="Download files")
    parser.add_argument("--country", help="Download specific country (latvia, estonia, portugal)")
    parser.add_argument("--output-dir", default="eurocropsml/data",
                        help="Output directory")
    args = parser.parse_args()

    files, metadata = get_file_list()

    if args.list:
        print(f"\nEuroCropsML — Zenodo Record {ZENODO_RECORD}")
        print(f"Title: {metadata.get('title', 'N/A')}")
        print(f"\nFiles ({len(files)}):")
        total = 0
        for f in sorted(files, key=lambda x: x["filename"]):
            size = f["size"]
            total += size
            print(f"  {f['filename']:40s}  {size / 1e6:8.1f} MB")
        print(f"\nTotal: {total / 1e6:.1f} MB")
        return

    if args.download:
        os.makedirs(args.output_dir, exist_ok=True)

        if args.country:
            country = args.country.lower()
            if country not in COUNTRY_FILES:
                print(f"Unknown country: {country}")
                print(f"Available: {', '.join(COUNTRY_FILES)}")
                sys.exit(1)
            # Download files matching this country
            patterns = [v for v in COUNTRY_FILES[country].values()]
            to_download = [f for f in files if f["filename"] in patterns]
        else:
            to_download = files

        print(f"\nDownloading {len(to_download)} files to {args.output_dir}...")
        for f in to_download:
            output_path = os.path.join(args.output_dir, f["filename"])
            download_file(f["url"], output_path, expected_size=f["size"])

        print("\nDone!")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
