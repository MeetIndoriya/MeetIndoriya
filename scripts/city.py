"""Contribution City: renders a year of GitHub activity as an isometric night skyline.

Mapping (every number comes from the calendar data, nothing is random):
  * one tile per day, 53 week-columns x 7 weekday-rows (Sunday at the back)
  * 0 contributions  -> empty plot (dark pad, street grid visible)
  * >0               -> a building. Height scales with that day's count relative to the busiest day,
                        facade colour/lit-window density step up through four quartile levels
  * busiest day      -> "commit tower": wider, stepped crown, antenna and a pulsing beacon
  * longest streak   -> its plots get a cyan outline (an "avenue", min. 3 days)
The only pseudo-random part is *which* windows are lit; it is seeded by the date so the same data
always yields the same picture (no daily churn in the repo).
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from kit import C, MONO, card, document, n1, pts, text

COLS, ROWS = 53, 7
UX, UY = 14.6, 3.1      # screen vector for +1 week  (long axis, nearly horizontal)
VX, VY = -6.6, 5.9      # screen vector for +1 weekday (depth axis)
OX, OY = 84.0, 162.0
W, H = 880, 424

LV = {
    1: dict(top="#1f4a66", front="#15344d", side="#0f2638", win="#62c6ee"),
    2: dict(top="#1e6c7b", front="#155562", side="#0f3f4a", win="#74e4e2"),
    3: dict(top="#26845f", front="#196548", side="#114a37", win="#98f2b8"),
    4: dict(top="#3fb950", front="#25873a", side="#1a6a2d", win="#f4e48c"),
}
LAND = dict(top="#8b6cf6", front="#6246d6", side="#4631a8", win="#a5f3ff")
LIT_P = {1: .34, 2: .46, 3: .58, 4: .68}

CSS = "".join(
    f".t{k}{{fill:{v['top']}}}.f{k}{{fill:{v['front']}}}.s{k}{{fill:{v['side']}}}.w{k}{{fill:{v['win']}}}"
    for k, v in {**LV, 9: LAND}.items()
) + ".wd{opacity:.62}.pad{fill:#0f1a27}.rd{fill:#080d14;stroke:#16222f;stroke-width:1}.mt{font-size:10.5px}"


def P(w: float, d: float) -> tuple[float, float]:
    return OX + w * UX + d * VX, OY + w * UY + d * VY


def footprint(w: int, d: int, m: float):
    return [P(w + m, d + m), P(w + 1 - m, d + m), P(w + 1 - m, d + 1 - m), P(w + m, d + 1 - m)]


def shift(p, h):
    return p[0], p[1] - h


def prism(fp, h0: float, h1: float, k: int):
    a, b, c, d = fp
    top = f'<path class="t{k}" d="{pts(shift(a,h1), shift(b,h1), shift(c,h1), shift(d,h1))}"/>'
    front = f'<path class="f{k}" d="{pts(shift(d,h0), shift(c,h0), shift(c,h1), shift(d,h1))}"/>'
    side = f'<path class="s{k}" d="{pts(shift(c,h0), shift(b,h0), shift(b,h1), shift(c,h1))}"/>'
    return side + front + top


def windows(p0, p1, h0: float, h1: float, rng: random.Random, prob: float, cols: int = 2):
    """Lit windows on the wall between ground points p0->p1 spanning heights h0..h1."""
    out, singles = [], []
    rows = int((h1 - h0 - 4) // 5.4)
    for j in range(max(rows, 0)):
        y0 = h0 + 3.2 + j * 5.4
        for i in range(cols):
            if rng.random() > prob:
                continue
            t0 = 0.13 + i * (0.74 / cols) + 0.02
            t1 = t0 + 0.74 / cols - 0.12
            xa, ya = p0[0] + t0 * (p1[0] - p0[0]), p0[1] + t0 * (p1[1] - p0[1])
            xb, yb = p0[0] + t1 * (p1[0] - p0[0]), p0[1] + t1 * (p1[1] - p0[1])
            q = pts((xa, ya - y0), (xb, yb - y0), (xb, yb - y0 - 2.7), (xa, ya - y0 - 2.7))
            out.append(q)
            singles.append(q)
    return "".join(out), singles


def levels(values: list[int]):
    nz = sorted(v for v in values if v > 0)
    if not nz:
        return lambda v: 0
    q = lambda f: nz[min(len(nz) - 1, int(len(nz) * f))]
    q1, q2, q3 = q(.25), q(.5), q(.75)
    return lambda v: 0 if v <= 0 else 1 if v <= q1 else 2 if v <= q2 else 3 if v <= q3 else 4


def render(data: dict, stats: dict, handle: str) -> str:
    cal = data["calendar"]
    start, end = stats["start"], stats["end"]
    counts: dict[date, int] = stats["counts"]
    grid_start = start - timedelta(days=(start.weekday() + 1) % 7)  # Sunday on/before window start
    mx = max(counts.values(), default=0)
    lvl = levels(list(counts.values()))
    ref = max(mx, 8)
    best_day, best_n = stats["best_day"]

    # tiles ------------------------------------------------------------------------
    cells = []
    for i in range(COLS * ROWS):
        dt = grid_start + timedelta(days=i)
        cells.append((i // 7, i % 7, dt, counts.get(dt, 0) if start <= dt <= end else 0))

    slab = pts(P(-.35, -.35), P(COLS + .35, -.35), P(COLS + .35, ROWS + .35), P(-.35, ROWS + .35))
    pl = 8
    plinth_f = pts(P(-.35, ROWS + .35), P(COLS + .35, ROWS + .35), shift(P(COLS + .35, ROWS + .35), -pl), shift(P(-.35, ROWS + .35), -pl))
    plinth_s = pts(P(COLS + .35, ROWS + .35), P(COLS + .35, -.35), shift(P(COLS + .35, -.35), -pl), shift(P(COLS + .35, ROWS + .35), -pl))
    pads = "".join(pts(*footprint(w, d, .06)) for w, d, _, _ in cells)

    lr = stats["longest_range"]
    streak_cells = ""
    if stats["longest_streak"] >= 3 and lr[0]:
        streak_cells = "".join(pts(*footprint(w, d, .06)) for w, d, dt, v in cells if lr[0] <= dt <= lr[1] and v > 0)

    # buildings --------------------------------------------------------------------
    n_active = sum(1 for c in cells if c[3] > 0)
    # keep the file small for very busy histories: fewer lit windows, no side-wall windows
    pmul = 1.0 if n_active <= 120 else 0.45 if n_active <= 250 else 0.22
    side_windows = n_active <= 250
    order = sorted((c for c in cells if c[3] > 0), key=lambda c: (c[0] * UY + c[1] * VY, c[0]))
    flick_pool, parts, tower = [], [], None
    for w, d, dt, v in order:
        rng = random.Random(dt.toordinal())
        k = lvl(v)
        h = 6 + 58 * (v / ref) ** 0.6
        if dt == best_day and v == mx and v > 0:
            tower = (w, d, dt, v, h)
            continue  # drawn separately, in depth order, below
        fp = footprint(w, d, .15)
        s = prism(fp, 0, h, k)
        wf, sf = windows(fp[3], fp[2], 0, h, rng, LIT_P[k] * pmul)
        ws, ss = windows(fp[2], fp[1], 0, h, rng, LIT_P[k] * .85 * pmul) if side_windows else ("", [])
        if wf:
            s += f'<path class="w{k}" d="{wf}"/>'
        if ws:
            s += f'<path class="w{k} wd" d="{ws}"/>'
        if k >= 3:  # rooftop unit
            cx, cy = (fp[0][0] + fp[2][0]) / 2, (fp[0][1] + fp[2][1]) / 2 - h
            s += f'<path class="s{k}" d="{pts((cx-2.4,cy-.4),(cx+2.4,cy-.4),(cx+2.4,cy-3.4),(cx-2.4,cy-3.4))}"/>'
        if k >= 2 and sf and len(flick_pool) < 40:
            flick_pool.append((sf[0], k))
        parts.append(((w, d), s))

    tower_svg, label = "", ""
    if tower:
        w, d, dt, v, h = tower
        rng = random.Random(dt.toordinal())
        hh = h + 16
        fp = footprint(w, d, .05)
        s = prism(fp, 0, hh, 9)
        wf, _ = windows(fp[3], fp[2], 0, hh, rng, .7, 3)
        ws, _ = windows(fp[2], fp[1], 0, hh, rng, .6, 3)
        s += f'<path class="w9" d="{wf}"/><path class="w9 wd" d="{ws}"/>'
        crown = footprint(w, d, .26)
        s += prism(crown, hh, hh + 13, 9)
        cx = sum(p[0] for p in crown) / 4
        cy = sum(p[1] for p in crown) / 4 - hh - 13
        s += f'<path d="M{n1(cx)} {n1(cy)}V{n1(cy-14)}" stroke="#c4b5fd" stroke-width="1.2"/>'
        s += (f'<circle class="pulse" cx="{n1(cx)}" cy="{n1(cy-15)}" r="2" fill="{C["cyan"]}"/>'
              f'<circle cx="{n1(cx)}" cy="{n1(cy-15)}" r="1.9" fill="#e0fbff"/>')
        tower_svg = (w, d, s)
        lx = min(max(cx, 110), W - 120)
        ly = max(cy - 30, 62)
        anchor = "middle"
        label = (f'<path d="M{n1(cx)} {n1(cy-18)}V{n1(ly+16)}" stroke="{C["violet"]}" stroke-opacity=".5" stroke-dasharray="2 3"/>'
                 + text(lx, ly, "commit tower", 12, C["text"], "m", anchor=anchor, weight="600")
                 + text(lx, ly + 14.5, f"{v} contributions · {dt.day} {dt.strftime('%b %Y')}", 10.5, C["muted"], "m", anchor=anchor))

    # merge the tower into depth order
    if tower_svg:
        tw, td, ts = tower_svg
        key = tw * UY + td * VY
        merged, placed = [], False
        for (cw_cd, s) in parts:
            cw, cd = cw_cd
            if not placed and cw * UY + cd * VY > key:
                merged.append(ts)
                placed = True
            merged.append(s)
        if not placed:
            merged.append(ts)
        body_buildings = "".join(merged)
    else:
        body_buildings = "".join(s for _, s in parts)

    flicks = "".join(
        f'<path class="w{k} fl" style="animation-delay:-{n1(i*0.83)}s;animation-duration:{n1(4+ (i%5)*1.1)}s" d="{q}"/>'
        for i, (q, k) in enumerate(flick_pool[::max(1, len(flick_pool)//8)][:8])
    )

    # streets & traffic --------------------------------------------------------------
    def road(a, b):
        return f"M{n1(a[0])} {n1(a[1])}L{n1(b[0])} {n1(b[1])}"
    front_road = road(P(-.17, ROWS + .17), P(COLS + .17, ROWS + .17))
    back_road = road(P(COLS + .17, -.17), P(-.17, -.17))
    lights_back = (f'<circle r="1.5" fill="{C["yellow"]}"><animateMotion dur="26s" repeatCount="indefinite" path="{back_road}"/></circle>')
    lights_front = (f'<circle r="1.6" fill="{C["cyan"]}"><animateMotion dur="19s" repeatCount="indefinite" path="{front_road}"/></circle>')

    # axes -----------------------------------------------------------------------------
    axes = []
    for d, name in ((0, "Sun"), (6, "Sat")):
        x, y = P(-.35, d + .5)
        axes.append(text(x - 8, y + 3.5, name, 10.5, C["muted"], "m", anchor="end"))
    last_x = -99
    bounds = []
    for col in range(COLS):
        dt = grid_start + timedelta(days=col * 7)
        if (col == 0 or dt.month != (dt - timedelta(days=7)).month) and dt >= start - timedelta(days=6):
            x, y = P(col, ROWS + .35)
            if x - last_x >= 44:
                axes.append(text(x - 2, y + 24, dt.strftime("%b").lower(), 10.5, C["muted"], "m"))
                if col:
                    bounds.append(road(P(col, -.2), P(col, ROWS + .2)))
                last_x = x
    month_lines = f'<path d="{"".join(bounds)}" fill="none" stroke="#26394f" stroke-width="1" stroke-dasharray="2 4"/>' if bounds else ""

    # bottom-left summary block ---------------------------------------------------------
    src = {"graphql": "source: GitHub contribution graph",
           "public-commits": "source: commits in public repositories"}.get(cal["source"], cal["source"])
    unit = "contributions" if cal["source"] == "graphql" else "commits"
    legend_x = 28
    legend = text(legend_x, 387, "less", 10.5, C["muted"], "m")
    for i, col in enumerate(("#0f1a27", LV[1]["top"], LV[2]["top"], LV[3]["top"], LV[4]["top"])):
        legend += f'<rect x="{legend_x+34+i*15}" y="378" width="10" height="10" rx="2" fill="{col}" stroke="{C["border2"]}" stroke-width=".6"/>'
    legend += text(legend_x + 34 + 5 * 15 + 4, 387, "more", 10.5, C["muted"], "m")
    streak_txt = f"longest streak {stats['longest_streak']} day{'s' if stats['longest_streak'] != 1 else ''}"
    block = (
        text(28, 322, f"{stats['total']:,}", 36, C["text"], "s", weight="700")
        + text(28 + 12 + 21 * len(f"{stats['total']:,}"), 322, unit, 13, C["text2"], "m")
        + text(28, 343, f"{stats['active_days']} active days in the last 12 months", 12, C["text2"], "m")
        + text(28, 360, streak_txt, 12, C["text2"], "m")
        + legend + text(28, 410, src, 10.5, C["muted"], "m")
    )
    if mx == 0:
        block += text(W / 2, 250, "No activity in the last 12 months yet. The first commit raises the first building.", 13, C["text2"], "m", anchor="middle")

    title = "Contribution city"
    desc = (f"Isometric city built from {stats['total']} {unit} over the last 12 months across "
            f"{stats['active_days']} active days. Taller, brighter buildings are busier days.")
    body = "\n".join([
        card(W, H, "contribution-city.svg", f"@{handle}", dots=True),
        f'<path d="{slab}" class="rd"/>',
        f'<path d="{plinth_f}" fill="#05080d"/><path d="{plinth_s}" fill="#04070b"/>',
        f'<path d="{pads}" class="pad"/>',
        f'<path d="{streak_cells}" fill="none" stroke="{C["cyan"]}" stroke-opacity=".6" stroke-width="1"/>' if streak_cells else "",
        month_lines,
        lights_back,
        body_buildings,
        flicks,
        lights_front,
        label,
        "".join(axes),
        block,
    ])
    return document(W, H, title, desc, body, css=CSS)
