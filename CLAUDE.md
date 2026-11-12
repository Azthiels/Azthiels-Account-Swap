# Azthiels Account Swap — notes for Claude

Personal project of Azthiels. **Talk to the user in Spanish**; everything in the repo (code, docs, UI) is in English.
GitHub: https://github.com/Azthiels/Azthiels-Account-Swap (private for now, will go public once polished).

## What it is
A Windows account switcher for games with a keyboard-only TUI (Textual, `mouse=False`).
It saves each account's local session and swaps it, so switching accounts needs no login.
Also meant for sharing account access without sharing passwords (encrypted, optionally expiring `.auc` files).

- **Riot** (LoL / Valorant): copies `%LOCALAPPDATA%\Riot Games\Riot Client\Data\RiotGamesPrivateSettings.yaml`.
  The active Riot ID (`Name#TAG`) is read from the Riot Client's local API via its `lockfile`.
- **Genshin Impact**: removed in the v4 rewrite, to be re-added. The old implementation (registry value
  `HKCU\Software\miHoYo\Genshin Impact\MIHOYOSDK_ADL_PROD_OVERSEA_h1158948810`) is in
  `_old/azthiels_universal_swap.py` (local only, gitignored) as reference.

## Layout (v4, modular)
```
run.py                  entry point (dev and PyInstaller) -> azswap.main.run()
azswap/
  main.py               staged startup (crash.log says which stage failed), --doctor/--self-test/--no-elevate
  doctor.py             checks each part on its own, prints OK/FAIL
  core/                 no UI
    paths.py            every path (AppData etc.)
    logs.py             logging -> debug.log; each line names the module that wrote it
    util.py             JSON read/write (atomic), dates, safe_name
    processes.py        tasklist/taskkill, launching processes
    elevation.py        admin: UAC once + scheduled task (checks target/priority); launch_as_user()
    tasks.py            creates scheduled tasks from XML (normal priority, no 72 h limit)
    timesync.py         internet time (verified TLS) cached on the monotonic clock
    auc.py              .auc format (AES-256-GCM + PBKDF2)
    storage.py          saved accounts (Account dataclass)
    state.py            state.json (active account per service, last service)
    config.py           config.json + ConfigField
    expiry.py           deletes expired imported accounts
    filepicker.py       native file dialog (tkinter)
  services/
    base.py             Service class (what every game implements)
    riot.py             RiotService
    __init__.py         SERVICES (order = tab order)
  ui/
    app.py              main window, list, details, shared plumbing (ask/confirm/set_status)
    theme.py            colors + CSS + key help text (colors are exact xterm-256 values on purpose:
                        the user's terminal runs in 256-color mode)
    banner.py, dialogs.py, options.py
    flows/              key actions: session.py (S/U/Enter/N/L), manage.py (R/D/B), transfer.py (E/I/A)
```
**Adding a game:** create `services/<game>.py` with a `Service` subclass and add it to `SERVICES`.
Its options go in `config_fields` (shown in Options) and its checks in `diagnose()` (shown in `--doctor`).

User data lives in `%APPDATA%\Azthiels Account Swap\`: `Accounts/<service_id>/<account>/session.bin + meta.json`,
`state.json`, `config.json`, `debug.log`, `crash.log`. Format compatible with v3 (no migrations in v4).

## Run and build
- Dev: `start.bat` (installs `requirements.txt` if missing, runs `run.py`; passes arguments, e.g. `start.bat --doctor`).
- Exe: `build.bat` → `dist\Azthiels-Account-Swap.exe` (PyInstaller onefile, `--console`, icon `assets\img.ico`),
  then runs `--self-test` on the built exe, so anything that wasn't bundled fails right there.
  `build/` and `dist/` are PyInstaller output (the `.spec` is generated in `build/`).
- `--no-elevate` or `RS_NO_ELEVATE=1` skips elevation. Dev and exe use separate tasks
  (`AzthielsAccountSwap-dev` / `AzthielsAccountSwap`).
- Headless UI testing: `run.py --self-test`, or `App.run(headless=True, auto_pilot=...)` + `save_screenshot()`.

## Games run without admin
The program runs elevated, but games start through `elevation.launch_as_user()`: it creates the
`AzthielsAccountSwap-launcher` task (LeastPrivilege) and runs it, so the game runs as a normal user
(Discord/OBS overlays work, LoL/Valorant don't inherit admin). If the task fails it launches directly with admin and logs it.

## Be careful
- **Do NOT read, show or modify `Accounts/`** (AppData) or any `session.bin`: they are real session tokens.
  Never upload or commit them (`.gitignore` excludes them).
- Legacy data from the old project folder (v1 Accounts, `files.zip`) was moved to
  `%APPDATA%\Azthiels Account Swap\_legacy_project_backup\`. Also real tokens.
- Killing processes, writing session files and creating scheduled tasks are real actions on the PC: test carefully.
- License is PolyForm Strict 1.0.0 (audit/use allowed, no modification or redistribution) — chosen on purpose.

## History
- The exe "that didn't open" (fixed in v4): the scheduled task pointed to an old exe that no longer existed; the new exe
  ran it (`schtasks /run` still returns OK) and exited. The task's target is now verified before use.
- Tasks created with `schtasks /tr` got priority 7 (below normal, inherited by Riot and the games) and a 72 h limit.
  They are now created from XML (`core/tasks.py`) and `task_problems()` recreates old ones.

## Open items
- Re-add Genshin Impact as `services/genshin.py`.
- `RiotService.is_busy()` always returns `False`, so an expired account is cleaned up even mid-match.
  Undecided whether to bring back a local LCU check just for this.
- LoL stats (region, level, ranked, mastery) were dropped: the public API needs a key that expires every 24 h,
  and touching the League Client was ruled out.
