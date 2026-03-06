#!/usr/bin/env python3
"""Generate per-dataset documentation pages from datasets.yaml.

Usage:
    python3 docs/generate_docs.py

Reads docs/datasets.yaml and docs/template.html, generates one HTML page
per dataset in docs/{dataset-id}.html.
"""
import os
import sys

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "template.html")
DATASETS_PATH = os.path.join(SCRIPT_DIR, "datasets.yaml")


def load_template():
    with open(TEMPLATE_PATH) as f:
        return f.read()


def load_datasets():
    with open(DATASETS_PATH) as f:
        return yaml.safe_load(f)


def render_access_rows(access_list):
    if not access_list:
        return "<tr><td colspan='2'>No direct access available</td></tr>"
    rows = []
    for item in access_list:
        method = item.get("method", "")
        url = item.get("url", "")
        layer = item.get("layer", "")
        badge_class = {
            "WMS": "badge-wms", "PMTiles": "badge-pmtiles"
        }.get(method, "badge-download")
        detail = f'<a href="{url}" target="_blank">{url}</a>'
        if layer:
            detail += f'<br><code>Layer: {layer}</code>'
        rows.append(
            f'<tr><td><span class="badge {badge_class}">{method}</span></td>'
            f'<td>{detail}</td></tr>'
        )
    return "\n  ".join(rows)


def render_papers(papers_list):
    if not papers_list:
        return "<li>No papers cited yet</li>"
    items = []
    for p in papers_list:
        if p.startswith("http"):
            items.append(f'<li><a href="{p}" target="_blank">{p}</a></li>')
        else:
            items.append(f"<li>{p}</li>")
    return "\n  ".join(items)


def generate_page(dataset_id, info, template):
    """Generate a single dataset documentation page."""
    replacements = {
        "{{title}}": info.get("title", dataset_id),
        "{{executive_summary}}": info.get("executive_summary", "").strip(),
        "{{coverage}}": info.get("coverage", "N/A"),
        "{{resolution}}": info.get("resolution", "N/A"),
        "{{temporal}}": info.get("temporal", "N/A"),
        "{{license}}": info.get("license", "N/A"),
        "{{description}}": info.get("description", "").strip(),
        "{{provenance}}": info.get("provenance", "").strip(),
        "{{classification_html}}": f'<p>{info.get("classification", "N/A")}</p>',
        "{{access_rows}}": render_access_rows(info.get("access", [])),
        "{{accuracy_html}}": f'<p>{info.get("accuracy", "N/A").strip()}</p>',
        "{{papers_html}}": render_papers(info.get("papers", [])),
        "{{attribution}}": info.get("attribution", "N/A"),
        "{{provider}}": info.get("provider", "N/A"),
    }

    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    return html


def main():
    template = load_template()
    datasets = load_datasets()

    print(f"Generating documentation pages for {len(datasets)} datasets...\n")

    for dataset_id, info in datasets.items():
        output_path = os.path.join(SCRIPT_DIR, f"{dataset_id}.html")
        html = generate_page(dataset_id, info, template)

        with open(output_path, "w") as f:
            f.write(html)

        print(f"  {dataset_id}.html — {info.get('title', dataset_id)}")

    print(f"\nDone! {len(datasets)} pages generated in {SCRIPT_DIR}/")


if __name__ == "__main__":
    main()
