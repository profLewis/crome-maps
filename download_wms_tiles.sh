#!/bin/bash
# download_wms_tiles.sh — Download WMS raster tiles and convert to PMTiles
# Usage: ./download_wms_tiles.sh <dataset_id> [year]
# Example: ./download_wms_tiles.sh germany 2024
#          ./download_wms_tiles.sh crome-raster 2020
set -uo pipefail

DATASET="${1:?Usage: $0 DATASET_ID [YEAR]}"
YEAR="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/raster_datasets.json"
WORKDIR="${SCRIPT_DIR}/../crome-work/raster_tiles"

# Check dependencies
for cmd in curl sqlite3 jq pmtiles python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: Required tool '$cmd' not found"
    exit 1
  fi
done

if [ ! -f "$CONFIG" ]; then
  echo "ERROR: Config file not found: $CONFIG"
  exit 1
fi

# Read config for this dataset
DS=$(jq -r --arg id "$DATASET" '.[$id] // empty' "$CONFIG")
if [ -z "$DS" ]; then
  echo "ERROR: Unknown dataset '$DATASET'"
  echo "Available datasets:"
  jq -r 'to_entries[] | select(.key != "_comment") | .key' "$CONFIG"
  exit 1
fi

LABEL=$(echo "$DS" | jq -r '.label')
AVAILABLE_YEARS=$(echo "$DS" | jq -r '.years[]' 2>/dev/null)

# Handle year
if [ -z "$YEAR" ]; then
  FIRST_YEAR=$(echo "$AVAILABLE_YEARS" | head -1)
  if [ "$FIRST_YEAR" = "current" ]; then
    YEAR="current"
  else
    echo "ERROR: Year required. Available: $AVAILABLE_YEARS"
    exit 1
  fi
fi

# Build output filename
if [ "$YEAR" = "current" ]; then
  OUTFILE="${SCRIPT_DIR}/${DATASET}.pmtiles"
  MBTILES="${WORKDIR}/${DATASET}.mbtiles"
else
  OUTFILE="${SCRIPT_DIR}/${DATASET}${YEAR}.pmtiles"
  MBTILES="${WORKDIR}/${DATASET}${YEAR}.mbtiles"
fi

mkdir -p "$WORKDIR"

echo "=== Downloading raster tiles: $LABEL ($YEAR) ==="
echo "Output: $OUTFILE"

# Export vars for the Python subprocess
export DATASET YEAR CONFIG MBTILES WORKDIR

# The entire download + MBTiles creation is done in Python for performance
python3 -u << 'PYEOF'
import json, math, os, sys, sqlite3, time, urllib.request, urllib.parse, urllib.error, concurrent.futures

dataset = os.environ.get("DATASET")
year = os.environ.get("YEAR")
config_path = os.environ.get("CONFIG")
mbtiles_path = os.environ.get("MBTILES")
workdir = os.environ.get("WORKDIR")

with open(config_path) as f:
    config = json.load(f)

ds = config[dataset]
wms_version = ds["wms_version"]
wms_url = ds["wms_url"].replace("{YEAR}", year)
layer = ds["layer"].replace("{YEAR}", year)
srs = ds.get("srs", "EPSG:3857")
fmt = ds.get("format", "image/png")
tile_size = ds.get("tile_size", 256)
min_zoom = ds.get("min_zoom", 0)
max_zoom = ds.get("max_zoom", 10)
time_param = ds.get("time_param")
west, south, east, north = ds["bounds"]

print(f"WMS: {wms_url}")
print(f"Layer: {layer}")
print(f"Zoom: {min_zoom}-{max_zoom}")
print(f"Bounds: {west},{south},{east},{north}")

extra_params = ""
if time_param and time_param != "null":
    extra_params = "&TIME=" + time_param.replace("{YEAR}", year)

# --- Tile math ---
def lon2x(lon, z):
    n = 2 ** z
    return max(0, min(n - 1, int((lon + 180.0) / 360.0 * n)))

def lat2y(lat, z):
    n = 2 ** z
    lat_rad = math.radians(lat)
    return max(0, min(n - 1, int((1.0 - math.log(math.tan(lat_rad) + 1.0/math.cos(lat_rad)) / math.pi) / 2.0 * n)))

def tile_bbox_3857(x, y, z):
    n = 2 ** z
    lon_min = x / n * 360.0 - 180.0
    lon_max = (x + 1) / n * 360.0 - 180.0
    lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    def to3857(lon, lat):
        mx = lon * 20037508.342789244 / 180.0
        my = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
        my = my * 20037508.342789244 / 180.0
        return mx, my
    x_min, y_min = to3857(lon_min, lat_min)
    x_max, y_max = to3857(lon_max, lat_max)
    return f"{x_min},{y_min},{x_max},{y_max}"

# --- Build tile list ---
tiles = []
for z in range(min_zoom, max_zoom + 1):
    x_min = lon2x(west, z)
    x_max = lon2x(east, z)
    y_min = lat2y(north, z)
    y_max = lat2y(south, z)
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            tiles.append((z, x, y))

print(f"Total tiles to download: {len(tiles)}")

# --- Create MBTiles ---
if os.path.exists(mbtiles_path):
    os.remove(mbtiles_path)

conn = sqlite3.connect(mbtiles_path)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("CREATE TABLE metadata (name TEXT, value TEXT)")
conn.execute("CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)")
conn.execute("CREATE UNIQUE INDEX tiles_idx ON tiles (zoom_level, tile_column, tile_row)")
conn.execute("INSERT INTO metadata VALUES ('name', ?)", (ds["label"],))
conn.execute("INSERT INTO metadata VALUES ('format', 'png')")
conn.execute("INSERT INTO metadata VALUES ('type', 'overlay')")
conn.execute("INSERT INTO metadata VALUES ('bounds', ?)", (f"{west},{south},{east},{north}",))
conn.execute("INSERT INTO metadata VALUES ('minzoom', ?)", (str(min_zoom),))
conn.execute("INSERT INTO metadata VALUES ('maxzoom', ?)", (str(max_zoom),))
conn.commit()

# --- URL encoder (done once) ---
encoded_layer = urllib.parse.quote(layer)

def build_url(bbox):
    if wms_version == "1.3.0":
        return (f"{wms_url}?service=WMS&version=1.3.0&request=GetMap"
                f"&layers={encoded_layer}&styles=&crs={srs}"
                f"&bbox={bbox}&width={tile_size}&height={tile_size}"
                f"&format={fmt}&transparent=true{extra_params}")
    else:
        return (f"{wms_url}?service=WMS&version=1.1.1&request=GetMap"
                f"&layers={encoded_layer}&styles=&srs={srs}"
                f"&bbox={bbox}&width={tile_size}&height={tile_size}"
                f"&format={fmt}&transparent=true{extra_params}")

# --- Download function ---
MAX_RETRIES = 3

def download_tile(tile):
    z, x, y = tile
    bbox = tile_bbox_3857(x, y, z)
    url = build_url(bbox)
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "crome-maps-downloader/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                if len(data) > 100:
                    tms_y = (1 << z) - 1 - y
                    return (z, x, tms_y, data)
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)
    return None

# --- Download with thread pool ---
downloaded = 0
failed = 0
batch_size = 500  # commit every N tiles
pending = []
t0 = time.time()

WORKERS = 8
current_zoom = -1

with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
    futures = {executor.submit(download_tile, t): t for t in tiles}
    for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
        result = future.result()
        tile = futures[future]
        if tile[0] != current_zoom:
            current_zoom = tile[0]

        if result:
            pending.append(result)
            downloaded += 1
        else:
            failed += 1

        # Batch insert
        if len(pending) >= batch_size:
            conn.executemany("INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)", pending)
            conn.commit()
            pending = []

        # Progress every 500 tiles or at the end
        if i % 500 == 0 or i == len(tiles):
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(tiles) - i) / rate if rate > 0 else 0
            pct = i * 100 // len(tiles)
            print(f"  [{pct:3d}%] {i}/{len(tiles)} — {downloaded} ok, {failed} fail — {rate:.1f} tiles/s, ETA {eta:.0f}s")

# Final insert
if pending:
    conn.executemany("INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)", pending)
    conn.commit()

conn.close()

elapsed = time.time() - t0
print(f"\nDownload complete in {elapsed:.1f}s: {downloaded} tiles, {failed} failed")

if downloaded == 0:
    print("ERROR: No tiles downloaded!")
    sys.exit(1)
PYEOF

RC=$?
if [ $RC -ne 0 ]; then
  echo "=== Download FAILED ==="
  exit $RC
fi

# --- Convert MBTiles to PMTiles ---
echo "Converting MBTiles to PMTiles..."
pmtiles convert "$MBTILES" "$OUTFILE" --force

if [ $? -eq 0 ] && [ -f "$OUTFILE" ]; then
  SIZE=$(ls -lh "$OUTFILE" | awk '{print $5}')
  echo "=== DONE: $LABEL $YEAR ($SIZE) ==="
  echo "Output: $OUTFILE"
else
  echo "=== PMTiles conversion FAILED ==="
  exit 1
fi
