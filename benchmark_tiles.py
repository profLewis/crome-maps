#!/usr/bin/env python3
"""Benchmark PMTiles vs MBTiles tile read performance.

Compares tile read latency for datasets that exist in both formats.

Usage:
    # Library-level benchmark (no HTTP, default)
    python3 benchmark_tiles.py --pmtiles-dir . --mbtiles-dir ../crome-work/mbtiles

    # HTTP benchmark (requires tile_server.py running)
    python3 benchmark_tiles.py --mode http --server http://127.0.0.1:8765

    # Benchmark specific dataset(s)
    python3 benchmark_tiles.py --datasets deafrica-crop,flik-overview
"""
import argparse
import glob
import math
import os
import random
import sqlite3
import statistics
import sys
import time
from pathlib import Path

from pmtiles.reader import Reader, MmapSource


def dataset_name(path: str) -> str:
    return Path(path).stem


def discover_datasets(pmtiles_dir: str, mbtiles_dir: str) -> dict:
    """Find datasets present in both formats. Returns {name: (pmtiles_path, mbtiles_path)}."""
    pm = {dataset_name(p): p for p in glob.glob(os.path.join(pmtiles_dir, "*.pmtiles"))}
    mb = {dataset_name(p): p for p in glob.glob(os.path.join(mbtiles_dir, "*.mbtiles"))}
    both = sorted(set(pm) & set(mb))
    return {name: (pm[name], mb[name]) for name in both}


def get_tile_coords(pmtiles_path: str, count: int, seed: int = 42) -> list[tuple[int, int, int]]:
    """Generate random tile coordinates within the dataset's bounds and zoom range."""
    rng = random.Random(seed)

    with open(pmtiles_path, "rb") as f:
        source = MmapSource(f)
        reader = Reader(source)
        header = reader.header()

    min_zoom = header.get("min_zoom", 0)
    max_zoom = header.get("max_zoom", 10)
    min_lon = header.get("min_lon_e7", -1800000000) / 1e7
    max_lon = header.get("max_lon_e7", 1800000000) / 1e7
    min_lat = header.get("min_lat_e7", -850000000) / 1e7
    max_lat = header.get("max_lat_e7", 850000000) / 1e7

    coords = []
    attempts = 0
    max_attempts = count * 20

    while len(coords) < count and attempts < max_attempts:
        attempts += 1
        z = rng.randint(min_zoom, max_zoom)
        n = 1 << z

        lon = rng.uniform(min_lon, max_lon)
        lat = rng.uniform(min_lat, max_lat)

        x = int((lon + 180.0) / 360.0 * n)
        x = max(0, min(n - 1, x))

        lat_rad = math.radians(lat)
        y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
        y = max(0, min(n - 1, y))

        coords.append((z, x, y))

    return coords


def benchmark_library(datasets: dict, tile_count: int = 500, warmup: int = 10) -> list[dict]:
    """Library-level benchmark: direct file reads, no HTTP."""
    results = []

    for name, (pm_path, mb_path) in datasets.items():
        pm_size = os.path.getsize(pm_path)
        mb_size = os.path.getsize(mb_path)

        print(f"\n{'='*60}")
        print(f"Dataset: {name}")
        print(f"  PMTiles: {pm_size / 1e6:.1f} MB  |  MBTiles: {mb_size / 1e6:.1f} MB")

        coords = get_tile_coords(pm_path, tile_count + warmup)
        if len(coords) < warmup + 10:
            print(f"  SKIP: Could not generate enough tile coordinates")
            continue

        # --- PMTiles benchmark ---
        pm_fh = open(pm_path, "rb")
        pm_source = MmapSource(pm_fh)
        pm_reader = Reader(pm_source)

        # Warmup
        for z, x, y in coords[:warmup]:
            pm_reader.get(z, x, y)

        pm_times = []
        pm_hits = 0
        for z, x, y in coords[warmup:]:
            t0 = time.perf_counter()
            data = pm_reader.get(z, x, y)
            t1 = time.perf_counter()
            pm_times.append((t1 - t0) * 1000)  # ms
            if data:
                pm_hits += 1
        pm_fh.close()

        # --- MBTiles benchmark ---
        mb_conn = sqlite3.connect(f"file:{mb_path}?mode=ro", uri=True)
        mb_conn.execute("PRAGMA mmap_size=268435456")

        # Warmup
        for z, x, y in coords[:warmup]:
            tms_y = (1 << z) - 1 - y
            mb_conn.execute(
                "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                (z, x, tms_y),
            ).fetchone()

        mb_times = []
        mb_hits = 0
        for z, x, y in coords[warmup:]:
            tms_y = (1 << z) - 1 - y
            t0 = time.perf_counter()
            row = mb_conn.execute(
                "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                (z, x, tms_y),
            ).fetchone()
            t1 = time.perf_counter()
            mb_times.append((t1 - t0) * 1000)  # ms
            if row:
                mb_hits += 1
        mb_conn.close()

        def stats(times):
            if not times:
                return {}
            s = sorted(times)
            return {
                "mean": statistics.mean(s),
                "median": statistics.median(s),
                "p95": s[int(len(s) * 0.95)],
                "p99": s[int(len(s) * 0.99)],
                "min": s[0],
                "max": s[-1],
                "stdev": statistics.stdev(s) if len(s) > 1 else 0,
            }

        pm_stats = stats(pm_times)
        mb_stats = stats(mb_times)

        result = {
            "dataset": name,
            "pmtiles_size_mb": pm_size / 1e6,
            "mbtiles_size_mb": mb_size / 1e6,
            "tiles_requested": tile_count,
            "pmtiles_hits": pm_hits,
            "mbtiles_hits": mb_hits,
            "pmtiles": pm_stats,
            "mbtiles": mb_stats,
        }
        results.append(result)

        # Print per-dataset results
        print(f"  Tiles requested: {tile_count}  (PMTiles hits: {pm_hits}, MBTiles hits: {mb_hits})")
        print(f"  {'':12s}  {'mean':>8s}  {'median':>8s}  {'p95':>8s}  {'p99':>8s}  {'min':>8s}  {'max':>8s}")
        for label, s in [("PMTiles", pm_stats), ("MBTiles", mb_stats)]:
            print(
                f"  {label:12s}  {s['mean']:7.3f}ms  {s['median']:7.3f}ms  "
                f"{s['p95']:7.3f}ms  {s['p99']:7.3f}ms  {s['min']:7.3f}ms  {s['max']:7.3f}ms"
            )

        if pm_stats["mean"] > 0 and mb_stats["mean"] > 0:
            ratio = pm_stats["mean"] / mb_stats["mean"]
            if ratio > 1:
                print(f"  → MBTiles is {ratio:.1f}x faster (mean)")
            else:
                print(f"  → PMTiles is {1/ratio:.1f}x faster (mean)")

    return results


def benchmark_http(server_url: str, datasets: list[str], tile_count: int = 200) -> list[dict]:
    """HTTP benchmark: requests through tile_server.py."""
    import urllib.request
    import json

    # Get available datasets
    resp = urllib.request.urlopen(f"{server_url}/datasets")
    info = json.loads(resp.read())
    available = info["both"]

    if datasets:
        available = [d for d in available if d in datasets]

    if not available:
        print("No datasets available in both formats on the server")
        return []

    results = []
    for name in available:
        print(f"\n{'='*60}")
        print(f"Dataset: {name} (HTTP)")

        # We need tile coords — fetch header from pmtiles endpoint
        # Use a fixed set of zoom levels
        coords = []
        for z in range(0, 11):
            n = 1 << z
            for _ in range(tile_count // 11 + 1):
                x = random.randint(0, n - 1)
                y = random.randint(0, n - 1)
                coords.append((z, x, y))
        coords = coords[:tile_count]

        for fmt in ["pmtiles", "mbtiles"]:
            times = []
            hits = 0
            for z, x, y in coords:
                url = f"{server_url}/{fmt}/{name}/{z}/{x}/{y}.png"
                t0 = time.perf_counter()
                try:
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = resp.read()
                        hits += 1
                except Exception:
                    pass
                t1 = time.perf_counter()
                times.append((t1 - t0) * 1000)

            s = sorted(times)
            stat = {
                "mean": statistics.mean(s),
                "median": statistics.median(s),
                "p95": s[int(len(s) * 0.95)],
                "p99": s[int(len(s) * 0.99)],
            }
            print(f"  {fmt:12s}  mean={stat['mean']:.1f}ms  median={stat['median']:.1f}ms  "
                  f"p95={stat['p95']:.1f}ms  p99={stat['p99']:.1f}ms  hits={hits}/{tile_count}")

    return results


def print_summary(results: list[dict]):
    """Print a summary comparison table."""
    if not results:
        return

    print(f"\n{'='*80}")
    print("SUMMARY: PMTiles vs MBTiles Library-Level Performance")
    print(f"{'='*80}")
    print(f"{'Dataset':<30s}  {'PM mean':>9s}  {'MB mean':>9s}  {'Ratio':>8s}  {'Winner':>10s}")
    print(f"{'-'*30}  {'-'*9}  {'-'*9}  {'-'*8}  {'-'*10}")

    pm_wins = 0
    mb_wins = 0

    for r in results:
        pm_mean = r["pmtiles"]["mean"]
        mb_mean = r["mbtiles"]["mean"]
        if mb_mean > 0 and pm_mean > 0:
            ratio = pm_mean / mb_mean
            if ratio > 1:
                winner = "MBTiles"
                ratio_str = f"{ratio:.2f}x"
                mb_wins += 1
            else:
                winner = "PMTiles"
                ratio_str = f"{1/ratio:.2f}x"
                pm_wins += 1
        else:
            ratio_str = "N/A"
            winner = "N/A"

        print(
            f"{r['dataset']:<30s}  {pm_mean:8.3f}ms  {mb_mean:8.3f}ms  {ratio_str:>8s}  {winner:>10s}"
        )

    print(f"\nPMTiles faster: {pm_wins}  |  MBTiles faster: {mb_wins}  |  Total: {len(results)}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark PMTiles vs MBTiles")
    parser.add_argument("--mode", choices=["library", "http"], default="library")
    parser.add_argument("--pmtiles-dir", default=".", help="PMTiles directory")
    parser.add_argument("--mbtiles-dir", default="../crome-work/mbtiles", help="MBTiles directory")
    parser.add_argument("--server", default="http://127.0.0.1:8765", help="Tile server URL (http mode)")
    parser.add_argument("--tiles", type=int, default=500, help="Tiles per dataset")
    parser.add_argument("--datasets", help="Comma-separated dataset names (default: all matching)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)

    if args.mode == "library":
        all_datasets = discover_datasets(args.pmtiles_dir, args.mbtiles_dir)
        if args.datasets:
            names = [n.strip() for n in args.datasets.split(",")]
            all_datasets = {k: v for k, v in all_datasets.items() if k in names}

        if not all_datasets:
            print("No datasets found in both PMTiles and MBTiles format.")
            print(f"  PMTiles dir: {args.pmtiles_dir}")
            print(f"  MBTiles dir: {args.mbtiles_dir}")
            sys.exit(1)

        print(f"Found {len(all_datasets)} datasets with both formats:")
        for name in all_datasets:
            print(f"  - {name}")

        results = benchmark_library(all_datasets, tile_count=args.tiles)
        print_summary(results)

    elif args.mode == "http":
        ds = [n.strip() for n in args.datasets.split(",")] if args.datasets else []
        benchmark_http(args.server, ds, tile_count=args.tiles)


if __name__ == "__main__":
    main()
