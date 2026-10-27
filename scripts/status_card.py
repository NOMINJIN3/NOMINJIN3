"""Build status.svg (terminal-style GitHub stats card).

Reads the contribution data the "Update profile art" workflow already saves:
    python scripts/status_card.py data/contributions.json status.svg
"""
import json
import os
import sys
import urllib.request
from datetime import date, timedelta

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/contributions.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "status.svg"
PROMPT_USER = "nominjin"

QUERY = """query($login:String!){user(login:$login){contributionsCollection{
contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def load_days(path):
    """data/contributions.json -> [(date, count), ...]"""
    data = json.load(open(path))
    return [(d["date"], d["count"]) for w in data["weeks"] for d in w]


def fetch_days(login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}",
                 "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        raise SystemExit(data["errors"])
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]


def fmt_date(d):
    return d.strftime("%b ") + str(d.day)


def compute(days):
    days = sorted((date.fromisoformat(d), c) for d, c in days)
    today = days[-1][0]
    total = sum(c for _, c in days)
    active = sum(1 for _, c in days if c > 0)

    # longest streak
    best_len, best_rng, run, start = 0, None, 0, None
    for d, c in days:
        if c > 0:
            if run == 0:
                start = d
            run += 1
            if run >= best_len:
                best_len, best_rng = run, (start, d)
        else:
            run = 0

    # current streak (today may still be empty, so allow starting from yesterday)
    i = len(days) - 1
    if days[i][1] == 0:
        i -= 1
    cur, end = 0, days[i][0] if i >= 0 else today
    while i >= 0 and days[i][1] > 0:
        cur += 1
        i -= 1
    cur_rng = (end - timedelta(days=cur - 1), end) if cur else None

    best_day = max(days, key=lambda x: x[1])

    # last 13 months
    months = []
    y, m = today.year, today.month
    for _ in range(13):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    month_tot = {k: 0 for k in months}
    for d, c in days:
        if (d.year, d.month) in month_tot:
            month_tot[(d.year, d.month)] += c

    return dict(total=total, active=active, span=len(days),
                cur=cur, cur_rng=cur_rng, best=best_len, best_rng=best_rng,
                best_day=best_day[1], best_day_date=best_day[0],
                avg=total / active if active else 0.0,
                months=[(date(y, m, 1).strftime("%b")[0], month_tot[(y, m)]) for y, m in months])


def counter(x, y, target, fmt, suffix, color, start, step=0.075, frames=16):
    """Count-up animation: a stack of texts shown one after another (works in GitHub's <img>)."""
    out = []
    vals = [target * (1 - (1 - k / (frames - 1)) ** 3) for k in range(frames)]
    for k, v in enumerate(vals):
        b = start + k * step
        hide = "" if k == frames - 1 else f'<set attributeName="opacity" to="0" begin="{b+step:.3f}s"/>'
        out.append(f'<text x="{x}" y="{y}" opacity="0" font-size="54" font-weight="700" fill="{color}">'
                   f'{fmt(v)}<tspan font-size="24" font-weight="400" fill="#7d8590">{suffix}</tspan>'
                   f'<set attributeName="opacity" to="1" begin="{b:.3f}s"/>{hide}</text>')
    return "".join(out)


def build(s):
    W, H = 840, 880
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
         '<style>.t{opacity:0;animation:in 0.45s ease-out both}@keyframes in{0%{opacity:0;transform:translateY(14px)}'
         '100%{opacity:1;transform:translateY(0)}}.b{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);'
         'animation:grow 0.6s ease-out both}@keyframes grow{to{transform:scaleY(1)}}'
         '@media (prefers-reduced-motion: reduce){.t,.b{opacity:1!important;transform:none!important;animation:none!important}}</style>',
         '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#111722"/>'
         '<stop offset="1" stop-color="#0d1117"/></linearGradient></defs>',
         f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="#30363d"/>']
    p.append(f'<line x1="0" y1="30" x2="{W}" y2="30" stroke="#30363d"/>')
    for cx, c in ((20, "#ff5f56"), (36, "#ffbd2e"), (52, "#27c93f")):
        p.append(f'<circle cx="{cx}" cy="15.0" r="5" fill="{c}"/>')
    p.append(f'<text x="420" y="19" fill="#7d8590" font-size="12" text-anchor="middle">{PROMPT_USER}@github: ~$ ./status.sh</text>')

    rng = lambda r: f"{fmt_date(r[0])} – {fmt_date(r[1])}" if r else "start one today"
    integer = lambda v: f"{round(v):,}"
    cards = [
        ("$ current streak", s["cur"], integer, " day" if s["cur"] == 1 else " days", rng(s["cur_rng"]), "#39d353"),
        ("$ longest streak", s["best"], integer, " day" if s["best"] == 1 else " days", rng(s["best_rng"]), "#e6edf3"),
        ("$ contributions", s["total"], integer, "", "in the last year", "#e6edf3"),
        ("$ active days", s["active"], integer, f" / {s['span']}",
         f"{round(100 * s['active'] / s['span'])}% of the year", "#e6edf3"),
        ("$ best day", s["best_day"], integer, "",
         fmt_date(s["best_day_date"]) if s["best_day"] else "—", "#e6edf3"),
        ("$ avg / active day", s["avg"], lambda v: f"{v:.1f}", "", "contributions", "#e6edf3"),
    ]
    for i, (label, val, fmt, suf, sub, color) in enumerate(cards):
        x = 20 if i % 2 == 0 else 428
        y = 54 + (i // 2) * 166
        tx = x + 24
        p.append(f'<g class="t" style="animation-delay:{i*0.15:.2f}s">'
                 f'<rect x="{x}" y="{y}" width="392" height="150" rx="10" fill="#161b22" stroke="#30363d"/>'
                 f'<text x="{tx}" y="{y+40}" fill="#7d8590" font-size="22">{label}</text>'
                 + counter(tx, y + 100, val, fmt, suf, color, 0.27 + i * 0.15)
                 + f'<text x="{tx}" y="{y+132}" fill="#7d8590" font-size="20">{sub}</text></g>')

    # monthly bar chart
    p.append('<g class="t" style="animation-delay:1.00s"><rect x="20" y="552" width="800" height="308" rx="10" '
             'fill="#161b22" stroke="#30363d"/><text x="44" y="592" fill="#7d8590" font-size="22">'
             '$ contributions / month</text></g>')
    months = s["months"]
    peak = max(v for _, v in months) or 1
    base, top = 820, 640                    # leaves room for the peak label below the heading
    slot = 750 / len(months)
    bw = slot * 0.62
    for k, (lab, v) in enumerate(months):
        h = max(2, (base - top) * v / peak) if v else 2
        x = 45 + k * slot + (slot - bw) / 2
        is_peak = v == peak and v > 0
        p.append(f'<rect class="b" x="{x:.1f}" y="{base-h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" '
                 f'fill="{"#39d353" if is_peak else ("#26a641" if v else "#30363d")}" style="animation-delay:{1.3+k*0.06:.2f}s"/>')
        p.append(f'<text x="{x+bw/2:.1f}" y="848" fill="#7d8590" font-size="18" text-anchor="middle">{lab}</text>')
        if is_peak:
            p.append(f'<text class="t" style="animation-delay:2.20s" x="{x+bw/2:.1f}" y="{base-h-10:.1f}" '
                     f'fill="#e6edf3" font-size="18" text-anchor="middle">{v:,}</text>')
    p.append("</svg>")
    return "".join(p)


if __name__ == "__main__":
    stats = compute(load_days(SRC))
    open(OUT, "w").write(build(stats))
    print(json.dumps({k: str(v) for k, v in stats.items() if k != "months"}, indent=1))
