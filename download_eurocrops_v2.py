#!/usr/bin/env python3
"""Download EuroCrops V2 GeoParquet files from JRC and convert to PMTiles.

EuroCrops V2 provides harmonized crop parcel data for 18 EU countries (2008-2023)
using HCAT v4 taxonomy, distributed as GeoParquet files.

Usage:
    # List available country/year combinations
    python3 download_eurocrops_v2.py --list

    # Download all countries (latest year each)
    python3 download_eurocrops_v2.py --download

    # Download specific countries
    python3 download_eurocrops_v2.py --download --countries at,de4,fr

    # Convert downloaded GeoParquet to a single PMTiles
    python3 download_eurocrops_v2.py --convert

Requirements:
    pip install geopandas pyarrow requests
    tippecanoe (brew install tippecanoe)
    pmtiles CLI
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

# EuroCrops V2 country codes and available years
# Source: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/DRLL/EuroCropsV2/gpqt/
COUNTRIES = {
    "at":   {"name": "Austria",           "years": list(range(2015, 2024))},
    "be2":  {"name": "Belgium (Flanders)", "years": list(range(2008, 2024))},
    "be3":  {"name": "Belgium (Wallonia)", "years": list(range(2013, 2024))},
    "bg":   {"name": "Bulgaria",          "years": [2021]},
    "cz":   {"name": "Czechia",           "years": [2021]},
    "de4":  {"name": "Germany (Brandenburg)", "years": [2021, 2022]},
    "dea":  {"name": "Germany (NRW)",     "years": [2021, 2022]},
    "dk":   {"name": "Denmark",           "years": list(range(2019, 2024))},
    "ee":   {"name": "Estonia",           "years": list(range(2021, 2024))},
    "es":   {"name": "Spain",             "years": list(range(2020, 2024))},
    "fi":   {"name": "Finland",           "years": [2021, 2022]},
    "fr":   {"name": "France",            "years": list(range(2018, 2024))},
    "ie":   {"name": "Ireland",           "years": [2021, 2022]},
    "iti1": {"name": "Italy (Tuscany)",   "years": list(range(2018, 2024))},
    "nl":   {"name": "Netherlands",       "years": list(range(2009, 2024))},
    "pt":   {"name": "Portugal",          "years": list(range(2018, 2024))},
    "si":   {"name": "Slovenia",          "years": list(range(2018, 2024))},
    "sk":   {"name": "Slovakia",          "years": list(range(2018, 2024))},
}

FTP_BASE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/DRLL/EuroCropsV2/gpqt"


def parquet_url(cc, year):
    return f"{FTP_BASE}/{cc}_{year}.parquet"


def download_file(url, output_path):
    if os.path.exists(output_path):
        print(f"  Exists: {output_path}")
        return True

    print(f"  Downloading: {url}")
    try:
        def progress(block, block_size, total):
            done = block * block_size
            if total > 0:
                pct = min(100, done * 100 // total)
                print(f"\r  {pct}% ({done / 1e6:.1f} MB)", end="", flush=True)

        urllib.request.urlretrieve(url, output_path, reporthook=progress)
        print()
        return True
    except Exception as e:
        print(f"\n  ERROR: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


def list_datasets():
    total = 0
    print("EuroCrops V2 — Available country/year combinations:\n")
    for cc, info in sorted(COUNTRIES.items()):
        years_str = ", ".join(str(y) for y in info["years"])
        n = len(info["years"])
        total += n
        print(f"  {cc:5s}  {info['name']:25s}  ({n:2d} years)  {years_str}")
    print(f"\nTotal: {total} files across {len(COUNTRIES)} countries")


def download(countries, download_dir, latest_only=False):
    os.makedirs(download_dir, exist_ok=True)
    downloaded = []

    for cc in countries:
        if cc not in COUNTRIES:
            print(f"Unknown country code: {cc}")
            continue

        info = COUNTRIES[cc]
        years = [info["years"][-1]] if latest_only else info["years"]

        for year in years:
            url = parquet_url(cc, year)
            local_path = os.path.join(download_dir, f"{cc}_{year}.parquet")
            if download_file(url, local_path):
                downloaded.append(local_path)

    print(f"\nDownloaded {len(downloaded)} files to {download_dir}")
    return downloaded


def convert_to_pmtiles(download_dir, output_path, max_zoom=12):
    """Convert all downloaded GeoParquet files to a single PMTiles."""
    import glob

    parquet_files = sorted(glob.glob(os.path.join(download_dir, "*.parquet")))
    if not parquet_files:
        print("No .parquet files found in", download_dir)
        return

    print(f"\nConverting {len(parquet_files)} GeoParquet files to PMTiles...")

    # Step 1: Convert each parquet to GeoJSON lines
    geojsonl_path = os.path.join(download_dir, "all_eurocrops_v2.geojsonl")
    if not os.path.exists(geojsonl_path):
        try:
            import geopandas as gpd
        except ImportError:
            print("ERROR: geopandas required. Install with: pip install geopandas pyarrow")
            sys.exit(1)

        print("  Reading GeoParquet files...")
        with open(geojsonl_path, "w") as out:
            for i, pf in enumerate(parquet_files, 1):
                print(f"  [{i}/{len(parquet_files)}] {os.path.basename(pf)}...")
                gdf = gpd.read_parquet(pf)
                # Reproject to WGS84 if needed
                if gdf.crs and gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs("EPSG:4326")
                # Keep only essential columns
                keep = [c for c in gdf.columns if c in [
                    "geometry", "EC_hcat_c", "EC_hcat_n", "EC_trans_n",
                    "EC_NUTS2", "EC_year", "country"
                ]]
                if "geometry" not in keep:
                    keep.append("geometry")
                gdf = gdf[keep]
                for _, row in gdf.iterrows():
                    feat = {
                        "type": "Feature",
                        "geometry": row.geometry.__geo_interface__,
                        "properties": {k: v for k, v in row.items() if k != "geometry"}
                    }
                    out.write(json.dumps(feat) + "\n")

        print(f"  GeoJSON lines: {geojsonl_path}")

    # Step 2: Run tippecanoe
    print(f"  Running tippecanoe (max zoom {max_zoom})...")
    subprocess.run([
        "tippecanoe",
        "-o", output_path,
        "-z", str(max_zoom),
        "-Z", "3",
        "--layer=eurocrops",
        "--drop-densest-as-needed",
        "--extend-zooms-if-still-dropping",
        "--force",
        geojsonl_path
    ], check=True)

    size = os.path.getsize(output_path)
    print(f"  Done: {output_path} ({size / 1e6:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Download EuroCrops V2")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--download", action="store_true", help="Download GeoParquet files")
    parser.add_argument("--convert", action="store_true", help="Convert to PMTiles")
    parser.add_argument("--countries", help="Comma-separated country codes (default: all)")
    parser.add_argument("--latest-only", action="store_true",
                        help="Download only latest year per country")
    parser.add_argument("--download-dir", default="/tmp/eurocrops_v2",
                        help="Download directory")
    parser.add_argument("--output", default="eurocrops-v2.pmtiles",
                        help="Output PMTiles path")
    parser.add_argument("--max-zoom", type=int, default=12, help="Max zoom for tippecanoe")
    args = parser.parse_args()

    if args.list:
        list_datasets()
        return

    if args.download:
        countries = (
            [c.strip() for c in args.countries.split(",")]
            if args.countries else list(COUNTRIES.keys())
        )
        download(countries, args.download_dir, latest_only=args.latest_only)

    if args.convert:
        convert_to_pmtiles(args.download_dir, args.output, max_zoom=args.max_zoom)

    if not args.list and not args.download and not args.convert:
        parser.print_help()


if __name__ == "__main__":
    main()
