"""All non-city SVG panels. Each function returns a complete SVG document string."""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import timedelta
from pathlib import Path

from kit import (C, LANG_COLORS, MONO, W, card, document, esc, n1, relative_date, text, truncate, wrap)

HERE = Path(__file__).parent
CHIP_DOT = {"frontend": C["cyan"], "backend": C["green"], "data": C["violet"]}
CHIP_KIND = {"React": "frontend", "Next.js": "frontend", "JavaScript": "frontend", "Tailwind CSS": "frontend",
             "Python": "backend", "FastAPI": "backend", "Node.js": "backend", "Express.js": "backend"}


def chip(x: float, y: float, label: str, dot: str, size: float = 12.5, h: int = 26) -> tuple[str, float]:
    w = len(label) * size * 0.61 + 30
    s = (f'<rect x="{n1(x)}" y="{n1(y)}" width="{n1(w)}" height="{h}" rx="7" fill="#0e1823" stroke="{C["border2"]}"/>'
         f'<circle cx="{n1(x+12)}" cy="{n1(y+h/2)}" r="3" fill="{dot}"/>'
         + text(x + 22, y + h / 2 + 4.3, label, size, C["text2"], "m"))
    return s, w


# ---------------------------------------------------------------- hero ----------------
def avatar(cfg: dict, x: float, y: float, size: float = 188) -> str:
    """Pixel identicon derived from the username, or the user's own picture if `avatar_path` is set."""
    p = cfg.get("avatar_path")
    if p and (HERE.parent / p).exists():
        b64 = base64.b64encode((HERE.parent / p).read_bytes()).decode()
        mime = "image/png" if p.lower().endswith("png") else "image/jpeg"
        return (f'<clipPath id="av"><rect x="{x}" y="{y}" width="{size}" height="{size}" rx="12"/></clipPath>'
                f'<image x="{x}" y="{y}" width="{size}" height="{size}" clip-path="url(#av)" '
                f'preserveAspectRatio="xMidYMid slice" href="data:{mime};base64,{b64}"/>'
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="12" fill="none" stroke="{C["border2"]}"/>')
    n, gap = 11, 2
    cell = (size - gap * (n - 1)) / n
    glyph = {
        "M": ["X...X", "XX.XX", "X.X.X", "X...X", "X...X", "X...X", "X...X"],
        "I": ["XXX", ".X.", ".X.", ".X.", ".X.", ".X.", "XXX"],
    }
    letters = [c for c in "".join(w[0] for w in cfg["name"].split()).upper() if c in glyph][:2] or ["M", "I"]
    lit = {}
    col0 = 1 if len(letters) == 2 else 3
    for li, ch in enumerate(letters):
        g = glyph[ch]
        for r, rowstr in enumerate(g):
            for c, v in enumerate(rowstr):
                if v == "X":
                    lit[(2 + r, col0 + c)] = C["cyan"] if r == 0 else C["green"]
        col0 += len(g[0]) + 1
    hsh = hashlib.sha256(cfg["username"].encode()).digest()
    out = [f'<rect x="{x-10}" y="{y-10}" width="{size+20}" height="{size+20}" rx="16" fill="#0a131d" stroke="{C["border"]}"/>']
    for r in range(n):
        for c in range(n):
            cx, cy = x + c * (cell + gap), y + r * (cell + gap)
            if (r, c) in lit:
                out.append(f'<rect x="{n1(cx)}" y="{n1(cy)}" width="{n1(cell)}" height="{n1(cell)}" rx="2.5" fill="{lit[(r,c)]}"/>')
            else:
                faint = hsh[(r * n + c) % 32] % 7 == 0 and not (1 <= r <= 9 and 0 <= c <= 10 and 2 <= r <= 8)  # sparse "matrix" noise outside the letters
                out.append(f'<rect x="{n1(cx)}" y="{n1(cy)}" width="{n1(cell)}" height="{n1(cell)}" rx="2.5" fill="{C["green"] if faint else "#101c28"}" fill-opacity="{.28 if faint else 1}"/>')
    L = 14
    for (bx, by, dx, dy) in ((x-10, y-10, 1, 1), (x+size+10, y-10, -1, 1), (x-10, y+size+10, 1, -1), (x+size+10, y+size+10, -1, -1)):
        out.append(f'<path d="M{bx+dx*L} {by}H{bx}V{by+dy*L}" fill="none" stroke="{C["cyan"]}" stroke-opacity=".7" stroke-width="1.5"/>')
    return "".join(out)


def hero(cfg: dict) -> str:
    H = 340
    out = [card(W, H, f"{cfg['signature']}: ~/profile", f"github.com/{cfg['username']}", dots=True)]
    x = 44
    out.append(text(x, 104, cfg["name"], 46, C["text"], "s", weight="700", extra='letter-spacing="-0.8"'))
    out.append(text(x, 138, cfg["role"], 22, C["green2"], "s", weight="600"))
    out.append(text(x, 162, cfg["subtitle"], 14.5, C["muted"], "s"))
    for i, ln in enumerate(wrap(cfg["tagline"], 62, 2)):
        out.append(text(x, 198 + i * 22, ln, 15.5, C["text2"], "s"))
    # location + status
    out.append(f'<path d="M{x+5} 237c-3.2 0-5.4 2.3-5.4 5.2 0 3.6 5.4 8.3 5.4 8.3s5.4-4.7 5.4-8.3c0-2.9-2.2-5.2-5.4-5.2z" fill="none" stroke="{C["muted"]}" stroke-width="1.4"/>'
               f'<circle cx="{x+5}" cy="242" r="1.8" fill="{C["muted"]}"/>')
    out.append(text(x + 20, 248, cfg["location"], 13.5, C["text2"], "s"))
    out.append(f'<circle class="pulse" cx="{x+5}" cy="268" r="3.4" fill="{C["green"]}"/><circle cx="{x+5}" cy="268" r="3.4" fill="{C["green"]}"/>')
    out.append(text(x + 20, 273, cfg["status"], 13.5, C["text2"], "s"))
    # chips
    cx = x
    for label in cfg["hero_chips"]:
        kind = CHIP_KIND.get(label, "data")
        s, w = chip(cx, 292, label, CHIP_DOT[kind])
        if cx + w > W - 40:
            break
        out.append(s)
        cx += w + 8
    out.append(avatar(cfg, 646, 82))
    desc = f"{cfg['name']}, {cfg['role']}. {cfg['subtitle']}. {cfg['tagline']}"
    return document(W, H, f"{cfg['name']} — {cfg['role']}", desc, "\n".join(out))


# ------------------------------------------------------------- metrics ----------------
def metrics(cfg: dict, data: dict, st: dict) -> str:
    H = 200
    u = data["user"]
    fmt = lambda v: "—" if v is None else f"{v:,}"
    since = f"on GitHub since {u['created_at'][:4]}" if u.get("created_at") else f"{len(st['languages'])} languages"
    unit = "contributions" if data["calendar"]["source"] == "graphql" else "commits"
    cells = [
        ("repositories", fmt(st["repo_count"]), since),
        ("followers", fmt(u.get("followers")), f"following {fmt(u.get('following'))}"),
        ("stars", fmt(st["stars"]), f"{fmt(st['forks'])} forks · public repos"),
        (unit, fmt(st["total"]), f"{st['active_days']} active days · 12 months"),
    ]
    out = [card(W, H)]
    cw = W / 4
    for i, (label, val, sub) in enumerate(cells):
        x = 30 + i * cw
        if i:
            out.append(f'<path d="M{n1(i*cw)} 22V92" stroke="{C["border"]}"/>')
        out.append(text(x, 38, label, 12.5, C["muted"], "m"))
        out.append(text(x, 78, val, 38, C["text"], "s", weight="700", extra='letter-spacing="-0.5"'))
        out.append(text(x, 102 - 0, sub, 12, C["muted"], "m"))
    out.append(f'<path d="M1 118.5H{W-1}" stroke="{C["border"]}"/>')
    # language strip (by repository count: bytes would be dominated by notebook JSON)
    langs = st["languages"].most_common(6)
    total = sum(c for _, c in langs) or 1
    out.append(text(30, 144, "languages", 12.5, C["muted"], "m"))
    out.append(text(W - 30, 144, "primary language per repository", 12, C["muted"], "m", anchor="end"))
    bx, bw, cur = 30, W - 60, 30.0
    clip = f'<clipPath id="lb"><rect x="30" y="154" width="{bw}" height="8" rx="4"/></clipPath>'
    segs = ""
    for name, cnt in langs:
        w = bw * cnt / total
        segs += f'<rect x="{n1(cur)}" y="154" width="{n1(w+.5)}" height="8" fill="{LANG_COLORS.get(name, C["muted"])}"/>'
        cur += w
    out.append(clip + f'<rect x="30" y="154" width="{bw}" height="8" rx="4" fill="#101c28"/><g clip-path="url(#lb)">{segs}</g>')
    lx = 30
    for name, cnt in langs:
        out.append(f'<circle cx="{lx+4}" cy="177" r="4" fill="{LANG_COLORS.get(name, C["muted"])}"/>')
        lab = f"{name} {cnt}"
        out.append(text(lx + 14, 181, lab, 12, C["text2"], "m"))
        lx += 14 + len(lab) * 7.3 + 22
    return document(W, H, "GitHub profile metrics",
                    f"{cells[0][1]} repositories, {cells[1][1]} followers, {cells[2][1]} stars, {cells[3][1]} {unit} in the last 12 months.",
                    "\n".join(out))


# ------------------------------------------------------------- activity ---------------
def activity(cfg: dict, data: dict, st: dict) -> str:
    H = 256
    unit = "contributions" if data["calendar"]["source"] == "graphql" else "commits"
    out = [card(W, H, "activity.log", "last 12 months")]
    base, top = 196, 92
    # A: months
    out.append(text(28, 70, f"{unit} per month", 12.5, C["text2"], "m"))
    mv = [v for _, v in st["months"]]
    mmax = max(mv) or 1
    for i, (k, v) in enumerate(st["months"]):
        x = 28 + i * 38
        bh = max(3, (base - top) * v / mmax) if v else 3
        col = C["green"] if v == max(mv) and v > 0 else C["cyan"]
        op = 1 if v == max(mv) and v > 0 else (.55 if v else .16)
        out.append(f'<rect x="{x}" y="{n1(base-bh)}" width="24" height="{n1(bh)}" rx="3" fill="{col}" fill-opacity="{op}"/>')
        if v:
            out.append(text(x + 12, base - bh - 6, v, 11, C["text2"], "m", anchor="middle"))
        mon = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"][int(k[5:]) - 1]
        out.append(text(x + 12, 214, mon, 10.5, C["muted"], "m", anchor="middle"))
    out.append(f'<path d="M24 {base+.5}H480" stroke="{C["border2"]}"/>')
    out.append(f'<path d="M498 58V232M672 58V232" stroke="{C["border"]}"/>')
    # B: weekday
    out.append(text(520, 70, "by weekday", 12.5, C["text2"], "m"))
    wd = st["weekday"]
    wmax = max(wd) or 1
    for i, v in enumerate(wd):
        x = 520 + i * 21
        bh = max(3, (base - top) * v / wmax) if v else 3
        hot = v == max(wd) and v > 0
        out.append(f'<rect x="{x}" y="{n1(base-bh)}" width="14" height="{n1(bh)}" rx="3" fill="{C["violet"] if not hot else C["yellow"]}" fill-opacity="{1 if hot else (.55 if v else .16)}"/>')
        out.append(text(x + 7, 214, "SMTWTFS"[i], 10.5, C["muted"], "m", anchor="middle"))
    out.append(f'<path d="M516 {base+.5}H660" stroke="{C["border2"]}"/>')
    # C: streaks
    out.append(text(694, 70, "streaks", 12.5, C["text2"], "m"))
    bd, bn = st["best_day"]
    rows = [("current", f"{st['current_streak']} d"), ("longest", f"{st['longest_streak']} d"),
            ("best day", f"{bn}"), ("active", f"{st['active_days']}/{st['span_days']}")]
    for i, (k, v) in enumerate(rows):
        y = [102, 130, 158, 198][i]
        out.append(text(694, y, k, 12, C["muted"], "m"))
        out.append(text(W - 28, y, v, 15, C["text"], "m", weight="700", anchor="end"))
        if k == "best day" and bn:
            out.append(text(W - 28, y + 13.5, f"{bd.day} {bd.strftime('%b %Y')}", 10.5, C["muted"], "m", anchor="end"))
    return document(W, H, "Activity breakdown",
                    f"{st['total']} {unit} in 12 months; longest streak {st['longest_streak']} days; best day {bn}.", "\n".join(out))


# ------------------------------------------------------------- stack ------------------
def _lum(hexc: str) -> float:
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


GLYPHS = {
    "rest": '<path d="M9 5C6 5 6 8 6 10s-1 4-3 4c2 0 3 2 3 4s0 5 3 5M19 5c3 0 3 3 3 5s1 4 3 4c-2 0-3 2-3 4s0 5-3 5" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" transform="translate(-1 -3) scale(.95)"/>',
    "integration": '<path d="M3 8h15M14 4l4 4-4 4M21 17H6M10 13l-4 4 4 4" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
}


def stack(cfg: dict) -> str:
    icons = json.loads((HERE / "icons.json").read_text())
    rows = cfg["stack"]
    rh, top = 78, 52
    H = top + rh * len(rows) + 6
    out = [card(W, H, "stack.config", "grouped by role")]
    for r, grp in enumerate(rows):
        cy = top + r * rh + rh / 2
        if r:
            out.append(f'<path d="M24 {top + r*rh}H{W-24}" stroke="{C["border"]}"/>')
        out.append(text(36, cy + 4.5, grp["group"], 13.5, C["text2"], "m"))
        for i, (slug, label) in enumerate(grp["items"]):
            cx = 214 + i * 128
            if slug in icons:
                col = "#" + icons[slug]["hex"]
                col = col if _lum(icons[slug]["hex"]) > 0.22 else C["text2"]
                out.append(f'<g transform="translate({n1(cx-14.4)} {n1(cy-24)}) scale(1.2)"><path d="{icons[slug]["path"]}" fill="{col}"/></g>')
            else:
                out.append(f'<g transform="translate({n1(cx-14.4)} {n1(cy-24)}) scale(1.2)">{GLYPHS[slug].format(c=C["cyan"])}</g>')
            out.append(text(cx, cy + 22, label, 11.5, C["text2"], "m", anchor="middle"))
    names = ", ".join(l for g in rows for _, l in g["items"])
    return document(W, H, "Tech stack", f"Technologies grouped by role: {names}.", "\n".join(out))


# ------------------------------------------------------------- terminal ---------------
def terminal(cfg: dict, data: dict) -> str:
    t = cfg["terminal"]
    rh = 21
    out_lines: list[str] = []
    y = 70

    def cmd(s: str):
        nonlocal y
        out_lines.append(text(28, y, "$", 13.5, C["green"], "m", weight="700") + text(46, y, s, 13.5, C["text"], "m"))
        y += rh

    def line(s: str, col=None):
        nonlocal y
        out_lines.append(text(46, y, s, 13.5, col or C["text2"], "m"))
        y += rh

    cmd("whoami")
    line(f"{cfg['username']} · {cfg['role']} · B.Tech CSE student")
    y += 8
    cmd("now --building")
    for b in t["building"]:
        out_lines.append(text(46, y, "▸", 13.5, C["cyan"], "m") + text(64, y, b["label"], 13.5, C["text2"], "m")
                         + text(300, y, b["repo"], 13.5, C["cyan"], "m") + text(430, y, b["detail"], 13.5, C["muted"], "m"))
        y += rh
    y += 8
    cmd("now --learning")
    line(" · ".join(t["learning"]))
    y += 8
    cmd(f"git log --author={cfg['username']} -n {min(4, len(data['recent_commits']))}")
    for c in data["recent_commits"][:4]:
        d = c["date"][:10]
        from datetime import date as _d
        dd = _d.fromisoformat(d)
        out_lines.append(text(46, y, f"{dd.day:>2} {dd.strftime('%b')}", 13.5, C["yellow"], "m")
                         + text(116, y, truncate(c["repo"], 18), 13.5, C["cyan"], "m")
                         + text(300, y, truncate(c["message"], 62), 13.5, C["text2"], "m"))
        y += rh
    if not data["recent_commits"]:
        line("no public commits yet", C["muted"])
    y += 8
    cmd("status")
    out_lines.append(f'<circle class="pulse" cx="52" cy="{y-4}" r="3.6" fill="{C["green"]}"/><circle cx="52" cy="{y-4}" r="3.6" fill="{C["green"]}"/>'
                     + text(64, y, cfg["status"], 13.5, C["text"], "m")
                     + f'<rect class="cur" x="{n1(64 + len(cfg["status"])*8.12 + 6)}" y="{y-12}" width="8" height="15" fill="{C["green"]}"/>')
    y += 22
    H = int(y + 6)
    body = card(W, H, f"{cfg['signature']}: ~/now", "zsh") + "\n" + "\n".join(out_lines)
    plain = "; ".join(b["label"] + " in " + b["repo"] for b in t["building"])
    return document(W, H, "Terminal: what I am working on",
                    f"Building: {plain}. Learning: {', '.join(t['learning'])}. Status: {cfg['status']}.", body)


# ------------------------------------------------------------- projects ---------------
def project_card(p: dict, show_zero: bool = False) -> str:
    H = 138
    lang = p.get("language")
    lc = LANG_COLORS.get(lang, C["muted"])
    out = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="url(#bg)" stroke="{C["border"]}"/>',
           f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="url(#grid)"/>',
           f'<ellipse cx="60" cy="0" rx="260" ry="70" fill="url(#glow)"/>',
           f'<rect x="20" y="24" width="4" height="{H-48}" rx="2" fill="{lc}"/>']
    out.append(text(40, 42, p["name"], 19, C["text"], "s", weight="700"))
    for i, ln in enumerate(wrap(p["description"], 76, 2)):
        out.append(text(40, 68 + i * 19, ln, 13.5, C["text2"], "s"))
    # tags
    x = 40
    for tag in p["tags"][:6]:
        w = len(tag) * 7 + 18
        if x + w > 640:
            break
        out.append(f'<rect x="{x}" y="{H-38}" width="{w}" height="22" rx="6" fill="#0e1823" stroke="{C["border2"]}"/>'
                   + text(x + w / 2, H - 22.5, tag, 11.5, C["text2"], "m", anchor="middle"))
        x += w + 7
    # right column
    out.append(f'<circle cx="{W-28-len(lang or "—")*7.8-14}" cy="38.5" r="4.5" fill="{lc}"/>' if lang else "")
    out.append(text(W - 28, 42, lang or "—", 12.5, C["text2"], "m", anchor="end"))
    out.append(text(W - 28, 62, f"updated {relative_date(p['pushed_at'])}", 11.5, C["muted"], "m", anchor="end"))
    stats = []
    if p["stars"] or show_zero:
        stats.append(f"★ {p['stars']}")
    if p["forks"] or show_zero:
        stats.append(f"⑂ {p['forks']}")
    if stats:
        out.append(text(W - 28, 81, "  ".join(stats), 12, C["text2"], "m", anchor="end"))
    out.append(f'<rect x="{W-168}" y="{H-44}" width="140" height="26" rx="7" fill="none" stroke="{C["cyan"]}" stroke-opacity=".55"/>'
               + text(W - 98, H - 26.5, "view repository", 12, C["cyan"], "m", anchor="middle"))
    return document(W, H, p["name"], f"{p['name']}: {p['description']} Tech: {', '.join(p['tags'])}.", "\n".join(out))


# ------------------------------------------------------------- footer -----------------
def footer(cfg: dict, st: dict) -> str:
    H = 176
    out = [card(W, H)]
    out.append(text(44, 74, "Let’s build something useful.", 30, C["text"], "s", weight="700", extra='letter-spacing="-0.4"'))
    out.append(text(44, 104, cfg["footer_line"], 14.5, C["text2"], "s"))
    out.append(text(44, 148, cfg["signature"], 18, C["green2"], "m", weight="600")
               + f'<rect class="cur" x="{n1(44 + len(cfg["signature"])*10.9 + 6)}" y="133" width="10" height="19" fill="{C["green"]}"/>')
    # weekly skyline silhouette from real weekly totals
    weeks = []
    d0 = st["start"]
    for i in range(53):
        tot = sum(st["counts"].get(d0 + timedelta(days=i * 7 + j), 0) for j in range(7))
        weeks.append(tot)
    mx = max(weeks) or 1
    bx, base = 500, 150
    for i, v in enumerate(weeks):
        h = 4 + 66 * (v / mx) ** 0.7 if v else 3
        col = C["green"] if v and v == mx else C["cyan"]
        out.append(f'<rect x="{bx + i*6.6:.1f}" y="{n1(base-h)}" width="4.6" height="{n1(h)}" rx="1" fill="{col}" fill-opacity="{.9 if v else .18}"/>')
    out.append(text(bx, 166, "weekly activity, last 12 months", 10.5, C["muted"], "m"))
    return document(W, H, "Footer", f"Let’s build something useful. {cfg['signature']}", "\n".join(out))
