#!/usr/bin/env python3
"""Lightweight accessibility sanity checks.

This is NOT a full WCAG audit. It catches common regressions that frequently
cause WCAG/Lighthouse/axe failures:
- icon-only links missing accessible names
- missing alt attributes
- aria-labelledby targets missing
- duplicate IDs

Usage:
  python3 tools/a11y_sanity_check.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates"


@dataclass(frozen=True)
class Issue:
    file: Path
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_duplicate_ids(html: str) -> set[str]:
    ids = re.findall(r"\bid\s*=\s*\"([^\"]+)\"", html)
    dups = {id_ for id_ in ids if ids.count(id_) > 1}
    return dups


def find_missing_aria_labelledby_targets(html: str) -> set[str]:
    aria = re.findall(r"aria-labelledby\s*=\s*\"([^\"]+)\"", html)
    ids = set(re.findall(r"\bid\s*=\s*\"([^\"]+)\"", html))
    return {a for a in aria if a not in ids}


def img_missing_alt_tags(html: str) -> list[str]:
    tags = re.findall(r"<img\b[^>]*>", html, flags=re.I)
    missing = [t for t in tags if re.search(r"\balt\s*=", t, flags=re.I) is None]
    return missing


def icon_only_links_missing_name(html: str) -> int:
    """Count <a> links with no text content that appear to be icon-only.

    Heuristic: anchor content contains only whitespace and (svg|i) tags,
    and anchor lacks aria-label/title.
    """

    # Normalize whitespace for matching.
    pattern = re.compile(
        r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>",
        flags=re.I | re.S,
    )
    count = 0
    for m in pattern.finditer(html):
        attrs = m.group("attrs")
        body = m.group("body")

        # Skip anchors that clearly have an accessible name.
        if re.search(r"\baria-label\s*=", attrs, flags=re.I):
            continue
        if re.search(r"\btitle\s*=", attrs, flags=re.I):
            continue

        # Strip tags, keep text.
        text = re.sub(r"<[^>]+>", "", body)
        if text.strip():
            continue

        # If it contains an icon tag, treat it as icon-only.
        if re.search(r"<\s*(svg|i)\b", body, flags=re.I):
            count += 1

    return count


def main() -> int:
    issues: list[Issue] = []

    for path in sorted(TEMPLATE_ROOT.rglob("*.html")):
        html = read_text(path)

        for tag in img_missing_alt_tags(html):
            issues.append(Issue(path, f"<img> missing alt: {tag[:120].strip()}"))

        missing = find_missing_aria_labelledby_targets(html)
        for target in sorted(missing):
            issues.append(Issue(path, f"aria-labelledby target missing: {target}"))

        dups = find_duplicate_ids(html)
        for id_ in sorted(dups):
            issues.append(Issue(path, f"duplicate id: {id_}"))

        icon_only = icon_only_links_missing_name(html)
        if icon_only:
            issues.append(Issue(path, f"icon-only <a> missing accessible name (heuristic count): {icon_only}"))

    if not issues:
        print("OK: no issues found")
        return 0

    print(f"Found {len(issues)} potential issues:\n")
    for issue in issues:
        rel = issue.file.relative_to(Path(__file__).resolve().parents[1])
        print(f"- {rel}: {issue.message}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
