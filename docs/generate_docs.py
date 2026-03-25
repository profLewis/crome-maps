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
            "WMS": "badge-wms", "PMTiles": "badge-pmtiles",
            "Vector": "badge-vector", "GeoParquet": "badge-vector",
            "GeoPackage": "badge-vector",
        }.get(method, "badge-download")
        detail = f'<a href="{url}" target="_blank">{url}</a>'
        if layer:
            detail += f'<br><code>Layer: {layer}</code>'
        rows.append(
            f'<tr><td><span class="badge {badge_class}">{method}</span></td>'
            f'<td>{detail}</td></tr>'
        )
    return "\n  ".join(rows)


def render_papers(papers_list, css_class="paper-ref"):
    if not papers_list:
        return "<li>No papers cited yet</li>"
    items = []
    for p in papers_list:
        if isinstance(p, dict):
            text = p.get("text", "")
            doi = p.get("doi", "")
            tags = ""
            if p.get("key"):
                tags += ' <span class="tag tag-key">key paper</span>'
            if p.get("open_access"):
                tags += ' <span class="tag tag-oa">open access</span>'
            if doi:
                text += f' <span class="doi"><a href="{doi}" target="_blank">{doi}</a></span>'
            items.append(f'<li class="{css_class}">{text}{tags}</li>')
        elif isinstance(p, str):
            if p.startswith("http"):
                items.append(f'<li class="{css_class}"><a href="{p}" target="_blank">{p}</a></li>')
            else:
                items.append(f'<li class="{css_class}">{p}</li>')
    return "\n  ".join(items)


def render_accuracy(info):
    """Render accuracy section with optional table."""
    parts = []
    text = info.get("accuracy", "").strip()
    if text:
        parts.append(f"<p>{text}</p>")

    # Accuracy table
    acc_table = info.get("accuracy_table")
    if acc_table:
        headers = acc_table.get("headers", ["Class", "Accuracy"])
        rows_data = acc_table.get("rows", [])
        highlight = acc_table.get("highlight_row", -1)
        parts.append('<table class="accuracy-table">')
        parts.append("<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>")
        for i, row in enumerate(rows_data):
            cls = ' class="accuracy-highlight"' if i == highlight else ""
            parts.append(f"<tr{cls}>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
        parts.append("</table>")

    # Validation note
    note = info.get("validation_note", "").strip()
    if note:
        parts.append(f'<div class="validation-note">{note}</div>')

    return "\n".join(parts) if parts else "<p>No accuracy information available.</p>"


def render_citing(citing_list):
    if not citing_list:
        return ""
    html = '<h2>Papers Citing This Dataset</h2>\n<ul class="papers">\n  '
    html += render_papers(citing_list, "paper-cite")
    html += "\n</ul>"
    return html


def render_related(related_list):
    if not related_list:
        return ""
    html = '<h2>Related Datasets</h2>\n<div class="related-grid">\n'
    for item in related_list:
        name = item.get("name", "")
        desc = item.get("desc", "")
        link = item.get("link", "")
        if link:
            html += f'  <a href="{link}" class="related-item" style="text-decoration:none;color:inherit;"><strong>{name}</strong><span>{desc}</span></a>\n'
        else:
            html += f'  <div class="related-item"><strong>{name}</strong><span>{desc}</span></div>\n'
    html += "</div>"
    return html


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
        "{{accuracy_html}}": render_accuracy(info),
        "{{papers_html}}": render_papers(info.get("papers", [])),
        "{{citing_section}}": render_citing(info.get("citing_papers", [])),
        "{{related_section}}": render_related(info.get("related", [])),
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
