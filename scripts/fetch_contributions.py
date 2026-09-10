"""
Fetches live GitHub contribution data and saves it as JSON for
render_heatmap_svg.py to consume.

Usage: python fetch_contributions.py <github_username> <output_json>
"""
import sys
import re
import json
import urllib.request
import urllib.error


def fetch_html(username):
    url = f"https://github.com/{username}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"Error: Failed to fetch data for user '{username}'")
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"URL: {e.url}")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching contributions: {e}")
        sys.exit(1)


def parse_cells(html_text):
    tds = re.findall(r'<td([^>]*data-date="[\d-]+"[^>]*)>', html_text)
    cells = []
    for t in tds:
        date = re.search(r'data-date="([\d-]+)"', t).group(1)
        level = int(re.search(r'data-level="(\d)"', t).group(1))
        idm = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', t)
        row, col = int(idm.group(1)), int(idm.group(2))
        cells.append({"date": date, "level": level, "row": row, "col": col})
    return cells


def parse_months(html_text):
    thead = re.search(r"<thead>(.*?)</thead>", html_text, re.S).group(1)
    raw = re.findall(
        r'<td class="ContributionCalendar-label"[^>]*colspan="(\d+)"[^>]*>.*?'
        r'<span aria-hidden="true"[^>]*>(\w+)</span>',
        thead,
        re.S,
    )
    return [{"span": int(span), "name": name} for span, name in raw]


def parse_total(html_text):
    m = re.search(r"<h2[^>]*>\s*([\d,]+)\s*\n?\s*contributions", html_text)
    return m.group(1) if m else "?"


def main():
    if len(sys.argv) != 3:
        print("Usage: python fetch_contributions.py <github_username> <output_json>")
        sys.exit(1)

    username, output_path = sys.argv[1], sys.argv[2]
    html_text = fetch_html(username)

    data = {
        "username": username,
        "total": parse_total(html_text),
        "months": parse_months(html_text),
        "cells": parse_cells(html_text),
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote {output_path} ({data['total']} contributions, {len(data['cells'])} cells)")


if __name__ == "__main__":
    main()
