#!/usr/bin/env python3
"""Regenerate every dynamic asset of the profile.

    python scripts/build_profile.py                       # live data (needs GITHUB_TOKEN for good rate limits)
    python scripts/build_profile.py --fixture scripts/fixtures/preview.json   # offline preview

Environment:
    GITHUB_TOKEN   built-in Actions token (public data, repo commits)
    PROFILE_TOKEN  optional classic PAT with `read:user`: unlocks the official contribution graph when the
                   profile hides activity, and private contributions if enabled on the profile.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import city  # noqa: E402
import data as D  # noqa: E402
import panels  # noqa: E402
from kit import esc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WEB_LANGS = {"JavaScript", "TypeScript", "HTML", "CSS", "Python", "Vue", "PHP", "Java", "C#"}


def select_projects(cfg: dict, data: dict) -> tuple[list[dict], list[dict]]:
    pc = cfg["projects"]
    repos = [r for r in data["repos"] if not r["fork"] and not r["archived"] and r["name"] not in pc["exclude"]]
    by_name = {r["name"]: r for r in repos}
    chosen = [by_name[n] for n in pc["pin"] if n in by_name]

    def score(r: dict) -> float:
        s = 2 if r["language"] in WEB_LANGS else 0
        s += 2 if r["homepage"] else 0
        s += min(r["stars"], 5) + 0.5 * min(r["forks"], 4)
        s += 1 if r["description"] else 0
        if r["pushed_at"]:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))).days
            s += 3 if age < 90 else 2 if age < 180 else 1 if age < 365 else 0
        return s

    rest = sorted((r for r in repos if r not in chosen), key=score, reverse=True)
    while len(chosen) < pc["max"] and rest:
        chosen.append(rest.pop(0))
    return chosen[: pc["max"]], rest


def decorate(r: dict, cfg: dict) -> dict:
    ov = cfg["projects"]["overrides"].get(r["name"], {})
    lang = r["language"]
    return {
        **r,
        "description": ov.get("description") or r["description"] or (f"Repository written mainly in {lang}." if lang else "Repository on GitHub."),
        "tags": ov.get("tags") or ([lang] if lang else []) + list(r["topics"][:4]),
    }


def projects_block(sel: list[dict], others: list[dict]) -> str:
    out = []
    for p in sel:
        alt = f"{p['name']}: {p['description']} Tech: {', '.join(p['tags'])}. Open the repository on GitHub."
        out.append(f'<a href="{p["html_url"]}"><img src="assets/projects/{p["name"]}.svg" width="100%" alt="{esc(alt)}"></a>')
        if p.get("homepage"):
            out.append(f'<p align="right"><a href="{esc(p["homepage"])}">Live demo of {esc(p["name"])}</a></p>')
    if others:
        links = " · ".join(f'<a href="{r["html_url"]}">{esc(r["name"])}</a>' for r in others)
        out.append(f"<sub>Coursework and practice repositories: {links}</sub>")
    return "\n\n".join(out)


def patch_readme(readme: Path, block: str) -> bool:
    text = readme.read_text(encoding="utf-8")
    new, n = re.subn(r"(<!--START:projects-->).*?(<!--END:projects-->)", lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}", text, flags=re.S)
    if n == 0:
        print("[warn] README.md has no <!--START:projects--> / <!--END:projects--> markers; skipped.")
        return False
    if new != text:
        readme.write_text(new, encoding="utf-8")
        return True
    return False


def validate(path: Path) -> int:
    s = path.read_text(encoding="utf-8")
    ET.fromstring(s)  # well-formed
    low = s.lower()
    for bad in ("<script", "<foreignobject", "javascript:", "onload=", "onclick="):
        assert bad not in low, f"{path.name}: forbidden content {bad}"
    for m in re.finditer(r'(?:href|src)="([^"#][^"]*)"', s):
        assert m.group(1).startswith("data:"), f"{path.name}: external reference {m.group(1)[:60]}"
    return len(s.encode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture")
    ap.add_argument("--out", default=str(ROOT / "assets"))
    ap.add_argument("--no-readme", action="store_true")
    args = ap.parse_args()

    cfg = json.loads((ROOT / "profile.config.json").read_text(encoding="utf-8"))
    user = os.environ.get("GH_USER") or cfg["username"]
    if args.fixture:
        data = D.load_fixture(args.fixture)
    else:
        try:
            data = D.collect(user, os.environ.get("GITHUB_TOKEN"), os.environ.get("PROFILE_TOKEN"))
        except D.GitHubError as e:
            print(f"[error] {e}\nKeeping previously generated assets.")
            return 1
    st = D.compute_stats(data)

    sel, rest = select_projects(cfg, data)
    sel = [decorate(r, cfg) for r in sel]
    out = Path(args.out)
    (out / "projects").mkdir(parents=True, exist_ok=True)

    files = {
        "hero.svg": panels.hero(cfg),
        "metrics.svg": panels.metrics(cfg, data, st),
        "contribution-city.svg": city.render(data, st, user),
        "activity.svg": panels.activity(cfg, data, st),
        "terminal.svg": panels.terminal(cfg, data),
        "stack.svg": panels.stack(cfg),
        "footer.svg": panels.footer(cfg, st),
    }
    for p in sel:
        files[f"projects/{p['name']}.svg"] = panels.project_card(p, cfg["projects"]["show_zero_stats"])

    changed = 0
    for rel, svg in files.items():
        path = out / rel
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != svg:
            path.write_text(svg, encoding="utf-8")
            changed += 1
    keep = {Path(r).name for r in files if r.startswith("projects/")}
    for stale in (out / "projects").glob("*.svg"):
        if stale.name not in keep:
            stale.unlink()
            changed += 1

    sizes = {rel: validate(out / rel) for rel in files}
    readme_changed = False
    if not args.no_readme:
        readme_changed = patch_readme(ROOT / "README.md", projects_block(sel, rest))

    src = data["calendar"]["source"]
    print(f"user={user} source={src} total={st['total']} active_days={st['active_days']} "
          f"longest_streak={st['longest_streak']} repos={st['repo_count']} stars={st['stars']}")
    print("projects:", ", ".join(p["name"] for p in sel))
    print("svg sizes (KB):", {Path(k).name: round(v / 1024, 1) for k, v in sizes.items()}, "total", round(sum(sizes.values()) / 1024, 1))
    print(f"files changed: {changed}  readme changed: {readme_changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
