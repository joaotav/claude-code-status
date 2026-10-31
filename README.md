# claude-code-status

A status line for Claude Code that shows, in one row under the prompt, where
you are, how much of your subscription you have used, which model you are on,
how much of your system's memory is in use, the state of your git repository,
and which account is logged in.

```
~/…/AI Productivity • 5h 23.5% [19:45] • Week: 41.2% [Thu 14:00] • Context: 477k/1M 48% • Opus 5.5 (high) • RAM: 7.6GB/14.8GB • obsidian_vault:main !2 +1 ?1 ⇡2 • Account: me@example.com
```

Shown here with text labels. By default each label is a Nerd Font icon.

## What it shows

| Field | Example | What it tells you |
|---|---|---|
| Directory | `~/…/AI Productivity` | Where the session is working. Home is `~`; deep paths keep only the last folder. |
| 5-hour limit | `5h 23.5% [19:45]` | Share of your 5-hour usage window spent, and when it resets. |
| Weekly limit | `Week: 41.2% [Thu 14:00]` | Share of your weekly limit spent, and when it resets. |
| Context | `Context: 477k/1M 48%` | How full the conversation's context window is. |
| Model | `Opus 5.5 (high)` | The model, and its effort level once the first turn has set it. |
| Memory | `RAM: 7.6GB/14.8GB` | System RAM in use out of the total, in binary units as `free -h` and system monitors count them. Linux and macOS. |
| Git | `obsidian_vault:main !2 +1 ?1 ⇡2` | Repository, branch and what has changed. Hidden outside a repository. |
| Account | `Account: me@example.com` | The logged-in account, for when you switch between several. |

Percentages turn **yellow from 60%** and **red from 85%**.

The git symbols are the ones [Starship](https://starship.rs) and
Powerlevel10k use, each shown only when its count is above zero:

| Symbol | Meaning | Colour |
|---|---|---|
| `!` | modified, not staged (merge conflicts count here too) | yellow |
| `+` | staged | green |
| `?` | untracked | blue |
| `✘` | deleted | red |
| `⇡` | commits to push | cyan |
| `⇣` | commits to pull | magenta |

A detached HEAD shows as `@a1b2c3d` in place of the branch.

## Design choices

- **A status line, not a mod.** Claude Code mods are more powerful, but under
  the prompt they can only add plain text that cannot fit itself to the
  terminal's width, or replace Claude Code's own hint line. A status line
  command gets colour, width fitting, and every field above from what Claude
  Code already sends it.
- **Nothing is fetched.** Every value comes from the data Claude Code passes
  in, one local `git status`, the account file Claude Code already keeps, or
  the operating system's memory figures. There is no daemon, cache or network call to break or slow down, and a
  render takes about 40 ms.
- **Missing means hidden, never zero.** A value Claude Code has not reported
  yet is left out rather than shown as `0%`, so the line never claims
  something it does not know.
- **Usage always stays on screen.** On a narrow terminal the line sheds detail
  first (reset times, raw token counts, the full path, git symbols, effort),
  then whole fields (account, memory, git,
  model, then directory). The quota and
  context are never dropped.
- **The account comes from Claude Code's own record**, not from the config
  folder's name, so it stays right after a `/login` to another account. Each
  account folder (`CLAUDE_CONFIG_DIR`) is read separately.
- **Memory counts what programs actually hold.** The disk cache the system
  hands back on demand is not counted as used, matching `free -h` on Linux
  and Activity Monitor's "Memory Used" on macOS.
- **Reset times are clock times** (`19:45`, `Thu 14:00`), not countdowns, so
  they stay correct between refreshes.
- **No session cost.** On a subscription it is an API-price estimate, not a
  bill, so it would take space without telling you anything you can act on.
- **Icons with a fallback.** The icons are Font Awesome glyphs, the set least
  likely to move between Nerd Font versions. Turn `icons` off and the text
  labels come back, for terminals without a Nerd Font (see
  [Icons and Nerd Fonts](#icons-and-nerd-fonts)).
- **Familiar git symbols and colours.** They match Starship and
  Powerlevel10k, so they read the same as a shell prompt, and the colours
  follow `git status`: staged green, unstaged yellow, untracked blue.

## Privacy

The script reads only what it needs, keeps nothing, and sends nothing
anywhere.

**What it reads**

- The JSON Claude Code passes it on stdin. Of that, it uses the directory,
  model, effort, usage limits and context size. It ignores the rest,
  including the session id and the transcript path, and never opens the
  transcript.
- Your repository's state, through one `git status` in the session's
  directory, plus a check for the `.git` folder to name the repository.
- Your account's email, the one field it takes from Claude Code's account
  file (`.claude.json` in the active config folder, or in your home
  directory). Turn `show_account` off and the file is not opened at all.
- The system's memory totals: from `/proc/meminfo` on Linux, and from
  `vm_stat` on macOS. Nothing about individual processes is read.

**What it never does**

- Make network requests.
- Read credentials or tokens. The login token lives in a separate file
  (`.credentials.json`) that the script never opens.
- Write files, logs or any state; each run starts from nothing.
- Change your repository. `git status` runs read-only, without taking the
  index lock that Claude's own git commands need, and gives up after 0.5 s.

It depends only on Python's standard library, so there are no third-party
packages to trust.

**On screen:** the directory, repository and account email are visible to
anyone who sees your terminal. When screen sharing, you can hide them with
`show_cwd`, `show_git` and `show_account`.

## Install

Requires Python 3 and Claude Code v2.1.153 or later. The icons need a Nerd
Font: see [Icons and Nerd Fonts](#icons-and-nerd-fonts).

Add this to `~/.claude/settings.json`:

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

`refreshInterval` keeps the numbers current while the session is idle. Remove
it to update only when a message is sent.

## Icons and Nerd Fonts

The status line is designed for a [Nerd Font](https://www.nerdfonts.com),
whose icons it uses as field labels. Without one, the icons show as boxes:
set `icons` to `False` and it falls back to text labels (`5h`, `Week:`,
`Context:`) that work in any font.

## Configuration

Edit the `CONFIG` block at the top of `statusline.py`.

| Key | Default | Effect |
|---|---|---|
| `show_cwd` | `True` | Directory |
| `show_quota` | `True` | 5-hour and weekly limits |
| `show_context` | `True` | Context window |
| `show_model` | `True` | Model and effort |
| `show_git` | `True` | Repository, branch and symbols |
| `show_account` | `True` | Logged-in account's email |
| `show_memory` | `True` | System RAM in use out of the total |
| `icons` | `True` | Nerd Font icons; `False` for text labels |
| `colour` | `True` | Colour; the `NO_COLOR` variable also turns it off |
| `warn_at` | `60.0` | Percentage that turns yellow |
| `crit_at` | `85.0` | Percentage that turns red |
| `separator` | `" • "` | Text between fields, drawn dim |
| `git_timeout` | `0.5` | Seconds before a slow `git status` is abandoned |

Off by default, for lack of room on one line:

| Key | Shows |
|---|---|
| `show_input_tokens` | `in 8.5k`: fresh input of the last request |
| `show_cache_split` | `(cache w5k r2k)`: tokens written to and read from the prompt cache |
| `show_output_tokens` | `out 1.2k`: tokens generated by the last request |
| `show_duration` | How long the session has run |
| `show_lines_changed` | `+156/-23`: lines Claude added and removed |

## When data is missing

- **No usage limits yet:** before the first reply of a session, and always
  when using an API key instead of a subscription. The limit fields are
  hidden; each window independently.
- **No context figures:** just after `/compact` or before the first reply.
  The raw counts are hidden; the percentage is recomputed when possible, the
  same way `/context` does.
- **No effort:** before the first turn, or on a model without effort levels.
  The model shows alone.
- **No repository, or git fails or is slow:** the git field is hidden.
- **No account:** logged out, or using an API key. The account field is
  hidden.
- **Not Linux or macOS:** the memory field is hidden.
- **Malformed input:** the affected fields are hidden. If everything fails,
  the line reads `usage unavailable` instead of going blank.

## Narrow terminals

The line reads the terminal's width and shrinks one step at a time:

```
230 cols  ~/Programming/claude-code-status • 5h 23.5% [18:44] • Week: 41.2% [Wed 16:44] • Context: 16k/200k 8% • Opus 5.5 (high) • RAM: 7.8GB/14.8GB • claude-code-status:main !6 ?1 • Account: me@example.com
166 cols  claude-code-status • 5h 23.5% • Week: 41.2% • Context: 8% • Opus 5.5 (high) • RAM: 7.8GB/14.8GB • claude-code-status:main !6 ?1 • Account: me@example.com
146 cols  claude-code-status • 5h 23.5% • Week: 41.2% • Context: 8% • Opus 5.5 • RAM: 7.8GB/14.8GB • claude-code-status:main • Account: me@example.com
139 cols  claude-code-status • 5h 23.5% • Week: 41.2% • Context: 8% • Opus 5.5 • RAM: 7.8GB/14.8GB • claude-code-status:main
113 cols  claude-code-status • 5h 23.5% • Week: 41.2% • Context: 8% • Opus 5.5 • claude-code-status:main
 93 cols  claude-code-status • 5h 23.5% • Week: 41.2% • Context: 8% • Opus 5.5
 56 cols  5h 23.5% • Week: 41.2% • Context: 8%
```

With icons on, each step comes at a smaller width, since icons are shorter
than the text labels.

## Development

Standard library only; the tests need Python 3.11 or later.

```sh
python3 -m unittest discover -s tests -t .   # run the tests
./scripts/run-fixtures.sh                    # render every sample input, to check by eye
./statusline.py < fixtures/full.json         # render one (after run-fixtures)
```

```
tests/
  payloads.py         sample inputs: a full one and each missing-data case
  support.py          frozen clock, canned git output, in-process runs
  test_formatting.py  numbers, percentages, reset times, directory
  test_git.py         every git status code, colours, and a real repository
  test_account.py     which account file is read, and when it is hidden
  test_memory.py      /proc and vm_stat parsing, sizes, the real system's figures
  test_layout.py      field order, the exact shrink sequence, icons, NO_COLOR
  test_cli.py         the script as a separate process, as Claude Code runs it
scripts/
  make-fixtures.py    writes the sample inputs to fixtures/ (not tracked)
  run-fixtures.sh     renders each of them
```

The tests freeze the clock and stub git, so they give the same result on any
machine at any time of day; a few also run against a real throwaway
repository to catch changes in git's output. CI runs them on Linux and
macOS, with Python 3.11 and 3.14, for every push and pull request.

## Not included

- **Per-model weekly limits and extra-usage balance.** Claude Code does not
  pass them to status lines. They exist only behind an undocumented,
  rate-limited endpoint that needs your login token, which would break the
  privacy guarantees above.
