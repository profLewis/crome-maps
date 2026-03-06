# Dataset Gallery

Visual previews of the crop and land cover datasets available in the [Global Crop Maps viewer](https://proflewis.github.io/crome-maps/).

Thumbnails are generated live from WMS services — availability depends on the upstream server.

---

## Europe — Classification

### CORINE Land Cover (2018)
**Coverage:** Europe | **Source:** [Copernicus / EEA](https://land.copernicus.eu/en/products/corine-land-cover) | **Type:** WMS

![CORINE Land Cover 2018](https://image.discomap.eea.europa.eu/arcgis/services/Corine/CLC2018_WM/MapServer/WMSServer?service=WMS&version=1.3.0&request=GetMap&layers=12&styles=&crs=EPSG:3857&bbox=-1113195,4163881,4452780,11068716&width=600&height=400&format=image/png&transparent=true)

### JRC EU Crop Map (2022)
**Coverage:** EU + Ukraine | **Source:** [JRC / European Commission](https://data.jrc.ec.europa.eu/collection/EUCROPMAP) | **Type:** WMS

![JRC EU Crop Map 2022](https://jeodpp.jrc.ec.europa.eu/jeodpp/services/ows/wms/landcover/eucropmap?service=WMS&version=1.1.1&request=GetMap&layers=LC.EUCROPMAP.2022&styles=&srs=EPSG:3857&bbox=-1113195,4163881,4452780,11068716&width=600&height=400&format=image/png&transparent=true)

### DLR Crop Types Germany (2024)
**Coverage:** Germany | **Source:** [DLR EOC](https://geoservice.dlr.de/web/maps/eoc:lulc:de) | **Type:** WMS

![DLR Crop Types 2024](https://geoservice.dlr.de/eoc/land/wms?service=WMS&version=1.1.1&request=GetMap&layers=CROPTYPES_DE_P1Y&styles=&srs=EPSG:3857&bbox=667917,5942074,1669792,7361866&width=500&height=500&format=image/png&transparent=true&TIME=2024-01-01T00:00:00Z)

### France RPG (2024)
**Coverage:** France | **Source:** [IGN / Geoplateforme](https://geoservices.ign.fr/rpg) | **Type:** WMS (filterable)

![France RPG 2024](https://data.geopf.fr/wms-r/wms?service=WMS&version=1.3.0&request=GetMap&layers=LANDUSE.AGRICULTURE2024&styles=&crs=EPSG:3857&bbox=-556597,5086374,1057535,6621294&width=500&height=500&format=image/png&transparent=true)

### Switzerland BLW LPIS
**Coverage:** Switzerland | **Source:** [swisstopo / BLW](https://map.geo.admin.ch/) | **Type:** WMS

![Switzerland BLW](https://wms.geo.admin.ch/?service=WMS&version=1.3.0&request=GetMap&layers=ch.blw.landwirtschaftliche-nutzungsflaechen&styles=&crs=EPSG:3857&bbox=656785,5748357,1168855,6073646&width=500&height=300&format=image/png&transparent=true)

### CROME England (2020)
**Coverage:** England | **Source:** [RPA / Defra](https://environment.data.gov.uk/dataset/7fdb6312-801c-41f6-996d-4585d2bb4684) | **Type:** Vector PMTiles

> Served as pre-processed vector PMTiles — no WMS preview available. [View in map](https://proflewis.github.io/crome-maps/)

### EuroCrops
**Coverage:** EU (16 countries) | **Source:** [EuroCrops / TU Munich](https://github.com/maja601/EuroCrops) | **Type:** Vector PMTiles

> Served as pre-processed vector PMTiles — no WMS preview available. [View in map](https://proflewis.github.io/crome-maps/)

---

## Americas

### USDA Cropland Data Layer (2024)
**Coverage:** USA | **Source:** [USDA NASS](https://nassgeodata.gmu.edu/CropScape/) | **Type:** PMTiles + WMS

> PMTiles served from GitHub LFS. [View in map](https://proflewis.github.io/crome-maps/)

### Canada AAFC Crop Inventory (2023)
**Coverage:** Canada | **Source:** [AAFC](https://open.canada.ca/data/en/dataset/ba2645d5-4458-414d-b196-6303ac06c1c9) | **Type:** WMS

![Canada AAFC 2023](https://www.agr.gc.ca/imagery-images/services/annual_crop_inventory/2023/ImageServer/WMSServer?service=WMS&version=1.1.1&request=GetMap&layers=2023%3Aannual_crop_inventory&styles=&srs=EPSG:3857&bbox=-13914936,5621521,-7347086,10018755&width=600&height=400&format=image/png&transparent=true)

### MapBiomas Brazil (2023)
**Coverage:** Brazil | **Source:** [MapBiomas](https://mapbiomas.org/en/collection-9) | **Type:** PMTiles + WMS

> PMTiles served from GitHub LFS. [View in map](https://proflewis.github.io/crome-maps/)

---

## Oceania

### ABARES Catchment Scale Land Use (2023)
**Coverage:** Australia | **Source:** [ABARES / Dept. of Agriculture](https://www.agriculture.gov.au/abares/aclump/catchment-scale-land-use) | **Type:** WMS

![ABARES CLUS](https://di-daa.img.arcgis.com/arcgis/services/Land_and_vegetation/Catchment_Scale_Land_Use_Simplified/ImageServer/WMSServer?service=WMS&version=1.1.1&request=GetMap&layers=Catchment_Scale_Land_Use_Simplified&styles=&srs=EPSG:3857&bbox=12467783,-5465442,17143202,-1118890&width=500&height=400&format=image/png&transparent=true)

### DEA Land Cover (2020)
**Coverage:** Australia | **Source:** [Digital Earth Australia](https://knowledge.dea.ga.gov.au/data/product/dea-land-cover/) | **Type:** WMS

![DEA Land Cover 2020](https://ows.dea.ga.gov.au/?service=WMS&version=1.1.1&request=GetMap&layers=ga_ls_landcover&styles=&srs=EPSG:3857&bbox=12467783,-5465442,17143202,-1118890&width=512&height=427&format=image/png&transparent=true&time=2020-01-01)

### LCDB New Zealand (v5.6)
**Coverage:** New Zealand | **Source:** [Manaaki Whenua](https://lris.scinfo.org.nz/layer/104400-lcdb-v56-land-cover-database-version-56-mainland-new-zealand/) | **Type:** PMTiles

> Served as pre-processed PMTiles from GitHub LFS. [View in map](https://proflewis.github.io/crome-maps/)

---

## Africa

### DE Africa Cropland Extent (2019)
**Coverage:** Africa | **Source:** [Digital Earth Africa](https://www.digitalearthafrica.org/products/cropland-extent) | **Type:** PMTiles

![DE Africa Cropland](https://ows.digitalearth.africa/wms?service=WMS&version=1.3.0&request=GetMap&layers=crop_mask&styles=&crs=EPSG:3857&bbox=-2003751,-4163881,5788614,4579426&width=500&height=500&format=image/png&transparent=true)

---

## Asia

### CLCD China Land Cover (2022)
**Coverage:** China | **Source:** [Wuhan University / Zenodo](https://zenodo.org/records/12779975) | **Type:** PMTiles

> Served as pre-processed PMTiles from GitHub LFS. [View in map](https://proflewis.github.io/crome-maps/)

---

## Global / Satellite

### MODIS Land Cover MCD12Q1 (2023)
**Coverage:** Global | **Source:** [NASA EOSDIS / LPDAAC](https://lpdaac.usgs.gov/products/mcd12q1v061/) | **Type:** WMS (GIBS)

![MODIS Land Cover 2023](https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi?service=WMS&version=1.1.1&request=GetMap&layers=MODIS_Combined_L3_IGBP_Land_Cover_Type_Annual&styles=&srs=EPSG:3857&bbox=-20037508,-8399738,20037508,12932243&width=800&height=400&format=image/png&transparent=true&time=2023-01-01)

### GFSAD Global Croplands (2000)
**Coverage:** Global | **Source:** [NASA EOSDIS / LPDAAC](https://lpdaac.usgs.gov/products/gfsad1kcmv001/) | **Type:** WMS (GIBS)

![GFSAD Croplands](https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi?service=WMS&version=1.1.1&request=GetMap&layers=Agricultural_Lands_Croplands_2000&styles=&srs=EPSG:3857&bbox=-20037508,-8399738,20037508,12932243&width=800&height=400&format=image/png&transparent=true)

### ESA WorldCover (2021)
**Coverage:** Global | **Source:** [ESA / Copernicus](https://esa-worldcover.org/) | **Type:** WMS

![ESA WorldCover 2021](https://services.terrascope.be/wms/v2?service=WMS&version=1.1.1&request=GetMap&layers=WORLDCOVER_2021_MAP&styles=&srs=EPSG:3857&bbox=-20037508,-8399738,20037508,12932243&width=800&height=400&format=image/png&transparent=true)

### WorldCereal Temporary Crops (2021)
**Coverage:** Global | **Source:** [ESA / VITO](https://esa-worldcereal.org/) | **Type:** WMS

![WorldCereal Temporary Crops](https://services.terrascope.be/wms/v2?service=WMS&version=1.1.1&request=GetMap&layers=WORLDCEREAL_TEMPORARYCROPS_V1&styles=&srs=EPSG:3857&bbox=-20037508,-8399738,20037508,12932243&width=800&height=400&format=image/png&transparent=true)

---

## Europe — Parcel Layers

These layers show individual agricultural parcels and require high zoom levels (z10–z15) to render. Thumbnails are not practical at overview scale.

| Dataset | Country | Min Zoom | Source |
|---------|---------|----------|--------|
| [SIGPAC](https://sigpac.mapama.gob.es/fega/visor/) | Spain | z12 | [FEGA / MAPA](https://www.fega.gob.es/) |
| [BRP](https://www.pdok.nl/datasets) | Netherlands | z14 | [PDOK / RVO](https://www.pdok.nl/) |
| [Flanders LPIS](https://landbouwcijfers.vlaanderen.be/open-geodata) | Belgium (FL) | z14 | [Dept. Landbouw & Visserij](https://landbouwcijfers.vlaanderen.be/) |
| [Wallonia SIGEC](https://geoportail.wallonie.be/catalogue/6fe407f3-40a3-4558-a684-bc43e1890dc1.html) | Belgium (WA) | z10 | [SPW Wallonie](https://geoportail.wallonie.be/) |
| [INVEKOS](https://www.data.gv.at/katalog/dataset/invekos-schlaege) | Austria | z13 | [AMA / BML](https://www.ama.at/) |
| [FVM Marker](https://geodata.fvm.dk/) | Denmark | z10 | [FVM Denmark](https://geodata.fvm.dk/) |
| [ASTA LPIS](https://data.public.lu/en/datasets/flik-2025/) | Luxembourg | z12 | [ASTA](https://agriculture.public.lu/) |
| [IFAP iSIP](https://www.ifap.pt/isip/ows/isip.data/wms) | Portugal | z10 | [IFAP](https://www.ifap.pt/) |
| [GERK](https://rkg.gov.si/GERK/) | Slovenia | z15 | [MKGP](https://www.gov.si/drzavni-organi/ministrstva/ministrstvo-za-kmetijstvo-gozdarstvo-in-prehrano/) |
| [ARKOD](https://www.apprrr.hr/arkod/) | Croatia | z14 | [APPRRR](https://www.apprrr.hr/) |
| [GSAA](https://kls.pria.ee/kaart/) | Estonia | z12 | [PRIA](https://www.pria.ee/) |
| [Field Blocks](https://karte.lad.gov.lv/karte/) | Latvia | z14 | [LAD](https://www.lad.gov.lv/) |
| [Jordbruk](https://jordbruksverket.se/) | Sweden | z12 | [SJV](https://jordbruksverket.se/) |
| [LPIS](https://www.ruokavirasto.fi/en/) | Finland | z12 | [Ruokavirasto](https://www.ruokavirasto.fi/) |
| [NIBIO AR5](https://nibio.no/tjenester/nedlasting-av-kartdata/ar5) | Norway | — | [NIBIO](https://www.nibio.no/) |

---

## Europe — Copernicus HRL Croplands

High Resolution Layer products from the Copernicus Land Monitoring Service at 10m resolution.

| Dataset | Coverage | Years | Source |
|---------|----------|-------|--------|
| [HRL Crop Types](https://land.copernicus.eu/en/products/high-resolution-layer-croplands) | EEA-39 | 2017-2023 | [Copernicus CLMS / GeoVille](https://land.copernicus.eu/) |
| [HRL Grassland](https://land.copernicus.eu/en/products/high-resolution-layer-croplands) | EEA-39 | 2017-2023 | [Copernicus CLMS / GeoVille](https://land.copernicus.eu/) |
| [HRL Cropping Seasons](https://land.copernicus.eu/en/products/high-resolution-layer-croplands) | EEA-39 | 2017-2023 | [Copernicus CLMS / GeoVille](https://land.copernicus.eu/) |

### EuroCrops V2
**Coverage:** 18 EU countries | **Source:** [JRC / European Commission](https://data.jrc.ec.europa.eu/dataset/b9fb9e67-78a9-4327-9d59-39a928d812d3) | **Type:** GeoParquet → Vector PMTiles

> Harmonized crop parcel dataset using HCAT v4 taxonomy. V2 expands V1 (16→18 countries, 2008-2023). Available as GeoParquet from JRC FTP. [Download script](download_eurocrops_v2.py)

---

## Overlays — Phenology & Vegetation

Vegetation phenology metrics and indices for monitoring crop growth cycles and seasonal dynamics.

### Copernicus HR-VPP (Europe, 10m)
**Coverage:** Europe (EEA-39) | **Source:** [Copernicus CLMS / VITO](https://land.copernicus.eu/en/products/vegetation/high-resolution-vegetation-phenology-and-productivity) | **Type:** WMS

High Resolution Vegetation Phenology and Productivity from Sentinel-2 at 10m resolution. Seven layers available:

| Layer | Metric | Description |
|-------|--------|-------------|
| Start of Season | SOSD | Date when vegetation starts growing |
| End of Season | EOSD | Date when vegetation becomes dormant |
| Peak Season Date | MAXD | Date of maximum Plant Phenology Index |
| Peak Greenness | MAXV | Maximum PPI value (peak canopy density) |
| Season Length | LENGTH | Duration of growing season (days) |
| Seasonal Productivity | SPROD | Integrated PPI over the growing season |
| Plant Phenology Index | PPI | Dekadal PPI trajectory (mid-July snapshot) |

Years: 2017–2024. WMS endpoint: `https://phenology.vgt.vito.be/wms`

### MODIS NDVI & EVI (Global)
**Coverage:** Global | **Source:** [NASA EOSDIS / GIBS](https://earthdata.nasa.gov/) | **Type:** WMS (GIBS)

MODIS Terra 16-day composite vegetation indices at 250m–1km resolution:
- **NDVI** (Normalized Difference Vegetation Index) — standard greenness measure
- **EVI** (Enhanced Vegetation Index) — improved sensitivity in high-biomass regions

Years: 2000–2025. Mid-July composites shown by default.

---

## Overlays — Environmental

Contextual environmental datasets that complement crop/land-cover analysis.

| Dataset | Coverage | Resolution | Source |
|---------|----------|------------|--------|
| [Land Productivity Dynamics](https://data.jrc.ec.europa.eu/dataset/c6e827f1-501e-4808-bb04-8ee9f0d3ac97) | Global | 1km | [JRC](https://data.jrc.ec.europa.eu/) |
| [River Flood Hazard](https://data.jrc.ec.europa.eu/dataset/1d128b6c-a4ee-4858-9e34-6210707f3c81) | Europe | 90m | [JRC / CEMS](https://data.jrc.ec.europa.eu/) |
| [INCA Crop Provision](https://data.jrc.ec.europa.eu/dataset/ecd792d1-61c3-478c-aa4a-587bad385805) | EU | 1km | [JRC MAES/INCA](https://data.jrc.ec.europa.eu/collection/maes) |
| [INCA Crop Pollination](https://data.jrc.ec.europa.eu/dataset/650331f3-e7ce-427b-8011-bd2c8f40599c) | EU | 1km | [JRC MAES/INCA](https://data.jrc.ec.europa.eu/collection/maes) |

> Overlays require downloading GeoTIFF data and converting to PMTiles. See [download_overlays.py](download_overlays.py).

---

## Validation / Ground Truth

| Dataset | Coverage | Size | Source |
|---------|----------|------|--------|
| [LUCAS 2022](https://data.jrc.ec.europa.eu/dataset/e3fe3cd0-44db-470e-8769-172a8b9e8874) | EU-27 | ~150K polygons | [Eurostat / JRC](https://data.jrc.ec.europa.eu/) |
| [EMBAL](https://data.jrc.ec.europa.eu/dataset/723355a8-e549-4691-9c0d-83ab7fc7a0c4) | EU-27 | 500x500m plots | [JRC](https://data.jrc.ec.europa.eu/) |

> LUCAS download: see [download_lucas.py](download_lucas.py). EMBAL requires data request to JRC.

---

## ML Benchmarks

| Dataset | Coverage | Parcels | Source |
|---------|----------|---------|--------|
| [EuroCropsML](https://zenodo.org/records/15095445) | LV, EE, PT | 706,683 | [Zenodo](https://zenodo.org/) |

> Download and explore: see [eurocropsml/](eurocropsml/README.md).
