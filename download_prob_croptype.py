#!/usr/bin/env python3
"""Download EU probabilistic crop type maps and convert to PMTiles.

Downloads the expected crop share maps from Baumert et al. (2025) at 1km
resolution for EU-28 (1990-2018) and creates:
  1. Dominant crop type map (argmax of 25 crop shares)
  2. Individual crop share maps for key crops

Reference:
    Baumert, J., Heckelei, T., & Storm, H. (2025).
    A dataset of yearly probabilistic crop type maps for the EU from 1990 to 2018.
    Data in Brief, 60, 111472.
    DOI: 10.1016/j.dib.2025.111472

Source: https://zenodo.org/records/14409498

Usage:
    python3 download_prob_croptype.py
"""
import os
import shutil
import subprocess
import sys
import zipfile

import numpy as np
from PIL import Image

# Crop codes in band order (bands 1-25; band 0 is weight)
CROP_CODES = [
    'BARL', 'CITR', 'DWHE', 'FARA', 'FRUI', 'GRAS', 'INDU', 'MAIZ',
    'OATS', 'OCER', 'OLIV', 'PARI', 'POTA', 'PULS', 'RAPE', 'ROOF',
    'RYEM', 'SOYA', 'SUGB', 'SUNF', 'SWHE', 'TEXT', 'TOBA', 'VEGE', 'VINY'
]

CROP_NAMES = {
    'BARL': 'Barley', 'CITR': 'Citrus', 'DWHE': 'Durum Wheat',
    'FARA': 'Forage', 'FRUI': 'Fruits/Nuts', 'GRAS': 'Grassland',
    'INDU': 'Industrial Crops', 'MAIZ': 'Maize', 'OATS': 'Oats',
    'OCER': 'Other Cereals', 'OLIV': 'Olives', 'PARI': 'Rice',
    'POTA': 'Potatoes', 'PULS': 'Dry Pulses', 'RAPE': 'Rapeseed',
    'ROOF': 'Root/Forage', 'RYEM': 'Rye', 'SOYA': 'Soybean',
    'SUGB': 'Sugar Beet', 'SUNF': 'Sunflower', 'SWHE': 'Common Wheat',
    'TEXT': 'Textile/Fibre', 'TOBA': 'Tobacco', 'VEGE': 'Vegetables',
    'VINY': 'Vineyards'
}

# Colors for each crop type (for dominant crop map)
CROP_COLORS = {
    'BARL': (218, 227, 27),    'CITR': (255, 200, 0),
    'DWHE': (200, 160, 40),    'FARA': (144, 192, 255),
    'FRUI': (192, 64, 192),    'GRAS': (112, 204, 64),
    'INDU': (127, 255, 255),   'MAIZ': (255, 211, 0),
    'OATS': (160, 89, 137),    'OCER': (210, 180, 130),
    'OLIV': (128, 128, 0),     'PARI': (0, 168, 226),
    'POTA': (168, 112, 0),     'PULS': (0, 175, 73),
    'RAPE': (255, 165, 0),     'ROOF': (205, 170, 102),
    'RYEM': (170, 0, 124),     'SOYA': (38, 112, 0),
    'SUGB': (255, 127, 127),   'SUNF': (255, 255, 0),
    'SWHE': (165, 112, 0),     'TEXT': (0, 128, 128),
    'TOBA': (128, 0, 0),       'VEGE': (255, 102, 102),
    'VINY': (128, 0, 255),
}

# Share color ramp: 0% → transparent, low → light yellow, high → dark green
SHARE_RAMP = [
    (0,   255, 255, 255, 0),    # 0% — transparent
    (50,  255, 255, 200, 160),  # 5% — pale yellow
    (100, 255, 230, 100, 180),  # 10%
    (200, 200, 200, 50, 200),   # 20%
    (300, 100, 180, 30, 210),   # 30%
    (500, 34, 139, 34, 220),    # 50% — forest green
    (700, 0, 100, 0, 240),      # 70% — dark green
    (1000, 0, 60, 0, 255),      # 100% — very dark green
]


def share_to_rgba(val):
    """Convert share value (0-1000) to RGBA."""
    if val <= 0:
        return (0, 0, 0, 0)
    for i in range(len(SHARE_RAMP) - 1):
        v0, r0, g0, b0, a0 = SHARE_RAMP[i]
        v1, r1, g1, b1, a1 = SHARE_RAMP[i + 1]
        if val <= v1:
            t = (val - v0) / max(1, v1 - v0)
            return (
                int(r0 + t * (r1 - r0)),
                int(g0 + t * (g1 - g0)),
                int(b0 + t * (b1 - b0)),
                int(a0 + t * (a1 - a0)),
            )
    return (0, 60, 0, 255)


def extract_eu_tifs(zip_path, extract_dir):
    """Extract GeoTIFFs from the EU expected crop shares zip."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        tifs = [f for f in zf.namelist() if f.endswith('.tif')]
        print(f"  Found {len(tifs)} GeoTIFFs in archive")
        for t in tifs:
            dest = os.path.join(extract_dir, os.path.basename(t))
            if not os.path.exists(dest):
                zf.extract(t, extract_dir)
                # Move if in subdirectory
                extracted = os.path.join(extract_dir, t)
                if extracted != dest and os.path.exists(extracted):
                    os.rename(extracted, dest)
        return sorted([os.path.join(extract_dir, os.path.basename(t)) for t in tifs])


def make_dominant_crop_map(tif_path, output_png, output_tif):
    """Create a dominant crop type RGBA image from multi-band GeoTIFF."""
    from osgeo import gdal
    ds = gdal.Open(tif_path)
    if ds is None:
        print(f"  ERROR: Cannot open {tif_path}")
        return False

    w, h = ds.RasterXSize, ds.RasterYSize
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()

    # Read weight band (band 1) and crop share bands (bands 2-26)
    weight = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    shares = np.zeros((25, h, w), dtype=np.float32)
    for i in range(25):
        shares[i] = ds.GetRasterBand(i + 2).ReadAsArray().astype(np.float32)
    ds = None

    # Find dominant crop (argmax)
    dominant = np.argmax(shares, axis=0)
    max_share = np.max(shares, axis=0)

    # Create RGBA image
    img = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            if weight[y, x] <= 0 or max_share[y, x] <= 0:
                continue
            crop_idx = dominant[y, x]
            code = CROP_CODES[crop_idx]
            r, g, b = CROP_COLORS[code]
            img[y, x] = [r, g, b, 200]

    Image.fromarray(img).save(output_png)

    # Write georeferenced GeoTIFF
    drv = gdal.GetDriverByName('GTiff')
    out_ds = drv.Create(output_tif, w, h, 4, gdal.GDT_Byte,
                        options=['COMPRESS=LZW'])
    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(proj)
    for band_i in range(4):
        out_ds.GetRasterBand(band_i + 1).WriteArray(img[:, :, band_i])
    out_ds.FlushCache()
    out_ds = None
    return True


def make_crop_share_map(tif_path, crop_idx, output_tif):
    """Create a single-crop share map as colored GeoTIFF."""
    from osgeo import gdal
    ds = gdal.Open(tif_path)
    w, h = ds.RasterXSize, ds.RasterYSize
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()

    weight = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    share = ds.GetRasterBand(crop_idx + 2).ReadAsArray().astype(np.float32)
    ds = None

    img = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            if weight[y, x] <= 0 or share[y, x] <= 0:
                continue
            r, g, b, a = share_to_rgba(share[y, x])
            img[y, x] = [r, g, b, a]

    drv = gdal.GetDriverByName('GTiff')
    out_ds = drv.Create(output_tif, w, h, 4, gdal.GDT_Byte,
                        options=['COMPRESS=LZW'])
    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(proj)
    for band_i in range(4):
        out_ds.GetRasterBand(band_i + 1).WriteArray(img[:, :, band_i])
    out_ds.FlushCache()
    out_ds = None
    return True


def geotiff_to_pmtiles(tif_path, pmtiles_path, max_zoom=8):
    """Convert GeoTIFF (EPSG:3035) to PMTiles."""
    base = os.path.splitext(pmtiles_path)[0]
    warped = base + '_3857.tif'
    tiles_dir = base + '_tiles'
    mbtiles_path = base + '.mbtiles'

    print(f"    Reprojecting...")
    subprocess.run([
        'gdalwarp', '-t_srs', 'EPSG:3857', '-r', 'near',
        '-co', 'COMPRESS=LZW', '-co', 'TILED=YES',
        '-overwrite', tif_path, warped
    ], check=True, capture_output=True)

    print(f"    Tiling z0-{max_zoom}...")
    subprocess.run([
        'gdal2tiles.py', '-z', f'0-{max_zoom}', '-w', 'none',
        '--xyz', warped, tiles_dir
    ], check=True, capture_output=True)

    print(f"    MBTiles...")
    subprocess.run([
        'mb-util', tiles_dir, mbtiles_path, '--image_format=png', '--scheme=xyz'
    ], check=True, capture_output=True)

    print(f"    PMTiles...")
    subprocess.run([
        'pmtiles', 'convert', mbtiles_path, pmtiles_path
    ], check=True, capture_output=True)

    for f in [warped, mbtiles_path]:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(tiles_dir):
        shutil.rmtree(tiles_dir)

    size_mb = os.path.getsize(pmtiles_path) / (1024 * 1024)
    print(f"    → {os.path.basename(pmtiles_path)} ({size_mb:.1f} MB)")


def main():
    download_dir = '/tmp/prob_crop'
    output_dir = os.path.dirname(os.path.abspath(__file__))

    zip_path = os.path.join(download_dir, 'EU_expected_crop_shares.zip')
    if not os.path.exists(zip_path):
        print(f"ERROR: Download first: {zip_path}")
        print("  curl -L -o /tmp/prob_crop/EU_expected_crop_shares.zip "
              "https://zenodo.org/records/14409498/files/EU_expected_crop_shares.zip")
        sys.exit(1)

    # Extract
    print("Extracting GeoTIFFs...")
    tif_files = extract_eu_tifs(zip_path, download_dir)
    print(f"  {len(tif_files)} year files")

    # Find the 2018 file (latest year)
    tif_2018 = None
    for t in tif_files:
        if '2018' in os.path.basename(t):
            tif_2018 = t
            break
    if not tif_2018:
        tif_2018 = tif_files[-1]  # fallback to last
    print(f"\nUsing: {os.path.basename(tif_2018)}")

    # 1. Dominant crop type map
    dom_tif = os.path.join(download_dir, 'prob-crop-dominant-2018.tif')
    dom_pmtiles = os.path.join(output_dir, 'prob-crop-dominant.pmtiles')
    if not os.path.exists(dom_pmtiles):
        print("\n[Dominant Crop Type Map]")
        dom_png = dom_tif.replace('.tif', '.png')
        make_dominant_crop_map(tif_2018, dom_png, dom_tif)
        os.remove(dom_png)
        geotiff_to_pmtiles(dom_tif, dom_pmtiles)

    # 2. Individual crop share maps for key crops
    KEY_CROPS = ['SWHE', 'MAIZ', 'BARL', 'RAPE', 'SUNF', 'GRAS']
    for code in KEY_CROPS:
        idx = CROP_CODES.index(code)
        name = CROP_NAMES[code]
        share_tif = os.path.join(download_dir, f'prob-crop-{code.lower()}-share-2018.tif')
        share_pmtiles = os.path.join(output_dir, f'prob-crop-{code.lower()}-share.pmtiles')
        if os.path.exists(share_pmtiles):
            print(f"\n[{name} Share] already exists")
            continue
        print(f"\n[{name} Share]")
        make_crop_share_map(tif_2018, idx, share_tif)
        geotiff_to_pmtiles(share_tif, share_pmtiles)

    print("\nDone!")


if __name__ == '__main__':
    main()
