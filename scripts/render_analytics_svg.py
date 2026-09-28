"""
Renders github-analytics.svg: total contributions, current / longest streak,
and a smooth line graph of the last 31 days, from data/contributions.json.

Usage: python render_analytics_svg.py <data_json> <output_svg> [display_name] [--graph-only]
"""
import json
import sys
from datetime import date

W, H = 900, 520
BG_TOP, BG_BOTTOM = "#0b1a33", "#050b16"
ACCENT = "#3fb4ff"
TEXT = "#e6f1ff"
MUTED = "#9fb3c8"
DAYS = 31


def fmt(d):
    return f"{d.strftime('%b')} {d.day}"


def streaks(days):
    """days: list of (date, count) sorted ascending. Returns (current, longest) as (len, start, end)."""
    longest = (0, None, None)
    run_len, run_start = 0, None
    for d, c in days:
        if c > 0:
            if run_len == 0:
                run_start = d
            run_len += 1
            if run_len > longest[0]:
                longest = (run_len, run_start, d)
        else:
            run_len = 0

    # Current streak: counting back from today; today with 0 doesn't break it yet
    i = len(days) - 1
    if i >= 0 and days[i][1] == 0:
        i -= 1
    end = days[i][0] if i >= 0 else None
    n = 0
    while i >= 0 and days[i][1] > 0:
        n += 1
        i -= 1
    start = days[i + 1][0] if n else None
    current = (n, start, end if n else None)
    return current, longest


def nice_max(v):
    for m in (10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 400, 500, 1000):
        if v <= m:
            return m
    return ((v // 500) + 1) * 500


def smooth_path(pts):
    """Catmull-Rom spline through pts, as SVG cubic Bezier path."""
    if len(pts) < 2:
        return ""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        # keep control points between the two endpoints so the curve never overshoots
        lo, hi = min(p1[1], p2[1]), max(p1[1], p2[1])
        c1 = (c1[0], min(max(c1[1], lo), hi))
        c2 = (c2[0], min(max(c2[1], lo), hi))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def build_svg(data, name, graph_only=False):
    days = sorted(
        ((date.fromisoformat(d["date"]), d["count"]) for w in data["weeks"] for d in w),
        key=lambda x: x[0],
    )
    total = int(data["total"])
    first, last = days[0][0], days[-1][0]
    current, longest = streaks(days)
    recent = days[-DAYS:]

    def rng(s):
        return f"{fmt(s[1])} - {fmt(s[2])}" if s[0] else "No active streak"

    # ---- chart geometry
    cx0, cx1, cy0, cy1 = 90, W - 40, 250, H - 70
    ymax = nice_max(max(c for _, c in recent) or 1)
    step = (cx1 - cx0) / (len(recent) - 1)
    pts = [(cx0 + i * step, cy1 - c / ymax * (cy1 - cy0)) for i, (_, c) in enumerate(recent)]
    line = smooth_path(pts)
    area = f"{line} L{pts[-1][0]:.1f},{cy1} L{pts[0][0]:.1f},{cy1} Z"

    shift = 200 if graph_only else 0  # graph-only: drop the stats row
    HH = H - shift
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{HH}" viewBox="0 0 {W} {HH}" '
        f'font-family="Ubuntu,-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
        f"""<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG_TOP}"/><stop offset="1" stop-color="{BG_BOTTOM}"/></linearGradient>
  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".45"/><stop offset="1" stop-color="{ACCENT}" stop-opacity=".03"/></linearGradient>
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<style>
  .big {{ fill:{ACCENT}; font-size:34px; font-weight:700; }}
  .lbl {{ fill:{TEXT}; font-size:16px; font-weight:600; }}
  .sub {{ fill:{MUTED}; font-size:13px; }}
  .axis {{ fill:{ACCENT}; font-size:10px; font-weight:700; }}
  .title {{ fill:{ACCENT}; font-size:14px; font-weight:700; }}
  .grid {{ stroke:#2b4d73; stroke-width:1; stroke-dasharray:3 3; }}
  .line {{ stroke-dasharray:3000; stroke-dashoffset:3000; animation:draw 2.2s ease-out .3s forwards; }}
  .fade {{ opacity:0; animation:fade .8s ease-out forwards; }}
  .ring {{ stroke-dasharray:283; stroke-dashoffset:283; animation:ring 1.4s ease-out .2s forwards; }}
  @keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
  @keyframes fade {{ to {{ opacity:1; }} }}
  @keyframes ring {{ to {{ stroke-dashoffset:0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .line,.ring {{ stroke-dashoffset:0; animation:none; }} .fade {{ opacity:1; animation:none; }} }}
</style>""",
    ]
    if not graph_only:  # graph-only: transparent background, blends into the page
        o.append(f'<rect width="{W}" height="{HH}" rx="12" fill="url(#bg)"/>')
    stats = []

    # ---- stats row
    col = [W / 2 - 250, W / 2, W / 2 + 250]
    stats.append(f'<text class="big" x="{col[0]}" y="92" text-anchor="middle">{total:,}</text>')
    stats.append(f'<text class="lbl" x="{col[0]}" y="126" text-anchor="middle">Total Contributions</text>')
    stats.append(f'<text class="sub" x="{col[0]}" y="152" text-anchor="middle">{fmt(first)}, {first.year} - Present</text>')

    stats.append(f'<line x1="{W/2-125}" y1="50" x2="{W/2-125}" y2="170" stroke="{TEXT}" stroke-opacity=".7" stroke-width="2"/>')
    stats.append(f'<line x1="{W/2+125}" y1="50" x2="{W/2+125}" y2="170" stroke="{TEXT}" stroke-opacity=".7" stroke-width="2"/>')

    stats.append(f'<circle cx="{col[1]}" cy="84" r="45" fill="none" stroke="{ACCENT}" stroke-opacity=".2" stroke-width="7"/>')
    stats.append(
        f'<circle class="ring" cx="{col[1]}" cy="84" r="45" fill="none" stroke="{ACCENT}" stroke-width="7" '
        f'stroke-linecap="round" transform="rotate(-90 {col[1]} 84)" filter="url(#glow)"/>'
    )
    # flame icon on a badge at the top of the ring
    stats.append(f'<circle cx="{col[1]}" cy="{84-45}" r="14" fill="{BG_TOP}"/>')
    stats.append(
        f'<path transform="translate({col[1]-9},{84-45-12}) scale(1.1 1.25)" fill="{ACCENT}" filter="url(#glow)" '
        f'd="M8 0 C9 5 16 7 16 13 A8 7.5 0 0 1 0 13 C0 9 3 7 4 4 C5 6 6 7 7 7 C7 5 7 2 8 0 Z"/>'
    )
    stats.append(f'<text x="{col[1]}" y="96" text-anchor="middle" fill="{TEXT}" font-size="32" font-weight="700">{current[0]}</text>')
    stats.append(f'<text class="lbl" x="{col[1]}" y="152" text-anchor="middle" fill="{ACCENT}" style="fill:{ACCENT}">Current Streak</text>')
    stats.append(f'<text class="sub" x="{col[1]}" y="176" text-anchor="middle">{rng(current)}</text>')

    stats.append(f'<text class="big" x="{col[2]}" y="92" text-anchor="middle">{longest[0]}</text>')
    stats.append(f'<text class="lbl" x="{col[2]}" y="126" text-anchor="middle">Longest Streak</text>')
    stats.append(f'<text class="sub" x="{col[2]}" y="152" text-anchor="middle">{rng(longest)}</text>')

    if not graph_only:
        o.extend(stats)

    # ---- chart
    o.append(f'<g transform="translate(0 {-shift})">')
    o.append(f'<text class="title" x="{W/2}" y="226" text-anchor="middle">{name}\'s Contribution Graph</text>')
    if not graph_only:
        o.append(f'<rect x="{cx0}" y="{cy0}" width="{cx1-cx0}" height="{cy1-cy0}" fill="#0a1f3d" fill-opacity=".55"/>')
    for k in range(11):
        v = ymax * k / 10
        y = cy1 - k / 10 * (cy1 - cy0)
        o.append(f'<line class="grid" x1="{cx0}" y1="{y:.1f}" x2="{cx1}" y2="{y:.1f}"/>')
        o.append(f'<text class="axis" x="{cx0-8}" y="{y+4:.1f}" text-anchor="end">{v:g}</text>')
    for (x, _), (d, _) in zip(pts, recent):
        o.append(f'<line class="grid" x1="{x:.1f}" y1="{cy0}" x2="{x:.1f}" y2="{cy1}"/>')
        o.append(f'<text class="axis" x="{x:.1f}" y="{cy1+20}" text-anchor="middle">{d.day}</text>')
    o.append(f'<text class="axis" x="{(cx0+cx1)/2}" y="{H-18}" text-anchor="middle" font-size="11">Days</text>')
    o.append(
        f'<text class="axis" transform="translate(32 {(cy0+cy1)/2}) rotate(-90)" text-anchor="middle" font-size="11">Contributions</text>'
    )

    o.append(f'<path class="fade" style="animation-delay:1s" d="{area}" fill="url(#area)"/>')
    o.append(
        f'<path class="line" d="{line}" fill="none" stroke="{ACCENT}" stroke-width="3.5" '
        f'stroke-linecap="round" filter="url(#glow)"/>'
    )
    for i, ((x, y), (d, c)) in enumerate(zip(pts, recent)):
        s = "" if c == 1 else "s"
        o.append(
            f'<circle class="fade" style="animation-delay:{0.3 + 2.2 * i / len(pts):.2f}s" cx="{x:.1f}" cy="{y:.1f}" r="5" '
            f'fill="#a8e1ff" stroke="{ACCENT}" stroke-width="2"><title>{c} contribution{s} on {d.isoformat()}</title></circle>'
        )

    o.append("</g>")
    o.append("</svg>")
    return "\n".join(o) + "\n"


def main():
    graph_only = "--graph-only" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--graph-only"]
    if len(args) not in (2, 3):
        sys.exit("Usage: python render_analytics_svg.py <data_json> <output_svg> [display_name] [--graph-only]")
    with open(args[0]) as f:
        data = json.load(f)
    name = args[2] if len(args) == 3 else data.get("username", "")
    with open(args[1], "w") as f:
        f.write(build_svg(data, name, graph_only))
    print(f"Wrote {args[1]}")


if __name__ == "__main__":
    main()
