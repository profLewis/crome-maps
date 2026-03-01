#!/bin/bash
# download_all.sh — Orchestrate downloading all datasets as PMTiles
# Usage: ./download_all.sh [--vector-only | --raster-only | --geotiff-only | --wms-only] [--dataset ID] [--year YEAR] [--update] [--dry-run]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WFS_CONFIG="$SCRIPT_DIR/wfs_datasets.json"
RASTER_CONFIG="$SCRIPT_DIR/raster_datasets.json"
LOGDIR="$SCRIPT_DIR/../crome-work/logs"
mkdir -p "$LOGDIR"

# Parse arguments
VECTOR_ONLY=false
RASTER_ONLY=false
GEOTIFF_ONLY=false
WMS_ONLY=false
UPDATE_MODE=false
SPECIFIC_DATASET=""
SPECIFIC_YEAR=""
DRY_RUN=false
SKIP_EXISTING=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vector-only) VECTOR_ONLY=true; shift ;;
    --raster-only) RASTER_ONLY=true; shift ;;
    --geotiff-only) GEOTIFF_ONLY=true; RASTER_ONLY=true; shift ;;
    --wms-only) WMS_ONLY=true; RASTER_ONLY=true; shift ;;
    --update) UPDATE_MODE=true; shift ;;
    --dataset) SPECIFIC_DATASET="$2"; shift 2 ;;
    --year) SPECIFIC_YEAR="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --force) SKIP_EXISTING=false; shift ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --vector-only     Only download vector (WFS) datasets"
      echo "  --raster-only     Only download raster (WMS+GeoTIFF) datasets"
      echo "  --geotiff-only    Only download GeoTIFF datasets"
      echo "  --wms-only        Only download WMS raster datasets"
      echo "  --update          Check for updates before downloading"
      echo "  --dataset ID      Only download a specific dataset"
      echo "  --year YEAR       Only download a specific year"
      echo "  --dry-run         Show what would be downloaded without downloading"
      echo "  --force           Re-download even if PMTiles file exists"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOGFILE="$LOGDIR/download_${TIMESTAMP}.log"

log() {
  echo "$@" | tee -a "$LOGFILE"
}

log "=== PMTiles Download Orchestrator ==="
log "Date: $(date -u)"
log "Log: $LOGFILE"
log ""

TOTAL=0
SUCCESS=0
SKIPPED=0
FAILED=0
ERRORS=()

# --- Vector (WFS) datasets ---
if [ "$RASTER_ONLY" != "true" ]; then
  log "--- Vector (WFS) Datasets ---"

  DATASETS=$(jq -r 'keys[]' "$WFS_CONFIG")
  for ds in $DATASETS; do
    if [ -n "$SPECIFIC_DATASET" ] && [ "$ds" != "$SPECIFIC_DATASET" ]; then
      continue
    fi

    LABEL=$(jq -r --arg id "$ds" '.[$id].label' "$WFS_CONFIG")
    YEARS=$(jq -r --arg id "$ds" '.[$id].years[]' "$WFS_CONFIG")

    for yr in $YEARS; do
      if [ -n "$SPECIFIC_YEAR" ] && [ "$yr" != "$SPECIFIC_YEAR" ]; then
        continue
      fi

      # Determine output filename
      if [ "$yr" = "current" ]; then
        OUTFILE="$SCRIPT_DIR/${ds}.pmtiles"
      else
        OUTFILE="$SCRIPT_DIR/${ds}${yr}.pmtiles"
      fi

      TOTAL=$((TOTAL + 1))

      # Skip if exists
      if [ "$SKIP_EXISTING" = "true" ] && [ -f "$OUTFILE" ]; then
        SIZE=$(ls -lh "$OUTFILE" | awk '{print $5}')
        log "  SKIP: $LABEL $yr ($SIZE exists)"
        SKIPPED=$((SKIPPED + 1))
        continue
      fi

      if [ "$DRY_RUN" = "true" ]; then
        log "  WOULD DOWNLOAD: $LABEL $yr → $OUTFILE"
        continue
      fi

      log "  DOWNLOADING: $LABEL $yr..."
      if "$SCRIPT_DIR/download_wfs_dataset.sh" "$ds" "$yr" >> "$LOGFILE" 2>&1; then
        SUCCESS=$((SUCCESS + 1))
        SIZE=$(ls -lh "$OUTFILE" 2>/dev/null | awk '{print $5}')
        log "  OK: $LABEL $yr ($SIZE)"
      else
        FAILED=$((FAILED + 1))
        ERRORS+=("WFS: $LABEL $yr")
        log "  FAILED: $LABEL $yr"
      fi
    done
  done
  log ""
fi

# --- Update check (if --update mode) ---
if [ "$UPDATE_MODE" = "true" ]; then
  log "--- Checking for updates ---"
  UPDATE_LIST=$("$SCRIPT_DIR/check_updates.sh" --quiet 2>/dev/null)
  if [ -z "$UPDATE_LIST" ]; then
    log "  No updates found."
  else
    log "  Updates available:"
    echo "$UPDATE_LIST" | while read -r line; do
      log "    $line"
    done
  fi
  log ""
fi

# --- Raster datasets (WMS + GeoTIFF) ---
if [ "$VECTOR_ONLY" != "true" ]; then
  log "--- Raster Datasets ---"

  DATASETS=$(jq -r 'to_entries[] | select(.key != "_comment") | .key' "$RASTER_CONFIG")
  for ds in $DATASETS; do
    if [ -n "$SPECIFIC_DATASET" ] && [ "$ds" != "$SPECIFIC_DATASET" ]; then
      continue
    fi

    LABEL=$(jq -r --arg id "$ds" '.[$id].label' "$RASTER_CONFIG")
    SOURCE_TYPE=$(jq -r --arg id "$ds" '.[$id].source_type // "wms"' "$RASTER_CONFIG")
    YEARS=$(jq -r --arg id "$ds" '.[$id].years[]' "$RASTER_CONFIG")

    # Filter by source type flags
    if [ "$GEOTIFF_ONLY" = "true" ] && [ "$SOURCE_TYPE" != "geotiff" ]; then
      continue
    fi
    if [ "$WMS_ONLY" = "true" ] && [ "$SOURCE_TYPE" != "wms" ]; then
      continue
    fi

    for yr in $YEARS; do
      if [ -n "$SPECIFIC_YEAR" ] && [ "$yr" != "$SPECIFIC_YEAR" ]; then
        continue
      fi

      # Determine output filename
      if [ "$yr" = "current" ]; then
        OUTFILE="$SCRIPT_DIR/${ds}.pmtiles"
      else
        OUTFILE="$SCRIPT_DIR/${ds}${yr}.pmtiles"
      fi

      TOTAL=$((TOTAL + 1))

      # In update mode, skip datasets that check_updates didn't flag
      if [ "$UPDATE_MODE" = "true" ] && [ -f "$OUTFILE" ]; then
        if ! echo "$UPDATE_LIST" | grep -q "^$ds"; then
          SIZE=$(ls -lh "$OUTFILE" | awk '{print $5}')
          log "  UP TO DATE: $LABEL $yr ($SIZE)"
          SKIPPED=$((SKIPPED + 1))
          continue
        fi
      fi

      # Skip if exists (normal mode)
      if [ "$SKIP_EXISTING" = "true" ] && [ -f "$OUTFILE" ]; then
        SIZE=$(ls -lh "$OUTFILE" | awk '{print $5}')
        log "  SKIP: $LABEL $yr ($SIZE exists)"
        SKIPPED=$((SKIPPED + 1))
        continue
      fi

      if [ "$DRY_RUN" = "true" ]; then
        log "  WOULD DOWNLOAD: $LABEL $yr [$SOURCE_TYPE] → $OUTFILE"
        continue
      fi

      log "  DOWNLOADING: $LABEL $yr [$SOURCE_TYPE]..."
      if [ "$SOURCE_TYPE" = "geotiff" ]; then
        if "$SCRIPT_DIR/download_geotiff.sh" "$ds" "$yr" >> "$LOGFILE" 2>&1; then
          SUCCESS=$((SUCCESS + 1))
          SIZE=$(ls -lh "$OUTFILE" 2>/dev/null | awk '{print $5}')
          log "  OK: $LABEL $yr ($SIZE)"
        else
          FAILED=$((FAILED + 1))
          ERRORS+=("GeoTIFF: $LABEL $yr")
          log "  FAILED: $LABEL $yr"
        fi
      else
        if "$SCRIPT_DIR/download_wms_tiles.sh" "$ds" "$yr" >> "$LOGFILE" 2>&1; then
          SUCCESS=$((SUCCESS + 1))
          SIZE=$(ls -lh "$OUTFILE" 2>/dev/null | awk '{print $5}')
          log "  OK: $LABEL $yr ($SIZE)"
        else
          FAILED=$((FAILED + 1))
          ERRORS+=("WMS: $LABEL $yr")
          log "  FAILED: $LABEL $yr"
        fi
      fi
    done
  done
  log ""
fi

# --- Summary ---
log "=== Download Summary ==="
log "Total: $TOTAL"
log "Success: $SUCCESS"
log "Skipped (existing): $SKIPPED"
log "Failed: $FAILED"

if [ ${#ERRORS[@]} -gt 0 ]; then
  log ""
  log "Failed datasets:"
  for err in "${ERRORS[@]}"; do
    log "  - $err"
  done
fi

log ""
log "Log saved to: $LOGFILE"

# --- Generate manifest ---
log ""
log "Generating PMTiles manifest..."
MANIFEST="$SCRIPT_DIR/pmtiles_manifest.json"
(
  echo "{"
  echo '  "generated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",'
  echo '  "files": {'
  first=true
  for f in "$SCRIPT_DIR"/*.pmtiles; do
    [ -f "$f" ] || continue
    fname=$(basename "$f")
    fsize=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)
    fdate=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%SZ" "$f" 2>/dev/null || date -r "$f" -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown")
    # Extract dataset ID from filename (remove year suffix and .pmtiles)
    ds_id=$(echo "$fname" | sed -E 's/[0-9]{4}\.pmtiles$/.pmtiles/' | sed 's/\.pmtiles$//')
    src_type=$(jq -r --arg id "$ds_id" '.[$id].source_type // "wms"' "$RASTER_CONFIG" 2>/dev/null)
    if [ "$first" = "true" ]; then
      first=false
    else
      echo ","
    fi
    printf '    "%s": {"size": %s, "modified": "%s", "source_type": "%s"}' "$fname" "$fsize" "$fdate" "$src_type"
  done
  echo ""
  echo "  }"
  echo "}"
) > "$MANIFEST"
log "Manifest: $MANIFEST"

# List available PMTiles
log ""
log "Available PMTiles files:"
ls -lhS "$SCRIPT_DIR"/*.pmtiles 2>/dev/null | while read -r line; do
  log "  $line"
done

exit $FAILED
