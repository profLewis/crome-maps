#!/usr/bin/env python3
"""Download SAGE Crop Calendar NetCDF and convert to PMTiles.

Downloads global crop planting/harvest date grids from Sacks et al. (2010)
at 0.5° resolution and converts to colored PMTiles for the map viewer.

Reference:
    Sacks, W.J., D. Deryng, J.A. Foley, and N. Ramankutty (2010).
    Crop planting dates: an analysis of global patterns.
    Global Ecology and Biogeography 19, 607-620.
    DOI: 10.1111/j.1466-8238.2010.00551.x

Source: https://sage.nelson.wisc.edu/data-and-models/datasets/crop-calendar-dataset/

Usage:
    python3 download_crop_calendar.py
"""
import gzip
import io
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

try:
    import requests
except ImportError:
    print("requests required: pip install requests")
    sys.exit(1)

try:
    from scipy.io import netcdf_file
except ImportError:
    print("scipy required: pip install scipy")
    sys.exit(1)

import numpy as np
from PIL import Image

BASE_URL = "https://sage-public-files.s3.amazonaws.com/crop-calendar-dataset/netcdf0.5deg"

# Crops to process — use filled (extrapolated) versions
CROPS = {
    'Wheat':         'Wheat.crop.calendar.fill.nc.gz',
    'Wheat.Winter':  'Wheat.Winter.crop.calendar.fill.nc.gz',
    'Maize':         'Maize.crop.calendar.fill.nc.gz',
    'Rice':          'Rice.crop.calendar.fill.nc.gz',
    'Soybeans':      'Soybeans.crop.calendar.fill.nc.gz',
    'Barley':        'Barley.crop.calendar.fill.nc.gz',
    'Cotton':        'Cotton.crop.calendar.fill.nc.gz',
    'Sorghum':       'Sorghum.crop.calendar.fill.nc.gz',
    'Potatoes':      'Potatoes.crop.calendar.fill.nc.gz',
    'Rapeseed.Winter': 'Rapeseed.Winter.crop.calendar.fill.nc.gz',
}

# Variables to extract
VARIABLES = {
    'plant':    'Planting Date',
    'harvest':  'Harvest Date',
}

# Color ramp for day-of-year (1-365): month-based colors
# Jan=blue/cold → spring=green → summer=yellow/red → autumn=orange → Dec=purple
DOY_COLORS = [
    (1,   48,  96, 204),    # Jan - deep blue
    (32,  48, 144, 232),    # Feb - blue
    (60,  32, 176, 144),    # Mar - teal
    (91,  64, 200,  64),    # Apr - green
    (121, 144, 224,  48),   # May - lime
    (152, 224, 224,  32),   # Jun - yellow-green
    (182, 255, 200,  32),   # Jul - gold
    (213, 255, 144,  32),   # Aug - orange
    (244, 232,  80,  32),   # Sep - red-orange
    (274, 200,  32,  48),   # Oct - red
    (305, 160,  32, 128),   # Nov - purple
    (335, 112,  48, 176),   # Dec - deep purple
    (366,  48,  96, 204),   # wrap to Jan
]


def doy_to_rgb(doy):
    """Convert day-of-year (1-365) to RGB color."""
    doy = max(1, min(365, int(doy)))
    for i in range(len(DOY_COLORS) - 1):
        d0, r0, g0, b0 = DOY_COLORS[i]
        d1, r1, g1, b1 = DOY_COLORS[i + 1]
        if doy <= d1:
            t = (doy - d0) / max(1, d1 - d0)
            r = int(r0 + t * (r1 - r0))
            g = int(g0 + t * (g1 - g0))
            b = int(b0 + t * (b1 - b0))
            return r, g, b
    return 48, 96, 204


def download_nc(crop_name, filename, download_dir):
    """Download and decompress a crop calendar NetCDF."""
    nc_path = os.path.join(download_dir, filename.replace('.gz', ''))
    if os.path.exists(nc_path):
        return nc_path

    gz_path = os.path.join(download_dir, filename)
    url = f"{BASE_URL}/{filename}"
    print(f"  Downloading {filename}...")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with open(gz_path, 'wb') as f:
        f.write(r.content)

    # Decompress
    with gzip.open(gz_path, 'rb') as gz, open(nc_path, 'wb') as out:
        out.write(gz.read())
    os.remove(gz_path)
    return nc_path


def nc_to_geotiff(nc_path, variable, output_tif):
    """Extract a variable from NetCDF and write as colored GeoTIFF."""
    ds = netcdf_file(nc_path, 'r')
    data = ds.variables[variable].data.copy()
    lat = ds.variables['latitude'].data.copy()
    lon = ds.variables['longitude'].data.copy()
    ds.close()

    # Data is 360x720, lat from 89.75 to -89.75, lon from -179.75 to 179.75
    h, w = data.shape

    # Create RGBA image
    img = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            val = data[y, x]
            if np.isnan(val) or val <= 0 or val > 365:
                continue  # transparent
            r, g, b = doy_to_rgb(val)
            img[y, x] = [r, g, b, 200]

    # Write as GeoTIFF using GDAL
    # First write PNG, then use gdal_translate to add georef
    png_path = output_tif.replace('.tif', '.png')
    Image.fromarray(img).save(png_path)

    # GeoTransform: pixel (0,0) is top-left
    # lon range: -180 to 180, lat range: 90 to -90
    xmin, xmax = -180.0, 180.0
    ymin, ymax = -90.0, 90.0
    xres = (xmax - xmin) / w
    yres = (ymax - ymin) / h

    subprocess.run([
        'gdal_translate', '-of', 'GTiff',
        '-a_srs', 'EPSG:4326',
        '-a_ullr', str(xmin), str(ymax), str(xmax), str(ymin),
        png_path, output_tif
    ], check=True, capture_output=True)
    os.remove(png_path)
    return output_tif


def geotiff_to_pmtiles(tif_path, pmtiles_path, max_zoom=6):
    """Convert GeoTIFF to PMTiles via gdalwarp → gdal2tiles → mb-util → pmtiles."""
    base = os.path.splitext(pmtiles_path)[0]
    warped = base + '_3857.tif'
    tiles_dir = base + '_tiles'
    mbtiles_path = base + '.mbtiles'

    # Reproject to Web Mercator
    subprocess.run([
        'gdalwarp', '-t_srs', 'EPSG:3857', '-r', 'near',
        '-co', 'COMPRESS=LZW', '-co', 'TILED=YES',
        tif_path, warped
    ], check=True, capture_output=True)

    # Generate tiles
    subprocess.run([
        'gdal2tiles.py', '-z', f'0-{max_zoom}', '-w', 'none',
        '--xyz', warped, tiles_dir
    ], check=True, capture_output=True)

    # Convert to MBTiles
    subprocess.run([
        'mb-util', tiles_dir, mbtiles_path, '--image_format=png', '--scheme=xyz'
    ], check=True, capture_output=True)

    # Convert to PMTiles
    subprocess.run([
        'pmtiles', 'convert', mbtiles_path, pmtiles_path
    ], check=True, capture_output=True)

    # Clean up
    for f in [warped, mbtiles_path]:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(tiles_dir):
        shutil.rmtree(tiles_dir)

    size_kb = os.path.getsize(pmtiles_path) / 1024
    print(f"    → {pmtiles_path} ({size_kb:.0f} KB)")


def main():
    download_dir = '/tmp/crop_calendar'
    output_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(download_dir, exist_ok=True)

    print("SAGE Crop Calendar → PMTiles")
    print(f"  Crops: {', '.join(CROPS.keys())}")
    print()

    for crop_name, filename in CROPS.items():
        print(f"[{crop_name}]")
        nc_path = download_nc(crop_name, filename, download_dir)

        for var_key, var_label in VARIABLES.items():
            slug = crop_name.lower().replace('.', '-')
            tif_path = os.path.join(download_dir, f"crop-cal-{slug}-{var_key}.tif")
            pmtiles_name = f"crop-cal-{slug}-{var_key}.pmtiles"
            pmtiles_path = os.path.join(output_dir, pmtiles_name)

            if os.path.exists(pmtiles_path):
                print(f"  {var_label}: already exists")
                continue

            print(f"  {var_label}...")
            nc_to_geotiff(nc_path, var_key, tif_path)
            geotiff_to_pmtiles(tif_path, pmtiles_path, max_zoom=6)

    print("\nDone!")


if __name__ == '__main__':
    main()
