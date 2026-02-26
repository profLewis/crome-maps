#!/bin/bash
# discover_updates.sh — Check WMS services for new years of data
# Reads datasets.txt and queries GetCapabilities for each WMS to find available layers/years.
# Run periodically to discover newly published data.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATASETS="$SCRIPT_DIR/datasets.txt"

echo "=== European Crop Map Dataset Discovery ==="
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# --- CROME (England) multi-year WFS check ---
echo "--- England (CROME) WFS years ---"
for year in $(seq 2016 2030); do
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://environment.data.gov.uk/spatialdata/crop-map-of-england-$year/wfs?service=WFS&version=2.0.0&request=GetCapabilities" 2>/dev/null)
  if [ "$code" = "200" ]; then
    echo "  CROME $year: AVAILABLE"
  fi
done
echo ""

# --- WMS year discovery ---
discover_wms_years() {
  local id="$1" label="$2" url="$3" pattern="$4"

  echo "--- $label ---"
  echo "  URL: $url"

  # Fetch GetCapabilities
  local caps
  caps=$(curl -s --max-time 15 "$url?service=WMS&request=GetCapabilities" 2>/dev/null)
  if [ -z "$caps" ]; then
    echo "  ERROR: Could not fetch capabilities"
    return
  fi

  # Extract layer names
  local layers
  layers=$(echo "$caps" | grep '<Name>' | sed 's/.*<Name>//' | sed 's/<.*//' | sort -u)

  case "$id" in
    germany)
      # TIME dimension — check the Dimension element
      local times
      times=$(echo "$caps" | grep -A1 'name="time"' | tail -1 | tr ',' '\n' | grep -o '[0-9]\{4\}' | sort -u)
      if [ -n "$times" ]; then
        echo "  Available years (TIME dimension): $(echo $times | tr '\n' ' ')"
      else
        echo "  Could not parse TIME dimension"
      fi
      ;;
    france)
      echo "  Available layers with years:"
      echo "$layers" | grep -i 'LANDUSE.AGRICULTURE' | while read -r l; do
        echo "    $l"
      done
      ;;
    belgium-fl)
      echo "  Available Flanders layers:"
      echo "$layers" | grep -i 'LbGebrPerc' | while read -r l; do
        echo "    $l"
      done
      ;;
    belgium-wa)
      echo "  Checking Wallonia year endpoints:"
      for yr in $(seq 2018 2030); do
        local wcode
        wcode=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
          "https://geoservices.wallonie.be/arcgis/services/AGRICULTURE/SIGEC_PARC_AGRI_ANON__${yr}/MapServer/WMSServer?service=WMS&request=GetCapabilities" 2>/dev/null)
        if [ "$wcode" = "200" ]; then
          echo "    $yr: AVAILABLE"
        fi
      done
      ;;
    austria)
      echo "  Available schlaege layers:"
      echo "$layers" | grep -i 'inspire_schlaege.*polygon' | while read -r l; do
        echo "    $l"
      done
      ;;
    denmark)
      echo "  Available Marker layers:"
      echo "$layers" | grep -i 'Marker_' | while read -r l; do
        echo "    $l"
      done
      ;;
    luxembourg)
      echo "  Available LPIS layers:"
      echo "$layers" | grep -i 'ExistingLandUseObject_LPIS' | while read -r l; do
        echo "    $l"
      done
      ;;
    portugal)
      echo "  Available parcelas years:"
      echo "$layers" | grep -i 'parcelas.AML' | while read -r l; do
        echo "    $l"
      done
      ;;
    *)
      echo "  All layers:"
      echo "$layers" | head -20 | while read -r l; do
        echo "    $l"
      done
      ;;
  esac
  echo ""
}

# Parse datasets.txt and run discovery for each WMS
while IFS='|' read -r id type label url pattern years notes; do
  # Skip comments and blanks
  [[ "$id" =~ ^[[:space:]]*# ]] && continue
  [[ -z "$id" ]] && continue
  # Only process WMS entries
  [ "$type" != "wms" ] && continue

  discover_wms_years "$id" "$label" "$url" "$pattern"
done < "$DATASETS"

echo "=== Discovery complete ==="
