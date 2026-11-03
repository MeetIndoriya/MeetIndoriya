"""GitHub data layer (stdlib only).

Data sources, in order of preference for the contribution calendar:
  1. GraphQL contributionCalendar  -> matches the official graph; includes PRs/issues/reviews.
                                      With PROFILE_TOKEN it can include private contributions.
  2. REST commits in public repos  -> used automatically when (1) reports zero, e.g. when the
                                      profile hides its activity. Commits only; labelled as such.

Nothing here invents numbers. If a request fails after retries the script exits non-zero and
the workflow keeps the previously committed assets.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone

API = "https://api.github.com"
UA = "profile-dashboard-generator"


class GitHubError(RuntimeError):
    pass


def _request(url: str, token: str | None, body: dict | None = None, retries: int = 3):
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r), r.headers
        except urllib.error.HTTPError as e:
            if e.code in (500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise GitHubError(f"{e.code} {e.reason} for {url}: {e.read()[:200]!r}") from e
        except urllib.error.URLError as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise GitHubError(f"network error for {url}: {e}") from e
    raise GitHubError("unreachable")


def rest(path: str, token: str | None):
    return _request(API + path, token)[0]


def graphql(query: str, variables: dict, token: str):
    res, _ = _request(f"{API}/graphql", token, {"query": query, "variables": variables})
    if "errors" in res:
        raise GitHubError(f"GraphQL: {res['errors']}")
    return res["data"]


# --- Window helpers ----------------------------------------------------------------
def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def window(today: date, days: int = 365) -> tuple[date, date]:
    return today - timedelta(days=days - 1), today


# --- Fetchers ----------------------------------------------------------------------
def fetch_user(login: str, token: str | None) -> dict:
    u = rest(f"/users/{login}", token)
    return {k: u.get(k) for k in ("login", "name", "bio", "location", "blog", "followers",
                                  "following", "public_repos", "created_at")}


def fetch_repos(login: str, token: str | None) -> list[dict]:
    out, page = [], 1
    while True:
        batch = rest(f"/users/{login}/repos?per_page=100&type=owner&sort=pushed&page={page}", token)
        for r in batch:
            out.append({
                "name": r["name"], "description": r.get("description"), "language": r.get("language"),
                "stars": r["stargazers_count"], "forks": r["forks_count"], "pushed_at": r.get("pushed_at"),
                "homepage": r.get("homepage") or None, "html_url": r["html_url"],
                "topics": r.get("topics", []), "fork": r["fork"], "archived": r["archived"],
            })
        if len(batch) < 100:
            return out
        page += 1


def calendar_graphql(login: str, start: date, end: date, token: str) -> dict[str, int]:
    q = """query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){contributionsCollection(from:$from,to:$to){
        contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
    d = graphql(q, {"login": login, "from": f"{start}T00:00:00Z", "to": f"{end}T23:59:59Z"}, token)
    weeks = d["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {x["date"]: x["contributionCount"] for w in weeks for x in w["contributionDays"] if x["contributionCount"]}


def commits_rest(login: str, repos: list[dict], start: date, token: str | None) -> tuple[dict[str, int], list[dict]]:
    """Commits authored by `login` in their own public, non-fork repos since `start`."""
    days: Counter = Counter()
    recent: list[dict] = []
    for r in repos:
        if r["fork"]:
            continue
        page = 1
        while page <= 10:
            path = (f"/repos/{login}/{r['name']}/commits?author={urllib.parse.quote(login)}"
                    f"&since={start}T00:00:00Z&per_page=100&page={page}")
            try:
                batch = rest(path, token)
            except GitHubError as e:
                if " 409 " in f" {e} ":  # empty repository
                    break
                raise
            for c in batch:
                when = c["commit"]["author"]["date"]
                days[when[:10]] += 1
                recent.append({"repo": r["name"], "message": c["commit"]["message"].splitlines()[0][:90], "date": when})
            if len(batch) < 100:
                break
            page += 1
    recent.sort(key=lambda c: c["date"], reverse=True)
    return dict(days), recent


def recent_commits_light(login: str, repos: list[dict], token: str | None, n: int = 8) -> list[dict]:
    """Newest commits across the most recently pushed repos (for the terminal 'git log')."""
    recent: list[dict] = []
    for r in sorted((r for r in repos if not r["fork"]), key=lambda r: r["pushed_at"] or "", reverse=True)[:5]:
        try:
            for c in rest(f"/repos/{login}/{r['name']}/commits?author={urllib.parse.quote(login)}&per_page=5", token):
                recent.append({"repo": r["name"], "message": c["commit"]["message"].splitlines()[0][:90],
                               "date": c["commit"]["author"]["date"]})
        except GitHubError:
            continue
    recent.sort(key=lambda c: c["date"], reverse=True)
    return recent[:n]


def collect(login: str, token: str | None, profile_token: str | None) -> dict:
    today = today_utc()
    start, end = window(today)
    user = fetch_user(login, profile_token or token)
    repos = fetch_repos(login, profile_token or token)

    source, days, recent = "graphql", {}, []
    gql_token = profile_token or token
    if gql_token:
        try:
            days = calendar_graphql(login, start, end, gql_token)
        except GitHubError as e:
            print(f"[warn] GraphQL calendar failed: {e}")
    if not days:
        print("[info] Contribution graph returned 0 (profile activity may be hidden). "
              "Falling back to commits in public repositories.")
        days, recent = commits_rest(login, repos, start, token or profile_token)
        source = "public-commits"
    if not recent:
        recent = recent_commits_light(login, repos, token or profile_token)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user": user, "repos": repos,
        "calendar": {"source": source, "from": str(start), "to": str(end), "days": days},
        "recent_commits": recent[:8],
    }


def load_fixture(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- Derived statistics ------------------------------------------------------------
def compute_stats(data: dict, today: date | None = None) -> dict:
    cal = data["calendar"]
    end = date.fromisoformat(cal["to"])
    start = date.fromisoformat(cal["from"])
    today = today or end
    counts = {date.fromisoformat(k): v for k, v in cal["days"].items()}
    span = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    series = [(d, counts.get(d, 0)) for d in span]

    total = sum(v for _, v in series)
    active = [d for d, v in series if v > 0]
    best = max(series, key=lambda x: x[1]) if series else (start, 0)

    longest, run, run_start, best_run = 0, 0, None, (None, None)
    for d, v in series:
        if v > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > longest:
                longest, best_run = run, (run_start, d)
        else:
            run = 0
    # current streak: walk back from today; today may still be empty without breaking it
    cur, probe = 0, today
    if counts.get(probe, 0) == 0:
        probe -= timedelta(days=1)
    while counts.get(probe, 0) > 0:
        cur += 1
        probe -= timedelta(days=1)

    months: list[tuple[str, int]] = []
    y, m = end.year, end.month
    for _ in range(12):
        months.append((f"{y}-{m:02d}", 0))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    mt = dict(months)
    for d, v in series:
        k = f"{d.year}-{d.month:02d}"
        if k in mt:
            mt[k] += v
    weekday = [0] * 7  # Sunday-first, like GitHub
    for d, v in series:
        weekday[(d.weekday() + 1) % 7] += v

    repos = [r for r in data["repos"] if not r["fork"]]
    return {
        "total": total, "active_days": len(active), "span_days": len(series),
        "best_day": best, "longest_streak": longest, "longest_range": best_run, "current_streak": cur,
        "months": list(mt.items()), "weekday": weekday,
        "stars": sum(r["stars"] for r in repos), "forks": sum(r["forks"] for r in repos),
        "repo_count": data["user"].get("public_repos") if data["user"].get("public_repos") is not None else len(repos),
        "languages": Counter(r["language"] for r in repos if r["language"]),
        "start": start, "end": end, "counts": counts,
    }
