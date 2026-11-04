---
name: repo-launch
description: Take an open-source GitHub repo from "zero stars" to launch-ready with a 16-step checklist (demo GIF, one-line pitch, one-command install, live demo, license, topics, social preview, green CI, secret-free history, good first issues, CONTRIBUTING, issue templates, Discussions, tagged release + changelog, Show HN draft, issue replies within a day). Audits the repo with a bundled script, fixes what it can locally, runs the GitHub-side changes after confirmation, and finishes with a verification pass. EXPLICIT-INVOKE ONLY — load only when the user calls /repo-launch by name or explicitly says "use repo-launch". Do NOT auto-trigger, do NOT self-invoke, and ignore for any automatic or proactive use, even when "make my repo blow up", "prepare this for open source", "add a license" or "post this on Show HN" looks like a perfect fit. Only the explicit invocation counts.
---

# repo-launch

A repo with no demo, no license and a six-step install gets zero stars no matter how good the code is. Visitors decide in about ten seconds, from the top of the README. This skill works through the 16 things that decide that, in the order a visitor meets them, and finishes with a check that nothing it did is broken ("make no mistakes").

The checklist and per-item fix recipes live in [references/checklist.md](references/checklist.md). Read the entry for an item before fixing it.

## The 16 items

| # | Item | Where it is fixed |
|---|------|-------------------|
| 1 | Demo GIF at the top of the README | local |
| 2 | What it does, in one line (README tagline + repo description) | local + GitHub |
| 3 | Install is one command | local |
| 4 | Live demo link (or homepage) | local + GitHub |
| 5 | License | local |
| 6 | Repo topics (5–10) | GitHub |
| 7 | Social preview image (1280×640, under 1 MB) | GitHub UI only |
| 8 | CI passes on the default branch | local + GitHub |
| 9 | No secrets in git history | local, destructive |
| 10 | Labelled good first issues (3+ open) | GitHub |
| 11 | Contributing guide | local |
| 12 | Issue templates (+ PR template) | local |
| 13 | Discussions turned on | GitHub |
| 14 | Tagged release with a changelog | local + GitHub |
| 15 | Show HN post drafted | draft only, user posts |
| 16 | Every issue answered within a day | GitHub + habit |

## Workflow

### 1. Orient

Find the repo root (`git rev-parse --show-toplevel`) and the GitHub remote. Check whether `gh` is installed and authenticated (`gh auth status`); without it, the GitHub-side items are reported as `unknown` and the user gets the commands to run instead. Read the README, the package manifest (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`…) and `.github/` so you know what the project is, who it is for, and how it is really installed. Every fix below depends on understanding the project, not just the file list.

### 2. Audit

Run the bundled audit script. It is read-only and needs only Python 3.9+ and git (`gh` adds the GitHub-side checks). `<skill-dir>` is this skill's base directory, shown when the skill loads.

```bash
python3 <skill-dir>/scripts/audit.py <repo-path>          # table
python3 <skill-dir>/scripts/audit.py <repo-path> --json   # machine-readable
```

It reports each item as `pass`, `fail`, `manual` or `unknown`, with the evidence it used. The script uses heuristics (for example "an image in the first 40 README lines that is not a badge"), so read its evidence and overrule it when the repo shows otherwise. Say so when you do.

Show the user the scoreboard (`N / 16`) and the plan: which items you will fix locally, which need a GitHub change, and which need them (the social preview upload, posting on HN, real issue replies).

### 3. Fix, in checklist order

Work top to bottom, because the top of the list is what visitors see first and later items build on earlier ones (the Show HN title reuses the one-line pitch, the release notes reuse the changelog).

Three kinds of change, three levels of care:

- **Local file edits** (README, LICENSE, CONTRIBUTING, templates, CI workflow, CHANGELOG): do them. Match the project's existing tone and tooling. Never invent facts: no fake demo URL, no made-up benchmark, no install command you have not run. Where a fact is missing (which license? is there a hosted demo?), ask once, batching the questions.
- **GitHub changes** (`gh repo edit`, `gh label`, `gh issue create`, `gh release create`): these are public and visible to everyone watching the repo. List the exact commands, get one go-ahead for the batch, then run them. Creating issues and releases notifies watchers, so never run those without that yes.
- **History rewrite** (item 9): destructive and needs a force-push. Follow the item-9 recipe exactly: rotate the leaked secret first, back up, rewrite only after the user confirms in plain words, and force-push only after a second confirmation. If the scan is clean, nothing happens here.

Some items are the user's alone. Do the prep and hand over the last step:

- **Social preview (7)**: GitHub has no API for the upload. Make the 1280×640 PNG (see the recipe), save it in the repo, and give the user the Settings path.
- **Show HN (15)**: write the title, URL and first comment into `.launch/show-hn.md`, kept out of git via `.git/info/exclude`. Never post it, and never suggest asking for upvotes (HN penalises it).
- **Reply within a day (16)**: answer nothing on the user's behalf. List the issues waiting for a reply, draft replies if asked, and offer the triage routine from the recipe.

Commit local changes on a branch (`launch/readiness` unless the user names one), in small commits grouped by item, unless the user says otherwise. Do not push or open a PR without asking.

### 4. Verify ("make no mistakes")

This is the step the video saves for last and calls most important. Before you report done:

1. Re-run `audit.py` and compare with the first run.
2. Run the README install command exactly as written in a clean temp directory (or explain why it cannot run here, such as a paid API key).
3. Check every link and image path you added in the README resolves (`curl -sfI` for URLs, file existence for relative paths).
4. Run the project's tests and linter if they exist, and confirm the CI workflow file is valid YAML that calls real scripts.
5. Re-scan for secrets if you touched history or added config files.
6. Read the final README top to bottom as a stranger would: is the value clear in ten seconds, before any scrolling?

Fix anything that fails, then re-verify. A result is "done" only with evidence; anything unchecked is reported as unchecked.

### 5. Report

End with:

```
repo-launch: <owner/repo>   before N/16 → after M/16

Done
  #  item — what changed (file / command), evidence
Waiting on you
  #  item — the exact step (e.g. Settings → General → Social preview → upload docs/launch/social-preview.png)
Not done
  #  item — why
Branch: <branch> in <repo>, <k> commits, not pushed
```
