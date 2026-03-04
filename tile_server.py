#!/usr/bin/env python3
"""Tile server for PMTiles and MBTiles.

Serves tiles from both formats via HTTP, enabling direct comparison.

Usage:
    python3 tile_server.py [options]
    python3 tile_server.py --pmtiles-dir ./  --mbtiles-dir ../crome-work/mbtiles --port 8765

Endpoints:
    GET /pmtiles/{dataset}/{z}/{x}/{y}.{ext}
    GET /mbtiles/{dataset}/{z}/{x}/{y}.{ext}
    GET /datasets
"""
import argparse
import glob
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, JSONResponse
import uvicorn

from pmtiles.reader import Reader, MmapSource

app = FastAPI(title="PMTiles & MBTiles Tile Server")

# Stores
pmtiles_readers: dict[str, tuple[Reader, any]] = {}  # name -> (Reader, file_handle)
mbtiles_conns: dict[str, sqlite3.Connection] = {}     # name -> Connection


def dataset_name(path: str) -> str:
    return Path(path).stem


def load_pmtiles(directory: str):
    for p in sorted(glob.glob(os.path.join(directory, "*.pmtiles"))):
        name = dataset_name(p)
        fh = open(p, "rb")
        source = MmapSource(fh)
        reader = Reader(source)
        pmtiles_readers[name] = (reader, fh)
    print(f"Loaded {len(pmtiles_readers)} PMTiles: {', '.join(sorted(pmtiles_readers))}")


def load_mbtiles(directory: str):
    for p in sorted(glob.glob(os.path.join(directory, "*.mbtiles"))):
        name = dataset_name(p)
        conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True, check_same_thread=False)
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        mbtiles_conns[name] = conn
    print(f"Loaded {len(mbtiles_conns)} MBTiles: {', '.join(sorted(mbtiles_conns))}")


@app.get("/datasets")
def list_datasets():
    pmtiles_names = sorted(pmtiles_readers.keys())
    mbtiles_names = sorted(mbtiles_conns.keys())
    both = sorted(set(pmtiles_names) & set(mbtiles_names))
    return {
        "pmtiles": pmtiles_names,
        "mbtiles": mbtiles_names,
        "both": both,
        "pmtiles_count": len(pmtiles_names),
        "mbtiles_count": len(mbtiles_names),
        "both_count": len(both),
    }


@app.get("/pmtiles/{dataset}/{z}/{x}/{y}.{ext}")
def get_pmtile(dataset: str, z: int, x: int, y: int, ext: str):
    if dataset not in pmtiles_readers:
        raise HTTPException(404, f"PMTiles dataset '{dataset}' not found")
    reader, _ = pmtiles_readers[dataset]
    data = reader.get(z, x, y)
    if data is None:
        raise HTTPException(204, "No tile at this location")
    content_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "pbf": "application/x-protobuf",
        "mvt": "application/x-protobuf",
    }.get(ext, "application/octet-stream")
    return Response(content=data, media_type=content_type)


@app.get("/mbtiles/{dataset}/{z}/{x}/{y}.{ext}")
def get_mbtile(dataset: str, z: int, x: int, y: int, ext: str):
    if dataset not in mbtiles_conns:
        raise HTTPException(404, f"MBTiles dataset '{dataset}' not found")
    conn = mbtiles_conns[dataset]
    # TMS Y-flip
    tms_y = (1 << z) - 1 - y
    row = conn.execute(
        "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
        (z, x, tms_y),
    ).fetchone()
    if row is None:
        raise HTTPException(204, "No tile at this location")
    content_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "pbf": "application/x-protobuf",
        "mvt": "application/x-protobuf",
    }.get(ext, "application/octet-stream")
    return Response(content=row[0], media_type=content_type)


def main():
    parser = argparse.ArgumentParser(description="PMTiles & MBTiles Tile Server")
    parser.add_argument(
        "--pmtiles-dir",
        default=".",
        help="Directory containing .pmtiles files (default: current dir)",
    )
    parser.add_argument(
        "--mbtiles-dir",
        default="../crome-work/mbtiles",
        help="Directory containing .mbtiles files",
    )
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    args = parser.parse_args()

    load_pmtiles(args.pmtiles_dir)
    load_mbtiles(args.mbtiles_dir)

    print(f"\nStarting tile server on http://{args.host}:{args.port}")
    print(f"  GET /datasets")
    print(f"  GET /pmtiles/{{dataset}}/{{z}}/{{x}}/{{y}}.png")
    print(f"  GET /mbtiles/{{dataset}}/{{z}}/{{x}}/{{y}}.png\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
