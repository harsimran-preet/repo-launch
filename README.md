# repo-launch

A Claude Code skill that takes your open-source repo from zero stars to launch-ready, in 16 steps.

![The repo-launch audit on a zero-star repo, then again after the skill's local fixes](docs/demo.gif)

## Install

```bash
git clone https://github.com/harsimran-preet/repo-launch ~/.claude/skills/repo-launch
```

That's all. Update later with `git -C ~/.claude/skills/repo-launch pull`. To install it for one project only, clone it into that project's `.claude/skills/repo-launch` instead.

## Use

Open Claude Code in the repo you want to launch and type:

```
/repo-launch
```

The skill only runs when you call it by name. Here's what it does:

1. Audits the repo against the checklist and shows a score out of 16.
2. Makes the local fixes on a `launch/readiness` branch, in small commits grouped by item.
3. Lists the public GitHub changes (topics, Discussions, labels, issues, release) and runs them after one go-ahead from you.
4. Verifies everything it did: re-runs the audit, runs your install command in a clean folder, checks every link, runs your tests.

You can also give it narrower instructions: `/repo-launch just audit, don't change anything` or `/repo-launch I'm posting on Show HN tomorrow`.

## The 16 steps

| # | Step | How the skill handles it |
|---|------|--------------------------|
| 1 | Demo GIF at the top of the README | Records it (VHS for CLIs) or writes the recording script |
| 2 | Say what it does in one line | Writes the README tagline and the repo description |
| 3 | Install in one command | Collapses the install steps and tests the command in a clean folder |
| 4 | Link a live demo | Links an existing demo. It never invents a URL. |
| 5 | Add a license | Uses the canonical text from GitHub's license API |
| 6 | Set repo topics | Runs `gh repo edit --add-topic` |
| 7 | Social preview image | Makes a 1280×640 PNG. You upload it, because GitHub has no API for this. |
| 8 | Make CI pass | Adds a workflow with your real test commands, or fixes the failing one |
| 9 | No secrets in git history | Scans history; rotate first, rewrite only after you confirm |
| 10 | Label good first issues | Drafts real issues from TODOs, missing tests and docs gaps |
| 11 | Contributing guide | Writes it with your real setup and test commands |
| 12 | Issue templates | Adds bug and feature forms, a PR template, and points questions to Discussions |
| 13 | Turn on Discussions | Runs `gh repo edit --enable-discussions` |
| 14 | Tag a release with a changelog | Writes a Keep a Changelog file, then tags and runs `gh release create` |
| 15 | Post it on Show HN | Writes the title and first comment. You post it. |
| 16 | Answer every issue within a day | Lists issues waiting for a reply and drafts answers. You post them. |

## What it won't do without you

- **Public GitHub changes** (topics, issues, releases) wait for your go-ahead, because they notify watchers.
- **History rewrites** get two confirmations, one before the rewrite and one before the force-push. You rotate the leaked key first, and the skill makes a backup before touching anything.
- **Posts** happen only on your account and only by you. It never submits to Hacker News and never replies to issues for you. Anything it can't confirm, such as a demo URL, a benchmark or an install command it hasn't run, stays out of your README.

## Audit without Claude

The audit is a plain Python script with no dependencies. It needs Python 3.9+, git, and optionally the [GitHub CLI](https://cli.github.com) for the GitHub-side checks. It never writes anything.

```bash
python3 ~/.claude/skills/repo-launch/scripts/audit.py path/to/repo          # table
python3 ~/.claude/skills/repo-launch/scripts/audit.py path/to/repo --json   # for CI or scripts
```

It uses [gitleaks](https://github.com/gitleaks/gitleaks) for the secrets scan if it's installed, and built-in patterns if not.

## How it was tested

`tests/` covers the audit heuristics, including cases that went wrong on real repos: a "title" that was actually a comment inside a code block, `LICENSE-MIT`, a commented-out GIF, and `.env` test fixtures.

The skill was also run through Anthropic's skill-creator eval loop on 3 scenarios, one run each, against plain Claude Code on the same prompts. The skill passed 30 of 30 checks and plain Claude Code passed 25. It costs more: about 2.3× the time and 27% more tokens, mostly for the verification pass.

## Layout

```
SKILL.md                 the workflow Claude follows
references/checklist.md  why, pass criteria and fix recipe for each of the 16 steps
scripts/audit.py         the read-only audit
assets/                  CONTRIBUTING and GitHub issue/PR templates
tests/                   unit tests for the audit
```

## Contributing

Ideas and fixes are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md), or pick an issue labelled [good first issue](https://github.com/harsimran-preet/repo-launch/labels/good%20first%20issue).

## Credits

The 16-step checklist comes from a short Instagram reel by builditlikerahul. This skill turns it into something Claude Code can run.

## License

[MIT](LICENSE)
