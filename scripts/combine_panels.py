"""Join portrait.svg and stats.svg into one two-panel image (profile.svg).

    python scripts/combine.py portrait.svg stats.svg profile.svg
"""
import re
import sys

PANEL_W, PANEL_H = 840, 880
PAD = 28
W = PAD * 4 + PANEL_W * 2
H = PAD * 2 + PANEL_H


def inner(path, tag):
    s = open(path).read()
    body = s[s.index(">", s.index("<svg")) + 1: s.rindex("</svg>")]
    # keep ids unique between the two panels
    for i in set(re.findall(r'id="([^"]+)"', body)):
        body = body.replace(f'id="{i}"', f'id="{tag}{i}"').replace(f"url(#{i})", f"url(#{tag}{i})")
    return body


def main(portrait, stats, out):
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
         f'<rect width="{W}" height="{H}" fill="#0d1117"/>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" fill="none" stroke="#30363d"/>',
         f'<line x1="{W/2}" y1="0" x2="{W/2}" y2="{H}" stroke="#30363d"/>']
    for k, (path, tag) in enumerate(((portrait, "p_"), (stats, "s_"))):
        x = PAD + k * (PANEL_W + PAD * 2)
        p.append(f'<svg x="{x}" y="{PAD}" width="{PANEL_W}" height="{PANEL_H}" '
                 f'viewBox="0 0 {PANEL_W} {PANEL_H}">{inner(path, tag)}</svg>')
    p.append("</svg>")
    open(out, "w").write("".join(p))


if __name__ == "__main__":
    main(*sys.argv[1:4])
