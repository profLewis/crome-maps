#!/bin/bash
# download_geotiff.sh — Download GeoTIFF and convert to PMTiles
# Usage: ./download_geotiff.sh <dataset_id> [year] [--force-reprocess]
# Example: ./download_geotiff.sh brazil-mapbiomas 2023
set -uo pipefail

DATASET="${1:?Usage: $0 DATASET_ID [YEAR] [--force-reprocess]}"
YEAR="${2:-}"
FORCE_REPROCESS=false
for arg in "$@"; do
  [ "$arg" = "--force-reprocess" ] && FORCE_REPROCESS=true
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/raster_datasets.json"
WORKDIR="${SCRIPT_DIR}/../crome-work/geotiff"

# Check dependencies
for cmd in curl jq gdalwarp gdal_translate gdaldem gdaladdo gdalinfo pmtiles; do
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
  echo "Available geotiff datasets:"
  jq -r 'to_entries[] | select(.value.source_type == "geotiff") | .key' "$CONFIG"
  exit 1
fi

SOURCE_TYPE=$(echo "$DS" | jq -r '.source_type // "wms"')
if [ "$SOURCE_TYPE" != "geotiff" ]; then
  echo "ERROR: Dataset '$DATASET' has source_type='$SOURCE_TYPE', not 'geotiff'"
  echo "Use download_wms_tiles.sh for WMS datasets"
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

# Build URLs and paths
SOURCE_URL=$(echo "$DS" | jq -r '.source_url' | sed "s/{YEAR}/$YEAR/g")
SOURCE_SRS=$(echo "$DS" | jq -r '.source_srs // "EPSG:4326"')
BAND_COUNT=$(echo "$DS" | jq -r '.band_count // 1')
COLOR_TABLE_NAME=$(echo "$DS" | jq -r '.color_table // "none"')
NODATA=$(echo "$DS" | jq -r '.nodata_value // "none"')
MIN_ZOOM=$(echo "$DS" | jq -r '.min_zoom // 0')
MAX_ZOOM=$(echo "$DS" | jq -r '.max_zoom // 12')

# Output filename
if [ "$YEAR" = "current" ]; then
  OUTFILE="${SCRIPT_DIR}/${DATASET}.pmtiles"
  PREFIX="${DATASET}"
else
  OUTFILE="${SCRIPT_DIR}/${DATASET}${YEAR}.pmtiles"
  PREFIX="${DATASET}${YEAR}"
fi

mkdir -p "$WORKDIR"

echo "=== Downloading GeoTIFF: $LABEL ($YEAR) ==="
echo "Source: $SOURCE_URL"
echo "Output: $OUTFILE"
echo ""

# ---- Step 1: Download raw GeoTIFF ----
RAW_TIFF="$WORKDIR/${PREFIX}_raw.tif"

if [ -f "$RAW_TIFF" ] && [ "$FORCE_REPROCESS" != "true" ]; then
  RAW_SIZE=$(ls -lh "$RAW_TIFF" | awk '{print $5}')
  echo "[1/5] Raw GeoTIFF exists ($RAW_SIZE), skipping download"
else
  echo "[1/5] Downloading GeoTIFF..."
  curl -L -C - --retry 3 --retry-delay 10 \
    --progress-bar \
    -H "User-Agent: crome-maps-downloader/1.0" \
    -o "$RAW_TIFF" "$SOURCE_URL"
  RC=$?
  if [ $RC -ne 0 ] || [ ! -f "$RAW_TIFF" ]; then
    echo "ERROR: Download failed (exit code $RC)"
    rm -f "$RAW_TIFF"
    exit 1
  fi
  RAW_SIZE=$(ls -lh "$RAW_TIFF" | awk '{print $5}')
  echo "  Downloaded: $RAW_SIZE"
fi

# ---- Step 2: Apply color table (single-band categorical → RGBA) ----
RGBA_TIFF="$WORKDIR/${PREFIX}_rgba.tif"

if [ "$BAND_COUNT" = "1" ] && [ "$COLOR_TABLE_NAME" != "none" ]; then
  COLOR_TABLE="$SCRIPT_DIR/color_tables/$COLOR_TABLE_NAME"
  if [ ! -f "$COLOR_TABLE" ]; then
    echo "ERROR: Color table not found: $COLOR_TABLE"
    exit 1
  fi

  if [ -f "$RGBA_TIFF" ] && [ "$FORCE_REPROCESS" != "true" ]; then
    echo "[2/5] RGBA GeoTIFF exists, skipping color relief"
  else
    echo "[2/5] Applying color table ($COLOR_TABLE_NAME)..."
    gdaldem color-relief "$RAW_TIFF" "$COLOR_TABLE" "$RGBA_TIFF" \
      -alpha -nearest_color_entry \
      -co COMPRESS=DEFLATE -co TILED=YES
    RC=$?
    if [ $RC -ne 0 ]; then
      echo "ERROR: gdaldem color-relief failed"
      rm -f "$RGBA_TIFF"
      exit 1
    fi
    RGBA_SIZE=$(ls -lh "$RGBA_TIFF" | awk '{print $5}')
    echo "  Created RGBA: $RGBA_SIZE"
  fi
else
  echo "[2/5] Multi-band or no color table — skipping color relief"
  RGBA_TIFF="$RAW_TIFF"
fi

# ---- Step 3: Reproject to EPSG:3857 ----
REPROJECTED_TIFF="$WORKDIR/${PREFIX}_3857.tif"

if [ "$SOURCE_SRS" = "EPSG:3857" ]; then
  echo "[3/5] Already EPSG:3857 — skipping reproject"
  REPROJECTED_TIFF="$RGBA_TIFF"
elif [ -f "$REPROJECTED_TIFF" ] && [ "$FORCE_REPROCESS" != "true" ]; then
  echo "[3/5] Reprojected GeoTIFF exists, skipping"
else
  echo "[3/5] Reprojecting to EPSG:3857 (nearest neighbor)..."
  NODATA_FLAGS=""
  if [ "$NODATA" != "none" ] && [ "$NODATA" != "null" ]; then
    NODATA_FLAGS="-srcnodata $NODATA -dstnodata 0"
  fi
  gdalwarp -s_srs "$SOURCE_SRS" -t_srs EPSG:3857 \
    -r nearest \
    -co COMPRESS=DEFLATE -co TILED=YES \
    -dstalpha \
    -wm 2048 -multi \
    -overwrite \
    $NODATA_FLAGS \
    "$RGBA_TIFF" "$REPROJECTED_TIFF"
  RC=$?
  if [ $RC -ne 0 ]; then
    echo "ERROR: gdalwarp failed"
    rm -f "$REPROJECTED_TIFF"
    exit 1
  fi
  REPROJ_SIZE=$(ls -lh "$REPROJECTED_TIFF" | awk '{print $5}')
  echo "  Reprojected: $REPROJ_SIZE"
fi

# ---- Step 4: Convert to MBTiles ----
MBTILES="$WORKDIR/${PREFIX}.mbtiles"

if [ -f "$MBTILES" ] && [ "$FORCE_REPROCESS" != "true" ]; then
  echo "[4/5] MBTiles exists, skipping"
else
  echo "[4/5] Converting to MBTiles (zoom $MIN_ZOOM-$MAX_ZOOM)..."
  # Remove existing to avoid append issues
  rm -f "$MBTILES"

  gdal_translate -of MBTiles \
    -co TILE_FORMAT=PNG \
    -co RESAMPLING=NEAREST \
    -co ZOOM_LEVEL_STRATEGY=LOWER \
    "$REPROJECTED_TIFF" "$MBTILES"
  RC=$?
  if [ $RC -ne 0 ]; then
    echo "ERROR: gdal_translate to MBTiles failed"
    rm -f "$MBTILES"
    exit 1
  fi

  echo "  Building overviews..."
  gdaladdo -r nearest "$MBTILES" 2 4 8 16
  RC=$?
  if [ $RC -ne 0 ]; then
    echo "WARNING: gdaladdo failed (non-fatal, overviews may be incomplete)"
  fi

  MBTILES_SIZE=$(ls -lh "$MBTILES" | awk '{print $5}')
  echo "  MBTiles: $MBTILES_SIZE"
fi

# ---- Step 5: Convert MBTiles to PMTiles ----
echo "[5/5] Converting MBTiles to PMTiles..."
pmtiles convert "$MBTILES" "$OUTFILE" --force
RC=$?
if [ $RC -eq 0 ] && [ -f "$OUTFILE" ]; then
  SIZE=$(ls -lh "$OUTFILE" | awk '{print $5}')
  echo ""
  echo "=== DONE: $LABEL $YEAR ($SIZE) ==="
  echo "Output: $OUTFILE"

  # Optionally cleanup intermediates (keep raw download)
  if [ "${CLEANUP:-false}" = "true" ]; then
    echo "Cleaning up intermediates..."
    [ "$RGBA_TIFF" != "$RAW_TIFF" ] && rm -f "$RGBA_TIFF"
    [ "$REPROJECTED_TIFF" != "$RGBA_TIFF" ] && rm -f "$REPROJECTED_TIFF"
    rm -f "$MBTILES"
  fi
else
  echo "=== PMTiles conversion FAILED ==="
  exit 1
fi
