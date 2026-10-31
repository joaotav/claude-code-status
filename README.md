# claude-usage-widget

A Claude Code statusline that shows subscription usage without running `/usage`.

```
5h 23.5% [19:45] | Week: 41.2% [Thu 14:00] | Context: 476.5k/1M 48% | $0.01
```

`5h` and `Week:` are your Pro/Max quota — percentage consumed, with the reset
time in brackets. `Context:` is the live context window, and the last field is
the session cost so far.

It renders in its own row at the bottom of the Claude Code window, above the
built-in footer badges — it does not replace them.

## How it works

Claude Code passes session data to the statusline command as JSON on stdin, and
that payload already includes `rate_limits.five_hour` and
`rate_limits.seven_day`. So this script makes **no network calls, reads no
credentials, and has no daemon or cache**. It is a pure stdin-to-stdout
formatter, which is why it can run on every render (~23 ms per invocation,
against Claude Code's 300 ms debounce).

## Install

Requires Python 3 and Claude Code v2.1.153+ (for terminal-width detection).

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "/path/to/claude-usage-widget/statusline.py",
    "padding": 0,
    "refreshInterval": 60
  }
}
```

`refreshInterval` keeps the percentages current while the session is idle —
event-driven updates go quiet when nothing is happening. Remove it if you only
want updates on new messages.

## Configuration

Edit the `CONFIG` block at the top of `statusline.py`:

| Key | Default | Effect |
|---|---|---|
| `show_quota` | `True` | `5h ...` and `Week: ...` |
| `show_context` | `True` | `Context: 476.5k/1M 48%` |
| `show_cost` | `True` | `$0.01` |
| `show_input_tokens` | `False` | `in 8.5k` — per-call fresh input |
| `show_cache_split` | `False` | `(cache w5k r2k)` — written / read |
| `show_output_tokens` | `False` | `out 1.2k` |
| `show_duration` | `False` | Session wall-clock time |
| `show_lines_changed` | `False` | `+156/-23` |
| `warn_at` | `60.0` | Percent at which numbers turn yellow |
| `crit_at` | `85.0` | Percent at which numbers turn red |
| `colour` | `True` | ANSI colour (also disabled by `NO_COLOR`) |
| `separator` | `" \| "` | Between segments |
| `cost_decimals` | `2` | Decimal places on the cost figure |

The per-call token fields are off by default because one line has no room for
them. They describe the **most recent API call**, not session totals:
`in` is fresh uncached input, `w` is tokens written to the prompt cache, `r` is
tokens read back from it, `out` is generated tokens. A large `r` next to a tiny
`in` is the healthy pattern — the conversation prefix is being reused rather
than reprocessed.

## Behaviour when data is missing

Nothing is ever invented — a value that isn't known is omitted rather than
shown as zero.

- **`rate_limits` absent** — the quota fields are dropped entirely. This is
  normal before the first API response of a session, and permanent on API-key
  auth (the field is Claude.ai Pro/Max only). Each window is handled
  independently, so if only `five_hour` is present you get only that.
- **After `/compact`, or before the first API call** — `current_usage` is
  `null`, so the token counts drop and the line shrinks to what's known.
- **`used_percentage` null** — recomputed from `current_usage` using the same
  input-only formula Claude Code uses, so it matches `/context`.
- **Malformed payload** — individual segments drop; the script never raises.
  A total failure prints `usage unavailable` rather than going blank.

## Narrow terminals

The script reads `COLUMNS` and shrinks in two stages: first the bracketed reset
times drop and `Context:` sheds its raw token counts, then whole fields are
dropped lowest-value first. The quota percentages are never dropped.

```
75 cols   5h 23.5% [15:25] | Week: 41.2% [Fri 13:25] | Context: 15.5k/200k 8% | $0.01
60 cols   5h 23.5% | Week: 41.2% | Context: 8% | $0.01
32 cols   5h 23.5% | Week: 41.2%
```

## Development

```sh
./run-fixtures.sh     # render every fixture; non-zero exit means something raised
./make-fixtures.py    # regenerate fixtures (reset times are relative to now)
```

Fixtures cover the full payload plus each degradation path. `make-fixtures.py`
regenerates them with timestamps relative to the current time, since static
epochs would drift into the past and stop exercising the same-day /
this-week / further-out formatting branches.

## Not included

Per-model weekly limits (`seven_day_opus`, `seven_day_sonnet`) and extra-credit
balance are **not** in the statusline payload. They exist only on the
undocumented `/api/oauth/usage` endpoint, which needs an OAuth token and rate
limits aggressively. Adding them would mean reintroducing credentials, caching,
and backoff — deliberately out of scope here.

Model, effort, thinking and PR indicators are also omitted: Claude Code already
shows those in its own footer badges.
