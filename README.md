# claude-code-status

A Claude Code statusline: where you are, subscription usage without running
`/usage`, the model, and the git state.

```
~/…/AI Productivity | 5h 23.5% [19:45] | Week: 41.2% [Thu 14:00] | Context: 476.5k/1M 48% | Opus 5.5 (high) | obsidian_vault:main !2 +1 ?1 ⇡2
```

(Shown with text labels. By default the labels are Nerd Font icons: see
`icons` below.)

- **cwd**: home shown as `~`, deep paths trimmed to `~/…/leaf`.
- **`5h` and `Week:`**: your Pro/Max quota, percentage consumed, with the
  reset time in brackets.
- **`Context:`**: the live context window.
- **Model**: with the effort level once the first turn has set it.
- **Git**: `repo:branch` (or `@sha` when detached), then Starship's symbols,
  each hidden at zero: `!` modified, `+` staged, `?` untracked, `✘` deleted,
  `⇡` ahead of upstream, `⇣` behind. Merge conflicts count as `!`. Hidden
  outside a repository.

It renders in its own row at the bottom of the Claude Code window, above the
built-in footer badges. It does not replace them.

## How it works

Claude Code passes session data to the statusline command as JSON on stdin, and
that payload already includes the quota, context, model, effort and directory.
So this script makes **no network calls, reads no credentials, and has no
daemon or cache**. Its one subprocess is a single `git status
--porcelain=v2 --branch`, which gives branch, ahead/behind and file states in
one call. It runs with a 0.5 s timeout and `GIT_OPTIONAL_LOCKS=0`, so it never
takes the index lock Claude's own git commands need. A render takes ~37 ms,
against Claude Code's 300 ms debounce.

## Install

Requires Python 3 and Claude Code v2.1.153+ (for terminal-width detection).

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "/path/to/claude-code-status/statusline.py",
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
| `show_cwd` | `True` | `~/…/AI Productivity` |
| `show_quota` | `True` | `5h ...` and `Week: ...` |
| `show_context` | `True` | `Context: 476.5k/1M 48%` |
| `show_model` | `True` | `Opus 5.5 (high)` |
| `show_git` | `True` | `obsidian_vault:main !2 +1 ?1 ⇡2` |
| `show_input_tokens` | `False` | `in 8.5k` — per-call fresh input |
| `show_cache_split` | `False` | `(cache w5k r2k)` — written / read |
| `show_output_tokens` | `False` | `out 1.2k` |
| `show_duration` | `False` | Session wall-clock time |
| `show_lines_changed` | `False` | `+156/-23` |
| `warn_at` | `60.0` | Percent at which numbers turn yellow |
| `crit_at` | `85.0` | Percent at which numbers turn red |
| `colour` | `True` | ANSI colour (also disabled by `NO_COLOR`) |
| `icons` | `True` | Nerd Font glyphs instead of text labels (see below) |
| `separator` | `" \| "` | Between segments |
| `git_timeout` | `0.5` | Seconds before a slow `git status` is abandoned and the git field hidden |

### Icons

With `icons` on, each field gets a Nerd Font glyph: folder (cwd), hourglass
(`5h`), calendar (`Week:`), database (`Context:`), microchip (model), branch
(git). They are Font Awesome codepoints, the set least likely to move between
Nerd Font versions. In a terminal without a Nerd Font they draw as boxes, so
set `icons` to `False` there to get the text labels back.

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
- **No `effort`**: before the first turn, or on a model without effort
  support. The model shows alone.
- **Not a git repository, or git fails or times out**: the git field is
  hidden.
- **Malformed payload** — individual segments drop; the script never raises.
  A total failure prints `usage unavailable` rather than going blank.

## Narrow terminals

The script reads `COLUMNS` and shrinks one step at a time: the reset times,
then `Context:`'s raw counts, then cwd down to its last folder, then the git
symbols, then the effort. Only then do whole fields drop: git, then model,
then cwd. Quota and context are never dropped.

```
170 cols  ~/Programming/claude-code-status | 5h 23.5% [17:42] | Week: 41.2% [Wed 15:42] | Context: 15.5k/200k 8% | Opus 5.5 (high) | claude-code-status:main !1 ?4
151 cols  ~/Programming/claude-code-status | 5h 23.5% | Week: 41.2% | Context: 15.5k/200k 8% | Opus 5.5 (high) | claude-code-status:main !1 ?4
131 cols  ~/Programming/claude-code-status | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5 (high) | claude-code-status:main !1 ?4
120 cols  claude-code-status | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5 (high) | claude-code-status:main !1 ?4
106 cols  claude-code-status | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5 (high) | claude-code-status:main
100 cols  claude-code-status | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5 | claude-code-status:main
 93 cols  claude-code-status | 5h 23.5% | Week: 41.2% | Context: 8% | Opus 5.5
 67 cols  claude-code-status | 5h 23.5% | Week: 41.2% | Context: 8%
 56 cols  5h 23.5% | Week: 41.2% | Context: 8%
```

Icons are narrower than the text labels, so with `icons` on each step comes
at a smaller width.

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

Session cost is omitted: on a subscription it is an API-price equivalent, not
a bill.
