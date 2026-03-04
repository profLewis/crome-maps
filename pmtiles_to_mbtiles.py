#!/usr/bin/env python3
"""Convert PMTiles to MBTiles.

Usage: python3 pmtiles_to_mbtiles.py <input.pmtiles> [output.mbtiles]

If output is not specified, replaces .pmtiles with .mbtiles in the filename.
"""
import json
import os
import sqlite3
import sys

from pmtiles.reader import Reader, MmapSource, all_tiles
from pmtiles.tile import TileType


def pmtiles_to_mbtiles(input_path, output_path):
    with open(input_path, "rb") as f:
        source = MmapSource(f)
        reader = Reader(source)
        header = reader.header()
        metadata = reader.metadata()

        tile_type = header.get("tile_type", TileType.PNG)
        fmt_map = {
            TileType.PNG: "png",
            TileType.JPEG: "jpeg",
            TileType.WEBP: "webp",
            TileType.MVT: "pbf",
        }
        fmt = fmt_map.get(tile_type, "png")

        min_zoom = header.get("min_zoom", 0)
        max_zoom = header.get("max_zoom", 14)
        min_lon = header.get("min_lon_e7", -1800000000) / 1e7
        min_lat = header.get("min_lat_e7", -850000000) / 1e7
        max_lon = header.get("max_lon_e7", 1800000000) / 1e7
        max_lat = header.get("max_lat_e7", 850000000) / 1e7
        center_lon = header.get("center_lon_e7", 0) / 1e7
        center_lat = header.get("center_lat_e7", 0) / 1e7
        center_zoom = header.get("center_zoom", min_zoom)

        if os.path.exists(output_path):
            os.remove(output_path)

        conn = sqlite3.connect(output_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
        conn.execute(
            "CREATE TABLE tiles "
            "(zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX tiles_idx ON tiles (zoom_level, tile_column, tile_row)"
        )

        # Write metadata
        name = metadata.get("name", os.path.basename(input_path).replace(".pmtiles", ""))
        meta_rows = [
            ("name", name),
            ("format", fmt),
            ("type", metadata.get("type", "overlay")),
            ("bounds", f"{min_lon},{min_lat},{max_lon},{max_lat}"),
            ("center", f"{center_lon},{center_lat},{center_zoom}"),
            ("minzoom", str(min_zoom)),
            ("maxzoom", str(max_zoom)),
        ]
        if "description" in metadata:
            meta_rows.append(("description", metadata["description"]))
        if "attribution" in metadata:
            meta_rows.append(("attribution", metadata["attribution"]))
        # Store full original metadata as json
        meta_rows.append(("json", json.dumps(metadata)))

        conn.executemany("INSERT INTO metadata VALUES (?, ?)", meta_rows)
        conn.commit()

        # Iterate all tiles
        count = 0
        batch = []
        batch_size = 1000

        # MmapSource returns the get_bytes function itself (it IS the callable)
        get_bytes = source

        for (z, x, y), tile_data in all_tiles(get_bytes):
            # PMTiles uses slippy-map Y (origin top-left)
            # MBTiles uses TMS Y (origin bottom-left)
            tms_y = (1 << z) - 1 - y
            batch.append((z, x, tms_y, tile_data))
            count += 1

            if len(batch) >= batch_size:
                conn.executemany(
                    "INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)", batch
                )
                conn.commit()
                batch = []
                if count % 10000 == 0:
                    print(f"  {count} tiles written...", flush=True)

        if batch:
            conn.executemany("INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)", batch)
            conn.commit()

        conn.close()
        print(f"Done: {count} tiles written to {output_path}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        output_path = input_path.replace(".pmtiles", ".mbtiles")

    print(f"Converting {input_path} → {output_path}")
    pmtiles_to_mbtiles(input_path, output_path)


if __name__ == "__main__":
    main()
