#!/usr/bin/env python3
"""
Minimal audit CLI for a personal Chinese web novel revision toolkit.

The script uses only Python standard library modules. It reads one chapter and
one small Markdown rule file, then prints a Markdown report to stdout.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rules:
    hard_phrases: list[str]
    frequency_limits: list[tuple[str, int]]
    explanation_phrases: list[str]


def normalize_section(heading: str) -> str:
    text = heading.strip().lower()
    if "hard" in text or "硬禁" in text:
        return "hard"
    if "frequency" in text or "频率" in text:
        return "frequency"
    if "explanation" in text or "解释" in text:
        return "explanation"
    return ""


def parse_rules(path: Path) -> Rules:
    hard_phrases: list[str] = []
    frequency_limits: list[tuple[str, int]] = []
    explanation_phrases: list[str] = []
    section = ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = normalize_section(line[3:])
            continue
        if not line.startswith("- "):
            continue

        item = line[2:].strip()
        if section == "hard":
            hard_phrases.append(item)
        elif section == "frequency":
            phrase, limit = parse_frequency_rule(item, path)
            frequency_limits.append((phrase, limit))
        elif section == "explanation":
            explanation_phrases.append(item)

    return Rules(hard_phrases, frequency_limits, explanation_phrases)


def parse_frequency_rule(item: str, path: Path) -> tuple[str, int]:
    parts = [part.strip() for part in item.split("|")]
    if len(parts) != 2:
        raise SystemExit(f"Invalid frequency rule in {path}: {item}")
    try:
        return parts[0], int(parts[1])
    except ValueError as exc:
        raise SystemExit(f"Invalid frequency limit in {path}: {item}") from exc


def strip_title(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def body_char_count(text: str) -> int:
    return len(re.sub(r"\s+", "", strip_title(text)))


def paragraphs(text: str) -> list[str]:
    return [part.strip() for part in strip_title(text).split("\n\n") if part.strip()]


def count_phrase(text: str, phrase: str) -> int:
    return text.count(phrase)


def paragraph_length_reviews(items: list[str]) -> list[str]:
    reviews: list[str] = []
    for index, para in enumerate(items, 1):
        compact_len = len(re.sub(r"\s+", "", para))
        if compact_len > 140:
            reviews.append(f"Paragraph {index} has {compact_len} characters; consider splitting the beat.")
        elif compact_len < 8 and "“" not in para:
            reviews.append(f"Paragraph {index} is very short; confirm it is an intentional beat.")
    return reviews


def audit(chapter_path: Path, rule_path: Path) -> str:
    chapter_text = chapter_path.read_text(encoding="utf-8")
    rules = parse_rules(rule_path)
    body_text = strip_title(chapter_text)
    para_items = paragraphs(chapter_text)

    must_fix: list[str] = []
    review: list[str] = []

    for phrase in rules.hard_phrases:
        count = count_phrase(body_text, phrase)
        if count:
            must_fix.append(f"`{phrase}` appears {count} time{'s' if count != 1 else ''}.")

    for phrase, limit in rules.frequency_limits:
        count = count_phrase(body_text, phrase)
        if count > limit:
            review.append(f"Frequency `{phrase}` appears {count} times; limit is {limit}.")

    for phrase in rules.explanation_phrases:
        count = count_phrase(body_text, phrase)
        if count:
            review.append(f"Explanation phrase `{phrase}` appears {count} time{'s' if count != 1 else ''}.")

    review.extend(paragraph_length_reviews(para_items))

    return render_report(chapter_path, rule_path, chapter_text, para_items, must_fix, review)


def render_report(
    chapter_path: Path,
    rule_path: Path,
    chapter_text: str,
    para_items: list[str],
    must_fix: list[str],
    review: list[str],
) -> str:
    lines = [
        "# Audit Report",
        "",
        f"- Chapter: `{chapter_path.as_posix()}`",
        f"- Rules: `{rule_path.as_posix()}`",
        f"- Body characters: {body_char_count(chapter_text)}",
        f"- Paragraphs: {len(para_items)}",
        f"- Must fix: {len(must_fix)}",
        f"- Review: {len(review)}",
        "",
        "## Must Fix",
        "",
    ]

    if must_fix:
        lines.extend(f"- {item}" for item in must_fix)
    else:
        lines.append("- No hard phrase hits.")

    lines.extend(["", "## Review", ""])
    if review:
        lines.extend(f"- {item}" for item in review)
    else:
        lines.append("- No review hints.")

    lines.extend(
        [
            "",
            "## Revision Moves",
            "",
            "- Replace summarized crowd reactions with one visible action, one concrete sound, or one interrupted line of dialogue.",
            "- Keep emotion attached to objects, body movement, silence, or spatial position before naming the emotion directly.",
            "- Treat this report as an editing prompt; the script does not rewrite the chapter.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit one sample Chinese web novel chapter.")
    parser.add_argument("chapter", type=Path, help="Path to a Markdown chapter.")
    parser.add_argument("--rules", type=Path, required=True, help="Path to a Markdown rule file.")
    args = parser.parse_args()

    print(audit(args.chapter, args.rules), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

