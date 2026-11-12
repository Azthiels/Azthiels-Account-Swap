"""The "AZTHIELS ACCOUNT SWAP" block-letter banner."""
from rich.text import Text

from .theme import BORDER, MUTED, TEXT

FONT = {
    "A": ["▄▀▄", "█▀█", "▀ ▀"], "Z": ["▀▀█", "▄▀ ", "█▄▄"], "T": ["▀█▀", " █ ", " ▀ "],
    "H": ["█ █", "█▀█", "▀ ▀"], "I": ["▀█▀", " █ ", "▄█▄"], "E": ["█▀▀", "█▀▀", "▀▀▀"],
    "L": ["█  ", "█  ", "▀▀▀"], "S": ["▄▀▀", "▀▀▄", "▄▄▀"], "C": ["█▀▀", "█  ", "▀▀▀"],
    "O": ["█▀█", "█ █", "▀▀▀"], "U": ["█ █", "█ █", "▀▀▀"], "N": ["█▄ █", "█ ▀█", "▀  ▀"],
    "P": ["█▀█", "█▀▀", "▀  "], "W": ["█   █", "█ █ █", "▀▄▀▄▀"], " ": ["  ", "  ", "  "],
}


def render_word(word: str) -> list[str]:
    rows = ["", "", ""]
    for ch in word.upper():
        glyph = FONT[ch]
        width = max(len(r) for r in glyph)
        for i in range(3):
            rows[i] += glyph[i].ljust(width) + " "
    return rows


def build_banner() -> Text:
    left, right = render_word("AZTHIELS"), render_word("ACCOUNT SWAP")
    t = Text()
    for a, b in zip(left, right):
        t.append(a + "  ", style=f"bold {BORDER}")
        t.append(b + "\n", style=f"bold {TEXT}")
    t.append("— universal multi-service session switcher —", style=MUTED)
    return t
