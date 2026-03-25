#!/usr/bin/env python3
"""Check all data sources for updates, new years, and version changes.

Produces a JSON report and an HTML status page showing:
- Current data availability per source
- Whether new years or versions are available
- Expected update calendar (when new data typically appears)
- Dead/discontinued projects
"""
import json, re, sys, os, time
from datetime import datetime, date
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from xml.etree import ElementTree as ET

TIMEOUT = 30
TODAY = date.today()
YEAR = TODAY.year

def fetch(url, timeout=TIMEOUT):
    """Fetch URL content, return bytes."""
    req = Request(url, headers={'User-Agent': 'CropMapUpdateChecker/1.0'})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.read()
    except (URLError, HTTPError, TimeoutError) as e:
        return None

def fetch_text(url, timeout=TIMEOUT):
    data = fetch(url, timeout)
    return data.decode('utf-8', errors='replace') if data else None

def parse_wms_capabilities(url):
    """Parse WMS GetCapabilities and return available layer names."""
    cap_url = url.split('?')[0] + '?service=WMS&request=GetCapabilities'
    data = fetch_text(cap_url, timeout=60)
    if not data:
        return None
    try:
        # Strip namespace for easier parsing
        data = re.sub(r'\sxmlns[^"]*"[^"]*"', '', data)
        root = ET.fromstring(data)
        layers = []
        for layer in root.iter('Layer'):
            name_el = layer.find('Name')
            if name_el is not None and name_el.text:
                layers.append(name_el.text)
        return layers
    except ET.ParseError:
        return None

def check_gibs_layers():
    """Check NASA GIBS for available layers by testing GetMap requests."""
    base = 'https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi'
    targets = {
        'MODIS_Terra_L3_NDVI_16Day': ('MODIS NDVI 16-day', '2024-07-12'),
        'MODIS_Terra_L3_EVI_16Day': ('MODIS EVI 16-day', '2024-07-12'),
        'MODIS_Combined_L3_IGBP_Land_Cover_Type_Annual': ('MODIS Land Cover', '2023-01-01'),
        'VIIRS_SNPP_NDVI_8Day': ('VIIRS NDVI 8-day', '2025-09-22'),
        'VIIRS_SNPP_EVI_8Day': ('VIIRS EVI 8-day', '2025-09-22'),
        'MODIS_Combined_L4_LAI_8Day': ('MODIS LAI 8-day', '2024-07-12'),
        'MODIS_Combined_L4_FPAR_8Day': ('MODIS FPAR 8-day', '2024-07-12'),
        'MODIS_Terra_L4_Gross_Primary_Productivity_8Day': ('MODIS GPP 8-day', '2024-07-12'),
    }
    results = {}
    for layer_name, (label, time_val) in targets.items():
        url = (base + f'?service=WMS&version=1.1.1&request=GetMap'
               f'&layers={layer_name}&srs=EPSG:3857'
               f'&bbox=0,5000000,2000000,7000000&width=4&height=4'
               f'&format=image/png&time={time_val}')
        data = fetch(url, timeout=15)
        available = data is not None and len(data) > 100 and b'ServiceException' not in data
        results[layer_name] = {'label': label, 'available': available}
    return results

def check_wms_years(base_url, layer_pattern, years_to_check, wms_version='1.1.1'):
    """Check which years have data by testing WMS GetMap requests."""
    available = []
    for yr in years_to_check:
        layer = layer_pattern.replace('{YEAR}', str(yr))
        if wms_version == '1.3.0':
            url = (base_url + '?service=WMS&version=1.3.0&request=GetMap'
                   + '&layers=' + layer + '&crs=EPSG:4326'
                   + '&bbox=48,0,52,5&width=4&height=4&format=image/png')
        else:
            url = (base_url + '?service=WMS&version=1.1.1&request=GetMap'
                   + '&layers=' + layer + '&srs=EPSG:4326'
                   + '&bbox=0,48,5,52&width=4&height=4&format=image/png')
        data = fetch(url, timeout=15)
        if data and len(data) > 200 and not (b'ServiceException' in data or b'error' in data.lower()):
            available.append(yr)
    return available

def check_ftp_directory(url):
    """Check FTP-style HTTP directory listing for files."""
    text = fetch_text(url, timeout=30)
    if not text:
        return None
    # Parse HTML directory listing for filenames
    files = re.findall(r'href="([^"]+)"', text)
    return [f for f in files if not f.startswith('?') and not f.startswith('/')]

def check_jrc_eucropmap():
    """Check JRC EU Crop Map for available years."""
    base = 'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EUCROPMAP/'
    listing = check_ftp_directory(base)
    if not listing:
        return {'status': 'error', 'message': 'Could not access JRC FTP'}
    years = sorted([int(d.strip('/')) for d in listing
                    if d.strip('/').isdigit() and len(d.strip('/')) == 4])
    return {
        'available_years': years,
        'latest_year': max(years) if years else None,
        'source': base,
    }

def check_copernicus_hrl():
    """Check Copernicus HRL Croplands WMS for available years."""
    base = 'https://geoserver.vlcc.geoville.com/geoserver/ows'
    # Try years 2015-2026
    years_to_check = list(range(2015, YEAR + 2))
    available_cty = check_wms_years(base, 'HRL_CPL:CTY_S{YEAR}', years_to_check)
    return {
        'crop_types_years': available_cty,
        'latest_year': max(available_cty) if available_cty else None,
        'source': 'https://land.copernicus.eu/en/products/high-resolution-layer-croplands',
    }

def check_crome():
    """Check DEFRA CROME data availability."""
    years_available = []
    for yr in range(2016, YEAR + 1):
        url = f'https://environment.data.gov.uk/spatialdata/crop-map-of-england-{yr}/wfs?service=WFS&version=2.0.0&request=GetCapabilities'
        data = fetch_text(url, timeout=15)
        if data and 'FeatureType' in data and 'Exception' not in data:
            years_available.append(yr)
    return {
        'available_years': years_available,
        'latest_year': max(years_available) if years_available else None,
        'source': 'https://environment.data.gov.uk/spatialdata/',
    }

def check_germany_dlr():
    """Check DLR Germany crop types WMS."""
    base = 'https://geoservice.dlr.de/eoc/land/wms'
    years_to_check = list(range(2016, YEAR + 2))
    available = check_wms_years(
        base, 'CROPTYPES_DE_P1Y',
        years_to_check
    )
    # DLR uses TIME parameter, so all years use same layer name
    # Check via GetCapabilities instead
    layers = parse_wms_capabilities(base)
    return {
        'layer_present': layers is not None and 'CROPTYPES_DE_P1Y' in (layers or []),
        'wms_available': layers is not None,
        'source': 'https://geoservice.dlr.de/eoc/land/wms',
    }

def check_france_rpg():
    """Check French RPG WMS for available years."""
    base = 'https://data.geopf.fr/wms-r/wms'
    years_to_check = list(range(2007, YEAR + 2))
    available = []
    for yr in years_to_check:
        layer = f'LANDUSE.AGRICULTURE{yr}'
        url = (base + f'?service=WMS&version=1.3.0&request=GetMap'
               f'&layers={layer}&crs=EPSG:4326'
               f'&bbox=46,1,48,3&width=4&height=4&format=image/png')
        data = fetch(url, timeout=15)
        if data and len(data) > 200 and b'ServiceException' not in data:
            available.append(yr)
    return {
        'available_years': available,
        'latest_year': max(available) if available else None,
        'source': 'https://geoservices.ign.fr/rpg',
    }

def check_usda_cdl():
    """Check USDA CDL GIBS for available years."""
    # USDA CDL is served via CropScape
    base = 'https://nassgeodata.gmu.edu/CropScape'
    years = []
    for yr in range(2008, YEAR + 1):
        url = f'https://nassgeodata.gmu.edu/CropScape/devapp/iamherealikecropsquare_wms.cgi?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=crop_cdl_{yr}&SRS=EPSG:4326&BBOX=-90,38,-89,39&WIDTH=4&HEIGHT=4&FORMAT=image/png'
        data = fetch(url, timeout=15)
        if data and len(data) > 200:
            years.append(yr)
    return {
        'available_years': years,
        'latest_year': max(years) if years else None,
        'source': 'https://nassgeodata.gmu.edu/CropScape/',
    }

def check_hrvpp():
    """Check Copernicus HR-VPP phenology WMS."""
    base = 'https://phenology.vgt.vito.be/wms'
    layers = parse_wms_capabilities(base)
    hrvpp_layers = [l for l in (layers or []) if 'HRVPP' in l or 'hrvpp' in l.lower()]
    return {
        'available_layers': hrvpp_layers[:20],  # cap at 20
        'layer_count': len(hrvpp_layers),
        'wms_available': layers is not None,
        'source': 'https://land.copernicus.eu/en/products/vegetation/high-resolution-vegetation-phenology-and-productivity',
    }

def check_eurocrops():
    """Check EuroCrops availability on source.coop."""
    url = 'https://data.source.coop/cholmes/eurocrops/eurocrops-all.pmtiles'
    req = Request(url, method='HEAD', headers={'User-Agent': 'CropMapUpdateChecker/1.0'})
    try:
        with urlopen(req, timeout=15) as r:
            size = int(r.headers.get('Content-Length', 0))
            last_mod = r.headers.get('Last-Modified', '')
            return {
                'available': True,
                'size_mb': round(size / 1048576),
                'last_modified': last_mod,
                'source': 'https://github.com/maja601/EuroCrops',
            }
    except:
        return {'available': False}

def check_esa_worldcover():
    """Check ESA WorldCover WMS."""
    base = 'https://services.terrascope.be/wms/v2'
    layers = parse_wms_capabilities(base)
    wc_layers = [l for l in (layers or []) if 'WORLDCOVER' in l.upper()]
    return {
        'available_layers': wc_layers,
        'wms_available': layers is not None,
        'source': 'https://esa-worldcover.org/',
    }

# === Data source definitions with update expectations ===
SOURCES = [
    {
        'id': 'crome',
        'name': 'England CROME (DEFRA)',
        'check': check_crome,
        'update_frequency': 'Annual',
        'typical_release': 'March–June (data from previous growing season)',
        'status': 'active',
        'sensor': 'Sentinel-2, RapidEye',
        'notes': 'Rural Payments Agency publishes annually for England only.',
    },
    {
        'id': 'jrc-eucropmap',
        'name': 'JRC EU Crop Map',
        'check': check_jrc_eucropmap,
        'update_frequency': 'Annual (irregular)',
        'typical_release': 'Variable — 2022 data released Nov 2023',
        'status': 'active',
        'sensor': 'Sentinel-2',
        'notes': 'Published by JRC. Limited to EU27. Processing can lag 1-2 years.',
    },
    {
        'id': 'hrl-crop-types',
        'name': 'Copernicus HRL Croplands',
        'check': check_copernicus_hrl,
        'update_frequency': 'Annual',
        'typical_release': 'Mid-year (data from previous year)',
        'status': 'active',
        'sensor': 'Sentinel-2',
        'notes': 'GeoVille WMS. Part of Copernicus Land Monitoring Service.',
    },
    {
        'id': 'germany',
        'name': 'Germany Crop Types (DLR)',
        'check': check_germany_dlr,
        'update_frequency': 'Annual',
        'typical_release': 'Spring (data from previous year)',
        'status': 'active',
        'sensor': 'Sentinel-2',
        'notes': 'DLR Earth Observation Center.',
    },
    {
        'id': 'france',
        'name': 'France RPG',
        'check': check_france_rpg,
        'update_frequency': 'Annual',
        'typical_release': 'Typically December–March for previous year',
        'status': 'active',
        'sensor': 'LPIS declarations + satellite',
        'notes': 'Registre Parcellaire Graphique from IGN/ASP.',
    },
    {
        'id': 'gibs-ndvi',
        'name': 'MODIS NDVI/EVI (NASA GIBS)',
        'check': check_gibs_layers,
        'update_frequency': '16-day composites, continuous',
        'typical_release': 'Near real-time (2-3 week latency)',
        'status': 'active',
        'sensor': 'MODIS Terra (2000–present)',
        'notes': 'Terra satellite operational since 2000. MODIS instrument aging but still functional. Data continuity via VIIRS.',
    },
    {
        'id': 'viirs-ndvi',
        'name': 'VIIRS NDVI/EVI (NASA GIBS)',
        'check': lambda: {'note': 'Checked as part of GIBS'},
        'update_frequency': '8-day composites, continuous',
        'typical_release': 'Near real-time',
        'status': 'active',
        'sensor': 'VIIRS SNPP (2012–present), NOAA-20 (2018–present)',
        'notes': 'Successor to MODIS. GIBS WMS layers only available from mid-2025. Long archive via LP DAAC.',
    },
    {
        'id': 'modis-landcover',
        'name': 'MODIS Land Cover (MCD12Q1)',
        'check': lambda: {'note': 'Checked as part of GIBS'},
        'update_frequency': 'Annual',
        'typical_release': 'Typically 1-2 years after observation year',
        'status': 'active',
        'sensor': 'MODIS Terra+Aqua',
        'notes': 'IGBP classification. Latest: 2023. No VIIRS equivalent yet.',
    },
    {
        'id': 'hrvpp',
        'name': 'HR-VPP Phenology (Copernicus)',
        'check': check_hrvpp,
        'update_frequency': 'Annual (VPP) / Dekadal (ST-PPI)',
        'typical_release': 'Seasonal trajectory near real-time; VPP metrics ~6 months after year end',
        'status': 'active',
        'sensor': 'Sentinel-2',
        'notes': 'Copernicus Land Monitoring Service via VITO. 10m resolution Europe only.',
    },
    {
        'id': 'eurocrops',
        'name': 'EuroCrops (V1)',
        'check': check_eurocrops,
        'update_frequency': 'Irregular',
        'typical_release': 'N/A — research dataset',
        'status': 'stable',
        'sensor': 'LPIS declarations',
        'notes': 'Community-compiled LPIS data. V1 on source.coop. V2 available on JRC FTP.',
    },
    {
        'id': 'esa-worldcover',
        'name': 'ESA WorldCover',
        'check': check_esa_worldcover,
        'update_frequency': 'Irregular (2-3 year cycle)',
        'typical_release': 'V100 (2020) released Oct 2021, V200 (2021) released Oct 2022',
        'status': 'active',
        'sensor': 'Sentinel-1 + Sentinel-2',
        'notes': '10m global land cover. Next update expected when new processing version ready.',
    },
    {
        'id': 'usda-cdl',
        'name': 'USDA Cropland Data Layer',
        'check': check_usda_cdl,
        'update_frequency': 'Annual',
        'typical_release': 'January–February for previous year',
        'status': 'active',
        'sensor': 'Landsat, MODIS, ground truth',
        'notes': 'USDA NASS. CONUS coverage. Preliminary release ~Jan, final ~Feb.',
    },
    {
        'id': 'canada',
        'name': 'Canada AAFC Annual Crop Inventory',
        'check': lambda: {'note': 'WMS check not implemented'},
        'update_frequency': 'Annual',
        'typical_release': 'March–April for previous year',
        'status': 'active',
        'sensor': 'RADARSAT-2, Sentinel, Landsat',
        'notes': 'Agriculture and Agri-Food Canada. 30m resolution.',
    },
    {
        'id': 'brazil-mapbiomas',
        'name': 'MapBiomas (Brazil)',
        'check': lambda: {'note': 'WMS check not implemented'},
        'update_frequency': 'Annual collection releases',
        'typical_release': 'August–September',
        'status': 'active',
        'sensor': 'Landsat, Sentinel',
        'notes': 'Annual land cover/land use maps since 1985. Latest: Collection 9.',
    },
    # Dead/discontinued projects
    {
        'id': 'gfsad-croplands',
        'name': 'GFSAD Croplands (Global)',
        'check': lambda: {'note': 'Static dataset'},
        'update_frequency': 'None (archived)',
        'typical_release': 'N/A',
        'status': 'archived',
        'sensor': 'MODIS, Landsat',
        'notes': 'Global Food Security-support Analysis Data. One-time release (2010 epoch). NASA project completed.',
    },
    {
        'id': 'ggcp10',
        'name': 'GGCP10 Crop Production Maps',
        'check': lambda: {'note': 'Static dataset'},
        'update_frequency': 'None (research dataset)',
        'typical_release': 'N/A',
        'status': 'archived',
        'sensor': 'Statistical models + remote sensing',
        'notes': 'Static global crop production maps (2020 epoch). Published via Harvard Dataverse.',
    },
    {
        'id': 'cropgrids',
        'name': 'CROPGRIDS Harvested Area',
        'check': lambda: {'note': 'Static dataset'},
        'update_frequency': 'None (research dataset)',
        'typical_release': 'N/A',
        'status': 'archived',
        'sensor': 'Statistical models',
        'notes': 'Static ~2020 epoch. Published via Figshare.',
    },
    {
        'id': 'crop-calendars',
        'name': 'Crop Calendar (UW-Madison)',
        'check': lambda: {'note': 'Static dataset'},
        'update_frequency': 'None',
        'typical_release': 'N/A',
        'status': 'archived',
        'sensor': 'Ground observations + models',
        'notes': 'Sacks et al. 2010 crop calendar. One-time research publication.',
    },
]

def run_checks():
    """Run all checks and return results."""
    results = {'timestamp': datetime.now().isoformat(), 'sources': []}

    for src in SOURCES:
        print(f"  Checking {src['name']}...", flush=True)
        try:
            check_result = src['check']()
        except Exception as e:
            check_result = {'error': str(e)}

        results['sources'].append({
            'id': src['id'],
            'name': src['name'],
            'update_frequency': src['update_frequency'],
            'typical_release': src['typical_release'],
            'status': src['status'],
            'sensor': src['sensor'],
            'notes': src['notes'],
            'check_result': check_result,
        })

    return results

def generate_html(results):
    """Generate an HTML status page from results."""
    ts = results['timestamp'][:19].replace('T', ' ')

    # Group by status
    active = [s for s in results['sources'] if s['status'] == 'active']
    stable = [s for s in results['sources'] if s['status'] == 'stable']
    archived = [s for s in results['sources'] if s['status'] == 'archived']

    def source_row(s):
        cr = s['check_result']
        detail = ''
        if 'available_years' in cr:
            yrs = cr['available_years']
            detail = f"Years: {min(yrs)}–{max(yrs)} ({len(yrs)} years)" if yrs else "No years found"
            if cr.get('latest_year'):
                if cr['latest_year'] >= YEAR:
                    detail += f' <span style="color:green">&#10003; {YEAR} available</span>'
                elif cr['latest_year'] == YEAR - 1:
                    detail += f' <span style="color:orange">&#9888; Latest: {cr["latest_year"]}</span>'
                else:
                    detail += f' <span style="color:red">&#9888; Latest: {cr["latest_year"]}</span>'
        elif 'available' in cr:
            detail = 'Available' if cr['available'] else 'Not available'
            if cr.get('size_mb'):
                detail += f" ({cr['size_mb']} MB)"
            if cr.get('last_modified'):
                detail += f" — Last modified: {cr['last_modified']}"
        elif 'layer_present' in cr:
            detail = 'WMS layer present' if cr['layer_present'] else 'Layer not found'
        elif 'layer_count' in cr:
            detail = f"{cr['layer_count']} layers available"
        elif 'error' in cr:
            detail = f'<span style="color:red">Error: {cr["error"]}</span>'
        elif 'note' in cr:
            detail = cr['note']
        elif isinstance(cr, dict):
            # GIBS results
            for k, v in cr.items():
                if isinstance(v, dict) and 'available' in v:
                    sym = '&#10003;' if v['available'] else '&#10007;'
                    color = 'green' if v['available'] else 'red'
                    detail += f'<span style="color:{color}">{sym}</span> {v.get("label", k)}  '

        status_color = {'active': '#28a745', 'stable': '#007bff', 'archived': '#6c757d'}
        badge = f'<span style="background:{status_color.get(s["status"],"#999")};color:#fff;padding:1px 6px;border-radius:3px;font-size:11px">{s["status"]}</span>'

        return f"""<tr>
  <td>{badge} <b>{s['name']}</b></td>
  <td>{s['sensor']}</td>
  <td>{s['update_frequency']}</td>
  <td>{s['typical_release']}</td>
  <td>{detail}</td>
  <td style="font-size:11px;color:#666">{s['notes']}</td>
</tr>"""

    rows_active = '\n'.join(source_row(s) for s in active)
    rows_stable = '\n'.join(source_row(s) for s in stable)
    rows_archived = '\n'.join(source_row(s) for s in archived)

    # Build update calendar
    calendar_entries = []
    for s in active + stable:
        if s['typical_release'] and s['typical_release'] != 'N/A':
            calendar_entries.append(f"<li><b>{s['name']}</b>: {s['typical_release']}</li>")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crop Map Data Sources — Update Status</title>
<style>
  body {{ font: 13px/1.6 system-ui, sans-serif; margin: 20px; max-width: 1400px; }}
  h1 {{ font-size: 20px; }}
  h2 {{ font-size: 16px; margin-top: 30px; border-bottom: 2px solid #e0e0e0; padding-bottom: 4px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #f5f5f5; font-size: 12px; }}
  tr:hover {{ background: #f9f9f9; }}
  .timestamp {{ color: #888; font-size: 11px; }}
  .calendar {{ columns: 2; column-gap: 30px; }}
  .calendar li {{ break-inside: avoid; margin-bottom: 4px; }}
</style>
</head>
<body>
<h1>Crop Map Data Sources — Update Status</h1>
<p class="timestamp">Last checked: {ts} | Run <code>python3 check_updates.py</code> to refresh</p>

<h2>Active Data Sources</h2>
<table>
<tr><th>Source</th><th>Sensor</th><th>Update Freq.</th><th>Typical Release</th><th>Current Status</th><th>Notes</th></tr>
{rows_active}
</table>

<h2>Stable / Community Datasets</h2>
<table>
<tr><th>Source</th><th>Sensor</th><th>Update Freq.</th><th>Typical Release</th><th>Current Status</th><th>Notes</th></tr>
{rows_stable}
</table>

<h2>Archived / Discontinued</h2>
<p>These are one-time research datasets or completed projects. No further updates expected.</p>
<table>
<tr><th>Source</th><th>Sensor</th><th>Update Freq.</th><th>Typical Release</th><th>Current Status</th><th>Notes</th></tr>
{rows_archived}
</table>

<h2>Expected Update Calendar</h2>
<p>When new data typically becomes available each year:</p>
<ul class="calendar">
{''.join(calendar_entries)}
</ul>

<h2>Sensor Status</h2>
<table>
<tr><th>Sensor/Platform</th><th>Status</th><th>Implications</th></tr>
<tr><td>MODIS Terra</td><td style="color:orange">Aging (launched 1999)</td><td>Orbit drift affecting data quality. VIIRS is successor. Data still produced but will eventually end.</td></tr>
<tr><td>MODIS Aqua</td><td style="color:orange">Aging (launched 2002)</td><td>Same as Terra. Decommission planning underway.</td></tr>
<tr><td>VIIRS SNPP</td><td style="color:green">Operational (2012–)</td><td>Primary MODIS successor. Long-term data continuity.</td></tr>
<tr><td>VIIRS NOAA-20</td><td style="color:green">Operational (2018–)</td><td>Second VIIRS instrument. Redundancy.</td></tr>
<tr><td>VIIRS NOAA-21</td><td style="color:green">Operational (2023–)</td><td>Latest VIIRS. No GIBS vegetation products yet.</td></tr>
<tr><td>Sentinel-2A/2B</td><td style="color:green">Operational (2015/2017–)</td><td>Primary source for European 10m products. Sentinel-2C launched 2024.</td></tr>
<tr><td>Landsat 8/9</td><td style="color:green">Operational (2013/2021–)</td><td>30m global coverage. Used by USDA CDL, MapBiomas.</td></tr>
<tr><td>RapidEye</td><td style="color:red">Decommissioned (2020)</td><td>Was used by CROME. Replaced by Sentinel-2.</td></tr>
</table>

</body>
</html>"""
    return html

if __name__ == '__main__':
    print(f"Checking {len(SOURCES)} data sources...", flush=True)
    results = run_checks()

    # Save JSON
    out_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(out_dir, 'update_status.json')
    html_path = os.path.join(out_dir, 'update_status.html')

    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"JSON report: {json_path}")

    html = generate_html(results)
    with open(html_path, 'w') as f:
        f.write(html)
    print(f"HTML report: {html_path}")
    print("Done!")
