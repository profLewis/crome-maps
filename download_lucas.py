#!/usr/bin/env python3
"""Download LUCAS 2022 Copernicus survey polygons and convert to PMTiles.

LUCAS (Land Use/Cover Area Frame Survey) provides ~150K ground truth polygons
across the EU with 82 land cover classes.

Usage:
    python3 download_lucas.py [--download] [--convert] [--output lucas-2022.pmtiles]

Requirements:
    pip install geopandas pyarrow
    ogr2ogr (from GDAL)
    tippecanoe (brew install tippecanoe)
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

LUCAS_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/LUCAS/"
    "LUCAS_2022_Copernicus/l2022_survey_cop_radpoly_attr.gpkg"
)
LUCAS_FILENAME = "l2022_survey_cop_radpoly_attr.gpkg"


def download(download_dir):
    os.makedirs(download_dir, exist_ok=True)
    output_path = os.path.join(download_dir, LUCAS_FILENAME)

    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(f"Already downloaded: {output_path} ({size / 1e6:.1f} MB)")
        return output_path

    print(f"Downloading LUCAS 2022 Copernicus polygons...")
    print(f"  URL: {LUCAS_URL}")

    def progress(block, block_size, total):
        done = block * block_size
        if total > 0:
            pct = min(100, done * 100 // total)
            print(f"\r  {pct}% ({done / 1e6:.1f} MB)", end="", flush=True)

    urllib.request.urlretrieve(LUCAS_URL, output_path, reporthook=progress)
    print()
    size = os.path.getsize(output_path)
    print(f"Done: {size / 1e6:.1f} MB")
    return output_path


def convert_to_pmtiles(gpkg_path, output_path, max_zoom=14):
    """Convert LUCAS GeoPackage to PMTiles via GeoJSON → tippecanoe."""
    geojsonl_path = gpkg_path.replace(".gpkg", ".geojsonl")

    if not os.path.exists(geojsonl_path):
        print("Converting GeoPackage to GeoJSON lines...")
        try:
            import geopandas as gpd
        except ImportError:
            print("ERROR: geopandas required. Install with: pip install geopandas")
            sys.exit(1)

        gdf = gpd.read_file(gpkg_path)
        print(f"  {len(gdf)} features, CRS: {gdf.crs}")

        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        # Keep key columns for the viewer
        keep_cols = [c for c in gdf.columns if c in [
            "geometry", "POINT_ID", "LC1", "LC1_LABEL", "LC2", "LC2_LABEL",
            "LU1", "LU1_LABEL", "SURVEY_DATE", "NUTS0", "NUTS2",
            "AREA_SIZE", "LC1_PCT", "INSPIRE_PLU"
        ]]
        if "geometry" not in keep_cols:
            keep_cols.append("geometry")

        gdf = gdf[keep_cols]

        with open(geojsonl_path, "w") as out:
            for _, row in gdf.iterrows():
                feat = {
                    "type": "Feature",
                    "geometry": row.geometry.__geo_interface__,
                    "properties": {
                        k: (str(v) if v is not None else None)
                        for k, v in row.items() if k != "geometry"
                    }
                }
                out.write(json.dumps(feat) + "\n")

        print(f"  Wrote {len(gdf)} features to {geojsonl_path}")

    # Run tippecanoe
    print(f"Running tippecanoe (max zoom {max_zoom})...")
    subprocess.run([
        "tippecanoe",
        "-o", output_path,
        "-z", str(max_zoom),
        "-Z", "2",
        "--layer=lucas",
        "--drop-densest-as-needed",
        "--extend-zooms-if-still-dropping",
        "--force",
        geojsonl_path
    ], check=True)

    size = os.path.getsize(output_path)
    print(f"Done: {output_path} ({size / 1e6:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Download and convert LUCAS 2022")
    parser.add_argument("--download", action="store_true", help="Download GeoPackage")
    parser.add_argument("--convert", action="store_true", help="Convert to PMTiles")
    parser.add_argument("--download-dir", default="/tmp/lucas",
                        help="Download directory")
    parser.add_argument("--output", default="lucas-2022.pmtiles",
                        help="Output PMTiles path")
    parser.add_argument("--max-zoom", type=int, default=14, help="Max zoom for tippecanoe")
    args = parser.parse_args()

    if args.download:
        gpkg_path = download(args.download_dir)
    else:
        gpkg_path = os.path.join(args.download_dir, LUCAS_FILENAME)

    if args.convert:
        if not os.path.exists(gpkg_path):
            print(f"GeoPackage not found: {gpkg_path}")
            print("Run with --download first")
            sys.exit(1)
        convert_to_pmtiles(gpkg_path, args.output, max_zoom=args.max_zoom)

    if not args.download and not args.convert:
        parser.print_help()


if __name__ == "__main__":
    main()
