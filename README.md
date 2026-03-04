# Global Crop Maps

Interactive web viewer for **crop and land cover maps** from around the world, combining live WMS services with pre-processed [PMTiles](https://github.com/protomaps/PMTiles) served directly from GitHub Pages.

**Live map:** [https://proflewis.github.io/crome-maps/](https://proflewis.github.io/crome-maps/)

Built with [MapLibre GL JS](https://maplibre.org/) — a single `index.html` file, no build step required.

## Features

- **35+ datasets** covering Europe, Americas, Oceania, Africa, Asia, and global satellite products
- **Class filtering** — click legend items to toggle individual crop/land cover classes on or off
- **Smart legend** — automatically reorders legend to show classes visible in your current viewport first
- **Multi-year support** — switch between available years for most datasets
- **Feature info** — hover over the map to see crop/land cover names
- **Auto-zoom** — selecting a dataset flies to its coverage area
- **Opacity control** — shared slider for all active overlays
- **PMTiles + WMS fallback** — uses cached PMTiles where available, live WMS otherwise

## Datasets

### Europe — Classification

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [CROME](https://environment.data.gov.uk/dataset/7fdb6312-801c-41f6-996d-4585d2bb4684) | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England | 2017–2020 | Vector PMTiles | RPA / Defra |
| [EuroCrops](https://github.com/maja601/EuroCrops) | 🇪🇺 EU (16 countries) | 2018–2021 | Vector PMTiles | EuroCrops / TU Munich |
| [CORINE Land Cover](https://land.copernicus.eu/en/products/corine-land-cover) | 🇪🇺 Europe | 2000, 2006, 2012, 2018 | WMS | Copernicus / EEA |
| [JRC EU Crop Map](https://data.jrc.ec.europa.eu/collection/EUCROPMAP) | 🇪🇺 EU + Ukraine | 2018, 2022 | WMS | JRC / European Commission |
| [DLR Land Use](https://geoservice.dlr.de/web/maps/eoc:lulc:de) | 🇩🇪 Germany | 2017–2024 | WMS | DLR EOC |
| [RPG](https://geoservices.ign.fr/rpg) | 🇫🇷 France | 2007–2024 | WMS (filterable) | IGN France |
| [BLW LPIS](https://map.geo.admin.ch/) | 🇨🇭 Switzerland | current | WMS | swisstopo / BLW |
| [NIBIO AR5](https://nibio.no/tjenester/nedlasting-av-kartdata/ar5) | 🇳🇴 Norway | current | WMS | NIBIO |

### Europe — Parcel Layers

| Dataset | Country | Years | Min Zoom | Source |
|---------|---------|-------|----------|--------|
| [SIGPAC](https://sigpac.mapama.gob.es/fega/visor/) | 🇪🇸 Spain | current | z12 | FEGA / MAPA |
| [BRP](https://www.pdok.nl/datasets) | 🇳🇱 Netherlands | 2024 | z14 | PDOK / RVO |
| [Flanders LPIS](https://landbouwcijfers.vlaanderen.be/open-geodata) | 🇧🇪 Belgium (FL) | 2008–2024 | z14 | Dept. Landbouw & Visserij |
| [Wallonia SIGEC](https://geoportail.wallonie.be/catalogue/6fe407f3-40a3-4558-a684-bc43e1890dc1.html) | 🇧🇪 Belgium (WA) | 2019–2023 | z10 | SPW Wallonie |
| [INVEKOS](https://www.data.gv.at/katalog/dataset/invekos-schlaege) | 🇦🇹 Austria | 2015–2025 | z13 | AMA / BML |
| [FVM Marker](https://geodata.fvm.dk/) | 🇩🇰 Denmark | 2008–2025 | z10 | FVM Denmark |
| [ASTA LPIS](https://data.public.lu/en/datasets/flik-2025/) | 🇱🇺 Luxembourg | 2016–2025 | z12 | ASTA |
| [IFAP iSIP](https://www.ifap.pt/isip/ows/isip.data/wms) | 🇵🇹 Portugal | 2017–2025 | z10 | IFAP |
| [GERK](https://rkg.gov.si/GERK/) | 🇸🇮 Slovenia | 2024 | z15 | MKGP |
| [ARKOD](https://www.apprrr.hr/arkod/) | 🇭🇷 Croatia | 2024 | z14 | APPRRR |
| [GSAA](https://kls.pria.ee/kaart/) | 🇪🇪 Estonia | 2024 | z12 | PRIA |
| [Field Blocks](https://karte.lad.gov.lv/karte/) | 🇱🇻 Latvia | 2024 | z14 | LAD |
| [Jordbruk](https://jordbruksverket.se/) | 🇸🇪 Sweden | 2024 | z12 | SJV |
| [LPIS](https://www.ruokavirasto.fi/en/) | 🇫🇮 Finland | 2020–2024 | z12 | Ruokavirasto |

### Americas

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [USDA CDL](https://nassgeodata.gmu.edu/CropScape/) | 🇺🇸 USA | 2008–2024 | PMTiles + WMS | USDA NASS |
| [AAFC Crop Inventory](https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9) | 🇨🇦 Canada | 2009–2024 | WMS | AAFC |
| [GeoINTA](https://geointa.inta.gob.ar/) | 🇦🇷 Argentina | 2024 | WMS | INTA |
| [MapBiomas](https://mapbiomas.org/en/collection-9) | 🇧🇷 Brazil | 2020–2023 | PMTiles + WMS | MapBiomas |

### Oceania

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [ABARES CLUS](https://www.agriculture.gov.au/abares/aclump/catchment-scale-land-use) | 🇦🇺 Australia | 2023 | WMS | ABARES |
| [DEA Land Cover](https://knowledge.dea.ga.gov.au/data/product/dea-land-cover/) | 🇦🇺 Australia | 1988–2020 | WMS | Digital Earth Australia |
| [LCDB](https://lris.scinfo.org.nz/layer/104400-lcdb-v56-land-cover-database-version-56-mainland-new-zealand/) | 🇳🇿 New Zealand | 2024 | PMTiles | Manaaki Whenua |

### Africa

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [DE Africa Cropland](https://www.digitalearthafrica.org/products/cropland-extent) | 🌍 Africa | 2019 | PMTiles | Digital Earth Africa |

### Asia

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [CLCD](https://zenodo.org/records/12779975) | 🇨🇳 China | 2017–2022 | PMTiles | Wuhan University |

### Global / Satellite

| Dataset | Coverage | Years | Type | Source |
|---------|----------|-------|------|--------|
| [MODIS MCD12Q1](https://lpdaac.usgs.gov/products/mcd12q1v061/) | Global | 2001–2024 | WMS (GIBS) | NASA EOSDIS |
| [GFSAD Croplands](https://lpdaac.usgs.gov/products/gfsad1kcmv001/) | Global | 2000 | WMS (GIBS) | NASA EOSDIS |
| [ESA WorldCover](https://esa-worldcover.org/) | Global | 2020, 2021 | WMS (GIBS) | ESA / Copernicus |
| [WorldCereal](https://esa-worldcereal.org/) | Global | 2021 | WMS (GIBS) | ESA / VITO |

## Architecture

The viewer is a single `index.html` file (~3,000 lines) using:

- **MapLibre GL JS v4.7** — WebGL-based map rendering
- **PMTiles.js** — serverless vector/raster tile access via HTTP range requests
- **Custom protocol handlers** — `filtered://` for pixel-level class filtering on PMTiles, `filtered-wms://` for WMS tiles
- **GitHub LFS** — large PMTiles files stored via Git LFS, served from `media.githubusercontent.com`

### Data sources

| Source type | How it works |
|-------------|--------------|
| **Vector PMTiles** | Pre-processed polygon tiles (CROME, EuroCrops) served from GitHub LFS |
| **Raster PMTiles** | Pre-processed classified raster tiles (CDL, Brazil, China, etc.) served from GitHub LFS |
| **WMS** | Live Web Map Service tiles fetched directly from government/agency servers |
| **WMS + PMTiles** | PMTiles preferred, WMS fallback if PMTiles unavailable for a given year |

### Processing pipelines

Two shell scripts convert source data to PMTiles:

- `download_geotiff.sh` — Downloads GeoTIFF, applies color table, reprojects to EPSG:3857, converts via MBTiles to PMTiles
- `download_wms_tiles.sh` — Downloads WMS tiles in parallel, stores as MBTiles, converts to PMTiles

Configuration: `raster_datasets.json`

## CROME (England)

The **Crop Map of England (CROME)** is the primary dataset, with vector PMTiles for 2017–2020:

- **Source:** [Defra Data Services](https://environment.data.gov.uk/dataset/7fdb6312-801c-41f6-996d-4585d2bb4684)
- **Publisher:** Rural Payments Agency
- **Licence:** [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
- **Coverage:** ~31.4 million hexagonal cells, 80+ land-use categories
- **Method:** Random Forest classification of Sentinel-1/2 imagery

CROME 2017–2019 are served from the [crome-work](https://github.com/profLewis/crome-work) repo; 2020 from this repo.

## Licence

Each dataset retains its original licence. See the attribution in the map viewer and the source links above. The viewer code itself is open source.
