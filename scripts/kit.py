"""Shared design tokens and SVG helpers.

Everything here is plain string building (stdlib only) so the GitHub Action needs no
`pip install` step. All output is self-contained SVG: no scripts, no external requests,
no web fonts (GitHub renders README SVGs inside <img>, which blocks all of those).
"""
from __future__ import annotations

from html import escape

# --- Design tokens -----------------------------------------------------------------
# Deep-navy surfaces, one GitHub green as the "signal" colour, cyan for structure,
# violet/yellow only as rare accents.
C = dict(
    bg="#060a10", surface="#0a111a", surface2="#0f1824", road="#0a111a",
    border="#1b2735", border2="#27384c",
    text="#e8eef5", text2="#b4c0cf", muted="#7a889a",
    green="#3fb950", green2="#56d364", cyan="#22d3ee", blue="#3b82f6",
    violet="#8b5cf6", yellow="#e3b341", red="#f85149",
)
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,'Helvetica Neue',Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'JetBrains Mono','Cascadia Code',Menlo,Consolas,'Liberation Mono',monospace"

W = 880  # shared base width. Every panel uses it so images line up and scale together.

LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Python": "#3572A5", "C#": "#178600",
    "Java": "#b07219", "HTML": "#e34c26", "CSS": "#663399", "Jupyter Notebook": "#DA5B0B",
    "C++": "#f34b7d", "C": "#8a8a8a", "PHP": "#4F5D95", "Go": "#00ADD8", "Shell": "#89e051",
    "SQL": "#e38c00", "Dart": "#00B4AB", "Kotlin": "#A97BFF", "Vue": "#41b883",
}


def esc(s) -> str:
    return escape(str(s), quote=True)


def n1(v: float) -> str:
    """Compact number formatting: 1 decimal max, no trailing zeros (keeps SVG small)."""
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def pts(*p) -> str:
    return "M" + "L".join(f"{n1(x)} {n1(y)}" for x, y in p) + "Z"


def text(x, y, s, size=14, fill=None, cls="s", weight=None, anchor=None, extra="") -> str:
    a = [f'x="{n1(x)}"', f'y="{n1(y)}"', f'class="{cls}"', f'font-size="{size}"',
         f'fill="{fill or C["text"]}"']
    if weight:
        a.append(f'font-weight="{weight}"')
    if anchor:
        a.append(f'text-anchor="{anchor}"')
    if extra:
        a.append(extra)
    return f'<text {" ".join(a)}>{esc(s)}</text>'


def wrap(s: str, max_chars: int, max_lines: int) -> list[str]:
    """Greedy word wrap with ellipsis. Widths are approximated by character count."""
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;:")[: max_chars - 1] + "…"
    return lines


def truncate(s: str, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


BASE_CSS = f"""
.s{{font-family:{SANS}}}.m{{font-family:{MONO}}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
@keyframes pulse{{0%{{opacity:.9;transform:scale(1)}}70%{{opacity:0;transform:scale(3.4)}}100%{{opacity:0;transform:scale(3.4)}}}}
@keyframes flick{{0%,100%{{opacity:1}}45%{{opacity:.25}}60%{{opacity:1}}}}
.cur{{animation:blink 1.1s steps(1) infinite}}
.pulse{{transform-box:fill-box;transform-origin:center;animation:pulse 2.4s ease-out infinite}}
.fl{{animation:flick 5s ease-in-out infinite}}
@media (prefers-reduced-motion:reduce){{.cur,.pulse,.fl{{animation:none}}}}
"""


def document(w: int, h: int, title: str, desc: str, body: str, css: str = "", defs: str = "") -> str:
    """Wrap a body in a complete, accessible SVG document with the shared defs."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-labelledby="t d">\n'
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>\n'
        f'<defs>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b131d"/>'
        f'<stop offset="1" stop-color="{C["bg"]}"/></linearGradient>'
        f'<radialGradient id="glow" cx="0" cy="0" r="1"><stop offset="0" stop-color="{C["cyan"]}" stop-opacity=".16"/>'
        f'<stop offset="1" stop-color="{C["cyan"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="glow2" cx="1" cy="1" r="1"><stop offset="0" stop-color="{C["green"]}" stop-opacity=".12"/>'
        f'<stop offset="1" stop-color="{C["green"]}" stop-opacity="0"/></radialGradient>'
        f'<pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse">'
        f'<path d="M22 0H0V22" fill="none" stroke="#fff" stroke-opacity=".028" stroke-width="1"/></pattern>'
        f'{defs}</defs>\n'
        f'<style>{BASE_CSS}{css}</style>\n{body}\n</svg>\n'
    )


def card(w: int, h: int, tab: str | None = None, right: str | None = None, dots: bool = False) -> str:
    """Rounded 'window' surface with an optional slim title bar (tab label, right label)."""
    out = [
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="14" fill="url(#bg)" stroke="{C["border"]}"/>',
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="14" fill="url(#grid)"/>',
        f'<ellipse cx="{int(w*0.12)}" cy="0" rx="{int(w*0.45)}" ry="{int(h*0.5)}" fill="url(#glow)"/>',
        f'<ellipse cx="{int(w*0.95)}" cy="{h}" rx="{int(w*0.35)}" ry="{int(h*0.45)}" fill="url(#glow2)"/>',
    ]
    if tab is not None:
        out.append(f'<path d="M1 40.5H{w-1}" stroke="{C["border"]}"/>')
        x = 24
        if dots:
            for i, col in enumerate(("#ff5f57", "#febc2e", "#28c840")):
                out.append(f'<circle cx="{24+i*18}" cy="20.5" r="5" fill="{col}" fill-opacity=".72"/>')
            x = 90
        out.append(text(x, 25, tab, 12.5, C["text2"], "m"))
        if right:
            out.append(text(w - 24, 25, right, 12.5, C["muted"], "m", anchor="end"))
    return "\n".join(out)


def relative_date(iso: str | None) -> str:
    """Absolute short date ('30 Sep 2026'). Absolute dates keep generated files stable day-to-day,
    so the workflow only commits when real data changes."""
    if not iso:
        return "—"
    from datetime import datetime

    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return f"{d.day} {d.strftime('%b %Y')}"
