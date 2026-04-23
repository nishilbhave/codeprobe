#!/usr/bin/env python3
"""Render the codeprobe audit dashboard with ANSI color to the terminal.

Reads a JSON payload on stdin and prints a colored dashboard to stdout that
mirrors the visual palette of assets/sample-output.svg. Falls back to plain
text when the terminal does not support color, when NO_COLOR is set, or when
stdout is not a TTY (so piped output stays clean).

Expected JSON payload:
{
  "project_name": "Growth Engine",
  "overall_score": 55,
  "categories": [{"name": "Architecture", "score": 91}, ...],  # 9 entries
  "stats": {
    "files": 391, "total_loc": 64146,
    "backend_files": 170, "backend_loc": 20987,
    "frontend_files": 221, "frontend_loc": 43239,
    "largest_file": "...", "largest_loc": 1979,
    "test_files": 29, "test_files_total": 391, "test_ratio_pct": 7.4,
    "comment_ratio_pct": 1.1
  },
  "hot_spots": [{"file": "...", "categories": ["SOLID", "..."]}],  # up to 3
  "command_label": "/codeprobe audit ."  # optional, used in chrome line
}

Any missing optional field is skipped gracefully.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


# Palette matches assets/sample-output.svg
GREEN = (74, 222, 128)    # #4ade80 — Healthy
YELLOW = (234, 179, 8)    # #eab308 — Needs Attention
RED = (248, 113, 113)     # #f87171 — Critical
TEXT = (203, 213, 225)    # #cbd5e1 — body
DIM = (100, 116, 139)     # #64748b — secondary
TRACK = (30, 41, 59)      # #1e293b — bar track / dividers


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False
    # Force color when the caller opts in (FORCE_COLOR) or when running inside
    # Claude Code, whose Bash tool captures stdout — so isatty() is False and
    # would otherwise defeat color output even on a truecolor terminal.
    if os.environ.get("FORCE_COLOR") or os.environ.get("CLAUDECODE"):
        return True
    if not sys.stdout.isatty():
        return False
    return True


def supports_truecolor() -> bool:
    ct = os.environ.get("COLORTERM", "").lower()
    if ct in ("truecolor", "24bit"):
        return True
    # Claude Code's shell advertises COLORTERM=truecolor, but the env var may
    # not always propagate through tool boundaries. Assume truecolor when
    # CLAUDECODE is set so bar backgrounds render at full fidelity.
    if os.environ.get("CLAUDECODE"):
        return True
    return False


USE_COLOR = supports_color()
USE_TRUECOLOR = USE_COLOR and supports_truecolor()


def fg(rgb: tuple[int, int, int]) -> str:
    if not USE_COLOR:
        return ""
    r, g, b = rgb
    if USE_TRUECOLOR:
        return f"\x1b[38;2;{r};{g};{b}m"
    return f"\x1b[38;5;{_rgb_to_256(r, g, b)}m"


def bg(rgb: tuple[int, int, int]) -> str:
    if not USE_COLOR:
        return ""
    r, g, b = rgb
    if USE_TRUECOLOR:
        return f"\x1b[48;2;{r};{g};{b}m"
    return f"\x1b[48;5;{_rgb_to_256(r, g, b)}m"


def bold() -> str:
    return "\x1b[1m" if USE_COLOR else ""


def reset() -> str:
    return "\x1b[0m" if USE_COLOR else ""


def _rgb_to_256(r: int, g: int, b: int) -> int:
    # 6x6x6 color cube (indices 16-231)
    def q(v: int) -> int:
        if v < 48:
            return 0
        if v < 115:
            return 1
        return (v - 35) // 40
    return 16 + 36 * q(r) + 6 * q(g) + q(b)


def status_for(score: int) -> tuple[str, tuple[int, int, int]]:
    if score >= 80:
        return "Healthy", GREEN
    if score >= 60:
        return "Needs Attention", YELLOW
    return "Critical", RED


BAR_WIDTH = 20


def bar(score: int, color: tuple[int, int, int]) -> str:
    filled = max(0, min(BAR_WIDTH, round(score / 100 * BAR_WIDTH)))
    empty = BAR_WIDTH - filled
    if USE_COLOR:
        return f"{bg(color)}{' ' * filled}{reset()}{bg(TRACK)}{' ' * empty}{reset()}"
    return "█" * filled + "░" * empty


def dot(color: tuple[int, int, int]) -> str:
    return f"{fg(color)}●{reset()}"


def hr(width: int = 72) -> str:
    return f"{fg(DIM)}{'─' * width}{reset()}"


def render(payload: dict[str, Any]) -> str:
    lines: list[str] = []

    project = payload.get("project_name", "project")
    cmd_label = payload.get("command_label", "/codeprobe audit .")
    overall = int(payload.get("overall_score", 0))
    overall_status, overall_color = status_for(overall)

    # Chrome line (three dots + command label) — mirrors the SVG chrome
    chrome = (
        f"{fg(RED)}●{reset()} {fg(YELLOW)}●{reset()} {fg(GREEN)}●{reset()}"
        f"   {fg(DIM)}{cmd_label}{reset()}"
    )
    lines.append(chrome)
    lines.append(hr())

    # Title
    lines.append(f"{bold()}{fg(GREEN)}Code Health Report{reset()} {fg(DIM)}— {project}{reset()}")
    lines.append("")

    # Overall health
    lines.append(
        f"{fg(TEXT)}Overall Health:{reset()} "
        f"{bold()}{fg(overall_color)}{overall}/100{reset()}  "
        f"{dot(overall_color)} {fg(overall_color)}{overall_status}{reset()}"
    )
    lines.append("")

    # Category section header
    lines.append(f"{fg(DIM)}CATEGORY SCORES{reset()}")
    lines.append(hr())

    categories = payload.get("categories", [])
    name_width = max((len(c.get("name", "")) for c in categories), default=16)
    name_width = max(name_width, 16)

    for c in categories:
        name = c.get("name", "")
        score = int(c.get("score", 0))
        status, color = status_for(score)
        lines.append(
            f"{fg(TEXT)}{name:<{name_width}}{reset()}  "
            f"{bar(score, color)}  "
            f"{fg(TEXT)}{score:>3}/100{reset()}  "
            f"{dot(color)} {fg(color)}{status}{reset()}"
        )

    # Codebase Stats
    stats = payload.get("stats") or {}
    if stats:
        lines.append("")
        lines.append(f"{fg(DIM)}CODEBASE STATS{reset()}")
        lines.append(hr())
        files = stats.get("files")
        total_loc = stats.get("total_loc")
        if files is not None and total_loc is not None:
            lines.append(
                f"{fg(TEXT)}Files:{reset()} {files:,}"
                f"    {fg(TEXT)}Total LOC:{reset()} {total_loc:,}"
            )
        be_f, be_l = stats.get("backend_files"), stats.get("backend_loc")
        fe_f, fe_l = stats.get("frontend_files"), stats.get("frontend_loc")
        if be_f is not None and fe_f is not None:
            lines.append(
                f"{fg(TEXT)}Backend:{reset()} {be_f} ({be_l:,} LOC)"
                f"    {fg(TEXT)}Frontend:{reset()} {fe_f} ({fe_l:,} LOC)"
            )
        if stats.get("largest_file"):
            lines.append(
                f"{fg(TEXT)}Largest file:{reset()} "
                f"{stats['largest_file']} ({stats.get('largest_loc', 0):,} LOC)"
            )
        if stats.get("test_files") is not None:
            lines.append(
                f"{fg(TEXT)}Test files:{reset()} {stats['test_files']} / "
                f"{stats.get('test_files_total', 0)} "
                f"({stats.get('test_ratio_pct', 0)}%)"
                f"    {fg(TEXT)}Comment ratio:{reset()} "
                f"{stats.get('comment_ratio_pct', 0)}%"
            )

    # Hot Spots
    hot = payload.get("hot_spots") or []
    if hot:
        lines.append("")
        lines.append(f"{fg(DIM)}HOT SPOTS{reset()} {fg(DIM)}(files needing most attention){reset()}")
        lines.append(hr())
        for i, h in enumerate(hot[:3], start=1):
            file = h.get("file", "")
            cats = h.get("categories", [])
            cat_list = ", ".join(cats)
            lines.append(
                f"{fg(DIM)}{i}.{reset()} {fg(TEXT)}{file}{reset()} "
                f"{fg(DIM)}—{reset()} {len(cats)} categories flagged "
                f"{fg(DIM)}({cat_list}){reset()}"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(f"render_dashboard: invalid JSON on stdin: {e}", file=sys.stderr)
        return 2

    output = render(payload)
    sys.stdout.write(output)
    if not output.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
