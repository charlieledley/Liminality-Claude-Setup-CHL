# Claude setup notes, 2026-10-09

The parts of the setup that are not files and so cannot be mirrored in `home/`. Written so a
new machine can be rebuilt from this repo. Update the date in the filename when the note is
substantially revised; small corrections can go in place.

## Machine and toolchain

- Windows 11 Pro. Claude Code is used through the Claude desktop app's Code tab; there is no
  `claude` command on the PATH and no Node.js install.
- Git for Windows 2.55, installed per-user under `AppData\Local\Programs\Git`. The credential
  helper is Git Credential Manager (`credential.helper = manager` in the install's own
  gitconfig). The GitHub login is stored there, so pushes to GitHub run without a prompt. On a
  new machine the first push opens a browser sign-in once.
- Python 3.12.10 on the PATH (`python` and `py`). The Bloomberg `blpapi` package is not in the
  system Python; each project installs it in its own `.venv` from Bloomberg's package index,
  as the `bbg-pull` skill describes.
- Company OneDrive is at the path in the `OneDriveCommercial` environment variable. All backup
  scripts read that variable, so they carry no machine-specific paths.

## Claude desktop app settings

As read from the app on 2026-10-09. Settings marked "account" follow the login across devices;
the rest are per machine.

| Setting | Value |
|---|---|
| Connect new sessions to Remote Control | on |
| Keep computer awake while Claude works, including on battery | on |
| Prompt suggestions | on |
| Branch prefix for new session branches (account) | `claude` |
| Auto-archive sessions | never |
| Worktree location | inside the project, `<repo>/.claude/worktrees` |
| Browser tools (built-in browser, dev servers) | on |
| Default permission mode | default; bypass and auto mode allowed by policy |
| Output style | default |
| Notifications | banners, system sound, no taskbar flash |

## Connectors, plugins, extensions

Connectors are enabled in the claude.ai account, not on this machine. Enabled on 2026-10-09:
Gmail, Google Calendar, Google Sheets, Dropbox, Granola, Zoom for Claude, Plaud, Wispr Flow,
and the visualize widget. One plugin: Bright Data (web scraping and search). The Claude in
Chrome extension is installed in Chrome on this PC and is separate from the app's built-in
browser.

## Hooks

One, wired in `home/settings.json`: on session start after a context compaction, the shell
script `home/hooks/after-compaction-reminder.sh` prints a reminder to re-read the project
rules, decision log and memory before asserting history. Lives at `~/.claude/hooks/` when
installed.

## Scheduled backup tasks

Four Windows Task Scheduler jobs, all hourly, all copy-only, all logging to a `backup.log` in
their destination folder on company OneDrive. `tools/register-backup-tasks.ps1` recreates any
or all of them.

| Task | Script | Destination folder on OneDrive |
|---|---|---|
| Liminality backtest backup to OneDrive | put-writing repo, `tools/backup-to-onedrive.ps1` | `Liminality-backtest-backup-current` |
| Liminality french-swap-spreads backup to OneDrive | swap-spreads repo, same script | `Liminality-french-swap-spreads-backup-current` |
| Liminality Claude-Setup-CHL backup to OneDrive | this repo, `tools/backup-to-onedrive.ps1` | `Liminality-Claude-Setup-CHL-backup-current` |
| Liminality claude-home backup to OneDrive | this repo, `tools/backup-claude-home-to-onedrive.ps1` | `Liminality-claude-home-backup-current` |

The per-repo jobs copy the repo plus that project's transcript and memory folder. The
claude-home job copies the whole live `~/.claude` folder minus caches and key files. There is
also a frozen snapshot `Liminality-backtest-backup-2026-09-22` from a recovery; no script
touches it.

## Repositories on this PC

All three sit at the root of `C:\`, each with a `tools/backup-to-onedrive.ps1` and a
`docs/decisions/` log.

| Repo | GitHub |
|---|---|
| `Liminality-put-writing-strategy` | `origin` in the LiminalityCapital organisation, `mine` in Charlie's account, `dashboard-v2` a collaborator's fork |
| `Liminality-french-swap-spreads` | none as of 2026-10-09 |
| `Liminality-Claude-Setup-CHL` | pending, see decision 0002 |

## Phone and other devices

Claude Code on the phone (and claude.ai/code in a browser) works through Remote Control,
driving sessions that run on this PC. There is nothing phone-side to back up. The claude.ai
app's own preferences, project instructions and memory live in the account and cannot be
tracked as files.

## Rebuilding a machine

1. Install the Claude desktop app, Git for Windows and Python 3.12. Sign in to OneDrive so
   the company folder syncs and `OneDriveCommercial` is set.
2. Clone this repo to `C:\Liminality-Claude-Setup-CHL`.
3. Run `python tools\sync_setup.py to-home` to install the global rules, settings, skills and
   hooks into `~/.claude`.
4. Clone the project repos to their `C:\` paths, or restore them from the OneDrive backup
   folders (each `project\` subfolder is a complete working copy with its git history).
5. Run `powershell -ExecutionPolicy Bypass -File tools\register-backup-tasks.ps1` to recreate
   the backup jobs.
6. Re-apply the app settings above by hand, and check the connectors in the claude.ai account.
7. Memory folders, if wanted, come back from `Liminality-claude-home-backup-current\claude-home\projects\`.
