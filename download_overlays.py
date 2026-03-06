#!/usr/bin/env python3
"""Download and convert JRC overlay datasets to PMTiles.

Downloads GeoTIFF datasets from JRC FTP, converts to raster PMTiles via
gdal2tiles → MBTiles → PMTiles pipeline.

Usage:
    python3 download_overlays.py [--dataset NAME] [--list] [--max-zoom 10]

Datasets:
    lpd           Land Productivity Dynamics (global, 1km, ~41MB per year)
    flood         River Flood Hazard maps for Europe (~90m)
    inca-crop     INCA Crop Provision (EU, 1km)
    inca-poll     INCA Crop Pollination (EU, 1km)

Requirements:
    pip install requests
    gdal2tiles.py (from GDAL)
    pmtiles CLI (go install github.com/protomaps/go-pmtiles/cmd/pmtiles@latest)
"""
import argparse
import os
import shutil
import subprocess
import sys
import urllib.request

DATASETS = {
    "lpd": {
        "label": "Land Productivity Dynamics",
        "files": {
            2015: "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/LPD/LPD_2015.tif",
            2019: "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/LPD/LPD_2019.tif",
            2023: "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/LPD/LPD_2023.tif",
        },
        "output_pattern": "lpd-{year}.pmtiles",
        "max_zoom": 8,  # 1km resolution → z8 is sufficient
    },
    "flood": {
        "label": "River Flood Hazard (Europe)",
        "files": {
            100: "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-EFAS/flood_hazard/Europe_RP100_filled_depth.tif",
        },
        "output_pattern": "flood-hazard-rp{year}.pmtiles",
        "max_zoom": 10,  # 90m resolution
    },
    "inca-crop": {
        "label": "INCA Crop Provision",
        "files": {
            "provision": "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/MAES/INCA/LATEST/crop_provision/CropProvision.zip",
        },
        "output_pattern": "inca-crop-provision.pmtiles",
        "max_zoom": 8,
        "is_zip": True,
    },
    "inca-poll": {
        "label": "INCA Crop Pollination",
        "files": {
            "pollination": "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/MAES/INCA/LATEST/crop_pollination/CropPollination.zip",
        },
        "output_pattern": "inca-crop-pollination.pmtiles",
        "max_zoom": 8,
        "is_zip": True,
    },
}


def download_file(url, output_path):
    """Download a file with progress reporting."""
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(f"  Already downloaded: {output_path} ({size / 1e6:.1f} MB)")
        return

    print(f"  Downloading: {url}")
    print(f"  → {output_path}")

    def progress(block, block_size, total):
        done = block * block_size
        if total > 0:
            pct = min(100, done * 100 // total)
            mb = done / 1e6
            print(f"\r  {pct}% ({mb:.1f} MB)", end="", flush=True)

    urllib.request.urlretrieve(url, output_path, reporthook=progress)
    print()
    size = os.path.getsize(output_path)
    print(f"  Done: {size / 1e6:.1f} MB")


def geotiff_to_pmtiles(tif_path, output_path, max_zoom=10):
    """Convert a GeoTIFF to PMTiles via gdal2tiles → MBTiles → pmtiles."""
    tiles_dir = tif_path + "_tiles"
    mbtiles_path = output_path.replace(".pmtiles", ".mbtiles")

    # Step 1: Reproject to EPSG:3857 if needed
    reprojected = tif_path.replace(".tif", "_3857.tif")
    if not os.path.exists(reprojected):
        print(f"  Reprojecting to EPSG:3857...")
        subprocess.run([
            "gdalwarp", "-t_srs", "EPSG:3857",
            "-r", "near", "-co", "COMPRESS=LZW",
            tif_path, reprojected
        ], check=True)

    # Step 2: Generate tiles
    if not os.path.exists(tiles_dir):
        print(f"  Generating tiles (z0-z{max_zoom})...")
        subprocess.run([
            "gdal2tiles.py", "-z", f"0-{max_zoom}",
            "-w", "none", "--processes=4",
            reprojected, tiles_dir
        ], check=True)

    # Step 3: Convert tiles directory to MBTiles
    if not os.path.exists(mbtiles_path):
        print(f"  Converting to MBTiles...")
        # Use mb-util or manual SQLite creation
        _tiles_to_mbtiles(tiles_dir, mbtiles_path)

    # Step 4: Convert MBTiles to PMTiles
    if not os.path.exists(output_path):
        print(f"  Converting to PMTiles...")
        subprocess.run([
            "pmtiles", "convert", mbtiles_path, output_path
        ], check=True)

    # Cleanup
    if os.path.exists(reprojected):
        os.remove(reprojected)
    if os.path.exists(tiles_dir):
        shutil.rmtree(tiles_dir)
    if os.path.exists(mbtiles_path):
        os.remove(mbtiles_path)

    size = os.path.getsize(output_path)
    print(f"  Done: {output_path} ({size / 1e6:.1f} MB)")


def _tiles_to_mbtiles(tiles_dir, mbtiles_path):
    """Convert a gdal2tiles directory to MBTiles."""
    import sqlite3

    conn = sqlite3.connect(mbtiles_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
    conn.execute(
        "CREATE TABLE tiles "
        "(zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX tiles_idx ON tiles (zoom_level, tile_column, tile_row)"
    )
    conn.execute("INSERT INTO metadata VALUES ('format', 'png')")
    conn.execute("INSERT INTO metadata VALUES ('type', 'overlay')")
    conn.commit()

    count = 0
    batch = []
    for z_dir in sorted(os.listdir(tiles_dir)):
        z_path = os.path.join(tiles_dir, z_dir)
        if not os.path.isdir(z_path) or not z_dir.isdigit():
            continue
        z = int(z_dir)
        for x_dir in sorted(os.listdir(z_path)):
            x_path = os.path.join(z_path, x_dir)
            if not os.path.isdir(x_path) or not x_dir.isdigit():
                continue
            x = int(x_dir)
            for tile_file in os.listdir(x_path):
                tile_path = os.path.join(x_path, tile_file)
                y_str = tile_file.split(".")[0]
                if not y_str.isdigit():
                    continue
                y = int(y_str)
                # gdal2tiles uses TMS Y convention
                with open(tile_path, "rb") as f:
                    data = f.read()
                batch.append((z, x, y, data))
                count += 1
                if len(batch) >= 1000:
                    conn.executemany("INSERT INTO tiles VALUES (?,?,?,?)", batch)
                    conn.commit()
                    batch = []
                    if count % 10000 == 0:
                        print(f"    {count} tiles...", flush=True)

    if batch:
        conn.executemany("INSERT INTO tiles VALUES (?,?,?,?)", batch)
        conn.commit()

    conn.close()
    print(f"    {count} tiles written to {mbtiles_path}")


def process_dataset(name, info, download_dir, output_dir, max_zoom_override=None):
    """Download and convert a dataset."""
    print(f"\n{'='*60}")
    print(f"Dataset: {info['label']}")
    print(f"{'='*60}")

    max_zoom = max_zoom_override or info["max_zoom"]

    for key, url in info["files"].items():
        ext = ".zip" if info.get("is_zip") else ".tif"
        local_file = os.path.join(download_dir, os.path.basename(url))
        download_file(url, local_file)

        if info.get("is_zip"):
            # Extract zip
            import zipfile
            extract_dir = local_file.replace(".zip", "")
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(local_file) as zf:
                    zf.extractall(extract_dir)
            # Find .tif files
            tif_files = []
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith(".tif") or f.endswith(".tiff"):
                        tif_files.append(os.path.join(root, f))
            if tif_files:
                tif_path = tif_files[0]  # Use first TIF
            else:
                print(f"  WARNING: No .tif found in {local_file}")
                continue
        else:
            tif_path = local_file

        output_name = info["output_pattern"].format(year=key)
        output_path = os.path.join(output_dir, output_name)

        if os.path.exists(output_path):
            print(f"  Already exists: {output_path}")
            continue

        geotiff_to_pmtiles(tif_path, output_path, max_zoom=max_zoom)


def main():
    parser = argparse.ArgumentParser(description="Download and convert JRC overlay datasets")
    parser.add_argument("--dataset", help="Specific dataset to process (default: all)")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--max-zoom", type=int, help="Override max zoom level")
    parser.add_argument("--download-dir", default="/tmp/overlay_downloads",
                        help="Directory for downloads")
    parser.add_argument("--output-dir", default=".", help="Output directory for PMTiles")
    args = parser.parse_args()

    if args.list:
        print("Available overlay datasets:")
        for name, info in DATASETS.items():
            print(f"  {name:15s} — {info['label']}")
            for key, url in info["files"].items():
                print(f"    {key}: {url}")
        return

    os.makedirs(args.download_dir, exist_ok=True)

    if args.dataset:
        names = [n.strip() for n in args.dataset.split(",")]
        for name in names:
            if name not in DATASETS:
                print(f"Unknown dataset: {name}")
                print(f"Available: {', '.join(DATASETS)}")
                sys.exit(1)
    else:
        names = list(DATASETS.keys())

    for name in names:
        process_dataset(name, DATASETS[name], args.download_dir, args.output_dir,
                        max_zoom_override=args.max_zoom)

    print("\nDone! PMTiles files are ready.")
    print("To use in the viewer, add them to Git LFS and push.")


if __name__ == "__main__":
    main()
