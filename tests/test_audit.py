"""Tests for scripts/audit.py. Run: python3 -m unittest discover -s tests"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("audit", ROOT / "scripts" / "audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def make_repo(files: dict, commits_then_delete: tuple = ()) -> Path:
    d = Path(tempfile.mkdtemp())
    git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=d, check=True)
    for name, body in files.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    subprocess.run(git + ["add", "-A"], cwd=d, check=True)
    subprocess.run(git + ["commit", "-qm", "init"], cwd=d, check=True)
    for name in commits_then_delete:
        subprocess.run(git + ["rm", "-q", name], cwd=d, check=True)
        subprocess.run(git + ["commit", "-qm", f"remove {name}"], cwd=d, check=True)
    return d


def status(report: dict, n: int) -> str:
    return next(c["status"] for c in report["checks"] if c["n"] == n)


GOOD_README = """# flux-cli

Deploy any folder to a live URL with one command.

![flux deploying a folder](docs/demo.gif)

**[Live demo](https://example.com/demo)**

## Install

```bash
npx flux-cli
```
"""


class AuditTests(unittest.TestCase):
    def test_bare_repo_fails_local_items(self):
        r = audit.audit(make_repo({"README.md": "# x\n\n## Install\n\n```\ngit clone x\ncd x\nnpm i\n```\n"}), False)
        for n in (1, 2, 3, 5, 8, 11, 12):
            self.assertEqual(status(r, n), "fail", n)
        self.assertEqual(status(r, 15), "manual")
        self.assertEqual(status(r, 6), "unknown")

    def test_well_prepared_repo_passes_local_items(self):
        r = audit.audit(make_repo({
            "README.md": GOOD_README,
            "LICENSE": "MIT License\n",
            "CONTRIBUTING.md": "how to help\n",
            "CHANGELOG.md": "# Changelog\n",
            ".github/workflows/ci.yml": "name: CI\n",
            ".github/ISSUE_TEMPLATE/bug_report.yml": "name: Bug\n",
        }), False)
        for n in (1, 3, 4, 5, 9, 11, 12):
            self.assertEqual(status(r, n), "pass", n)

    def test_tagline_ignores_code_block_comments_and_logos(self):
        readme = '<p align="center"><img src="logo.svg"></p>\n\n```bash\n# not a title\nalias x=y\n```\n\n# bat\n\nA cat clone with wings.\n'
        self.assertEqual(audit.tagline(readme), "A cat clone with wings.")

    def test_no_tagline_when_next_section_follows_title(self):
        self.assertIsNone(audit.tagline("# x\n\n## Install\n\n```\nnpm i x\n```\n"))

    def test_commented_out_gif_and_logo_are_not_a_demo(self):
        readme = '# x\n\nDoes y.\n\n<!-- ![demo](docs/demo.gif) -->\n<img src="docs/logo.svg">\n'
        self.assertEqual(audit.check_demo(readme)["status"], "fail")

    def test_badges_are_not_a_demo(self):
        readme = "# x\n\n[![CI](https://github.com/a/b/actions/workflows/ci.yml/badge.svg)](x)\n"
        self.assertEqual(audit.check_demo(readme)["status"], "fail")

    def test_suffixed_license_file_counts(self):
        r = audit.audit(make_repo({"README.md": GOOD_README, "LICENSE-MIT": "MIT\n"}), False)
        self.assertEqual(status(r, 5), "pass")

    def test_install_counts_chained_commands(self):
        r = audit.check_install("# x\n\n## Install\n\n```\ngit clone x && cd x && make\n```\n")
        self.assertEqual(r["status"], "fail")

    def test_deleted_secret_still_found_in_history(self):
        d = make_repo({"README.md": GOOD_README, ".env": "KEY=sk-proj-Q7fz2LmN8vR4tY6wX1aB3cD5eF\n"},
                      commits_then_delete=(".env",))
        r = audit.check_secrets(d)
        self.assertEqual(r["status"], "fail")
        self.assertIn(".env", r["evidence"])

    def test_env_files_in_test_dirs_do_not_fail(self):
        d = make_repo({"README.md": GOOD_README, "tests/fixtures/.env": "A=1\n", ".env.example": "A=\n"})
        r = audit.check_secrets(d)
        self.assertEqual(r["status"], "pass")
        self.assertIn("tests/fixtures/.env", r["evidence"])


if __name__ == "__main__":
    unittest.main()
