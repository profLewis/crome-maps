# Setup & Installation Guide

Complete instructions for setting up, running, and maintaining the Global Crop Maps viewer and its supporting tools.

## Quick Start

The viewer itself is a single HTML file — just open `index.html` in a browser. No build step, no server required.

```
open index.html
```

Or visit the live deployment: [https://proflewis.github.io/crome-maps/](https://proflewis.github.io/crome-maps/)

## Prerequisites

### For viewing only
- Any modern web browser (Chrome, Firefox, Safari, Edge)

### For data processing and scripts
- **Python 3.9+** (Anaconda recommended)
- **GDAL 3.x** with Python bindings (`osgeo` module)
- **tippecanoe** (for vector PMTiles generation)
- **mb-util** (for MBTiles processing)
- **pmtiles** CLI (for MBTiles → PMTiles conversion)
- **Git LFS** (for storing/serving large PMTiles files)

### Installing dependencies

#### macOS (with Homebrew + Anaconda)

```bash
# Homebrew tools
brew install gdal tippecanoe pmtiles
pip install mb-util

# Python packages
pip install requests pyyaml geopandas pyarrow Pillow

# Git LFS (if not already installed)
brew install git-lfs
git lfs install
```

#### Ubuntu/Debian

```bash
sudo apt-get install gdal-bin python3-gdal
# tippecanoe
git clone https://github.com/felt/tippecanoe.git && cd tippecanoe && make -j && sudo make install
# pmtiles
curl -L https://github.com/protomaps/go-pmtiles/releases/latest/download/go-pmtiles_Linux_x86_64.tar.gz | tar xz
sudo mv pmtiles /usr/local/bin/
# Python packages
pip install requests pyyaml geopandas pyarrow Pillow mb-util
# Git LFS
sudo apt-get install git-lfs && git lfs install
```

#### Verify installation

```bash
python3 -c "import requests, yaml, geopandas; print('Python OK')"
gdalinfo --version
tippecanoe --version
pmtiles --version
git lfs version
```

## Repository Structure

```
crome-maps/
├── index.html              # Main viewer (single page application)
├── README.md               # Project overview
├── SETUP.md                # This file
├── DATASETS.md             # Visual dataset previews
├── requirements.txt        # Python dependencies
├── raster_datasets.json    # WMS download pipeline config
│
├── docs/                   # Dataset documentation
│   ├── datasets.yaml       # Metadata for all datasets (29 entries)
│   ├── template.html       # HTML template for doc pages
│   ├── generate_docs.py    # Generates HTML from YAML
│   └── *.html              # Generated info pages (29 files)
│
├── updates/                # Automated update check results
│   ├── YYYY-MM-DD.md       # Changelog from each check run
│   ├── launchd.log         # Scheduled job stdout
│   └── launchd-error.log   # Scheduled job stderr
│
├── update_datasets.py      # Automated dataset update checker
├── run_update.sh           # Wrapper for launchd scheduled execution
│
├── eurocropsml/            # EuroCropsML benchmark tools
│   ├── download.py
│   ├── explore.py
│   └── README.md
│
├── download_*.py/sh        # Data download/conversion scripts
│   ├── download_eurocrops_v2.py
│   ├── download_lucas.py
│   ├── download_overlays.py
│   ├── download_phenology.py
│   ├── download_tiles_z10.sh
│   └── download_geotiff.sh
│
├── *.pmtiles               # PMTiles data files (Git LFS)
│   ├── cropgrids-*.pmtiles # CROPGRIDS (15 crops)
│   ├── crop-cal-*.pmtiles  # SAGE crop calendars (20 files)
│   ├── ggcp10-*.pmtiles    # GGCP10 production (4 crops)
│   └── ...
│
└── tile_server.py          # Local tile server (for development)
```

## Data Processing

### Generating PMTiles from source data

Each script downloads source data and converts to PMTiles format:

```bash
# CROPGRIDS (global gridded crop areas, 15 crops)
python3 /tmp/convert_cropgrids3.py

# SAGE Crop Calendars (planting/harvest dates, 10 crops)
python3 /tmp/convert_crop_calendars.py

# GGCP10 (gridded crop production, 4 crops)
python3 /tmp/convert_ggcp10.py

# JRC overlays (LPD, Flood, INCA)
python3 download_overlays.py

# LUCAS 2022 (EU ground truth)
python3 download_lucas.py

# EuroCrops V2 (EU field parcels)
python3 download_eurocrops_v2.py

# USGS eVIIRS phenology
python3 download_phenology.py
```

### Regenerating CROME PMTiles

CROME data is processed in the [crome-work](https://github.com/profLewis/crome-work) repository:

```bash
cd /path/to/crome-work
# For each year (example: 2024)
tippecanoe -o pmtiles_per_year/crome_2024.pmtiles \
  --no-feature-limit --no-tile-size-limit \
  --drop-smallest-as-needed \
  -l crome -z12 \
  geojson_per_year/crome_2024.geojson
```

### Generating documentation pages

```bash
# Regenerate all 29 HTML info pages from datasets.yaml
python3 docs/generate_docs.py
```

To add a new dataset's info page:
1. Add an entry to `docs/datasets.yaml` (follow existing format)
2. Run `python3 docs/generate_docs.py`
3. Add the layer-to-page mapping in `index.html` → `docPages` object

## Automated Update Checking

The `update_datasets.py` script monitors all datasets for updates (new years, changed endpoints, new versions) and discovers new datasets from registries.

### Manual run

```bash
# Check for updates to existing datasets
python3 update_datasets.py

# Also search for new datasets on Zenodo and JRC
python3 update_datasets.py --discover

# Apply discovered temporal updates to datasets.yaml
python3 update_datasets.py --apply

# Non-interactive mode (exit code 1 if updates found)
python3 update_datasets.py --cron
```

### What it checks

| Source | What it checks |
|--------|---------------|
| **HRL Crop Types WMS** | New years in GetCapabilities |
| **USDA CDL WMS** | New years in GetCapabilities |
| **CORINE WMS** | New layers |
| **HR-VPP WMS** | New years |
| **ESA WorldCover WMS** | New years |
| **WorldCereal WMS** | New years/layers |
| **EuroCrops FTP** | New countries/years in GeoParquet listing |
| **CROPGRIDS Zenodo** | New versions via Zenodo API |
| **Netherlands BRP WFS** | New years in WFS capabilities |
| **CROME Defra** | New years on data.gov.uk |
| **Zenodo** | New crop/agriculture/land cover datasets |
| **JRC Data Catalogue** | New JRC datasets |

### Output

Results are written to `updates/YYYY-MM-DD.md` with findings grouped by severity:
- **Updates**: New years or versions available
- **Warnings**: Endpoints down or changed
- **Status**: Information about current state

### Scheduled execution (macOS launchd)

A launchd agent runs the checker every Monday at 06:00. If the computer is asleep or off at that time, launchd runs it at the next opportunity (wake/login).

#### Installing the scheduled job

```bash
# Copy the plist to LaunchAgents
cp com.cromemaps.updater.plist ~/Library/LaunchAgents/

# Load the agent
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.cromemaps.updater.plist

# Verify it's loaded
launchctl list | grep cromemaps
```

The plist file is at: `~/Library/LaunchAgents/com.cromemaps.updater.plist`

#### Checking scheduled job status

```bash
# Is it loaded?
launchctl list | grep cromemaps

# Check most recent run output
cat updates/launchd.log

# Check for errors
cat updates/launchd-error.log

# Check most recent changelog
ls -lt updates/*.md | head -1

# Trigger a manual run now
launchctl kickstart gui/$(id -u)/com.cromemaps.updater
```

#### Uninstalling the scheduled job

```bash
launchctl bootout gui/$(id -u)/com.cromemaps.updater
rm ~/Library/LaunchAgents/com.cromemaps.updater.plist
```

#### Adapting for Linux (cron)

On Linux, use cron instead of launchd. Add to crontab (`crontab -e`):

```cron
# Run every Monday at 06:00; anacron handles missed jobs
0 6 * * 1 cd /path/to/crome-maps && /path/to/python3 update_datasets.py --discover >> updates/cron.log 2>&1
```

For catching up missed jobs on Linux, install `anacron` or use a systemd timer with `Persistent=true`.

## Adding a New Dataset

### WMS layer (no PMTiles needed)

1. Find the WMS endpoint URL
2. Add entry to the `LAYERS` array in `index.html`:
   ```javascript
   { id: 'my-layer', label: 'My Dataset Name',
     tileUrl: yr => wms11('https://example.com/wms', 'layer_name', yr),
     featureInfoUrl: yr => gfi11('https://example.com/wms', 'layer_name', yr),
     attribution: 'Provider Name', years: [2020, 2021, 2022], defaultYear: 2022 }
   ```
3. Add to appropriate section in `sections` array
4. Add to `originalSources` with link to source
5. Add to `docPages` mapping
6. Add entry to `docs/datasets.yaml` and regenerate docs
7. Add WMS endpoint to `update_datasets.py` → `WMS_ENDPOINTS` for monitoring

### PMTiles layer (raster)

1. Download source data (GeoTIFF/NetCDF)
2. Apply color ramp → write colored GeoTIFF
3. Reproject to EPSG:3857: `gdalwarp -t_srs EPSG:3857 input.tif output_3857.tif`
4. Create tiles: `gdal2tiles.py -z 0-6 --xyz output_3857.tif tiles_dir`
5. Pack: `mb-util tiles_dir output.mbtiles --image_format=png --scheme=xyz`
6. Convert: `pmtiles convert output.mbtiles output.pmtiles`
7. Add to Git LFS: `git lfs track "*.pmtiles"` then `git add output.pmtiles`
8. Add layer entry in `index.html`

### PMTiles layer (vector)

1. Get source data (GeoJSON, GeoPackage, Shapefile)
2. Convert to GeoJSON if needed: `ogr2ogr -f GeoJSON output.geojson input.gpkg`
3. Create PMTiles: `tippecanoe -o output.pmtiles --no-feature-limit --no-tile-size-limit -z12 output.geojson`
4. Add to Git LFS and `index.html`

## Local Development

### Running the viewer locally

```bash
# Simple HTTP server (Python)
python3 -m http.server 8000
# Then open http://localhost:8000

# Or use the custom tile server (for debugging)
python3 tile_server.py
```

### Git LFS

PMTiles files are stored in Git LFS. To work with the data:

```bash
# Ensure LFS is set up
git lfs install

# Pull LFS files (may take a while on first clone)
git lfs pull

# Check LFS status
git lfs status
```

## Troubleshooting

### "No datasets showing" / blank map
- Check browser console for JavaScript errors
- Most common cause: a `bounds: undefined` in a vector source crashes MapLibre's style validator
- Verify `index.html` loads correctly: `python3 -m http.server 8000`

### WMS layers not loading
- Some WMS servers don't support CORS — add to `noCorsHosts` array in `index.html`
- Check if the WMS server is up: visit the GetCapabilities URL directly
- Run `python3 update_datasets.py` to check endpoint status

### PMTiles not loading
- Verify the file exists and is valid: `pmtiles show filename.pmtiles`
- Check Git LFS: `git lfs status` — if files show as "pointer", run `git lfs pull`
- For GitHub Pages: files must be under 2GB and served from `media.githubusercontent.com`

### Scheduled job not running
- Check: `launchctl list | grep cromemaps`
- Check logs: `cat updates/launchd-error.log`
- Reload: `launchctl bootout gui/$(id -u)/com.cromemaps.updater && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.cromemaps.updater.plist`

### Python import errors in launchd
- launchd uses a minimal environment — the script includes a `sys.path` fix for anaconda
- If using a different Python distribution, update the path in `update_datasets.py` line 31-34
