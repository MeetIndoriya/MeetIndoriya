# Setup guide

This repository **is** your GitHub profile: GitHub shows `README.md` of the repo named exactly like your username (`MeetIndoriya/MeetIndoriya`) on your profile page.

## 1. Put the files in place

Everything in this folder goes into the root of `MeetIndoriya/MeetIndoriya`, keeping the paths:

```text
MeetIndoriya/
├── README.md                       <- profile page (replaces your current one)
├── SETUP.md                        <- this file (optional, you can delete it)
├── profile.config.json             <- all your text, links, stack and project copy
├── .gitignore
├── assets/                         <- generated SVGs (already included, refreshed by the Action)
│   ├── hero.svg  metrics.svg  contribution-city.svg  activity.svg
│   ├── terminal.svg  stack.svg  footer.svg
│   └── projects/*.svg
├── scripts/
│   ├── build_profile.py            <- entry point
│   ├── data.py  city.py  panels.py  kit.py
│   ├── check_assets.py             <- safety check used by the workflow
│   ├── icons.json                  <- brand icon paths (so no icon CDN is needed)
│   └── fixtures/preview.json       <- sample data for offline testing
└── .github/workflows/update-profile.yml
```

**Step 1.** Download and unzip the project.
**Step 2.** Open your `MeetIndoriya/MeetIndoriya` repository on github.com → **Add file → Upload files**, drag in *everything* (including the hidden `.github` folder; if the browser skips it, use Step 2b).
**Step 2b (if `.github` was skipped).** On GitHub: **Add file → Create new file**, type `.github/workflows/update-profile.yml` as the name (the slashes create folders) and paste the workflow file's content.
**Step 3.** Commit to `main`. Your profile already shows the new design, because the generated SVGs are included.

## 2. Let the Action write to the repo

**Step 4.** Repo → **Settings → Actions → General → Workflow permissions**. Choose **Read and write permissions**, Save. (The workflow also requests `contents: write` itself; this setting just must not forbid it.)

**Step 5.** Repo → **Actions** tab → **Update profile dashboard** → **Run workflow**. Wait about 30 seconds and open the run log. Its first lines tell you which data source was used:

```text
user=MeetIndoriya source=public-commits total=... active_days=...
```

From now on it refreshes every 12 hours, and whenever you edit `profile.config.json` or `scripts/`.

## 3. Secrets: do you need a token?

**Not to get started.** The built-in `GITHUB_TOKEN` is created automatically for every run; you add nothing.

Your profile currently **hides its activity** (the profile page shows "@MeetIndoriya's activity is private") so GitHub's contribution graph reports 0 to anyone but you. The generator detects this and falls back to counting **your commits in your public repositories**. The city then says `source: commits in public repositories`. That is accurate, but it excludes pull requests, issues, reviews and private work.

If you want the city to match the official graph:

| | |
|---|---|
| **Token type** | Personal access token (classic) |
| **Scope** | `read:user` only (nothing else) |
| **Create at** | GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic) |
| **Expiry** | Your choice (90 days is reasonable; set a reminder) |
| **Add it as** | Repo → Settings → Secrets and variables → Actions → **New repository secret** → name `PROFILE_TOKEN` |
| **Also** | In your profile settings, enable **Include private contributions on my profile** if you want private work counted. |

Why a PAT is needed here: `GITHUB_TOKEN` only represents the Action's bot, so it sees your profile like any stranger does. If the run log still says `source=public-commits` after adding the secret, the token is not being accepted or the graph is empty for that token; the fallback keeps the page working either way.

Never paste a token into any file. Only the Actions secret store should hold it.

## 4. Make it yours

* Text, links, tech stack, "now building", chosen projects: `profile.config.json`.
* Add a **description** to each repository on GitHub (the ⚙ next to "About"); descriptions in `profile.config.json → projects.overrides` win over them, so delete an override once the GitHub description is good.
* Real photo instead of the pixel monogram: put `avatar.png` in the repo and set `"avatar_path": "avatar.png"` in the config (it is embedded in the SVG, because images in a README SVG cannot load external URLs).
* Live demo links: set the repository's **Website** field on GitHub; the generator then adds a "Live demo" link under that project's card automatically. Nothing is invented.

## 5. Test locally (optional)

```bash
python scripts/build_profile.py --fixture scripts/fixtures/preview.json   # offline, sample data
python scripts/check_assets.py                                            # same checks the Action runs
GITHUB_TOKEN=ghp_xxx python scripts/build_profile.py                      # live data
```

Python 3.10+ and nothing to install (standard library only).

## 6. Verification checklist

| Check | How |
|---|---|
| README renders | Open `github.com/MeetIndoriya` in a private window; all images load |
| SVGs load | `check_assets.py` rejects invalid XML, scripts, external references, missing `viewBox` |
| City reflects real data | The numbers under the city equal the run log's `total=` and `active_days=` |
| Action succeeds | Actions tab shows a green run; second run says "No changes to commit" when nothing changed |
| Mobile | View your profile in the GitHub mobile app. Headline, numbers and project names are legible; fine print is small (see notes) |
| Links | The four links under the footer match your real profiles |
| No fake stats | Metrics come only from the GitHub API; unknown values show `—` |
