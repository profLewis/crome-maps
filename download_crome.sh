#!/bin/bash
# download_crome.sh — Download and convert CROME for a given year
# Usage: ./download_crome.sh [YEAR]
# Example: ./download_crome.sh 2023
set -uo pipefail

YEAR="${1:?Usage: $0 YEAR (e.g. 2020, 2021, 2022, 2023, 2024)}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="${SCRIPT_DIR}/../crome-work"
OUTFILE="${SCRIPT_DIR}/crome${YEAR}.pmtiles"
FIFO="${WORKDIR}/geojson_fifo_${YEAR}"
WFS="WFS:https://environment.data.gov.uk/spatialdata/crop-map-of-england-${YEAR}/wfs"

# Check WFS exists
echo "Checking CROME $YEAR WFS availability..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://environment.data.gov.uk/spatialdata/crop-map-of-england-${YEAR}/wfs?service=WFS&version=2.0.0&request=GetCapabilities")
if [ "$HTTP_CODE" != "200" ]; then
  echo "ERROR: CROME $YEAR WFS not available (HTTP $HTTP_CODE)"
  exit 1
fi

# Discover county layer names from GetCapabilities
echo "Discovering county layers..."
CAPS=$(curl -s "https://environment.data.gov.uk/spatialdata/crop-map-of-england-${YEAR}/wfs?service=WFS&version=2.0.0&request=GetCapabilities")
# Extract layer names matching Crop_Map_of_England_YEAR_*
COUNTIES=()
while IFS= read -r line; do
  COUNTIES+=("$line")
done < <(echo "$CAPS" | grep -o "Crop_Map_of_England_${YEAR}_[A-Za-z_]*" | sort -u)

if [ ${#COUNTIES[@]} -eq 0 ]; then
  echo "ERROR: No county layers found for CROME $YEAR"
  exit 1
fi
echo "Found ${#COUNTIES[@]} counties for CROME $YEAR"

mkdir -p "$WORKDIR"
rm -f "$FIFO"
mkfifo "$FIFO"

# Tippecanoe reads from FIFO in background
tippecanoe \
  -o "$OUTFILE" \
  -l "crome${YEAR}" \
  -z12 \
  --coalesce-densest-as-needed \
  --drop-rate=1 \
  --hilbert \
  -y lucode \
  --simplification=10 \
  --force \
  < "$FIFO" &
TIPPECANOE_PID=$!

# Stream all counties into the FIFO
(
  TOTAL=${#COUNTIES[@]}
  COUNT=0
  FAILED=0
  for county in "${COUNTIES[@]}"; do
    COUNT=$((COUNT + 1))
    echo "[$COUNT/$TOTAL] Fetching $county..." >&2
    if ! ogr2ogr -f GeoJSONSeq /vsistdout/ "$WFS" "$county" \
      -t_srs EPSG:4326 -select lucode 2>/dev/null; then
      echo "  WARNING: $county FAILED, skipping" >&2
      FAILED=$((FAILED + 1))
    fi
  done
  echo "=== Streaming complete: $COUNT counties, $FAILED failed ===" >&2
) > "$FIFO"

echo "Waiting for tippecanoe to finish..."
wait $TIPPECANOE_PID
RC=$?

rm -f "$FIFO"

if [ $RC -eq 0 ]; then
  echo "=== DONE: CROME $YEAR ==="
  ls -lh "$OUTFILE"
else
  echo "=== TIPPECANOE FAILED with exit code $RC ==="
fi
