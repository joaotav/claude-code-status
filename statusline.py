#!/usr/bin/env python3
"""Claude Code statusline: subscription usage at a glance.

Reads the statusline JSON payload on stdin and prints one row:

    5h 23.5% [19:45] | Week: 41.2% [Thu 14:00] | Context: 476.5k/1M 48% | $0.01

Quota data comes straight from stdin (`rate_limits`), so this makes no network
calls and reads no credentials.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------

CONFIG = {
    # Segments, in display order.
    "show_quota": True,
    "show_context": True,
    "show_cost": True,
    # Per-call token detail — off by default, one line has no room for it.
    "show_input_tokens": False,
    "show_cache_split": False,
    "show_output_tokens": False,
    # Session activity rather than usage — off by default.
    "show_duration": False,
    "show_lines_changed": False,
    # Colour thresholds, as percent used.
    "warn_at": 60.0,
    "crit_at": 85.0,
    "colour": True,
    # Layout
    "separator": " | ",
    "cost_decimals": 2,
    "fallback_width": 80,
}

GREEN, YELLOW, RED, DIM, RESET = (
    "\033[32m",
    "\033[33m",
    "\033[31m",
    "\033[2m",
    "\033[0m",
)

ANSI_RE = re.compile(r"\033\[[0-9;]*m")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def dig(obj, *path):
    """Walk nested dicts, returning None if any level is missing or not a dict."""
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def use_colour() -> bool:
    # https://no-color.org/ — any non-empty value disables colour.
    return CONFIG["colour"] and not os.environ.get("NO_COLOR")


def paint(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if use_colour() else text


def colour_for(pct: float) -> str:
    if pct >= CONFIG["crit_at"]:
        return RED
    if pct >= CONFIG["warn_at"]:
        return YELLOW
    return GREEN


def fmt_tokens(n) -> str:
    """16700 -> '16.7k', 200000 -> '200k', 1000000 -> '1M'."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "—"
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        v = n / 1000
        return f"{v:.0f}k" if abs(v - round(v)) < 0.05 else f"{v:.1f}k"
    v = n / 1_000_000
    return f"{v:.0f}M" if abs(v - round(v)) < 0.005 else f"{v:.2f}M"


def fmt_pct(pct: float) -> str:
    """One decimal, but drop it when it adds nothing (23.0% -> 23%)."""
    return f"{pct:.0f}%" if abs(pct - round(pct)) < 0.05 else f"{pct:.1f}%"


def fmt_reset(epoch) -> str | None:
    """Absolute local reset time. Same day -> '19:45', this week -> 'Thu 14:00',
    further out -> '12 Aug 14:00'."""
    if epoch is None:
        return None
    try:
        when = datetime.fromtimestamp(float(epoch))
    except (ValueError, OverflowError, OSError):
        return None
    now = datetime.now()
    delta_days = (when.date() - now.date()).days
    if delta_days == 0:
        return when.strftime("%H:%M")
    if 0 < delta_days <= 6:
        return when.strftime("%a %H:%M")
    return when.strftime("%-d %b %H:%M")


def fmt_duration(ms) -> str | None:
    if not ms:
        return None
    total = int(ms) // 1000
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def visible_len(text: str) -> int:
    return len(ANSI_RE.sub("", text))


def fit(segments: list[tuple[int, list[str]]], width: int) -> str:
    """Join segments to fit `width`, shrinking in two stages.

    Each segment carries one or more variants, richest first. First try every
    segment at its richest variant, then step all segments down a variant at a
    time. Only once everything is at its sparsest do we start dropping whole
    segments, highest priority number first. Priority 0 is never dropped, so a
    row that still overflows is emitted as-is rather than mangled.
    """
    sep = CONFIG["separator"]

    def render(segs, level):
        return sep.join(v[min(level, len(v) - 1)] for _, v in segs)

    depth = max((len(v) for _, v in segments), default=1)
    for level in range(depth):
        line = render(segments, level)
        if visible_len(line) <= width:
            return line

    kept = list(segments)
    while kept:
        line = render(kept, depth - 1)
        if visible_len(line) <= width:
            return line
        droppable = [p for p, _ in kept if p > 0]
        if not droppable:
            return line
        worst = max(droppable)
        # Drop one at a time, last occurrence first, for a stable shrink order.
        for i in range(len(kept) - 1, -1, -1):
            if kept[i][0] == worst:
                del kept[i]
                break
    return ""


# --------------------------------------------------------------------------
# Segments
# --------------------------------------------------------------------------


def quota_segment(window: dict | None, label: str) -> tuple[int, list[str]] | None:
    """One rate-limit window. Returns None when the window is absent, so an
    unknown quota is omitted rather than rendered as 0%."""
    if not isinstance(window, dict):
        return None
    pct = window.get("used_percentage")
    if pct is None:
        return None
    try:
        pct = float(pct)
    except (TypeError, ValueError):
        return None

    compact = f"{label} {paint(fmt_pct(pct), colour_for(pct))}"
    reset = fmt_reset(window.get("resets_at"))
    # The percentage matters more than the reset time, so on a narrow terminal
    # we shed the reset rather than the whole window.
    variants = [f"{compact} [{reset}]", compact] if reset else [compact]
    return (0, variants)


def quota_segments(data: dict) -> list[tuple[int, list[str]]]:
    limits = data.get("rate_limits")
    if not isinstance(limits, dict):
        return []
    segs = []
    for key, label in (("five_hour", "5h"), ("seven_day", "Week:")):
        seg = quota_segment(limits.get(key), label)
        if seg:
            segs.append(seg)
    return segs


def context_segments(data: dict) -> list[tuple[int, list[str]]]:
    ctx = data.get("context_window")
    if not isinstance(ctx, dict):
        return []

    segs: list[tuple[int, list[str]]] = []
    size = ctx.get("context_window_size")
    used = ctx.get("total_input_tokens")
    pct = ctx.get("used_percentage")
    usage = ctx.get("current_usage")
    usage = usage if isinstance(usage, dict) else {}

    # used_percentage can be null early in a session; derive it from the
    # input-only components so it matches Claude Code's own calculation.
    if pct is None and size:
        parts = [
            usage.get("input_tokens"),
            usage.get("cache_creation_input_tokens"),
            usage.get("cache_read_input_tokens"),
        ]
        if any(p is not None for p in parts):
            derived = sum(p or 0 for p in parts)
            pct = derived / float(size) * 100
            if used is None:
                used = derived

    try:
        pct = float(pct) if pct is not None else None
    except (TypeError, ValueError):
        pct = None

    used_s, size_s = fmt_tokens(used), fmt_tokens(size)
    if used_s != "—" or size_s != "—":
        full = f"Context: {used_s}/{size_s}"
        compact = full
        if pct is not None:
            shown = paint(fmt_pct(pct), colour_for(pct))
            full += f" {shown}"
            # On a narrow terminal keep the percentage, shed the raw counts.
            compact = f"Context: {shown}"
        segs.append((1, [full, compact]))

    if CONFIG["show_input_tokens"] and usage.get("input_tokens") is not None:
        short = f"in {fmt_tokens(usage['input_tokens'])}"
        variants = [short]
        if CONFIG["show_cache_split"]:
            w = usage.get("cache_creation_input_tokens")
            r = usage.get("cache_read_input_tokens")
            if w is not None or r is not None:
                cache = f" (cache w{fmt_tokens(w or 0)} r{fmt_tokens(r or 0)})"
                variants = [short + cache, short]
        segs.append((4, variants))

    if CONFIG["show_output_tokens"] and usage.get("output_tokens") is not None:
        segs.append((3, [f"out {fmt_tokens(usage['output_tokens'])}"]))

    if CONFIG["show_cost"]:
        cost = dig(data, "cost", "total_cost_usd")
        if cost is not None:
            try:
                segs.append((2, [f"${float(cost):.{CONFIG['cost_decimals']}f}"]))
            except (TypeError, ValueError):
                pass

    if CONFIG["show_duration"]:
        dur = fmt_duration(dig(data, "cost", "total_duration_ms"))
        if dur:
            segs.append((5, [dur]))

    if CONFIG["show_lines_changed"]:
        added = dig(data, "cost", "total_lines_added")
        removed = dig(data, "cost", "total_lines_removed")
        if added or removed:
            segs.append((6, [f"+{added or 0}/-{removed or 0}"]))

    return segs


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def terminal_width() -> int:
    # tput and shutil.get_terminal_size can't see the real terminal here —
    # Claude Code captures our stdout. It sets COLUMNS for us instead.
    try:
        return max(20, int(os.environ.get("COLUMNS", "")))
    except ValueError:
        return CONFIG["fallback_width"]


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if not isinstance(data, dict):
        data = {}

    segments: list[tuple[int, list[str]]] = []
    if CONFIG["show_quota"]:
        segments += quota_segments(data)
    if CONFIG["show_context"]:
        segments += context_segments(data)

    if not segments:
        return  # nothing known yet — print nothing rather than an empty shell
    line = fit(segments, terminal_width())
    if line:
        print(line)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # A traceback would leave the statusline blank, so degrade to a marker.
        print(paint("usage unavailable", DIM))
