# Contributing to repo-launch

Thanks for helping. A sharper check, a better fix recipe, or a typo fix are all welcome.

## Quick start

1. Fork and clone: `git clone https://github.com/<you>/repo-launch && cd repo-launch`
2. Run the tests: `python3 -m unittest discover -s tests`
3. Try the audit on any repo: `python3 scripts/audit.py path/to/repo`

No dependencies to install: the audit uses only the Python 3.9+ standard library, git, and optionally `gh`.

## To try your changes in Claude Code

Point Claude Code at your clone by symlinking it: `ln -s "$PWD" ~/.claude/skills/repo-launch` (move any existing install aside first), then run `/repo-launch` in a test repo.

## Where things live

- `SKILL.md`: the workflow Claude follows. Keep it short; detail goes in `references/checklist.md`.
- `references/checklist.md`: per-item why / pass criteria / fix recipe.
- `scripts/audit.py`: the read-only audit. Every heuristic change needs a test in `tests/test_audit.py`, ideally from a real repo it got wrong.

## Pull requests

- One topic per PR; describe what changed and why, and link the issue (`Fixes #12`).
- CI must pass. A maintainer usually replies within a day.

## Code of conduct

Be kind and assume good intent.
