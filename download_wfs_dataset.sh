#!/bin/bash
# download_wfs_dataset.sh — Download vector data via WFS and convert to PMTiles
# Usage: ./download_wfs_dataset.sh <dataset_id> [year]
# Example: ./download_wfs_dataset.sh netherlands
#          ./download_wfs_dataset.sh denmark 2024
#          ./download_wfs_dataset.sh crome 2023
set -uo pipefail

DATASET="${1:?Usage: $0 DATASET_ID [YEAR]}"
YEAR="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/wfs_datasets.json"
WORKDIR="${SCRIPT_DIR}/../crome-work"

if [ ! -f "$CONFIG" ]; then
  echo "ERROR: Config file not found: $CONFIG"
  exit 1
fi

# Check dependencies
for cmd in ogr2ogr tippecanoe jq curl; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: Required tool '$cmd' not found"
    exit 1
  fi
done

# Read config for this dataset
DS=$(jq -r --arg id "$DATASET" '.[$id] // empty' "$CONFIG")
if [ -z "$DS" ]; then
  echo "ERROR: Unknown dataset '$DATASET'"
  echo "Available datasets:"
  jq -r 'keys[]' "$CONFIG"
  exit 1
fi

LABEL=$(echo "$DS" | jq -r '.label')
DS_TYPE=$(echo "$DS" | jq -r '.type')
WFS_URL_TEMPLATE=$(echo "$DS" | jq -r '.wfs_url')
LAYER_PATTERN=$(echo "$DS" | jq -r '.layer_pattern')
MAX_ZOOM=$(echo "$DS" | jq -r '.tippecanoe.max_zoom // 12')
SIMPLIFICATION=$(echo "$DS" | jq -r '.tippecanoe.simplification // 10')
COALESCE=$(echo "$DS" | jq -r '.tippecanoe.coalesce // false')
DROP_DENSEST=$(echo "$DS" | jq -r '.tippecanoe.drop_densest // false')
BOUNDS=$(echo "$DS" | jq -r '.bounds // empty')
DISCOVERY=$(echo "$DS" | jq -r '.discovery // "fixed"')
AVAILABLE_YEARS=$(echo "$DS" | jq -r '.years[]' 2>/dev/null)

# Handle "current" year
if [ -z "$YEAR" ]; then
  FIRST_YEAR=$(echo "$AVAILABLE_YEARS" | head -1)
  if [ "$FIRST_YEAR" = "current" ]; then
    YEAR="current"
  else
    echo "ERROR: Year required for $DATASET. Available: $AVAILABLE_YEARS"
    exit 1
  fi
fi

# Build output filename
if [ "$YEAR" = "current" ]; then
  OUTFILE="${SCRIPT_DIR}/${DATASET}.pmtiles"
  LAYER_NAME="$DATASET"
else
  OUTFILE="${SCRIPT_DIR}/${DATASET}${YEAR}.pmtiles"
  LAYER_NAME="${DATASET}${YEAR}"
fi

echo "=== Downloading $LABEL ($YEAR) ==="
echo "Output: $OUTFILE"

# --- Special handling for CROME (multi-county) ---
if [ "$DATASET" = "crome" ]; then
  if [ "$YEAR" = "current" ]; then
    echo "ERROR: CROME requires a specific year"
    exit 1
  fi
  exec "$SCRIPT_DIR/download_crome.sh" "$YEAR"
fi

# --- Special handling for Portugal (multi-region) ---
if [ "$DATASET" = "portugal" ]; then
  REGIONS=$(echo "$DS" | jq -r '.regions[]')
  WFS_URL=$(echo "$WFS_URL_TEMPLATE" | sed "s/{YEAR}/$YEAR/g")
  FIFO="${WORKDIR}/${DATASET}_fifo_${YEAR}"
  mkdir -p "$WORKDIR"
  rm -f "$FIFO"
  mkfifo "$FIFO"

  # Build tippecanoe args
  TIPP_ARGS=(-o "$OUTFILE" -l "$LAYER_NAME" -z"$MAX_ZOOM" --simplification="$SIMPLIFICATION" --hilbert --force)
  [ "$COALESCE" = "true" ] && TIPP_ARGS+=(--coalesce-densest-as-needed)
  [ "$DROP_DENSEST" = "true" ] && TIPP_ARGS+=(--drop-densest-as-needed --drop-rate=1)

  tippecanoe "${TIPP_ARGS[@]}" < "$FIFO" &
  TIPP_PID=$!

  (
    for region in $REGIONS; do
      LAYER="isip.data:parcelas.${region}.${YEAR}jun10"
      echo "Fetching region: $region ($LAYER)..." >&2
      ogr2ogr -f GeoJSONSeq /vsistdout/ "$WFS_URL" "$LAYER" -t_srs EPSG:4326 2>/dev/null || \
        echo "  WARNING: Region $region failed" >&2
    done
  ) > "$FIFO"

  wait $TIPP_PID
  RC=$?
  rm -f "$FIFO"

  if [ $RC -eq 0 ]; then
    echo "=== DONE: $LABEL $YEAR ==="
    ls -lh "$OUTFILE"
  else
    echo "=== FAILED with exit code $RC ==="
  fi
  exit $RC
fi

# --- Generic WFS download ---

# Substitute year into WFS URL and layer pattern
WFS_URL=$(echo "$WFS_URL_TEMPLATE" | sed "s/{YEAR}/$YEAR/g")
LAYER=$(echo "$LAYER_PATTERN" | sed "s/{YEAR}/$YEAR/g")

# Handle Austria's special layer naming
if [ "$DATASET" = "austria" ]; then
  if [ "$YEAR" != "current" ] && [ "$YEAR" -le 2021 ] 2>/dev/null; then
    LAYER=$(echo "$DS" | jq -r '.layer_pattern_pre2022' | sed "s/{YEAR}/$YEAR/g")
  else
    LAYER=$(echo "$DS" | jq -r '.layer_pattern_post2022' | sed "s/{YEAR}/$YEAR/g")
  fi
fi

# Check WFS availability
echo "Checking WFS availability..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
  "$(echo "$WFS_URL" | sed 's/^WFS://')?service=WFS&version=2.0.0&request=GetCapabilities" 2>/dev/null)
if [ "$HTTP_CODE" != "200" ]; then
  echo "WARNING: WFS may not be available (HTTP $HTTP_CODE)"
  echo "Attempting download anyway..."
fi

# Discover layers if needed
if [ "$DISCOVERY" = "auto" ]; then
  echo "Discovering layers..."
  CAPS=$(curl -s --max-time 30 "$(echo "$WFS_URL" | sed 's/^WFS://')?service=WFS&version=2.0.0&request=GetCapabilities")
  DISCOVERED=$(echo "$CAPS" | grep -o "${LAYER_PATTERN/\{YEAR\}/$YEAR}" | sed "s/{COUNTY}/[A-Za-z_]*/g" | sort -u)
  if [ -n "$DISCOVERED" ]; then
    echo "Found layers: $(echo "$DISCOVERED" | wc -l | tr -d ' ')"
  fi
fi

# Setup FIFO for streaming
FIFO="${WORKDIR}/${DATASET}_fifo_${YEAR}"
mkdir -p "$WORKDIR"
rm -f "$FIFO"
mkfifo "$FIFO"

# Build tippecanoe arguments
TIPP_ARGS=(-o "$OUTFILE" -l "$LAYER_NAME" -z"$MAX_ZOOM" --simplification="$SIMPLIFICATION" --hilbert --force)
[ "$COALESCE" = "true" ] && TIPP_ARGS+=(--coalesce-densest-as-needed)
[ "$DROP_DENSEST" = "true" ] && TIPP_ARGS+=(--drop-densest-as-needed --drop-rate=1)

echo "Starting tippecanoe..."
tippecanoe "${TIPP_ARGS[@]}" < "$FIFO" &
TIPP_PID=$!

MAX_RETRIES=3

# Stream features to FIFO
(
  echo "Fetching layer: $LAYER from $WFS_URL ..." >&2
  ok=0
  for attempt in $(seq 1 $MAX_RETRIES); do
    # Use bbox if bounds are specified
    if [ -n "$BOUNDS" ] && [ "$BOUNDS" != "null" ]; then
      BBOX=$(echo "$BOUNDS" | jq -r 'join(",")')
      if ogr2ogr -f GeoJSONSeq /vsistdout/ "$WFS_URL" "$LAYER" \
        -t_srs EPSG:4326 -spat_srs EPSG:4326 -spat $BBOX 2>/dev/null; then
        ok=1
        break
      fi
    else
      if ogr2ogr -f GeoJSONSeq /vsistdout/ "$WFS_URL" "$LAYER" \
        -t_srs EPSG:4326 2>/dev/null; then
        ok=1
        break
      fi
    fi
    echo "  Attempt $attempt/$MAX_RETRIES failed, retrying in 5s..." >&2
    sleep 5
  done
  if [ $ok -eq 0 ]; then
    echo "  ERROR: Failed to download $LAYER after $MAX_RETRIES attempts" >&2
  fi
) > "$FIFO"

echo "Waiting for tippecanoe to finish..."
wait $TIPP_PID
RC=$?

rm -f "$FIFO"

if [ $RC -eq 0 ] && [ -f "$OUTFILE" ]; then
  SIZE=$(ls -lh "$OUTFILE" | awk '{print $5}')
  echo "=== DONE: $LABEL $YEAR ($SIZE) ==="
else
  echo "=== FAILED with exit code $RC ==="
fi
exit $RC
