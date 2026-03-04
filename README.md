# Global Crop Maps

Interactive web viewer for **crop and land cover maps** from around the world, combining live WMS services with pre-processed [PMTiles](https://github.com/protomaps/PMTiles) served directly from GitHub Pages.

**Live map:** [https://proflewis.github.io/crome-maps/](https://proflewis.github.io/crome-maps/)

Built with [MapLibre GL JS](https://maplibre.org/) — a single `index.html` file, no build step required.

See [DATASETS.md](DATASETS.md) for visual previews of each dataset.

## Features

- **35+ datasets** covering Europe, Americas, Oceania, Africa, Asia, and global satellite products
- **Class filtering** — click legend items to toggle individual crop/land cover classes on or off
- **Smart legend** — automatically reorders legend to show classes visible in your current viewport first
- **Multi-year support** — switch between available years for most datasets
- **Feature info** — hover over the map to see crop/land cover names
- **Auto-zoom** — selecting a dataset flies to its coverage area
- **Opacity control** — shared slider for all active overlays
- **PMTiles + WMS fallback** — uses cached PMTiles where available, live WMS otherwise

## Project Status

This is an actively maintained research tool for exploring global crop and land cover data. Key status notes:

- **Viewer**: Stable, single-page application hosted on GitHub Pages
- **WMS layers**: Depend on upstream government/agency servers — availability may vary
- **PMTiles**: Stored in GitHub LFS and served from `media.githubusercontent.com` — reliable but subject to LFS bandwidth limits
- **Data currency**: Most WMS datasets update annually as agencies release new data; PMTiles are regenerated manually using the processing scripts
- **Known limitations**:
  - EU parcel layers (Netherlands, Belgium, etc.) require high zoom (z10–z15) due to server-side rendering limits
  - Latvia WMS shows field block outlines only — no crop-type classification available via WMS
  - Some WMS servers (e.g., JRC) do not support CORS; the viewer uses workarounds for these

## Datasets

### Europe — Classification

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [CROME](https://environment.data.gov.uk/dataset/7fdb6312-801c-41f6-996d-4585d2bb4684) | England | 2017–2020 | Vector PMTiles | [RPA / Defra](https://www.gov.uk/government/organisations/rural-payments-agency) |
| [EuroCrops](https://github.com/maja601/EuroCrops) | EU (16 countries) | 2018–2021 | Vector PMTiles | [EuroCrops / TU Munich](https://github.com/maja601/EuroCrops) |
| [CORINE Land Cover](https://land.copernicus.eu/en/products/corine-land-cover) | Europe | 2000, 2006, 2012, 2018 | WMS | [Copernicus / EEA](https://www.eea.europa.eu/) |
| [JRC EU Crop Map](https://data.jrc.ec.europa.eu/collection/EUCROPMAP) | EU + Ukraine | 2018, 2022 | WMS | [JRC / European Commission](https://joint-research-centre.ec.europa.eu/) |
| [DLR Crop Types](https://geoservice.dlr.de/web/maps/eoc:lulc:de) | Germany | 2017–2024 | WMS | [DLR EOC](https://www.dlr.de/eoc/) |
| [RPG](https://geoservices.ign.fr/rpg) | France | 2007–2024 | WMS (filterable) | [IGN / Geoplateforme](https://www.ign.fr/) |
| [BLW LPIS](https://map.geo.admin.ch/) | Switzerland | current | WMS | [swisstopo / BLW](https://www.blw.admin.ch/) |
| [NIBIO AR5](https://nibio.no/tjenester/nedlasting-av-kartdata/ar5) | Norway | current | WMS | [NIBIO](https://www.nibio.no/) |

### Europe — Parcel Layers

| Dataset | Country | Years | Min Zoom | Source |
|---------|---------|-------|----------|--------|
| [SIGPAC](https://sigpac.mapama.gob.es/fega/visor/) | Spain | current | z12 | [FEGA / MAPA](https://www.fega.gob.es/) |
| [BRP](https://www.pdok.nl/datasets) | Netherlands | 2024 | z14 | [PDOK / RVO](https://www.pdok.nl/) |
| [Flanders LPIS](https://landbouwcijfers.vlaanderen.be/open-geodata) | Belgium (FL) | 2008–2024 | z14 | [Dept. Landbouw & Visserij](https://landbouwcijfers.vlaanderen.be/) |
| [Wallonia SIGEC](https://geoportail.wallonie.be/catalogue/6fe407f3-40a3-4558-a684-bc43e1890dc1.html) | Belgium (WA) | 2019–2023 | z10 | [SPW Wallonie](https://geoportail.wallonie.be/) |
| [INVEKOS](https://www.data.gv.at/katalog/dataset/invekos-schlaege) | Austria | 2015–2025 | z13 | [AMA / BML](https://www.ama.at/) |
| [FVM Marker](https://geodata.fvm.dk/) | Denmark | 2008–2025 | z10 | [FVM Denmark](https://geodata.fvm.dk/) |
| [ASTA LPIS](https://data.public.lu/en/datasets/flik-2025/) | Luxembourg | 2016–2025 | z12 | [ASTA](https://agriculture.public.lu/) |
| [IFAP iSIP](https://www.ifap.pt/isip/ows/isip.data/wms) | Portugal | 2017–2025 | z10 | [IFAP](https://www.ifap.pt/) |
| [GERK](https://rkg.gov.si/GERK/) | Slovenia | 2024 | z15 | [MKGP](https://www.gov.si/drzavni-organi/ministrstva/ministrstvo-za-kmetijstvo-gozdarstvo-in-prehrano/) |
| [ARKOD](https://www.apprrr.hr/arkod/) | Croatia | 2024 | z14 | [APPRRR](https://www.apprrr.hr/) |
| [GSAA](https://kls.pria.ee/kaart/) | Estonia | 2024 | z12 | [PRIA](https://www.pria.ee/) |
| [Field Blocks](https://karte.lad.gov.lv/karte/) | Latvia | 2024 | z14 | [LAD](https://www.lad.gov.lv/) |
| [Jordbruk](https://jordbruksverket.se/) | Sweden | 2024 | z12 | [SJV](https://jordbruksverket.se/) |
| [LPIS](https://www.ruokavirasto.fi/en/) | Finland | 2020–2024 | z12 | [Ruokavirasto](https://www.ruokavirasto.fi/) |

### Americas

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [USDA CDL](https://nassgeodata.gmu.edu/CropScape/) | USA | 2008–2024 | PMTiles + WMS | [USDA NASS](https://www.nass.usda.gov/) |
| [AAFC Crop Inventory](https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9) | Canada | 2009–2024 | WMS | [AAFC](https://agriculture.canada.ca/) |
| [GeoINTA](https://geointa.inta.gob.ar/) | Argentina | 2024 | WMS | [INTA](https://www.argentina.gob.ar/inta) |
| [MapBiomas](https://mapbiomas.org/en/collection-9) | Brazil | 2020–2023 | PMTiles + WMS | [MapBiomas](https://mapbiomas.org/) |

### Oceania

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [ABARES CLUS](https://www.agriculture.gov.au/abares/aclump/catchment-scale-land-use) | Australia | 2023 | WMS | [ABARES](https://www.agriculture.gov.au/abares) |
| [DEA Land Cover](https://knowledge.dea.ga.gov.au/data/product/dea-land-cover/) | Australia | 1988–2020 | WMS | [Digital Earth Australia](https://www.dea.ga.gov.au/) |
| [LCDB](https://lris.scinfo.org.nz/layer/104400-lcdb-v56-land-cover-database-version-56-mainland-new-zealand/) | New Zealand | 2024 | PMTiles | [Manaaki Whenua](https://www.landcareresearch.co.nz/) |

### Africa

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [DE Africa Cropland](https://www.digitalearthafrica.org/products/cropland-extent) | Africa | 2019 | PMTiles | [Digital Earth Africa](https://www.digitalearthafrica.org/) |

### Asia

| Dataset | Country | Years | Type | Source |
|---------|---------|-------|------|--------|
| [CLCD](https://zenodo.org/records/12779975) | China | 2017–2022 | PMTiles | [Wuhan University](https://doi.org/10.5281/zenodo.12779975) |

### Global / Satellite

| Dataset | Coverage | Years | Type | Source |
|---------|----------|-------|------|--------|
| [MODIS MCD12Q1](https://lpdaac.usgs.gov/products/mcd12q1v061/) | Global | 2001–2024 | WMS (GIBS) | [NASA EOSDIS](https://earthdata.nasa.gov/) |
| [GFSAD Croplands](https://lpdaac.usgs.gov/products/gfsad1kcmv001/) | Global | 2000 | WMS (GIBS) | [NASA EOSDIS](https://earthdata.nasa.gov/) |
| [ESA WorldCover](https://esa-worldcover.org/) | Global | 2020, 2021 | WMS | [ESA / Copernicus](https://esa-worldcover.org/) |
| [WorldCereal](https://esa-worldcereal.org/) | Global | 2021 | WMS | [ESA / VITO](https://esa-worldcereal.org/) |

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

## Licence & Copyright

Each dataset retains its original licence from the publishing agency. **This viewer does not redistribute the underlying data** — WMS layers are fetched live from government servers, and PMTiles are derived from openly licensed source data.

### Dataset licences

| Dataset | Licence | Redistribution |
|---------|---------|----------------|
| CROME (England) | [OGL v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | Open — with attribution |
| EuroCrops | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Open — with attribution |
| CORINE Land Cover | [Copernicus Data Policy](https://land.copernicus.eu/en/data-policy) | Open — full, free, and open access |
| JRC EU Crop Map | [JRC Data Policy](https://data.jrc.ec.europa.eu/) | Open — reuse encouraged |
| DLR Crop Types | [DLR EOC Terms](https://geoservice.dlr.de/web/about) | Open for research use |
| France RPG | [Licence Ouverte 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/) | Open — with attribution |
| USDA CDL | Public domain (US Government work) | Unrestricted |
| Canada AAFC | [Open Government Licence - Canada](https://open.canada.ca/en/open-government-licence-canada) | Open — with attribution |
| MapBiomas | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Open — with attribution, share-alike |
| ESA WorldCover | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Open — with attribution |
| MODIS / GFSAD | Public domain (US Government work) | Unrestricted |
| CLCD (China) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Open — with attribution |
| DE Africa Cropland | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Open — with attribution |
| EU Parcel Layers | Varies by country (mostly open government data) | Check individual agency terms |

### Viewer code

The viewer code itself (`index.html` and processing scripts) is open source. Third-party libraries used:

- [MapLibre GL JS](https://maplibre.org/) — BSD-3-Clause
- [PMTiles](https://github.com/protomaps/PMTiles) — BSD-3-Clause
