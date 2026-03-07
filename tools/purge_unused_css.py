from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import pathlib
import re
from typing import Iterable


WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[1]


@dataclasses.dataclass(frozen=True)
class Removal:
    selector: str
    classes: tuple[str, ...]
    ids: tuple[str, ...]
    reason: str


_CLASS_RE = re.compile(r"\.([_a-zA-Z]+[\w-]*)")
_ID_RE = re.compile(r"#([_a-zA-Z]+[\w-]*)")


def _strip_css_comments(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)


def _selector_has_type_or_attribute(selector: str) -> bool:
    """Conservatively detect selectors that aren't purely class/id-based.

    If a selector contains a type selector (e.g. `h2`, `a`) or an attribute selector
    (e.g. `[data-x]`), keep it to avoid accidentally removing base or JS-hook styles.
    """

    s = _strip_css_comments(selector)

    if "[" in s and "]" in s:
        return True

    # Remove strings so we don't mis-detect type selectors inside quotes.
    s = re.sub(r"('([^\\']|\\.)*'|\"([^\\\"]|\\.)*\")", "", s)

    # Drop pseudo classes/elements and id/class tokens, leaving behind potential type selectors.
    s = re.sub(r"::?[a-zA-Z_-][\w-]*(\([^)]*\))?", " ", s)
    s = re.sub(r"\.[_a-zA-Z]+[\w-]*", " ", s)
    s = re.sub(r"#[_a-zA-Z]+[\w-]*", " ", s)
    s = s.replace(":root", " ").replace(":host", " ")
    s = s.replace("*", " ")

    return re.search(r"(^|[\s>+~(])([a-zA-Z][\w-]*)", s) is not None


def _split_selector_list(selector_list: str) -> list[str]:
    """Split a selector prelude by commas, ignoring commas in (), [], and strings."""

    parts: list[str] = []
    buf: list[str] = []
    depth_paren = 0
    depth_bracket = 0
    in_string: str | None = None
    i = 0

    while i < len(selector_list):
        ch = selector_list[i]

        if in_string is not None:
            buf.append(ch)
            if ch == "\\":
                if i + 1 < len(selector_list):
                    buf.append(selector_list[i + 1])
                    i += 2
                    continue
            elif ch == in_string:
                in_string = None
            i += 1
            continue

        if ch in {"'", '"'}:
            in_string = ch
            buf.append(ch)
            i += 1
            continue

        if ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren = max(0, depth_paren - 1)
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket = max(0, depth_bracket - 1)

        if ch == "," and depth_paren == 0 and depth_bracket == 0:
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    if buf:
        parts.append("".join(buf).strip())

    return [p for p in parts if p]


def _iter_files(paths: Iterable[pathlib.Path]) -> Iterable[pathlib.Path]:
    for path in paths:
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from (p for p in path.rglob("*") if p.is_file())


def extract_used_tokens(*, template_paths: list[pathlib.Path], js_paths: list[pathlib.Path]) -> tuple[set[str], set[str]]:
    used_classes: set[str] = set()
    used_ids: set[str] = set()

    class_attr_re = re.compile(
        r"\bclass\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
    id_attr_re = re.compile(
        r"\bid\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)

    for path in _iter_files(template_paths):
        if path.suffix.lower() not in {".html", ".jinja", ".j2"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for _quote, value in class_attr_re.findall(text):
            for token in re.split(r"\s+", value.strip()):
                if not token or "{" in token or "}" in token:
                    continue
                used_classes.add(token)
        for _quote, value in id_attr_re.findall(text):
            token = value.strip()
            if token and "{" not in token and "}" not in token:
                used_ids.add(token)

    # JS: look for `.classList.add('foo')` and querySelector strings.
    string_re = re.compile(r"([\"'])(.*?)(?<!\\)\1")

    for path in _iter_files(js_paths):
        if path.suffix.lower() != ".js":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")

        # classList.add/remove/toggle('a', 'b')
        for m in re.finditer(r"\bclassList\.(?:add|remove|toggle)\(([^)]*)\)", text):
            args = m.group(1)
            for q, s in string_re.findall(args):
                for token in re.split(r"\s+", s.strip()):
                    if token:
                        used_classes.add(token)

        # querySelector/querySelectorAll('.foo #bar')
        for m in re.finditer(r"\bquerySelector(All)?\(([^)]*)\)", text):
            args = m.group(2)
            for _q, s in string_re.findall(args):
                used_classes.update(_CLASS_RE.findall(s))
                used_ids.update(_ID_RE.findall(s))

    # Always-keep tokens that are commonly toggled dynamically.
    used_classes.update(
        {
            "show",
            "active",
            "open",
            "collapse",
            "collapsed",
            "collapsing",
            "fade",
            "in",
            "modal-open",
            "current",
            "disabled",
            "focus",
            "hover",
        }
    )

    return used_classes, used_ids


def _scan_next_block(text: str, start: int) -> tuple[int, int, int, int] | None:
    """Return (prelude_start, prelude_end, body_start, body_end_exclusive) for next top-level block.

    Works at the current nesting level (assumes caller passes a segment with balanced braces).
    Skips braces inside strings and comments.
    """

    i = start
    n = len(text)
    in_string: str | None = None
    in_comment = False
    prelude_start: int | None = None

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_comment:
            if ch == "*" and nxt == "/":
                in_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_string is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue

        if ch == "/" and nxt == "*":
            in_comment = True
            i += 2
            continue

        if ch in {"'", '"'}:
            in_string = ch
            i += 1
            continue

        if prelude_start is None and not ch.isspace():
            prelude_start = i

        if ch == "{":
            if prelude_start is None:
                prelude_start = start
            prelude_end = i
            body_start = i + 1

            # Find matching closing brace.
            depth = 1
            j = body_start
            in_string2: str | None = None
            in_comment2 = False

            while j < n:
                c = text[j]
                nn = text[j + 1] if j + 1 < n else ""

                if in_comment2:
                    if c == "*" and nn == "/":
                        in_comment2 = False
                        j += 2
                        continue
                    j += 1
                    continue

                if in_string2 is not None:
                    if c == "\\":
                        j += 2
                        continue
                    if c == in_string2:
                        in_string2 = None
                    j += 1
                    continue

                if c == "/" and nn == "*":
                    in_comment2 = True
                    j += 2
                    continue

                if c in {"'", '"'}:
                    in_string2 = c
                    j += 1
                    continue

                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        body_end_exclusive = j
                        return prelude_start, prelude_end, body_start, body_end_exclusive
                j += 1

            raise ValueError("Unbalanced braces in CSS")

        i += 1

    return None


def _extract_selector_tokens(selector: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    classes = tuple(dict.fromkeys(_CLASS_RE.findall(selector)))
    ids = tuple(dict.fromkeys(_ID_RE.findall(selector)))
    return classes, ids


def _prune_selector_list(*, selector_list: str, used_classes: set[str], used_ids: set[str]) -> tuple[str, list[Removal]]:
    removals: list[Removal] = []
    selectors = _split_selector_list(selector_list)
    kept: list[str] = []

    for sel in selectors:
        raw = sel.strip()
        classes, ids = _extract_selector_tokens(raw)

        if _selector_has_type_or_attribute(raw):
            kept.append(raw)
            continue

        if not classes and not ids:
            kept.append(raw)
            continue

        if any(c in used_classes for c in classes) or any(i in used_ids for i in ids):
            kept.append(raw)
            continue

        removals.append(
            Removal(
                selector=raw,
                classes=classes,
                ids=ids,
                reason="Pure class/id selector not referenced in templates or main JS",
            )
        )

    return ",\n".join(kept), removals


def process_css_segment(*, text: str, used_classes: set[str], used_ids: set[str]) -> tuple[str, list[Removal]]:
    removed: list[Removal] = []

    out_parts: list[str] = []
    cursor = 0

    while True:
        block = _scan_next_block(text, cursor)
        if block is None:
            out_parts.append(text[cursor:])
            break

        prelude_start, prelude_end, body_start, body_end = block
        prelude = text[prelude_start:prelude_end]
        selector = prelude.strip()
        body = text[body_start:body_end]
        block_text = text[prelude_start: body_end + 1]

        # Emit any text between cursor and this block's prelude.
        if prelude_start > cursor:
            out_parts.append(text[cursor:prelude_start])

        if selector.startswith("@"):  # at-rule with a block
            at_name = selector.split(None, 1)[0].lower()
            if at_name in {"@keyframes", "@font-face"}:
                out_parts.append(block_text)
            else:
                new_body, removed_inner = process_css_segment(
                    text=body, used_classes=used_classes, used_ids=used_ids)
                removed.extend(removed_inner)
                # If the body becomes whitespace-only, drop the whole at-rule.
                if new_body.strip() == "":
                    removed.append(
                        Removal(
                            selector=selector,
                            classes=(),
                            ids=(),
                            reason="At-rule body became empty after pruning",
                        )
                    )
                else:
                    out_parts.append(prelude)
                    out_parts.append("{")
                    out_parts.append(new_body)
                    out_parts.append("}")
        else:
            new_selector, removed_selectors = _prune_selector_list(
                selector_list=selector, used_classes=used_classes, used_ids=used_ids
            )
            removed.extend(removed_selectors)
            if new_selector.strip() == "":
                pass
            else:
                out_parts.append(new_selector)
                out_parts.append("{")
                out_parts.append(body)
                out_parts.append("}")

        cursor = body_end + 1

    return "".join(out_parts), removed


def write_report(*, report_path: pathlib.Path, removals: list[Removal]) -> None:
    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines: list[str] = []
    lines.append(f"Unused CSS purge report ({now})")
    lines.append("")
    lines.append(f"Removed rules: {len(removals)}")
    lines.append("")

    for r in removals:
        cls = ", ".join(r.classes) if r.classes else "-"
        ids = ", ".join(r.ids) if r.ids else "-"
        lines.append(f"- {r.selector}")
        lines.append(f"  classes: {cls}")
        lines.append(f"  ids: {ids}")
        lines.append(f"  reason: {r.reason}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--css", default=str(WORKSPACE_ROOT / "static/css/style.css"))
    parser.add_argument(
        "--report", default=str(WORKSPACE_ROOT / "unused-css-report.txt"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes back to the CSS file. If omitted, runs as a dry-run and only writes the report.",
    )
    args = parser.parse_args()

    css_path = pathlib.Path(args.css)
    report_path = pathlib.Path(args.report)

    used_classes, used_ids = extract_used_tokens(
        template_paths=[WORKSPACE_ROOT / "templates"],
        js_paths=[WORKSPACE_ROOT / "static/js/main.js"],
    )

    original = css_path.read_text(encoding="utf-8", errors="ignore")
    new_css, removed = process_css_segment(
        text=original, used_classes=used_classes, used_ids=used_ids)

    if args.apply and new_css != original:
        css_path.write_text(new_css, encoding="utf-8")

    write_report(report_path=report_path, removals=removed)

    print(f"CSS: {css_path}")
    print(f"Report: {report_path}")
    print(f"Removed: {len(removed)}")
    print("Mode: APPLY" if args.apply else "Mode: DRY-RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
