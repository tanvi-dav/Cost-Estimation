"""
utils.py
========
Small, dependency-free helpers shared by the CLI, the AI module and the web
layer. Keeping these here avoids duplicated code (DRY) and isolates all the
"talking to the terminal" logic from the calculation logic.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from constants import DEFAULT_CURRENCY


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def banner(title: str) -> str:
    """Return a framed title block for console output."""
    line = "=" * max(28, len(title) + 4)
    return f"{line}\n  {title}\n{line}"


def money(amount: float, currency: str = DEFAULT_CURRENCY) -> str:
    """Format a number as currency, e.g. 2430000 -> '£2,430,000'."""
    return f"{currency}{amount:,.0f}"


def pct(value: float) -> str:
    """Format a 0-100 number as a percentage string."""
    return f"{value:.0f}%"


# ---------------------------------------------------------------------------
# JSON parsing (LLMs sometimes wrap JSON in ``` fences or prose)
# ---------------------------------------------------------------------------
def safe_json_parse(raw: str) -> Optional[dict]:
    """
    Best-effort extraction of a JSON object from an LLM response.

    Strips Markdown code fences and any leading/trailing prose, then attempts
    to parse the first {...} block found. Returns None on failure rather than
    raising, so callers can fall back gracefully.
    """
    if not raw:
        return None

    cleaned = raw.strip()
    # Remove ```json ... ``` or ``` ... ``` fences.
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    # Try a direct parse first.
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fall back to grabbing the outermost brace-delimited block.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# Interactive input helpers (used only by the CLI, never by the web layer)
# ---------------------------------------------------------------------------
def ask_choice(prompt: str, options: list[str], default_index: int = 0) -> int:
    """
    Display a numbered list and return the zero-based index the user picks.

    Pressing Enter accepts ``default_index``. Re-prompts on invalid input.
    """
    print(f"\n{prompt}")
    for i, option in enumerate(options, start=1):
        print(f"  {i}. {option}")
    while True:
        raw = input(f"Choice [{default_index + 1}]: ").strip()
        if raw == "":
            return default_index
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print("  Please enter a number from the list.")


def ask_float(prompt: str, minimum: float = 0.0) -> float:
    """Prompt repeatedly until the user enters a valid number >= minimum."""
    while True:
        raw = input(f"{prompt}: ").strip()
        try:
            value = float(raw)
            if value < minimum:
                print(f"  Value must be at least {minimum}.")
                continue
            return value
        except ValueError:
            print("  Please enter a valid number.")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Yes/No prompt. Enter accepts the default."""
    hint = "Y/n" if default else "y/N"
    raw = input(f"{prompt} ({hint}): ").strip().lower()
    if raw == "":
        return default
    return raw.startswith("y")


def read_transcript() -> str:
    """
    Let the user supply a transcript either by file path or by pasting text.
    Returns the transcript content as a single string.
    """
    mode = ask_choice(
        "How would you like to provide the transcript?",
        ["Load from a text file", "Paste text directly"],
    )
    if mode == 0:
        path = input("Path to transcript file: ").strip().strip('"')
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            print(f"  Could not read file ({exc}). Falling back to paste mode.")
    print("Paste the transcript. Finish with an empty line containing only 'END':")
    lines: list[str] = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)
