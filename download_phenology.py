#!/usr/bin/env python3
"""Download USGS eVIIRS phenology GeoTIFFs and convert to PMTiles.

Downloads phenological metrics from the USGS EROS Remote Sensing Phenology
programme for CONUS (Continental US) at 375m resolution from the eVIIRS sensor.

Metrics:
  SOST  - Start of Season Time (day of year)
  SOSN  - Start of Season NDVI
  EOST  - End of Season Time (day of year)
  EOSN  - End of Season NDVI
  MAXT  - Maximum Time (day of year)
  MAXN  - Maximum NDVI
  DUR   - Duration of growing season (days)
  AMP   - Amplitude (MAXN - base NDVI)
  TIN   - Time Integrated NDVI (cumulative greenness)

Usage:
    python3 download_phenology.py [--metrics SOST,EOST,MAXN] [--years 2022,2023]
                                  [--region east|west|alaska] [--output-dir phenology/]

Requirements:
    - GDAL (gdalwarp, gdal2tiles.py) — brew install gdal / apt install gdal-bin
    - mb-util — pip install mbutil
    - pmtiles CLI — https://github.com/protomaps/go-pmtiles
    - requests — pip install requests
"""
import argparse
import os
import subprocess
import sys
import zipfile

try:
    import requests
except ImportError:
    print("requests required: pip install requests")
    sys.exit(1)

# USGS eVIIRS download base URL
BASE_URL = "https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/phenology/downloads/rspzip/eVIIRS"

# Available metrics
ALL_METRICS = ['SOST', 'SOSN', 'EOST', 'EOSN', 'MAXT', 'MAXN', 'DUR', 'AMP', 'TIN']

# Regions and their URL path components
REGIONS = {
    'east': 'east',
    'west': 'west',
    'alaska': 'alaska'
}

# Filename patterns per region
FILENAME_PATTERNS = {
    'east': 'S-NPP_375m_eVIIRS_East_{metric}{year}.zip',
    'west': 'S-NPP_375m_eVIIRS_West_{metric}{year}.zip',
    'alaska': 'S-NPP_375m_eVIIRS_Alaska_{metric}{year}.zip'
}

# Color tables for each metric type (RGBA for GDAL)
COLOR_TABLES = {
    'SOST': {  # Day of year: green for early, red for late
        1: (26, 150, 65, 255),      # Jan - deep green
        60: (166, 217, 106, 255),    # Mar - light green
        120: (255, 255, 191, 255),   # May - yellow
        180: (253, 174, 97, 255),    # Jul - orange
        240: (215, 25, 28, 255),     # Sep - red
        365: (128, 0, 0, 255)        # Dec - dark red
    },
    'EOST': {  # Day of year: green for early, red for late
        180: (26, 150, 65, 255),
        220: (166, 217, 106, 255),
        260: (255, 255, 191, 255),
        300: (253, 174, 97, 255),
        340: (215, 25, 28, 255),
        365: (128, 0, 0, 255)
    },
    'MAXN': {  # NDVI value scaled 0-10000: brown to green
        0: (139, 69, 19, 255),
        2000: (210, 180, 140, 255),
        4000: (255, 255, 0, 255),
        6000: (144, 238, 144, 255),
        8000: (34, 139, 34, 255),
        10000: (0, 100, 0, 255)
    },
    'DUR': {  # Duration in days: red (short) to green (long)
        0: (215, 25, 28, 255),
        60: (253, 174, 97, 255),
        120: (255, 255, 191, 255),
        180: (166, 217, 106, 255),
        240: (26, 150, 65, 255),
        365: (0, 68, 27, 255)
    }
}
# Default color table for metrics without a specific one
DEFAULT_COLORS = COLOR_TABLES['MAXN']

# Available years (eVIIRS)
AVAILABLE_YEARS = list(range(2021, 2025))


def download_file(url, dest_path):
    """Download a file with progress indication."""
    print(f"  Downloading {os.path.basename(dest_path)}...")
    try:
        r = requests.get(url, stream=True, timeout=300)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  ERROR: {e}")
        return False

    total = int(r.headers.get('content-length', 0))
    downloaded = 0
    with open(dest_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 // total
                print(f"\r  {pct}% ({downloaded // 1024 // 1024}MB)", end='', flush=True)
    print()
    return True


def extract_tif(zip_path, extract_dir):
    """Extract GeoTIFF from zip archive."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        tif_files = [f for f in zf.namelist() if f.lower().endswith('.tif')]
        if not tif_files:
            print(f"  WARNING: No .tif files found in {zip_path}")
            return None
        zf.extract(tif_files[0], extract_dir)
        return os.path.join(extract_dir, tif_files[0])


def write_color_table(metric, path):
    """Write a GDAL color table file for the given metric."""
    colors = COLOR_TABLES.get(metric, DEFAULT_COLORS)
    with open(path, 'w') as f:
        f.write("nv 0 0 0 0\n")  # nodata = transparent
        for value, (r, g, b, a) in sorted(colors.items()):
            f.write(f"{value} {r} {g} {b} {a}\n")
    return path


def convert_to_pmtiles(tif_path, output_path, metric, max_zoom=8):
    """Convert GeoTIFF to PMTiles via gdalwarp → gdal2tiles → MBTiles → PMTiles."""
    base = os.path.splitext(output_path)[0]
    reprojected = base + '_3857.tif'
    colored = base + '_colored.tif'
    tiles_dir = base + '_tiles'
    mbtiles_path = base + '.mbtiles'

    # Write color table
    color_file = base + '_colors.txt'
    write_color_table(metric, color_file)

    print(f"  Reprojecting to EPSG:3857...")
    subprocess.run([
        'gdalwarp', '-t_srs', 'EPSG:3857', '-r', 'near',
        '-co', 'COMPRESS=LZW', '-co', 'TILED=YES',
        tif_path, reprojected
    ], check=True, capture_output=True)

    print(f"  Applying color table...")
    subprocess.run([
        'gdaldem', 'color-relief', reprojected, color_file, colored,
        '-alpha', '-of', 'GTiff', '-co', 'COMPRESS=LZW'
    ], check=True, capture_output=True)

    print(f"  Generating tiles (z0-{max_zoom})...")
    subprocess.run([
        'gdal2tiles.py', '-z', f'0-{max_zoom}', '-w', 'none',
        '--xyz', colored, tiles_dir
    ], check=True, capture_output=True)

    print(f"  Converting to MBTiles...")
    subprocess.run([
        'mb-util', tiles_dir, mbtiles_path, '--image_format=png', '--scheme=xyz'
    ], check=True, capture_output=True)

    print(f"  Converting to PMTiles...")
    subprocess.run([
        'pmtiles', 'convert', mbtiles_path, output_path
    ], check=True, capture_output=True)

    # Clean up intermediates
    for f in [reprojected, colored, color_file, mbtiles_path]:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(tiles_dir):
        import shutil
        shutil.rmtree(tiles_dir)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Created {output_path} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(
        description='Download USGS eVIIRS phenology data and convert to PMTiles'
    )
    parser.add_argument('--metrics', default='SOST,EOST,MAXN,DUR',
                        help='Comma-separated metrics (default: SOST,EOST,MAXN,DUR)')
    parser.add_argument('--years', default='2023',
                        help='Comma-separated years (default: 2023)')
    parser.add_argument('--region', default='east', choices=REGIONS.keys(),
                        help='Region to download (default: east)')
    parser.add_argument('--output-dir', default='phenology',
                        help='Output directory (default: phenology/)')
    parser.add_argument('--max-zoom', type=int, default=8,
                        help='Maximum tile zoom level (default: 8)')
    parser.add_argument('--download-only', action='store_true',
                        help='Download GeoTIFFs only, skip PMTiles conversion')
    parser.add_argument('--list-available', action='store_true',
                        help='List available metrics and years')
    args = parser.parse_args()

    if args.list_available:
        print("Available metrics:", ', '.join(ALL_METRICS))
        print("Available years:", ', '.join(str(y) for y in AVAILABLE_YEARS))
        print("Available regions:", ', '.join(REGIONS.keys()))
        print("\nMetric descriptions:")
        descs = {
            'SOST': 'Start of Season Time (day of year)',
            'SOSN': 'Start of Season NDVI value',
            'EOST': 'End of Season Time (day of year)',
            'EOSN': 'End of Season NDVI value',
            'MAXT': 'Maximum NDVI Time (day of year)',
            'MAXN': 'Maximum NDVI value',
            'DUR': 'Duration of growing season (days)',
            'AMP': 'Amplitude (peak - base NDVI)',
            'TIN': 'Time Integrated NDVI (cumulative greenness)'
        }
        for m, d in descs.items():
            print(f"  {m:5s} — {d}")
        return

    metrics = [m.strip().upper() for m in args.metrics.split(',')]
    years = [int(y.strip()) for y in args.years.split(',')]
    region = args.region

    # Validate
    for m in metrics:
        if m not in ALL_METRICS:
            print(f"ERROR: Unknown metric '{m}'. Available: {', '.join(ALL_METRICS)}")
            sys.exit(1)
    for y in years:
        if y not in AVAILABLE_YEARS:
            print(f"WARNING: Year {y} may not be available (known: {AVAILABLE_YEARS})")

    os.makedirs(args.output_dir, exist_ok=True)
    zip_dir = os.path.join(args.output_dir, 'downloads')
    os.makedirs(zip_dir, exist_ok=True)

    print(f"USGS eVIIRS Phenology Download")
    print(f"  Region: {region}")
    print(f"  Metrics: {', '.join(metrics)}")
    print(f"  Years: {', '.join(str(y) for y in years)}")
    print()

    for year in years:
        for metric in metrics:
            filename = FILENAME_PATTERNS[region].format(metric=metric, year=year)
            url = f"{BASE_URL}/{REGIONS[region]}/{metric}/{filename}"
            zip_path = os.path.join(zip_dir, filename)

            print(f"[{metric} {year}] {region}")

            # Download
            if os.path.exists(zip_path):
                print(f"  Already downloaded: {zip_path}")
            else:
                if not download_file(url, zip_path):
                    continue

            # Extract
            tif_path = extract_tif(zip_path, zip_dir)
            if not tif_path:
                continue
            print(f"  Extracted: {os.path.basename(tif_path)}")

            if args.download_only:
                continue

            # Convert to PMTiles
            output_name = f"phenology-{metric.lower()}-{region}-{year}.pmtiles"
            output_path = os.path.join(args.output_dir, output_name)
            if os.path.exists(output_path):
                print(f"  Already exists: {output_path}")
                continue

            try:
                convert_to_pmtiles(tif_path, output_path, metric, args.max_zoom)
            except subprocess.CalledProcessError as e:
                print(f"  ERROR during conversion: {e}")
                continue
            except FileNotFoundError as e:
                print(f"  ERROR: Required tool not found: {e}")
                print("  Install: brew install gdal && pip install mbutil && go install github.com/protomaps/go-pmtiles/cmd/pmtiles@latest")
                sys.exit(1)

    print("\nDone!")


if __name__ == '__main__':
    main()
