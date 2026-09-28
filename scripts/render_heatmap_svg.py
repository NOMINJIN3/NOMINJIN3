"""
Renders contrib-heatmap.svg from the JSON produced by fetch_contributions.py.

Usage: python render_heatmap_svg.py <data_json> <output_svg>
"""
import json
import sys
from datetime import date

# GitHub dark-theme palette: level 0 (no contributions) .. level 4
LEVEL_COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CELL, STEP, LEFT, TOP, H = 13, 16, 34, 24, 158
WAVE_SECONDS = 2.0  # total length of the left-to-right pop-in wave

STYLE = """<style>
  text.lbl { fill:#7d8590; font-size:13px; font-weight:600; }
  text.total { fill:#e6edf3; font-size:15px; font-weight:700; }
  .c { transform-box:fill-box; transform-origin:center; opacity:0; animation:pop 0.55s ease-out both; }
  .g { animation:pop 0.55s ease-out both, flash 0.7s ease-out both; }
  @keyframes pop { 0%{opacity:0;transform:scale(.2)} 60%{opacity:1;transform:scale(1.1)} 100%{opacity:1;transform:scale(1)} }
  @keyframes flash { 0%{filter:brightness(2.4)} 45%{filter:brightness(2.4)} 100%{filter:brightness(1)} }
  @media (prefers-reduced-motion: reduce) { .c { opacity:1 !important; animation:none !important; } }
</style>"""


def fill_missing_levels(weeks):
    """If levels are absent, approximate GitHub's quartiles from the counts."""
    days = [d for w in weeks for d in w]
    if all("level" in d for d in days):
        return
    counts = sorted(d["count"] for d in days if d["count"] > 0)
    if not counts:
        cuts = [0, 0, 0]
    else:
        cuts = [counts[int(len(counts) * q)] for q in (0.25, 0.5, 0.75)]
    for d in days:
        c = d["count"]
        d["level"] = 0 if c == 0 else 1 + sum(c > cut for cut in cuts)


def build_svg(data):
    weeks = data["weeks"]
    fill_missing_levels(weeks)
    width = LEFT + len(weeks) * STEP + 6
    total_cells = sum(len(w) for w in weeks)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{H}" viewBox="0 0 {width} {H}" '
        f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
        STYLE,
    ]

    # Month labels above the first week that starts in a new month
    last_month, last_x = None, -100
    for i, week in enumerate(weeks):
        m = date.fromisoformat(week[0]["date"]).month
        x = LEFT + i * STEP
        if m != last_month:
            if x - last_x >= 32:
                out.append(f'<text class="lbl" x="{x}" y="16">{MONTHS[m - 1]}</text>')
                last_x = x
            last_month = m

    out.append('<text class="lbl" x="2" y="54">Mon</text>')
    out.append('<text class="lbl" x="2" y="86">Wed</text>')
    out.append('<text class="lbl" x="2" y="118">Fri</text>')

    idx = 0
    for i, week in enumerate(weeks):
        for d in week:
            x, y = LEFT + i * STEP, TOP + d["weekday"] * STEP
            delay = idx / max(total_cells - 1, 1) * WAVE_SECONDS
            idx += 1
            cls = "c g" if d["count"] else "c"
            s = "" if d["count"] == 1 else "s"
            out.append(
                f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{LEVEL_COLORS[d["level"]]}" style="animation-delay:{delay:.3f}s">'
                f'<title>{d["count"]} contribution{s} on {d["date"]}</title></rect>'
            )

    total = int(data["total"])
    out.append(
        f'<text class="total" x="{LEFT}" y="152">{total:,} contribution{"" if total == 1 else "s"} in the last year</text>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python render_heatmap_svg.py <data_json> <output_svg>")
    with open(sys.argv[1]) as f:
        data = json.load(f)
    with open(sys.argv[2], "w") as f:
        f.write(build_svg(data))
    print(f"Wrote {sys.argv[2]}")


if __name__ == "__main__":
    main()
