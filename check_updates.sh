#!/bin/bash
# check_updates.sh — Check all datasets for available updates
# Usage: ./check_updates.sh [--dataset ID] [--json] [--quiet]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RASTER_CONFIG="$SCRIPT_DIR/raster_datasets.json"
WFS_CONFIG="$SCRIPT_DIR/wfs_datasets.json"
MANIFEST="$SCRIPT_DIR/pmtiles_manifest.json"

SPECIFIC_DATASET=""
JSON_OUTPUT=false
QUIET=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset) SPECIFIC_DATASET="$2"; shift 2 ;;
    --json) JSON_OUTPUT=true; shift ;;
    --quiet) QUIET=true; shift ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --dataset ID   Check only a specific dataset"
      echo "  --json         Output as JSON"
      echo "  --quiet        Only output dataset IDs with updates (for scripting)"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Check dependencies
for cmd in curl jq; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: Required tool '$cmd' not found" >&2
    exit 1
  fi
done

# Load manifest (if exists)
if [ -f "$MANIFEST" ]; then
  MANIFEST_DATA=$(cat "$MANIFEST")
else
  MANIFEST_DATA='{"files":{}}'
fi

log() {
  [ "$QUIET" = "true" ] || echo "$@"
}

UPDATES_FOUND=0
JSON_RESULTS="[]"

# ---- Check HTTP HEAD (for GeoTIFF sources with direct URLs) ----
check_http_head() {
  local url="$1" ds_id="$2" year="$3"
  local filename
  if [ "$year" = "current" ]; then
    filename="${ds_id}.pmtiles"
  else
    filename="${ds_id}${year}.pmtiles"
  fi

  # Get remote headers
  local headers
  headers=$(curl -sI -L --max-time 15 "$url" 2>/dev/null)
  local remote_size=$(echo "$headers" | grep -i "^content-length:" | tail -1 | awk '{print $2}' | tr -d '\r\n')
  local remote_date=$(echo "$headers" | grep -i "^last-modified:" | tail -1 | sed 's/^[^:]*: //' | tr -d '\r\n')

  # Get local info from manifest
  local local_size
  local_size=$(echo "$MANIFEST_DATA" | jq -r --arg f "$filename" '.files[$f].source_size // 0')
  local local_date
  local_date=$(echo "$MANIFEST_DATA" | jq -r --arg f "$filename" '.files[$f].source_last_modified // ""')

  if [ -z "$remote_size" ] || [ "$remote_size" = "0" ]; then
    echo "CHECK_FAILED"
    return
  fi

  if [ ! -f "$SCRIPT_DIR/$filename" ]; then
    echo "NEW:$remote_size:$remote_date"
    return
  fi

  if [ "$remote_size" != "$local_size" ] || [ "$remote_date" != "$local_date" ]; then
    echo "UPDATE_AVAILABLE:$remote_size:$remote_date"
  else
    echo "UP_TO_DATE"
  fi
}

# ---- Check Zenodo API ----
check_zenodo() {
  local record_id="$1" ds_id="$2"
  local filename="${ds_id}.pmtiles"

  local response
  response=$(curl -s --max-time 15 "https://zenodo.org/api/records/$record_id" 2>/dev/null)
  local latest_date
  latest_date=$(echo "$response" | jq -r '.metadata.publication_date // .updated // ""')
  local latest_version
  latest_version=$(echo "$response" | jq -r '.metadata.version // "unknown"')

  local local_date
  local_date=$(echo "$MANIFEST_DATA" | jq -r --arg f "$filename" '.files[$f].source_last_modified // ""')

  if [ ! -f "$SCRIPT_DIR/$filename" ]; then
    echo "NEW:$latest_version:$latest_date"
    return
  fi

  if [ "$latest_date" != "$local_date" ]; then
    echo "UPDATE_AVAILABLE:$latest_version:$latest_date"
  else
    echo "UP_TO_DATE"
  fi
}

# ---- Check Figshare API ----
check_figshare() {
  local article_id="$1" ds_id="$2"
  local filename="${ds_id}.pmtiles"

  local response
  response=$(curl -s --max-time 15 "https://api.figshare.com/v2/articles/$article_id" 2>/dev/null)
  local latest_version
  latest_version=$(echo "$response" | jq -r '.version // 0')
  local latest_date
  latest_date=$(echo "$response" | jq -r '.modified_date // ""')

  local local_version
  local_version=$(echo "$MANIFEST_DATA" | jq -r --arg f "$filename" '.files[$f].source_version // "0"')

  if [ ! -f "$SCRIPT_DIR/$filename" ]; then
    echo "NEW:v$latest_version:$latest_date"
    return
  fi

  if [ "$latest_version" != "$local_version" ]; then
    echo "UPDATE_AVAILABLE:v$latest_version:$latest_date"
  else
    echo "UP_TO_DATE"
  fi
}

# ---- Check WMS GetCapabilities for new years/layers ----
check_wms_capabilities() {
  local ds_id="$1" wms_url="$2" layer_pattern="$3" wms_version="$4"

  local caps
  caps=$(curl -s --max-time 30 "${wms_url}?service=WMS&version=${wms_version}&request=GetCapabilities" 2>/dev/null)

  # Extract available layer names matching the pattern
  local base_pattern
  base_pattern=$(echo "$layer_pattern" | sed 's/{YEAR}/[0-9]*/g')
  local available_layers
  available_layers=$(echo "$caps" | grep -oE "<Name>[^<]*</Name>" | sed 's/<[^>]*>//g' | grep -E "$base_pattern" | sort -u)

  if [ -z "$available_layers" ]; then
    echo "CHECK_FAILED"
    return
  fi

  # Check which years we have PMTiles for
  local new_layers=""
  for layer in $available_layers; do
    # Extract year from layer name
    local yr
    yr=$(echo "$layer" | grep -oE '[0-9]{4}')
    [ -z "$yr" ] && continue
    local filename="${ds_id}${yr}.pmtiles"
    if [ ! -f "$SCRIPT_DIR/$filename" ]; then
      new_layers="$new_layers $yr"
    fi
  done

  if [ -n "$new_layers" ]; then
    echo "NEW_YEARS:$new_layers"
  else
    echo "UP_TO_DATE"
  fi
}

# ---- Process all raster datasets ----
log "=== Dataset Update Check ==="
log "Date: $(date -u)"
log ""

if [ -f "$RASTER_CONFIG" ]; then
  DATASETS=$(jq -r 'to_entries[] | select(.key != "_comment") | .key' "$RASTER_CONFIG")
  for ds in $DATASETS; do
    if [ -n "$SPECIFIC_DATASET" ] && [ "$ds" != "$SPECIFIC_DATASET" ]; then
      continue
    fi

    LABEL=$(jq -r --arg id "$ds" '.[$id].label' "$RASTER_CONFIG")
    SOURCE_TYPE=$(jq -r --arg id "$ds" '.[$id].source_type // "wms"' "$RASTER_CONFIG")
    CHECK_METHOD=$(jq -r --arg id "$ds" '.[$id].version_check.method // "none"' "$RASTER_CONFIG")
    YEARS=$(jq -r --arg id "$ds" '.[$id].years[]' "$RASTER_CONFIG" 2>/dev/null)

    case "$CHECK_METHOD" in
      http_head)
        for yr in $YEARS; do
          CHECK_URL=$(jq -r --arg id "$ds" '.[$id].version_check.check_url // .[$id].source_url' "$RASTER_CONFIG" | sed "s/{YEAR}/$yr/g")
          RESULT=$(check_http_head "$CHECK_URL" "$ds" "$yr")
          case "$RESULT" in
            UP_TO_DATE) log "  UP TO DATE: $LABEL $yr" ;;
            NEW:*) log "  NEW: $LABEL $yr ($(echo "$RESULT" | cut -d: -f3))"; UPDATES_FOUND=$((UPDATES_FOUND+1)); [ "$QUIET" = "true" ] && echo "$ds $yr" ;;
            UPDATE_AVAILABLE:*) log "  UPDATE: $LABEL $yr ($(echo "$RESULT" | cut -d: -f3))"; UPDATES_FOUND=$((UPDATES_FOUND+1)); [ "$QUIET" = "true" ] && echo "$ds $yr" ;;
            CHECK_FAILED) log "  FAILED: $LABEL $yr (could not check)" ;;
          esac
        done
        ;;
      zenodo_api)
        RECORD_ID=$(jq -r --arg id "$ds" '.[$id].version_check.record_id' "$RASTER_CONFIG")
        RESULT=$(check_zenodo "$RECORD_ID" "$ds")
        case "$RESULT" in
          UP_TO_DATE) log "  UP TO DATE: $LABEL" ;;
          NEW:*) log "  NEW: $LABEL ($(echo "$RESULT" | cut -d: -f2-))"; UPDATES_FOUND=$((UPDATES_FOUND+1)); [ "$QUIET" = "true" ] && echo "$ds" ;;
          UPDATE_AVAILABLE:*) log "  UPDATE: $LABEL ($(echo "$RESULT" | cut -d: -f2-))"; UPDATES_FOUND=$((UPDATES_FOUND+1)); [ "$QUIET" = "true" ] && echo "$ds" ;;
        esac
        ;;
      figshare_api)
        ARTICLE_ID=$(jq -r --arg id "$ds" '.[$id].version_check.article_id' "$RASTER_CONFIG")
        RESULT=$(check_figshare "$ARTICLE_ID" "$ds")
        case "$RESULT" in
          UP_TO_DATE) log "  UP TO DATE: $LABEL" ;;
          NEW:*) log "  NEW: $LABEL ($(echo "$RESULT" | cut -d: -f2-))"; UPDATES_FOUND=$((UPDATES_FOUND+1)); [ "$QUIET" = "true" ] && echo "$ds" ;;
          UPDATE_AVAILABLE:*) log "  UPDATE: $LABEL ($(echo "$RESULT" | cut -d: -f2-))"; UPDATES_FOUND=$((UPDATES_FOUND+1)); [ "$QUIET" = "true" ] && echo "$ds" ;;
        esac
        ;;
      wms_getcapabilities|none|"")
        if [ "$SOURCE_TYPE" = "wms" ] && [ "$CHECK_METHOD" != "none" ]; then
          WMS_URL=$(jq -r --arg id "$ds" '.[$id].wms_url' "$RASTER_CONFIG")
          LAYER=$(jq -r --arg id "$ds" '.[$id].layer' "$RASTER_CONFIG")
          WMS_VER=$(jq -r --arg id "$ds" '.[$id].wms_version' "$RASTER_CONFIG")
          RESULT=$(check_wms_capabilities "$ds" "$WMS_URL" "$LAYER" "$WMS_VER")
          case "$RESULT" in
            UP_TO_DATE) log "  UP TO DATE: $LABEL" ;;
            NEW_YEARS:*) log "  NEW YEARS: $LABEL ($(echo "$RESULT" | cut -d: -f2))"; UPDATES_FOUND=$((UPDATES_FOUND+1)); [ "$QUIET" = "true" ] && echo "$ds $(echo "$RESULT" | cut -d: -f2)" ;;
            CHECK_FAILED) log "  SKIPPED: $LABEL (capabilities check failed)" ;;
          esac
        else
          # Count existing PMTiles
          local_count=0
          for yr in $YEARS; do
            if [ "$yr" = "current" ]; then
              [ -f "$SCRIPT_DIR/${ds}.pmtiles" ] && local_count=$((local_count+1))
            else
              [ -f "$SCRIPT_DIR/${ds}${yr}.pmtiles" ] && local_count=$((local_count+1))
            fi
          done
          total=$(echo "$YEARS" | wc -w | tr -d ' ')
          log "  $LABEL: $local_count/$total years available (no auto-check)"
        fi
        ;;
    esac
  done
fi

# ---- Process WFS datasets ----
if [ -f "$WFS_CONFIG" ]; then
  log ""
  log "--- Vector (WFS) Datasets ---"
  DATASETS=$(jq -r 'keys[]' "$WFS_CONFIG")
  for ds in $DATASETS; do
    if [ -n "$SPECIFIC_DATASET" ] && [ "$ds" != "$SPECIFIC_DATASET" ]; then
      continue
    fi
    LABEL=$(jq -r --arg id "$ds" '.[$id].label' "$WFS_CONFIG")
    YEARS=$(jq -r --arg id "$ds" '.[$id].years[]' "$WFS_CONFIG" 2>/dev/null)
    local_count=0
    for yr in $YEARS; do
      if [ "$yr" = "current" ]; then
        [ -f "$SCRIPT_DIR/${ds}.pmtiles" ] && local_count=$((local_count+1))
      else
        [ -f "$SCRIPT_DIR/${ds}${yr}.pmtiles" ] && local_count=$((local_count+1))
      fi
    done
    total=$(echo "$YEARS" | wc -w | tr -d ' ')
    log "  $LABEL: $local_count/$total years available"
  done
fi

log ""
log "=== Summary: $UPDATES_FOUND update(s) found ==="
exit $UPDATES_FOUND
