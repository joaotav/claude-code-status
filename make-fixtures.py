#!/usr/bin/env python3
"""Regenerate test fixtures with timestamps relative to now.

Reset times are epoch seconds, so static fixtures would drift into the past and
stop exercising the same-day / this-week / further-out formatting branches.
Run this before ./run-fixtures.sh.
"""

import json
import pathlib
import time

HERE = pathlib.Path(__file__).parent
OUT = HERE / "fixtures"
NOW = time.time()
HOUR = 3600
DAY = 24 * HOUR


def base():
    return {
        "cwd": "/home/joao/Programming/claude-usage-widget",
        "session_id": "fixture-session-0001",
        "transcript_path": "/tmp/transcript.jsonl",
        "model": {"id": "claude-opus-5", "display_name": "Opus"},
        "workspace": {
            "current_dir": "/home/joao/Programming/claude-usage-widget",
            "project_dir": "/home/joao/Programming/claude-usage-widget",
            "added_dirs": [],
        },
        "version": "2.1.220",
        "output_style": {"name": "default"},
        "cost": {
            "total_cost_usd": 0.01234,
            "total_duration_ms": 135000,
            "total_api_duration_ms": 2300,
            "total_lines_added": 156,
            "total_lines_removed": 23,
        },
        "context_window": {
            "total_input_tokens": 15500,
            "total_output_tokens": 1200,
            "context_window_size": 200000,
            "used_percentage": 8,
            "remaining_percentage": 92,
            "current_usage": {
                "input_tokens": 8500,
                "output_tokens": 1200,
                "cache_creation_input_tokens": 5000,
                "cache_read_input_tokens": 2000,
            },
        },
        "exceeds_200k_tokens": False,
        "rate_limits": {
            "five_hour": {"used_percentage": 23.5, "resets_at": int(NOW + 2 * HOUR)},
            "seven_day": {"used_percentage": 41.2, "resets_at": int(NOW + 4 * DAY)},
        },
    }


FIXTURES = {}

# Everything present — the happy path.
FIXTURES["full"] = base()

# Pro/Max quota not yet known: before the first API response, or API-key auth.
f = base()
del f["rate_limits"]
FIXTURES["no-rate-limits"] = f

# Windows can be absent independently.
f = base()
del f["rate_limits"]["seven_day"]
FIXTURES["one-window"] = f

# Immediately after /compact, or before the first API call.
f = base()
f["context_window"]["current_usage"] = None
f["context_window"]["used_percentage"] = None
f["context_window"]["remaining_percentage"] = None
f["context_window"]["total_input_tokens"] = 0
f["context_window"]["total_output_tokens"] = 0
FIXTURES["null-usage"] = f

# used_percentage null but current_usage present — exercises the derived path.
f = base()
f["context_window"]["used_percentage"] = None
FIXTURES["derived-pct"] = f

# Brand new session: no quota yet, no context yet. Should print nothing at all.
f = base()
del f["rate_limits"]
del f["context_window"]
del f["cost"]
FIXTURES["empty"] = f

# High usage: red thresholds and the >200k marker.
f = base()
f["rate_limits"]["five_hour"]["used_percentage"] = 94.0
f["rate_limits"]["seven_day"]["used_percentage"] = 71.8
f["context_window"]["total_input_tokens"] = 210000
f["context_window"]["used_percentage"] = 96
f["context_window"]["current_usage"] = {
    "input_tokens": 120000,
    "output_tokens": 8400,
    "cache_creation_input_tokens": 60000,
    "cache_read_input_tokens": 30000,
}
f["exceeds_200k_tokens"] = True
f["cost"]["total_cost_usd"] = 4.8231
FIXTURES["maxed"] = f

# Reset further than a week out — exercises the date-prefixed branch.
f = base()
f["rate_limits"]["seven_day"]["resets_at"] = int(NOW + 10 * DAY)
FIXTURES["far-reset"] = f

# Malformed input: wrong types where numbers are expected.
FIXTURES["garbage"] = {
    "rate_limits": {"five_hour": "not-a-dict", "seven_day": {"used_percentage": "abc"}},
    "context_window": {"context_window_size": "big", "current_usage": []},
    "cost": {"total_cost_usd": "free"},
}


def main():
    OUT.mkdir(exist_ok=True)
    for name, payload in FIXTURES.items():
        path = OUT / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"wrote {path.relative_to(HERE)}")


if __name__ == "__main__":
    main()
