#!/bin/bash
# download_tiles_z10.sh — Download WMS tiles z0-z10 only for faster overview
# Usage: ./download_tiles_z10.sh <dataset_id> [year]
set -uo pipefail

DATASET="${1:?Usage: $0 DATASET_ID [YEAR]}"
YEAR="${2:-current}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/raster_datasets.json"
WORKDIR="${SCRIPT_DIR}/../crome-work/raster_tiles"

for cmd in curl sqlite3 jq pmtiles python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: Required tool '$cmd' not found"; exit 1
  fi
done

DS=$(jq -r --arg id "$DATASET" '.[$id] // empty' "$CONFIG")
if [ -z "$DS" ]; then echo "ERROR: Unknown dataset '$DATASET'"; exit 1; fi

LABEL=$(echo "$DS" | jq -r '.label')
OUTFILE="${SCRIPT_DIR}/${DATASET}-overview.pmtiles"
MBTILES="${WORKDIR}/${DATASET}-overview.mbtiles"
mkdir -p "$WORKDIR"

echo "=== Downloading overview tiles: $LABEL ($YEAR) z0-z10 ==="

export DATASET YEAR CONFIG MBTILES WORKDIR

python3 -u << 'PYEOF'
import json, math, os, sys, sqlite3, time, urllib.request, urllib.parse, concurrent.futures

dataset = os.environ["DATASET"]
year = os.environ["YEAR"]
config_path = os.environ["CONFIG"]
mbtiles_path = os.environ["MBTILES"]

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
max_zoom = min(ds.get("max_zoom", 10), 10)  # Cap at z10
time_param = ds.get("time_param")
west, south, east, north = ds["bounds"]

extra_params = ""
if time_param and time_param != "null":
    extra_params = "&TIME=" + time_param.replace("{YEAR}", year)

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

tiles = []
for z in range(min_zoom, max_zoom + 1):
    x_min = lon2x(west, z)
    x_max = lon2x(east, z)
    y_min = lat2y(north, z)
    y_max = lat2y(south, z)
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            tiles.append((z, x, y))

print(f"Zoom: {min_zoom}-{max_zoom}, Total tiles: {len(tiles)}")

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

def download_tile(tile):
    z, x, y = tile
    bbox = tile_bbox_3857(x, y, z)
    url = build_url(bbox)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                if len(data) > 100:
                    tms_y = (1 << z) - 1 - y
                    return (z, x, tms_y, data)
        except Exception:
            if attempt < 2:
                time.sleep(1)
    return None

downloaded = 0
failed = 0
pending = []
t0 = time.time()

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(download_tile, t): t for t in tiles}
    for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
        result = future.result()
        if result:
            pending.append(result)
            downloaded += 1
        else:
            failed += 1
        if len(pending) >= 500:
            conn.executemany("INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)", pending)
            conn.commit()
            pending = []
        if i % 500 == 0 or i == len(tiles):
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(tiles) - i) / rate if rate > 0 else 0
            print(f"  [{i*100//len(tiles):3d}%] {i}/{len(tiles)} — {downloaded} ok, {failed} fail — {rate:.1f}/s, ETA {eta:.0f}s")

if pending:
    conn.executemany("INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)", pending)
    conn.commit()
conn.close()

print(f"\nDone in {time.time()-t0:.1f}s: {downloaded} tiles, {failed} failed")
if downloaded == 0:
    sys.exit(1)
PYEOF

echo "Converting MBTiles to PMTiles..."
pmtiles convert "$MBTILES" "$OUTFILE" --force

if [ $? -eq 0 ] && [ -f "$OUTFILE" ]; then
  SIZE=$(ls -lh "$OUTFILE" | awk '{print $5}')
  echo "=== DONE: $LABEL overview ($SIZE) ==="
else
  echo "=== PMTiles conversion FAILED ==="
  exit 1
fi
