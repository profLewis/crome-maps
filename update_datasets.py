#!/Users/plewis/anaconda3/bin/python3
"""
Dataset Update Checker for crome-maps.

Checks existing datasets for updates (new years, new versions, changed endpoints)
and discovers potential new datasets from known registries.

Usage:
    python3 update_datasets.py              # Check all datasets
    python3 update_datasets.py --discover   # Also discover new datasets
    python3 update_datasets.py --apply      # Apply discovered updates to datasets.yaml
    python3 update_datasets.py --cron       # Non-interactive mode for cron jobs

Output:
    - Console summary of findings
    - updates/YYYY-MM-DD.md changelog file for any discovered changes
    - If --apply: modifies docs/datasets.yaml with updated temporal ranges

Requires: requests, pyyaml, lxml (optional, for WMS parsing)
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import traceback
from urllib.parse import urlencode

# Ensure anaconda site-packages is on the path (needed for launchd which strips env)
_conda_sp = os.path.expanduser('~/anaconda3/lib/python3.11/site-packages')
if os.path.isdir(_conda_sp) and _conda_sp not in sys.path:
    sys.path.insert(0, _conda_sp)

import requests
import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_YAML = os.path.join(SCRIPT_DIR, 'docs', 'datasets.yaml')
UPDATES_DIR = os.path.join(SCRIPT_DIR, 'updates')

# Timeout for HTTP requests
TIMEOUT = 30

# ─────────────────────────────────────────────────────────────────
# Checker registry: each checker returns a list of Finding objects
# ─────────────────────────────────────────────────────────────────

class Finding:
    """A discovered update or change."""
    def __init__(self, dataset_id, category, summary, details=None, severity='info'):
        self.dataset_id = dataset_id
        self.category = category  # 'new_year', 'new_version', 'endpoint_change', 'new_dataset'
        self.summary = summary
        self.details = details or ''
        self.severity = severity  # 'info', 'update', 'warning'
        self.timestamp = datetime.datetime.now().isoformat()

    def to_markdown(self):
        icon = {'info': 'ℹ️', 'update': '🆕', 'warning': '⚠️'}.get(self.severity, '')
        line = f"- {icon} **{self.dataset_id}** [{self.category}]: {self.summary}"
        if self.details:
            line += f"\n  - {self.details}"
        return line


def load_datasets():
    """Load current datasets.yaml."""
    with open(DATASETS_YAML) as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────────
# WMS-based checks: probe GetCapabilities for new years/layers
# ─────────────────────────────────────────────────────────────────

WMS_ENDPOINTS = {
    'hrl-crop-types': {
        'url': 'https://geoserver.vlcc.geoville.com/geoserver/ows',
        'layer_pattern': r'CTY_S(\d{4})',
        'known_years': list(range(2017, 2024)),
    },
    'usda-cdl': {
        'url': 'https://nassgeodata.gmu.edu/CropScape/devService',
        'layer_pattern': r'(?:cdl|CDL)[_ ]?(\d{4})',
        'known_years': list(range(2008, 2025)),
    },
    'corine': {
        'url': 'https://image.discomap.eea.europa.eu/arcgis/services/Corine/CLC2018_WM/MapServer/WmsServer',
        'layer_pattern': r'CLC(\d{4})',
        'known_years': [2018],  # This specific WMS only serves CLC2018
    },
    'hrvpp-phenology': {
        'url': 'https://phenology.vgt.vito.be/wms',
        'layer_pattern': r'CLMS_HRVPP_VPP_SOSD_SEASON1_10M',
        'known_years': list(range(2017, 2025)),
    },
    'worldcereal': {
        'url': 'https://ewoc-rdm-api.iiasa.ac.at/geoserver/ows',
        'layer_pattern': r'worldcereal.*?(\d{4})',
        'known_years': [2021],
    },
    'esa-worldcover': {
        'url': 'https://services.terrascope.be/wms/v2',
        'layer_pattern': r'WORLDCOVER_(\d{4})_MAP',
        'known_years': [2020, 2021],
    },
}


def check_wms_capabilities(endpoint_id, config):
    """Check WMS GetCapabilities for new layers/years."""
    findings = []
    url = config['url']
    params = {
        'service': 'WMS',
        'request': 'GetCapabilities',
        'version': '1.1.1',
    }
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        if resp.status_code != 200:
            findings.append(Finding(endpoint_id, 'endpoint_change',
                f'WMS returned status {resp.status_code}', severity='warning'))
            return findings

        text = resp.text
        # Extract years from layer names matching pattern
        years_found = set()
        for match in re.finditer(config['layer_pattern'], text):
            groups = match.groups()
            if groups:
                try:
                    years_found.add(int(groups[0]))
                except ValueError:
                    pass

        if years_found:
            known = set(config['known_years'])
            new_years = years_found - known
            if new_years:
                findings.append(Finding(endpoint_id, 'new_year',
                    f"New year(s) available: {sorted(new_years)}",
                    f"Known: {sorted(known)}, Found: {sorted(years_found)}",
                    severity='update'))
            missing = known - years_found
            if missing:
                findings.append(Finding(endpoint_id, 'endpoint_change',
                    f"Previously known years no longer in capabilities: {sorted(missing)}",
                    severity='warning'))

    except requests.RequestException as e:
        findings.append(Finding(endpoint_id, 'endpoint_change',
            f'WMS endpoint unreachable: {e}', severity='warning'))

    return findings


# ─────────────────────────────────────────────────────────────────
# HTTP-based checks: probe download endpoints for new files
# ─────────────────────────────────────────────────────────────────

HTTP_ENDPOINTS = {
    'crome': {
        'url_template': 'https://environment.data.gov.uk/dataset/a27312b5-d6c9-4710-ad5e-382d727c1b05',
        'check_type': 'page_content',
        'pattern': r'CROME[_ ]?(\d{4})',
        'known_years': list(range(2016, 2025)),
    },
    'eurocrops': {
        'url': 'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/DRLL/EuroCropsV2/gpqt/',
        'check_type': 'ftp_listing',
        'pattern': r'(\w{2})_(\d{4})\.parquet',
        'known_countries': ['at', 'bg', 'cz', 'dk', 'e2', 'e3', 'e4', 'ea',
                           'ee', 'es', 'fi', 'fr', 'i1', 'ie', 'nl', 'pt', 'si', 'sk'],
    },
    'cropgrids': {
        'url': 'https://zenodo.org/api/records/7814458',
        'check_type': 'zenodo_api',
    },
    'crop-calendars': {
        'url': 'https://sage.nelson.wisc.edu/data-and-models/datasets/crop-calendar-dataset/',
        'check_type': 'page_exists',
    },
    'ftw': {
        'url': 'https://beta.source.coop/repositories/kerner-lab/fields-of-the-world/',
        'check_type': 'page_exists',
    },
}


def check_http_endpoint(endpoint_id, config):
    """Check HTTP endpoints for updates."""
    findings = []
    check_type = config.get('check_type', 'page_exists')

    try:
        if check_type == 'zenodo_api':
            resp = requests.get(config['url'], timeout=TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                # Check for newer versions
                doi = data.get('doi', '')
                modified = data.get('updated', '')
                version = data.get('metadata', {}).get('version', '')
                findings.append(Finding(endpoint_id, 'info',
                    f"Current Zenodo version: {version}, last updated: {modified[:10] if modified else 'unknown'}"))

                # Check if there are newer records in the same concept
                conceptdoi = data.get('conceptdoi', '')
                if conceptdoi:
                    concept_url = f"https://zenodo.org/api/records?q=conceptdoi:\"{conceptdoi}\"&sort=mostrecent"
                    resp2 = requests.get(concept_url, timeout=TIMEOUT)
                    if resp2.status_code == 200:
                        hits = resp2.json().get('hits', {}).get('hits', [])
                        if len(hits) > 1:
                            latest = hits[0]
                            latest_id = latest.get('id')
                            current_id = data.get('id')
                            if latest_id and current_id and latest_id != current_id:
                                findings.append(Finding(endpoint_id, 'new_version',
                                    f"Newer Zenodo record found: {latest_id} (current: {current_id})",
                                    severity='update'))

        elif check_type == 'ftp_listing':
            resp = requests.get(config['url'], timeout=TIMEOUT)
            if resp.status_code == 200:
                matches = re.findall(config['pattern'], resp.text)
                if matches:
                    found_countries = set()
                    found_years = set()
                    for m in matches:
                        if isinstance(m, tuple):
                            found_countries.add(m[0])
                            found_years.add(int(m[1]))
                        else:
                            found_years.add(int(m))

                    if found_countries and 'known_countries' in config:
                        known = set(config['known_countries'])
                        new_countries = found_countries - known
                        if new_countries:
                            findings.append(Finding(endpoint_id, 'new_year',
                                f"New countries found: {sorted(new_countries)}",
                                severity='update'))

                    if found_years:
                        max_year = max(found_years)
                        findings.append(Finding(endpoint_id, 'info',
                            f"Years available: {min(found_years)}-{max_year} ({len(found_years)} years, {len(found_countries)} countries)"))

        elif check_type == 'page_content':
            url = config.get('url') or config.get('url_template')
            resp = requests.get(url, timeout=TIMEOUT)
            if resp.status_code == 200:
                years_found = set()
                for m in re.finditer(config['pattern'], resp.text):
                    try:
                        years_found.add(int(m.group(1)))
                    except (ValueError, IndexError):
                        pass
                if years_found and 'known_years' in config:
                    known = set(config['known_years'])
                    new_years = years_found - known
                    if new_years:
                        findings.append(Finding(endpoint_id, 'new_year',
                            f"New year(s) on data page: {sorted(new_years)}",
                            severity='update'))

        elif check_type == 'page_exists':
            url = config.get('url')
            resp = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code >= 400:
                findings.append(Finding(endpoint_id, 'endpoint_change',
                    f"Endpoint returned {resp.status_code}", severity='warning'))

    except requests.RequestException as e:
        findings.append(Finding(endpoint_id, 'endpoint_change',
            f'Endpoint unreachable: {e}', severity='warning'))

    return findings


# ─────────────────────────────────────────────────────────────────
# National LPIS WFS checks
# ─────────────────────────────────────────────────────────────────

NATIONAL_WFS = {
    'netherlands-brp': {
        'url': 'https://service.pdok.nl/rvo/brpgewaspercelen/wfs/v1_0',
        'params': {'service': 'WFS', 'request': 'GetCapabilities'},
        'pattern': r'BrpGewas(\d{4})',
        'known_years': list(range(2009, 2025)),
    },
}


def check_national_wfs(endpoint_id, config):
    """Check national WFS endpoints for new years."""
    findings = []
    try:
        resp = requests.get(config['url'], params=config['params'], timeout=TIMEOUT)
        if resp.status_code == 200:
            years_found = set()
            for m in re.finditer(config['pattern'], resp.text):
                try:
                    years_found.add(int(m.group(1)))
                except (ValueError, IndexError):
                    pass
            if years_found:
                known = set(config['known_years'])
                new_years = years_found - known
                if new_years:
                    findings.append(Finding(endpoint_id, 'new_year',
                        f"New year(s) in WFS: {sorted(new_years)}",
                        severity='update'))
    except requests.RequestException as e:
        findings.append(Finding(endpoint_id, 'endpoint_change',
            f'WFS unreachable: {e}', severity='warning'))
    return findings


# ─────────────────────────────────────────────────────────────────
# Dataset Discovery: search known registries for new datasets
# ─────────────────────────────────────────────────────────────────

DISCOVERY_SOURCES = [
    {
        'name': 'Zenodo',
        'url': 'https://zenodo.org/api/records',
        'params': {
            'q': 'crop type map OR cropland OR "land cover" OR "agricultural parcels"',
            'type': 'dataset',
            'sort': 'mostrecent',
            'size': 20,
        },
        'result_key': 'hits.hits',
    },
    {
        'name': 'JRC Data Catalogue',
        'url': 'https://data.jrc.ec.europa.eu/api/3/action/package_search',
        'params': {
            'q': 'crop OR agriculture OR land cover',
            'sort': 'metadata_modified desc',
            'rows': 20,
        },
        'result_key': 'result.results',
    },
]

# Known dataset titles/IDs to skip (already in our system)
KNOWN_DATASETS = {
    'cropgrids', 'eurocrops', 'lucas', 'worldcereal', 'worldcover',
    'ftw', 'fields of the world', 'mapbiomas', 'corine',
    'crop calendar', 'modis', 'gfsad', 'ggcp',
}


def discover_new_datasets():
    """Search registries for potentially new datasets."""
    findings = []

    for source in DISCOVERY_SOURCES:
        try:
            resp = requests.get(source['url'], params=source['params'], timeout=TIMEOUT)
            if resp.status_code != 200:
                continue

            data = resp.json()

            # Navigate to results
            results = data
            for key in source['result_key'].split('.'):
                if isinstance(results, dict):
                    results = results.get(key, [])
                elif isinstance(results, list) and key.isdigit():
                    results = results[int(key)]

            if not isinstance(results, list):
                continue

            for item in results[:15]:
                title = ''
                url = ''

                if source['name'] == 'Zenodo':
                    title = item.get('metadata', {}).get('title', item.get('title', ''))
                    url = item.get('links', {}).get('html', '')
                elif source['name'] == 'JRC Data Catalogue':
                    title = item.get('title', '')
                    url = f"https://data.jrc.ec.europa.eu/dataset/{item.get('name', '')}"

                if not title:
                    continue

                # Skip known datasets
                title_lower = title.lower()
                if any(known in title_lower for known in KNOWN_DATASETS):
                    continue

                # Only keep if relevant keywords present
                relevant_keywords = ['crop', 'agriculture', 'farmland', 'cropland',
                                   'land cover', 'land use', 'field boundar', 'parcel',
                                   'vegetation', 'phenology']
                if any(kw in title_lower for kw in relevant_keywords):
                    findings.append(Finding('discovery', 'new_dataset',
                        f"[{source['name']}] {title}",
                        f"URL: {url}",
                        severity='info'))

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            findings.append(Finding('discovery', 'endpoint_change',
                f"{source['name']} search failed: {e}", severity='warning'))

    return findings


# ─────────────────────────────────────────────────────────────────
# Changelog generation
# ─────────────────────────────────────────────────────────────────

def write_changelog(findings, output_dir=UPDATES_DIR):
    """Write findings to a dated markdown changelog."""
    if not findings:
        return None

    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    filepath = os.path.join(output_dir, f'{date_str}.md')

    # Group by severity
    updates = [f for f in findings if f.severity == 'update']
    warnings = [f for f in findings if f.severity == 'warning']
    infos = [f for f in findings if f.severity == 'info']

    lines = [f"# Dataset Update Check — {date_str}\n"]

    if updates:
        lines.append("## Updates Found\n")
        for f in updates:
            lines.append(f.to_markdown())
        lines.append("")

    if warnings:
        lines.append("## Warnings\n")
        for f in warnings:
            lines.append(f.to_markdown())
        lines.append("")

    if infos:
        lines.append("## Status\n")
        for f in infos:
            lines.append(f.to_markdown())
        lines.append("")

    lines.append(f"\n---\nGenerated by `update_datasets.py` at {datetime.datetime.now().isoformat()}\n")

    with open(filepath, 'w') as fp:
        fp.write('\n'.join(lines))

    return filepath


# ─────────────────────────────────────────────────────────────────
# Apply updates to datasets.yaml
# ─────────────────────────────────────────────────────────────────

def apply_updates(findings, datasets):
    """Update datasets.yaml temporal ranges based on findings."""
    changes = []
    for f in findings:
        if f.category == 'new_year' and f.severity == 'update':
            # Extract new max year from summary
            year_match = re.findall(r'\d{4}', f.summary)
            if year_match:
                new_max_year = max(int(y) for y in year_match)
                ds_id = f.dataset_id
                if ds_id in datasets:
                    old_temporal = datasets[ds_id].get('temporal', '')
                    # Update temporal field
                    new_temporal = re.sub(r'(\d{4})([\s\-–]+)(\d{4})',
                        lambda m: f"{m.group(1)}{m.group(2)}{new_max_year}",
                        old_temporal)
                    if new_temporal != old_temporal:
                        datasets[ds_id]['temporal'] = new_temporal
                        changes.append(f"Updated {ds_id} temporal: {old_temporal} → {new_temporal}")

    if changes:
        with open(DATASETS_YAML, 'w') as fp:
            yaml.dump(datasets, fp, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"\nApplied {len(changes)} update(s) to datasets.yaml:")
        for c in changes:
            print(f"  - {c}")

    return changes


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Check for dataset updates')
    parser.add_argument('--discover', action='store_true', help='Also discover new datasets')
    parser.add_argument('--apply', action='store_true', help='Apply updates to datasets.yaml')
    parser.add_argument('--cron', action='store_true', help='Non-interactive cron mode')
    parser.add_argument('--quiet', action='store_true', help='Only show updates and warnings')
    args = parser.parse_args()

    datasets = load_datasets()
    all_findings = []

    print("=" * 60)
    print(f"Dataset Update Check — {datetime.date.today()}")
    print("=" * 60)

    # 1. Check WMS endpoints
    print("\n[WMS Endpoints]")
    for eid, config in WMS_ENDPOINTS.items():
        if not args.quiet:
            print(f"  Checking {eid}...", end=' ', flush=True)
        findings = check_wms_capabilities(eid, config)
        all_findings.extend(findings)
        if not args.quiet:
            status = 'OK' if not findings or all(f.severity == 'info' for f in findings) else \
                     'UPDATE' if any(f.severity == 'update' for f in findings) else 'WARN'
            print(status)
        time.sleep(0.5)  # Be polite

    # 2. Check HTTP endpoints
    print("\n[HTTP Endpoints]")
    for eid, config in HTTP_ENDPOINTS.items():
        if not args.quiet:
            print(f"  Checking {eid}...", end=' ', flush=True)
        findings = check_http_endpoint(eid, config)
        all_findings.extend(findings)
        if not args.quiet:
            status = 'OK' if not findings or all(f.severity == 'info' for f in findings) else \
                     'UPDATE' if any(f.severity == 'update' for f in findings) else 'WARN'
            print(status)
        time.sleep(0.5)

    # 3. Check national WFS
    print("\n[National WFS]")
    for eid, config in NATIONAL_WFS.items():
        if not args.quiet:
            print(f"  Checking {eid}...", end=' ', flush=True)
        findings = check_national_wfs(eid, config)
        all_findings.extend(findings)
        if not args.quiet:
            status = 'OK' if not findings or all(f.severity == 'info' for f in findings) else \
                     'UPDATE' if any(f.severity == 'update' for f in findings) else 'WARN'
            print(status)
        time.sleep(0.5)

    # 4. Discover new datasets
    if args.discover:
        print("\n[Dataset Discovery]")
        findings = discover_new_datasets()
        all_findings.extend(findings)
        if not args.quiet:
            print(f"  Found {len(findings)} potential new datasets")

    # Summary
    updates = [f for f in all_findings if f.severity == 'update']
    warnings = [f for f in all_findings if f.severity == 'warning']

    print("\n" + "=" * 60)
    print(f"Summary: {len(updates)} update(s), {len(warnings)} warning(s), {len(all_findings)} total finding(s)")

    if updates:
        print("\nUpdates:")
        for f in updates:
            print(f"  🆕 {f.dataset_id}: {f.summary}")

    if warnings:
        print("\nWarnings:")
        for f in warnings:
            print(f"  ⚠️  {f.dataset_id}: {f.summary}")

    # Write changelog
    changelog_path = write_changelog(all_findings)
    if changelog_path:
        print(f"\nChangelog written to: {changelog_path}")

    # Apply updates if requested
    if args.apply and updates:
        apply_updates(all_findings, datasets)

    # Exit code for cron: 0 if no updates, 1 if updates found
    if args.cron and updates:
        sys.exit(1)


if __name__ == '__main__':
    main()
