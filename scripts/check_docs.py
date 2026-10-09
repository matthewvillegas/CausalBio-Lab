"""Validate Markdown links and GitHub-style headings against public files."""

from __future__ import annotations

import argparse
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from public_files import ROOT, public_files


def anchors(path: Path) -> set[str]:
    content = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    counts: Counter[str] = Counter()
    result = set(re.findall(r'\bid=["\']([^"\']+)["\']', content))
    for heading in re.findall(r"^#{1,6}\s+(.+)$", content, flags=re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        result.add(f"{slug}-{counts[slug]}" if counts[slug] else slug)
        counts[slug] += 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--external",
        action="store_true",
        help="Also request external links; no accounts or cookies.",
    )
    args = parser.parse_args()
    files = public_files()
    public = {path.resolve() for path in files}
    errors = []
    external = set()
    count = 0
    for path in files:
        if path.suffix != ".md":
            continue
        content = path.read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^\n)]+)\)", content)
        links += re.findall(r"^\[[^\]]+\]:\s*(\S+)", content, flags=re.M)
        for raw in links:
            href = raw.strip().split(' "', 1)[0].strip("<>")
            parsed = urllib.parse.urlsplit(href)
            if parsed.scheme in {"http", "https"}:
                external.add(href)
                continue
            if parsed.scheme == "mailto":
                continue
            count += 1
            target = (
                (path.parent / urllib.parse.unquote(parsed.path)).resolve() if parsed.path else path
            )
            reason = None
            if target.is_dir() and any(item.is_relative_to(target) for item in public):
                if parsed.fragment:
                    reason = "directory link cannot name a document heading"
            elif target not in public:
                reason = "target missing from public file set"
            elif (
                parsed.fragment
                and target.suffix == ".md"
                and urllib.parse.unquote(parsed.fragment) not in anchors(target)
            ):
                reason = "heading anchor missing"
            if reason:
                errors.append(f"{path.relative_to(ROOT).as_posix()}: {href}: {reason}")
    if args.external:
        for url in sorted(external):
            if urllib.parse.urlsplit(url).hostname in {"localhost", "127.0.0.1"}:
                continue
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "CausalBio documentation link check",
                    "Range": "bytes=0-1023",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    print(f"HTTP {response.status}: {url}")
            except (urllib.error.URLError, TimeoutError) as error:
                errors.append(f"External link unverified: {url}: {type(error).__name__}")
    for error in errors:
        print(error)
    print(
        f"Documentation check: {count} local links, {len(external)} external references, {len(errors)} findings."
    )
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
