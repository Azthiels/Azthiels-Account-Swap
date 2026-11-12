"""Colors and CSS for the whole TUI.

All colors are exact xterm-256 palette entries, so the TUI looks the same in a 256-color terminal
(where Textual rounds every color to the nearest entry) and in a truecolor one.
"""
BG = "#000000"
BG_DIALOG = "#005f5f"
BORDER = "#005f5f"          # the "blue" of every frame
BORDER_FOCUS = "#008787"    # same frame, a bit brighter, when it has keyboard focus
ACCENT = "#af5f00"          # orange: selected row, active tab, dialog frame
TEXT = "#949494"
MUTED = "#6c6c6c"
FAINT = "#585858"

STATUS_COLORS = {"ok": "#4ade80", "busy": "#facc15", "err": "#ff4655", "warn": "#fb923c"}
ACTIVE = "#4ade80"
BANNED = "#ef4444"

APP_CSS = f"""
Screen {{ background: {BG}; color: {TEXT}; }}
#banner {{ height: 6; padding: 1 2 0 2; }}
#tabs {{ height: 1; padding: 0 2; }}
#main {{ height: 1fr; }}
#accounts {{ width: 32%; height: 100%; border: round {BORDER}; padding: 0 1; }}
#accounts:focus {{ border: round {BORDER_FOCUS}; background-tint: {BG} 0%; }}
#details {{ width: 1fr; border: round {BORDER}; padding: 1 2; }}
OptionList {{ background: {BG}; border: none; padding: 0; }}
OptionList:focus {{ background-tint: {BG} 0%; }}
OptionList > .option-list--option-highlighted {{ color: {ACCENT}; text-style: bold; background: {BG}; }}
OptionList:focus > .option-list--option-highlighted {{ color: {ACCENT}; text-style: bold; background: {BG}; }}
#statusbox {{ height: auto; border: round {BORDER}; padding: 0 2; }}
Ask, Confirm {{ align: center middle; }}
#dialog {{ width: 64; height: auto; border: round {ACCENT}; background: {BG_DIALOG}; padding: 1 2; }}
.hint {{ color: {MUTED}; margin-top: 1; }}
#search {{ display: none; border: round {ACCENT}; }}
"""

KEY_HELP = (
    "⇥ Game   / Search   ↑↓ Nav   ⏎ Switch   S Save   U Update   N New   "
    "R Rename   D Delete   B Ban   E Export   A Backup all   I Import   L Logout   O Options   Q Quit"
)
