# CROME 2020 — Crop Map of England (PMTiles)

Vector tile edition of the **Crop Map of England (CROME) 2020** dataset, converted to [PMTiles](https://github.com/protomaps/PMTiles) for lightweight web map serving directly from GitHub Pages.

**Live map:** https://proflewis.github.io/crome-maps/

## About the dataset

The Crop Map of England (CROME) is a polygon vector dataset produced by the **Rural Payments Agency (RPA)**. The 2020 edition classifies England into approximately **31.4 million hexagonal cells** (~40 m edge length, ~69 m centre-to-centre spacing) covering over 80 land-use categories including cereal crops, leguminous crops, grassland, woodland, water, and non-agricultural land.

The classification was generated using supervised Random Forest classification of **Sentinel-1** (radar) and **Sentinel-2** (optical) satellite imagery acquired between late January and September 2020. Overall accuracy is reported as 70.5 % with a Cohen's Kappa of 0.66.

- **Source:** [Crop Map of England (CROME) 2020](https://environment.data.gov.uk/dataset/7fdb6312-801c-41f6-996d-4585d2bb4684) — Defra Data Services Platform
- **Publisher:** Rural Payments Agency
- **Temporal coverage:** January – September 2020
- **Native CRS:** EPSG:27700 (British National Grid)
- **Specification:** [CROME Product Specification v12 (PDF)](https://environment.data.gov.uk/api/file/download?fileDataSetId=41adeeb3-89f1-4a86-8982-c2d27b5f3e6f&fileName=RPA+CROME_Specification_v12.pdf)

## What this repo contains

| File | Description |
|---|---|
| `crome2020.pmtiles` | Vector tiles (zoom 0–10, ~20 MB) |
| `index.html` | Interactive map viewer (MapLibre GL JS + pmtiles.js) |

### Processing

The source GeoDatabase was converted using [GDAL/OGR](https://gdal.org/) and [Tippecanoe](https://github.com/felt/tippecanoe):

1. Reprojected from EPSG:27700 → EPSG:4326
2. Only the `lucode` (land-use code) attribute is retained
3. Tiled with Tippecanoe using spatial subsampling at coarser zoom levels and geometry simplification to minimise file size

## Using the tiles in your app

The PMTiles file is served via GitHub Pages with HTTP range-request support. Your app fetches only the tiles it needs — not the full file.

```js
import { Protocol } from 'pmtiles';
import maplibregl from 'maplibre-gl';

const protocol = new Protocol();
maplibregl.addProtocol('pmtiles', protocol.tile);

const map = new maplibregl.Map({
  container: 'map',
  style: {
    version: 8,
    sources: {
      crome: {
        type: 'vector',
        url: 'pmtiles://https://proflewis.github.io/crome-maps/crome2020.pmtiles'
      }
    },
    layers: [{
      id: 'crome-fill',
      type: 'fill',
      source: 'crome',
      'source-layer': 'crome2020',
      paint: { 'fill-color': '#4CAF50', 'fill-opacity': 0.7 }
    }]
  }
});
```

The source layer is `crome2020`. Each feature has a single property `lucode` containing the land-use code (e.g. `AC66` = Winter Wheat, `PG01` = Grass). See the [CROME lookup table](https://environment.data.gov.uk/api/file/download?fileDataSetId=41adeeb3-89f1-4a86-8982-c2d27b5f3e6f&fileName=CROME_LUCODE_LOOKUP.XLSX) for the full code list.

## Licence and attribution

The source dataset is **© Rural Payments Agency** and is published under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

> Contains public sector information licensed under the Open Government Licence v3.0.

Under the terms of the OGL v3.0 you are free to copy, publish, distribute, transmit, and adapt this information, and to exploit it commercially and non-commercially, provided you acknowledge the source.

**Required acknowledgement when using this data:**

> Source: Rural Payments Agency — Crop Map of England (CROME) 2020.
> Licensed under the Open Government Licence v3.0.
> https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

The processed PMTiles derivative in this repository is distributed under the same Open Government Licence v3.0 terms.

## Other CROME years

The RPA publishes CROME datasets annually. Other years are available from the [Defra Data Services Platform](https://environment.data.gov.uk/).
