# Azthiels Account Swap

A Windows account switcher for games, with a keyboard-only terminal UI.

It saves each account's local login session and swaps them, so you can move between accounts
**without typing usernames and passwords again** — and share access to an account through an encrypted,
optionally expiring file instead of handing out its password.

![icon](assets/img.png)

## Supported services

| Service | What is saved | Account name |
|---|---|---|
| Riot Games (League of Legends / VALORANT) | the Riot Client's `RiotGamesPrivateSettings.yaml` | Riot ID detected automatically (`Name#TAG`) |

More are planned (Genshin Impact). Each service is a single file in `azswap/services/`.

## Usage

1. Open the game and log in (tick "Stay signed in").
2. In Azthiels Account Swap, press `S` to save that account.
3. Press `N` to reopen the game logged out, log into another account, and press `S` again.
4. To switch: pick an account with ↑↓ and press `Enter`. The game is closed, the session is swapped and the game reopens.

| Key | Action | Key | Action |
|---|---|---|---|
| `Tab` | next game | `/` | search |
| `Enter` | switch to account | `S` | save the current session |
| `U` | update the selected account | `N` | new account (opens logged out) |
| `R` | rename | `D` | delete from the program |
| `B` | mark banned (days or `PERMA`) | `L` | log out |
| `E` | export encrypted `.auc` | `I` | import `.auc` |
| `A` | back up everything (**unencrypted** zip) | `O` | options |
| `Q` | quit | | |

### Sharing an account (`.auc` files)
`E` exports one account to a password-protected `.auc` file (AES-256-GCM, key derived with PBKDF2-SHA256).
It can expire after N minutes. Expiration is checked against internet time (HTTPS `Date` headers over verified TLS),
never the local clock, and an expired account is removed automatically from the program that imported it.

> ⚠️ An `.auc` file (or an `A` backup) gives access to the account. Only share it with people you trust.
> Sharing accounts may go against a game's terms of service — that's on you.

### Administrator rights
Closing the game's processes needs admin rights. The first launch asks for UAC once and creates a scheduled task
(`AzthielsAccountSwap`) so it doesn't ask again. Games are **not** started as admin: they run as your normal user.

## Where data is stored
`%APPDATA%\Azthiels Account Swap\` — saved accounts (`Accounts/`), `state.json`, `config.json`, `debug.log`, `crash.log`.
`O` → `O` opens that folder.

## Development

Requires Windows and Python 3.12+.

```bat
start.bat              :: installs dependencies and runs run.py
start.bat --doctor     :: checks every part of the program (OK / FAIL)
build.bat              :: builds dist\Azthiels-Account-Swap.exe and runs its --self-test
```

```
run.py                 entry point
azswap/
  main.py              staged startup + crash reporting
  doctor.py            --doctor / --self-test
  core/                logic without UI (accounts, state, crypto, scheduled tasks, processes, internet time)
  services/            one file per game (base.py defines the interface)
  ui/                  Textual TUI; ui/flows/ holds what each key does
```

### Adding a game
1. Create `azswap/services/<game>.py` with a subclass of `Service` (see `base.py` and `riot.py`).
2. Add it to `SERVICES` in `azswap/services/__init__.py`.

Its options show up automatically in the Options screen (`config_fields`) and its checks in `--doctor` (`diagnose()`).

## License

[PolyForm Strict 1.0.0](LICENSE): you may read, audit and use this software for noncommercial purposes,
but not modify it or redistribute it. This is source-available, not open source.

## Disclaimer
Personal project, not affiliated with or endorsed by Riot Games or any other publisher. It only copies local
session files on your own PC; it does not modify games or talk to their servers.
