#!/usr/bin/env python3
"""Read-only launch-readiness audit for an open-source repo (repo-launch skill).

Checks the 16 checklist items using local files, git history and, when the
GitHub CLI is installed and authenticated, the GitHub API. Never writes.

Usage:
    audit.py [REPO_PATH] [--json] [--no-github]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PASS, FAIL, MANUAL, UNKNOWN = "pass", "fail", "manual", "unknown"

LOGO_HINTS = ("logo", "banner", "icon", "header")  # branding images are not a demo
BADGE_HOSTS = ("shields.io", "badgen.net", "badge.fury.io", "codecov.io", "/badge.svg",
               "/badges/", "travis-ci", "circleci.com", "img.shields", "badge")
MEDIA_RE = re.compile(
    r"!\[[^\]]*\]\(([^)\s]+)[^)]*\)|<img[^>]+src=[\"']([^\"']+)|<video[^>]*|<source[^>]+src=[\"']([^\"']+)",
    re.I)
INSTALL_HEADING_RE = re.compile(r"^#{1,4}\s*(install(ation)?|getting started|quick ?start|usage|setup)\b", re.I | re.M)
CODE_BLOCK_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)|<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)

SECRET_PATTERNS = {
    "AWS access key": r"\b(AKIA|ASIA)[0-9A-Z]{16}\b",
    "GitHub token": r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b",
    "OpenAI/Anthropic key": r"\bsk-(ant-|proj-)?[A-Za-z0-9_-]{20,}\b",
    "Slack token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    "Stripe live key": r"\b(sk|rk)_live_[A-Za-z0-9]{20,}\b",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "Private key block": r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY",
}
SECRET_FILE_RE = re.compile(r"(^|/)(\.env(\.[^/]*)?|id_rsa|id_ed25519|.*\.pem|.*\.p12|.*\.pfx|credentials\.json|service-account.*\.json)$")
FIXTURE_DIR_RE = re.compile(r"(^|/)(tests?|spec|fixtures?|testdata|examples?|samples?|__tests__)/", re.I)
SECRET_FILE_OK = re.compile(r"\.env\.(example|sample|template|dist)$")


def run(cmd: list[str], cwd: Path, timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout)
        return p.returncode, p.stdout if p.returncode == 0 else p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def find_file(root: Path, names: list[str], dirs: tuple[str, ...] = ("", ".github", "docs")) -> Path | None:
    for d in dirs:
        base = root / d if d else root
        if not base.is_dir():
            continue
        lower = {p.name.lower(): p for p in base.iterdir() if p.is_file()}
        for n in names:
            if n.lower() in lower:
                return lower[n.lower()]
    return None


class GitHub:
    """Thin wrapper around `gh`; every method returns None when GitHub is unreachable."""

    def __init__(self, root: Path, enabled: bool):
        self.root = root
        self.ok = False
        self.reason = "disabled with --no-github"
        self.repo: dict | None = None
        if not enabled:
            return
        if not shutil.which("gh"):
            self.reason = "gh CLI not installed"
            return
        code, out = run(["gh", "repo", "view", "--json",
                         "nameWithOwner,description,homepageUrl,repositoryTopics,hasDiscussionsEnabled,"
                         "defaultBranchRef,licenseInfo,usesCustomOpenGraphImage,isPrivate,stargazerCount"],
                        root)
        if code != 0:
            self.reason = "gh repo view failed: " + out.strip().splitlines()[-1] if out.strip() else "gh repo view failed"
            return
        self.repo = json.loads(out)
        self.ok = True

    def json(self, args: list[str]):
        if not self.ok:
            return None
        code, out = run(["gh", *args], self.root)
        if code != 0:
            return None
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return None


def result(n: int, item: str, status: str, evidence: str, fix: str = "") -> dict:
    return {"n": n, "item": item, "status": status, "evidence": evidence, "fix": fix}


def readme_info(root: Path) -> tuple[Path | None, str]:
    p = find_file(root, ["README.md", "README.markdown", "README.rst", "README.txt", "README"])
    return p, (p.read_text(errors="replace") if p else "")


def check_demo(readme: str) -> dict:
    head = re.sub(r"<!--.*?-->", "", "\n".join(readme.splitlines()[:40]), flags=re.S)  # commented-out images don't count
    media = []
    for m in MEDIA_RE.finditer(head):
        src = next((g for g in m.groups() if g), m.group(0))
        if not any(b in src.lower() for b in BADGE_HOSTS + LOGO_HINTS):
            media.append(src)
    if media:
        return result(1, "Demo GIF at the top", PASS, f"media in first 40 lines: {media[0]}")
    return result(1, "Demo GIF at the top", FAIL, "no non-badge image/GIF/video in the first 40 README lines",
                  "record a GIF (VHS for CLIs) and place it under the tagline")


def tagline(readme: str) -> str | None:
    lines = readme.splitlines()
    fenced, i = False, None
    for k, l in enumerate(lines):  # first H1 outside code fences
        if l.strip().startswith("```"):
            fenced = not fenced
        elif not fenced and (l.startswith("# ") or re.match(r"^\s*<h1", l, re.I)):
            i = k
            break
    if i is None:  # README opens with a logo, no H1: scan from the top instead
        i = -1
    in_fence = False
    for l in lines[i + 1:i + 15]:
        s = l.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if s.startswith("#"):  # next section reached: no tagline under the H1
            return None
        if not s or s.startswith(("![", "[![", "<img", "<p align", "</p", "<a ", "<div", "</div", "---", "<picture",
                                  "</picture", "<source")):
            continue
        s = re.sub(r"<[^>]+>", "", s).strip("> *_")
        if s:
            return s
    return None


def check_one_line(readme: str, gh: GitHub) -> dict:
    t = tagline(readme)
    desc = (gh.repo or {}).get("description") if gh.ok else None
    parts = [f"README tagline: {t!r}" if t else "no tagline after the README H1"]
    if gh.ok:
        parts.append(f"repo description: {desc!r}" if desc else "repo description empty")
    ok_readme = bool(t) and len(t) <= 160
    if not gh.ok:
        status = PASS if ok_readme else FAIL
        parts.append(f"repo description unknown ({gh.reason})")
        if ok_readme:
            status = UNKNOWN
    else:
        status = PASS if (ok_readme and desc) else FAIL
    return result(2, "What it does, in one line", status, "; ".join(parts),
                  "one sentence under the H1 + gh repo edit --description")


def check_install(readme: str) -> dict:
    m = INSTALL_HEADING_RE.search(readme)
    if not m:
        return result(3, "Install is one command", FAIL, "no Install / Getting started / Quick start heading",
                      "add an Install section with one copy-paste command")
    block = CODE_BLOCK_RE.search(readme, m.end())
    if not block:
        return result(3, "Install is one command", FAIL, f"'{m.group(0).strip()}' has no code block")
    cmds = [l.strip().lstrip("$> ").strip() for l in block.group(1).splitlines()]
    cmds = [c for c in cmds if c and not c.startswith(("#", "//"))]
    joined = []
    for c in cmds:  # fold backslash continuations into one command
        if joined and joined[-1].endswith("\\"):
            joined[-1] = joined[-1][:-1] + " " + c
        else:
            joined.append(c)
    chained = sum(c.count("&&") for c in joined)
    n = len(joined) + chained
    status = PASS if n == 1 else FAIL
    return result(3, "Install is one command", status,
                  f"first install code block has {n} command(s): {joined[:6]}",
                  "" if status == PASS else "collapse to npx/pipx/uvx/brew/curl|sh or a single setup script")


def check_live_demo(readme: str, gh: GitHub) -> dict:
    for m in LINK_RE.finditer(readme):
        text = (m.group(1) or m.group(4) or "").lower()
        url = (m.group(2) or m.group(3) or "")
        if url.startswith("http") and re.search(r"demo|playground|try it|try online|live", text + " " + url.lower()) \
                and not any(b in url.lower() for b in BADGE_HOSTS):
            return result(4, "Live demo link", PASS, f"README link: {url}")
    home = (gh.repo or {}).get("homepageUrl") if gh.ok else None
    if home:
        return result(4, "Live demo link", PASS, f"repo homepage: {home}")
    return result(4, "Live demo link", FAIL if gh.ok else UNKNOWN,
                  "no demo/playground link in README" + ("" if gh.ok else f"; homepage unknown ({gh.reason})"),
                  "link a hosted demo and gh repo edit --homepage")


def check_license(root: Path, gh: GitHub) -> dict:
    p = next((f for f in sorted(root.iterdir())
              if f.is_file() and re.match(r"^(licen[cs]e|copying|unlicense)([-._].*)?$", f.name, re.I)), None)
    spdx = ((gh.repo or {}).get("licenseInfo") or {}).get("spdxId") if gh.ok else None
    if p:
        return result(5, "License", PASS, f"{p.name}" + (f" (GitHub detects {spdx})" if spdx else ""))
    return result(5, "License", FAIL, "no LICENSE file in repo root — no license = nobody may use it",
                  "gh api licenses/mit --jq .body > LICENSE")


def check_topics(gh: GitHub) -> dict:
    if not gh.ok:
        return result(6, "Repo topics", UNKNOWN, gh.reason)
    topics = [t["name"] for t in (gh.repo.get("repositoryTopics") or [])]
    return result(6, "Repo topics", PASS if len(topics) >= 3 else FAIL,
                  f"{len(topics)} topic(s): {topics}", "" if len(topics) >= 3 else "gh repo edit --add-topic a,b,c,d,e")


def check_social(gh: GitHub) -> dict:
    if not gh.ok:
        return result(7, "Social preview image", UNKNOWN, gh.reason)
    custom = gh.repo.get("usesCustomOpenGraphImage")
    return result(7, "Social preview image", PASS if custom else FAIL,
                  "custom social preview set" if custom else "using GitHub's generic card",
                  "" if custom else "1280x640 PNG < 1 MB, upload in Settings > General > Social preview")


def check_ci(root: Path, gh: GitHub) -> dict:
    wf = root / ".github" / "workflows"
    files = sorted(p.name for p in wf.glob("*.y*ml")) if wf.is_dir() else []
    if not files:
        return result(8, "CI passes", FAIL, "no .github/workflows/*.yml", "add ci.yml running the real lint + test")
    if not gh.ok:
        return result(8, "CI passes", UNKNOWN, f"workflows {files}; run status unknown ({gh.reason})")
    branch = (gh.repo.get("defaultBranchRef") or {}).get("name") or "main"
    runs = gh.json(["run", "list", "--branch", branch, "-L", "10", "--json", "conclusion,status,workflowName,createdAt"])
    if not runs:
        return result(8, "CI passes", FAIL, f"workflows {files} but no runs on {branch}",
                      "push to the default branch or trigger the workflow")
    latest: dict[str, dict] = {}
    for r in runs:  # newest first; keep the latest run per workflow
        latest.setdefault(r["workflowName"], r)
    bad = {k: (v.get("conclusion") or v.get("status")) for k, v in latest.items() if v.get("conclusion") != "success"}
    if bad:
        return result(8, "CI passes", FAIL, f"latest runs on {branch} not green: {bad}",
                      "gh run view <id> --log-failed, fix the cause")
    return result(8, "CI passes", PASS, f"latest run of each workflow on {branch} succeeded: {sorted(latest)}")


def check_secrets(root: Path) -> dict:
    code, _ = run(["git", "rev-parse", "--git-dir"], root)
    if code != 0:
        return result(9, "No secrets in git history", UNKNOWN, "not a git repository")
    findings: list[str] = []
    fixtures: list[str] = []
    tool = None
    if shutil.which("gitleaks"):
        tool = "gitleaks"
        rc, out = run(["gitleaks", "git", "--no-banner", "--report-format", "json", "--report-path", "-", "."], root, 300)
        if "unknown command" in out.lower() or "Error: unknown" in out:
            rc, out = run(["gitleaks", "detect", "--no-banner", "--source", ".", "--report-format", "json",
                           "--report-path", "/dev/stdout"], root, 300)
        try:
            data = json.loads(out[out.index("["):]) if "[" in out else []
            findings += [f"gitleaks: {f.get('RuleID')} in {f.get('File')} @ {str(f.get('Commit'))[:8]}" for f in data]
        except ValueError:
            if rc not in (0,):
                findings.append("gitleaks reported leaks (could not parse report; run it by hand)")
    else:
        tool = "built-in patterns"
        rc, log = run(["git", "log", "--all", "-p", "--no-color", "-U0", "--no-ext-diff"], root, 300)
        if rc == 0:
            hits: dict[str, str] = {}  # pattern name -> first file it was added in
            current = ""
            for line in log.splitlines():
                if line.startswith("+++ "):
                    current = line[6:] if line.startswith("+++ b/") else ""
                    continue
                if not line.startswith("+"):
                    continue  # only lines a commit added
                for name, pat in SECRET_PATTERNS.items():
                    if re.search(pat, line):
                        if FIXTURE_DIR_RE.search(current):
                            fixtures.append(f"{name} in {current}")
                        else:
                            hits.setdefault(name, current)
            findings += [f"{name}: in {path or 'history'}" for name, path in hits.items()]
    rc, names = run(["git", "log", "--all", "--diff-filter=A", "--name-only", "--format="], root, 120)
    if rc == 0:
        for f in sorted(set(names.split())):
            if SECRET_FILE_RE.search(f) and not SECRET_FILE_OK.search(f):
                if FIXTURE_DIR_RE.search(f):
                    fixtures.append(f)
                else:
                    findings.append(f"sensitive file committed at some point: {f}")
    if findings:
        return result(9, "No secrets in git history", FAIL, f"[{tool}] " + "; ".join(findings[:8]),
                      "review hits; rotate real secrets FIRST, then git filter-repo (destructive, confirm)")
    fixtures = sorted(set(fixtures))
    note = f"; {len(fixtures)} key-like value(s)/file(s) under test/example dirs, glance at them: {fixtures[:3]}" if fixtures else ""
    return result(9, "No secrets in git history", PASS, f"[{tool}] no findings" + note)


def check_gfi(gh: GitHub) -> dict:
    if not gh.ok:
        return result(10, "Good first issues", UNKNOWN, gh.reason)
    issues = gh.json(["issue", "list", "--state", "open", "--label", "good first issue", "-L", "50", "--json", "number"])
    n = len(issues or [])
    return result(10, "Good first issues", PASS if n >= 3 else FAIL, f"{n} open 'good first issue' issue(s)",
                  "" if n >= 3 else "draft 3-5 real starter issues from TODOs / missing tests / docs gaps")


def check_contributing(root: Path) -> dict:
    p = find_file(root, ["CONTRIBUTING.md", "CONTRIBUTING.rst", "CONTRIBUTING"])
    return result(11, "Contributing guide", PASS if p else FAIL,
                  str(p.relative_to(root)) if p else "no CONTRIBUTING.md (root, .github/, docs/)",
                  "" if p else "start from assets/CONTRIBUTING.md")


def check_templates(root: Path) -> dict:
    d = root / ".github" / "ISSUE_TEMPLATE"
    files = sorted(p.name for p in d.iterdir() if p.is_file()) if d.is_dir() else []
    legacy = find_file(root, ["ISSUE_TEMPLATE.md"], ("", ".github", "docs"))
    pr = find_file(root, ["pull_request_template.md", "PULL_REQUEST_TEMPLATE.md"], ("", ".github", "docs"))
    if files or legacy:
        ev = f"issue templates: {files or [legacy.name]}" + ("; PR template present" if pr else "; no PR template")
        return result(12, "Issue templates", PASS, ev)
    return result(12, "Issue templates", FAIL, "no .github/ISSUE_TEMPLATE/", "copy assets/github/")


def check_discussions(gh: GitHub) -> dict:
    if not gh.ok:
        return result(13, "Discussions turned on", UNKNOWN, gh.reason)
    on = gh.repo.get("hasDiscussionsEnabled")
    return result(13, "Discussions turned on", PASS if on else FAIL, "enabled" if on else "disabled",
                  "" if on else "gh repo edit --enable-discussions")


def check_release(root: Path, gh: GitHub) -> dict:
    cl = find_file(root, ["CHANGELOG.md", "CHANGELOG", "CHANGES.md", "HISTORY.md"], ("", "docs"))
    rc, tags = run(["git", "tag", "--list"], root)
    tag_list = tags.split() if rc == 0 else []
    ev = [f"changelog: {cl.name}" if cl else "no CHANGELOG.md", f"{len(tag_list)} git tag(s)"]
    if not gh.ok:
        ev.append(f"GitHub releases unknown ({gh.reason})")
        return result(14, "Tagged release with a changelog", FAIL if not cl else UNKNOWN, "; ".join(ev))
    rels = gh.json(["release", "list", "-L", "5", "--json", "tagName,isDraft,publishedAt"]) or []
    rels = [r for r in rels if not r.get("isDraft")]
    ev.append(f"{len(rels)} published release(s)" + (f", latest {rels[0]['tagName']}" if rels else ""))
    ok = bool(cl) and bool(rels)
    return result(14, "Tagged release with a changelog", PASS if ok else FAIL, "; ".join(ev),
                  "" if ok else "CHANGELOG.md + git tag + gh release create")


def check_show_hn(root: Path) -> dict:
    draft = root / ".launch" / "show-hn.md"
    return result(15, "Show HN post drafted", MANUAL,
                  "draft at .launch/show-hn.md; posting is the user's step" if draft.exists() else "no draft yet",
                  "" if draft.exists() else "write .launch/show-hn.md (title, URL, first comment)")


def _comment_author(comment) -> tuple[str, bool]:
    """Return (login, is_bot) for one issue comment, in any shape gh gives."""
    author = (comment or {}).get("author") if isinstance(comment, dict) else None
    if isinstance(author, str):
        login = author
        is_bot = login.lower().endswith("[bot]")
    elif isinstance(author, dict):
        login = str(author.get("login") or "")
        is_bot = bool(author.get("is_bot")) or author.get("type") == "Bot" or author.get("__typename") == "Bot"
        is_bot = is_bot or login.lower().endswith("[bot]")
    else:
        login, is_bot = "", False
    return login.lower(), is_bot


def is_a_reply(comment, issue_author: str, owner: str = "") -> bool:
    """True only for a human reply to an issue.

    Bot comments do not count as a reply, and neither does a comment
    from the issue's own author: a bot-only thread is still waiting
    for a first human answer.
    """
    login, is_bot = _comment_author(comment)
    return bool(login) and not is_bot and login != issue_author.lower() and login != ""


def check_replies(gh: GitHub) -> dict:
    """Check item 16: every issue answered within a day.

    An issue counts as answered only when it has a human reply: a
    comment from a bot, or from the issue's own author, does not
    count, so an issue whose comments are bot-only is still waiting.
    """
    if not gh.ok:
        return result(16, "Every issue answered within a day", UNKNOWN, gh.reason)
    owner = gh.repo["nameWithOwner"].split("/")[0].lower()
    issues = gh.json(["issue", "list", "--state", "open", "-L", "200",
                      "--json", "number,title,createdAt,author,comments"]) or []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    waiting = []
    for i in issues:
        created = datetime.fromisoformat(i["createdAt"].replace("Z", "+00:00"))
        author = ((i.get("author") or {}).get("login") or "").lower()
        is_bot = (i.get("author") or {}).get("is_bot") or author.endswith("[bot]")
        comments = i.get("comments") or []
        replied = any(is_a_reply(c, author, owner) for c in comments) if isinstance(comments, list) else len(comments) > 0
        if created < cutoff and author != owner and not is_bot and not replied:
            waiting.append(f"#{i['number']} ({(datetime.now(timezone.utc) - created).days}d)")
    if waiting:
        return result(16, "Every issue answered within a day", FAIL,
                      f"{len(waiting)} issue(s) >24h with no reply: {waiting[:10]}", "reply (user posts), set a triage routine")
    return result(16, "Every issue answered within a day", PASS,
                  f"{len(issues)} open issue(s); none waiting >24h for a first reply")


def audit(root: Path, use_github: bool) -> dict:
    gh = GitHub(root, use_github)
    _, readme = readme_info(root)
    checks = [
        check_demo(readme), check_one_line(readme, gh), check_install(readme), check_live_demo(readme, gh),
        check_license(root, gh), check_topics(gh), check_social(gh), check_ci(root, gh), check_secrets(root),
        check_gfi(gh), check_contributing(root), check_templates(root), check_discussions(gh),
        check_release(root, gh), check_show_hn(root), check_replies(gh),
    ]
    return {
        "repo": (gh.repo or {}).get("nameWithOwner") or str(root),
        "github": "ok" if gh.ok else gh.reason,
        "stars": (gh.repo or {}).get("stargazerCount"),
        "private": (gh.repo or {}).get("isPrivate"),
        "score": sum(c["status"] == PASS for c in checks),
        "total": len(checks),
        "checks": checks,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    ap.add_argument("--no-github", action="store_true", help="skip all GitHub API checks")
    a = ap.parse_args()
    root = Path(a.path).resolve()
    code, top = run(["git", "rev-parse", "--show-toplevel"], root)
    if code == 0:
        root = Path(top.strip())
    report = audit(root, not a.no_github)
    if a.json:
        print(json.dumps(report, indent=2))
        return 0
    mark = {PASS: "✓", FAIL: "✗", MANUAL: "…", UNKNOWN: "?"}
    print(f"repo-launch audit: {report['repo']}   {report['score']} / {report['total']} passing"
          + (f"   ★ {report['stars']}" if report["stars"] is not None else ""))
    if report["github"] != "ok":
        print(f"GitHub checks skipped: {report['github']}")
    if report["private"]:
        print("note: repo is PRIVATE — best moment to fix item 9 (history) before going public")
    print()
    for c in report["checks"]:
        print(f" {mark[c['status']]} {c['n']:>2}. {c['item']:<34} {c['status']:<8} {c['evidence']}")
        if c["fix"] and c["status"] != PASS:
            print(f"{'':>8}fix: {c['fix']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
