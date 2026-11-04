# repo-launch checklist: pass criteria and fix recipes

One section per item. Each has **Why** (so you can judge edge cases), **Pass** (what the audit looks for) and **Fix** (how to get there). Commands assume `gh` is authenticated and the working directory is the repo root.

Contents: [1 Demo](#1-demo-gif-at-the-top) · [2 One line](#2-what-it-does-in-one-line) · [3 Install](#3-install-is-one-command) · [4 Live demo](#4-live-demo-link) · [5 License](#5-license) · [6 Topics](#6-repo-topics) · [7 Social preview](#7-social-preview-image) · [8 CI](#8-ci-passes) · [9 Secrets](#9-no-secrets-in-git-history) · [10 Good first issues](#10-good-first-issues) · [11 Contributing](#11-contributing-guide) · [12 Templates](#12-issue-and-pr-templates) · [13 Discussions](#13-discussions) · [14 Release](#14-tagged-release-with-a-changelog) · [15 Show HN](#15-show-hn-draft) · [16 Replies](#16-every-issue-answered-within-a-day)

---

## 1. Demo GIF at the top

**Why.** "Show it, don't tell it." A moving picture of the tool working answers "what is this?" faster than any paragraph, and it is the first thing a visitor sees.

**Pass.** An image, GIF or video in the first ~40 README lines that is not a badge (shields.io, badgen, CI badge).

**Fix.**
- **CLI:** record with [VHS](https://github.com/charmbracelet/vhs). Write `demo.tape` that runs the real happy path (install already done, 2–4 commands, short sleeps), then `vhs demo.tape` writes `demo.gif`. Alternative: `asciinema rec` + `agg demo.cast demo.gif`.
- **Web app / GUI:** record the screen (macOS `Cmd+Shift+5`), trim to 5–15 s, convert:
  ```bash
  ffmpeg -i in.mov -vf "fps=12,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" demo.gif
  ```
- **Library:** a short code snippet plus its output often beats a GIF; a screenshot of the output is fine.
- Keep it small (aim for under ~5 MB) so the README loads fast. Store it in-repo (`docs/demo.gif` or `.github/demo.gif`) and place it right under the title and tagline: `![flux-cli deploying a folder](docs/demo.gif)`.
- Recording needs the tool to really run. If you cannot run it here, write the `.tape` file or the recording steps and hand the last step to the user. Never fake output.

## 2. What it does, in one line

**Why.** The tagline is the sentence people repeat when they share the repo, and the repo description is what GitHub search, topic pages and link previews show.

**Pass.** A plain-text line (not a badge, not a heading) right after the README H1, and a non-empty GitHub repo description.

**Fix.** Write one sentence, ideally under 120 characters: what it does + for whom or how it differs. "Deploy any folder to a live URL in one command." beats "A modern, blazing-fast deployment solution." No buzzwords, no "simply".
```bash
gh repo edit --description "Deploy any folder to a live URL in one command"
```
Use the same line in the package manifest `description` field.

## 3. Install is one command

**Why.** Every extra install step loses people. One copy-paste line that works is what turns a visitor into a user.

**Pass.** The first code block under an Install / Getting started / Quick start heading has one command line (comments and `$` prompts ignored).

**Fix.** Pick the channel the project is already on (or close to): `npx <pkg>`, `npm i -g <pkg>`, `pipx install <pkg>` / `uvx <pkg>`, `brew install <tap>/<pkg>`, `cargo install <crate>`, `go install <module>@latest`, `docker run …`, or a `curl -fsSL … | sh` script for binaries. If the project is not published anywhere, a single wrapper (`./setup.sh` or `make setup`) that does clone-free setup still beats six steps. Publishing to a registry is outward-facing: propose it, do not do it unasked. Keep the long manual path below under "From source". Run the one command in a clean temp directory before claiming it works.

## 4. Live demo link

**Why.** Lets people try it without installing anything; the strongest proof after the GIF.

**Pass.** A README link whose text or URL mentions "demo", "playground" or "try", or a homepage set on the repo.

**Fix.** Use what fits: GitHub Pages for static sites, StackBlitz / CodeSandbox for JS, a Hugging Face Space or Colab for ML, an asciinema recording for CLIs, a hosted instance if one exists. Ask before deploying anything. Then:
```bash
gh repo edit --homepage "https://…"
```
Put the link next to the GIF: `**[Live demo](https://…)**`.

## 5. License

**Why.** No license means default copyright: nobody may legally use, copy or modify the code, so careful users and companies walk away.

**Pass.** A `LICENSE`, `LICENSE.md`, `LICENSE.txt` or `COPYING` file.

**Fix.** Ask which license if the user has not said. MIT is the common default for adoption; Apache-2.0 adds a patent grant; GPL-3.0 keeps derivatives open. Fetch the canonical text instead of writing it from memory:
```bash
gh api licenses/mit --jq .body > LICENSE   # then replace [year] and [fullname]
```
Set the same SPDX id in the manifest (`"license": "MIT"`, `license = "MIT"`).

## 6. Repo topics

**Why.** Topics put the repo on GitHub topic pages and in search filters, where people browse for tools.

**Pass.** At least 3 topics (aim for 5–10; GitHub allows 20).

**Fix.** Lowercase, letters, digits and hyphens, max 50 characters each. Cover language, framework, domain and category (`cli`, `typescript`, `deployment`, `static-site`, `developer-tools`). Prefer topics that already have a GitHub topic page.
```bash
gh repo edit --add-topic cli,typescript,deployment,static-site,developer-tools
```

## 7. Social preview image

**Why.** This image appears on every shared link (Slack, X, Discord, LinkedIn). Without it, GitHub shows a generic card.

**Pass.** `usesCustomOpenGraphImage` is true (GraphQL). The audit checks this.

**Fix.** 1280×640 px (minimum 640×320), PNG or JPG, under 1 MB. Repo name large, the one-line tagline, maybe a small screenshot; keep text away from the edges because some sites crop. Quick ways to make one: an HTML file rendered by headless Chrome (`--screenshot --window-size=1280,640`), or Pillow / ImageMagick. Save it as `.github/social-preview.png`. GitHub has no API for the upload, so hand it over: **Settings → General → Social preview → Edit → Upload an image**.

## 8. CI passes

**Why.** A green check signals the project works and is maintained, and it is what contributors' PRs get judged against.

**Pass.** A workflow in `.github/workflows/` and the latest run on the default branch concluded `success`.

**Fix.** No workflow: add `.github/workflows/ci.yml` that runs the project's real install, lint and test commands on `push` and `pull_request`. Use the current major versions of official actions (`actions/checkout`, `actions/setup-node`, `actions/setup-python`, …). Failing workflow: read the failure and fix the cause, not the check:
```bash
gh run list --branch <default> -L 5
gh run view <run-id> --log-failed
```
Add a status badge under the tagline.

## 9. No secrets in git history

**Why.** Public repos are scraped for keys within minutes of going public. A key deleted in a later commit is still in the history.

**Pass.** No findings from `gitleaks`/`trufflehog` (if installed) or the audit's built-in patterns, and no `.env`, `*.pem`, `id_rsa` and similar files ever committed.

**Fix.**
1. Scan properly if a scanner exists: `gitleaks git -v` (gitleaks ≥ 8.19; older: `gitleaks detect --source . -v`) or `trufflehog git file://. --only-verified`. Review each hit; test fixtures and placeholders are false positives.
2. A real secret is compromised the moment it was pushed anywhere. **Tell the user to revoke and rotate it at the provider first.** Rewriting history does not un-leak a key that forks, clones or caches already hold.
3. Rewrite only after a plain-words yes from the user, because it changes every commit hash and needs a force-push:
   ```bash
   git clone --mirror <remote> ../repo-backup.git           # backup first
   git filter-repo --replace-text replacements.txt          # literal==>REDACTED lines
   git filter-repo --path config/.env --invert-paths        # or drop a whole file
   ```
4. Force-push only after a second confirmation, and tell the user that collaborators must re-clone.
5. Prevent a repeat: add the files to `.gitignore`, commit a `.env.example`, and suggest GitHub secret scanning + push protection (Settings → Code security).

If the repo is still private, this is the cheapest moment to do it.

## 10. Good first issues

**Why.** Newcomers filter by this label. Open, well-described starter issues turn visitors into contributors, and contributors bring stars.

**Pass.** At least 3 open issues labelled `good first issue`.

**Fix.** Find real, small work in the code: `TODO`/`FIXME` comments, missing tests, docs gaps, small flags, platform support. Each issue: what and why, the file(s) to touch (`src/cli.ts:42`), what done looks like, and a rough size. Show the user the drafts, then after a yes:
```bash
gh label create "good first issue" --color 7057ff --description "Good for newcomers" --force
gh label create "help wanted" --color 008672 --description "Extra attention is needed" --force
gh issue create --title "…" --body-file issue.md --label "good first issue"
```

## 11. Contributing guide

**Why.** It answers "how do I help?" and saves you explaining setup in every PR.

**Pass.** `CONTRIBUTING.md` in the root, `.github/` or `docs/`.

**Fix.** Start from [../assets/CONTRIBUTING.md](../assets/CONTRIBUTING.md) and fill it with the project's real commands: fork and clone, install, run tests, branch and commit style, open a PR. Short beats complete. Link it from the README.

## 12. Issue and PR templates

**Why.** Templates get you the version, OS and repro steps on the first message, so you can reply in one round.

**Pass.** At least one file in `.github/ISSUE_TEMPLATE/` (or a legacy `.github/ISSUE_TEMPLATE.md`).

**Fix.** Copy from [../assets/github/](../assets/github/): `ISSUE_TEMPLATE/bug_report.yml`, `ISSUE_TEMPLATE/feature_request.yml`, `ISSUE_TEMPLATE/config.yml` (points questions to Discussions) and `pull_request_template.md`. Adjust the fields to the project (a CLI asks for OS and version; a library asks for runtime version).

## 13. Discussions

**Why.** Gives questions, ideas and show-and-tell a home that is not the issue tracker, and makes the project look alive.

**Pass.** `hasDiscussionsEnabled` is true.

**Fix.**
```bash
gh repo edit --enable-discussions
```
GitHub creates the default categories (Announcements, General, Ideas, Polls, Q&A, Show and tell). Point the `config.yml` contact link at `https://github.com/<owner>/<repo>/discussions`.

## 14. Tagged release with a changelog

**Why.** A release tells people the project is usable now, lets them pin a version, and shows in the repo sidebar. Watchers get notified.

**Pass.** At least one GitHub release and a `CHANGELOG.md` (or `CHANGES.md`, `HISTORY.md`).

**Fix.** Write `CHANGELOG.md` in [Keep a Changelog](https://keepachangelog.com) format from the real git history (`git log --oneline`). Pick a semver version (`v0.1.0` for a first public release unless the project says otherwise) and make the manifest version match. Then, after a yes (tags and releases are public):
```bash
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
gh release create v0.1.0 --title "v0.1.0" --notes-file release-notes.md
```

## 15. Show HN draft

**Why.** Hacker News "Show HN" is where developers look for new tools. A good first post brings the first wave of real users.

**Pass.** Manual. The audit marks it `manual`; it passes once `.launch/show-hn.md` exists and the user has posted.

**Fix.** Write `.launch/show-hn.md` and keep it out of git (`echo .launch/ >> .git/info/exclude`): a launch draft in a public repo looks odd.
- **Title:** `Show HN: <Name> – <the one-line tagline>`. Plain, specific, no hype or superlatives.
- **URL:** the repo or the live demo. Show HN is for things people can try now.
- **First comment** (posted by the user right after submitting): who made it and why, what it does, how it is built, what is rough, and what feedback they want.
- **Rules to repeat to the user:** never ask anyone to upvote (HN detects and penalises it), and stay around for the first hours to answer every comment.
- Posting is the user's step. Never submit it.

## 16. Every issue answered within a day

**Why.** The first reply is the moment a newcomer decides to stay. "Answered in 3h" builds more trust than any badge.

**Pass.** No open issue opened by someone else is older than 24 h with zero comments.

**Fix.** List the ones waiting:
```bash
gh issue list --state open --json number,title,createdAt,author,comments
```
Draft replies when asked, but each reply is posted by the user or after their explicit yes per reply: it speaks for them in public. A first reply can be short ("Thanks, reproduced on macOS, looking into it"). To keep it going: watch the repo (Custom → Issues), bookmark the search `is:issue is:open comments:0`, and offer a daily scheduled check if the user wants one.
