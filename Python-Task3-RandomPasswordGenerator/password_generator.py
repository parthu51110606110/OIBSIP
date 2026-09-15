"""A secure desktop password generator built with Tkinter.

Requires Python 3.8+ and the optional third-party package ``pyperclip`` for
clipboard support.  Run with: python password_generator.py
"""

from __future__ import annotations

import secrets
import string
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

try:
    import pyperclip
except ImportError:  # The GUI remains usable, but copying will explain the fix.
    pyperclip = None


MIN_LENGTH = 8
MAX_LENGTH = 128
AMBIGUOUS_CHARACTERS = frozenset("0OIl1")
CHARACTER_SETS = {
    "Uppercase letters": string.ascii_uppercase,
    "Lowercase letters": string.ascii_lowercase,
    "Numbers": string.digits,
    "Symbols": "!@#$%^&*()-_=+[]{};:,.?",
}


@dataclass(frozen=True)
class PasswordOptions:
    """Validated settings used to create a password."""

    length: int
    include_uppercase: bool
    include_lowercase: bool
    include_numbers: bool
    include_symbols: bool
    exclude_ambiguous: bool = False

    def selected_sets(self) -> list[str]:
        """Return the character pools selected by the user."""
        choices = (
            (self.include_uppercase, "Uppercase letters"),
            (self.include_lowercase, "Lowercase letters"),
            (self.include_numbers, "Numbers"),
            (self.include_symbols, "Symbols"),
        )
        pools = [CHARACTER_SETS[name] for selected, name in choices if selected]
        if self.exclude_ambiguous:
            pools = [
                "".join(character for character in pool if character not in AMBIGUOUS_CHARACTERS)
                for pool in pools
            ]
        return pools

    def validate(self) -> None:
        """Raise ValueError when settings cannot produce a valid password."""
        if not MIN_LENGTH <= self.length <= MAX_LENGTH:
            raise ValueError(f"Password length must be between {MIN_LENGTH} and {MAX_LENGTH}.")

        pools = self.selected_sets()
        if len(pools) < 2:
            raise ValueError("Select at least two character types.")
        if self.length < len(pools):
            raise ValueError("Length must be at least the number of selected character types.")
        if any(not pool for pool in pools):
            raise ValueError("The chosen settings leave an empty character set.")


def secure_shuffle(characters: list[str]) -> None:
    """Shuffle in place with a cryptographically secure Fisher-Yates shuffle."""
    for index in range(len(characters) - 1, 0, -1):
        swap_index = secrets.randbelow(index + 1)
        characters[index], characters[swap_index] = characters[swap_index], characters[index]


def generate_password(options: PasswordOptions) -> str:
    """Generate a password containing at least one character from every selected pool."""
    options.validate()
    pools = options.selected_sets()
    all_characters = "".join(pools)

    # One secure choice per selected category guarantees the requested diversity.
    password_characters = [secrets.choice(pool) for pool in pools]
    password_characters.extend(
        secrets.choice(all_characters) for _ in range(options.length - len(password_characters))
    )
    secure_shuffle(password_characters)
    return "".join(password_characters)


def password_strength(length: int, diversity: int) -> tuple[str, int]:
    """Return a simple strength label and progress value based on length/diversity."""
    score = min(100, (length * 4) + (diversity * 8))
    if length >= 16 and diversity >= 3:
        return "Strong", max(score, 80)
    if length >= 12 and diversity >= 2:
        return "Medium", max(score, 50)
    return "Weak", min(score, 40)


class PasswordGeneratorApp(tk.Tk):
    """Tkinter interface for secure password creation."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Secure Password Generator")
        self.resizable(False, False)
        self.configure(padx=24, pady=24)

        self.length_var = tk.IntVar(value=16)
        self.uppercase_var = tk.BooleanVar(value=True)
        self.lowercase_var = tk.BooleanVar(value=True)
        self.numbers_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=True)
        self.exclude_ambiguous_var = tk.BooleanVar(value=False)
        self.password_var = tk.StringVar(value="Click Generate Password")
        self.status_var = tk.StringVar(value="Choose options, then generate a new password.")
        self.strength_var = tk.StringVar(value="Strength: —")
        self.history: list[str] = []

        self._configure_styles()
        self._build_widgets()
        self._update_strength_preview()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.configure("Weak.Horizontal.TProgressbar", background="#d9534f")
        style.configure("Medium.Horizontal.TProgressbar", background="#f0ad4e")
        style.configure("Strong.Horizontal.TProgressbar", background="#2e8b57")

    def _build_widgets(self) -> None:
        ttk.Label(self, text="Secure Password Generator", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 14)
        )

        ttk.Label(self, text="Password length:").grid(row=1, column=0, sticky="w")
        length_spinbox = ttk.Spinbox(
            self,
            from_=MIN_LENGTH,
            to=MAX_LENGTH,
            textvariable=self.length_var,
            width=8,
            command=self._update_strength_preview,
        )
        length_spinbox.grid(row=1, column=1, sticky="w", padx=(10, 0))
        length_spinbox.bind("<KeyRelease>", lambda _event: self._update_strength_preview())
        ttk.Label(self, text=f"({MIN_LENGTH}–{MAX_LENGTH})").grid(row=1, column=2, sticky="w", padx=(8, 0))

        choices_frame = ttk.LabelFrame(self, text="Include at least two character types", padding=12)
        choices_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=14)
        checkboxes = (
            ("Uppercase letters (A–Z)", self.uppercase_var),
            ("Lowercase letters (a–z)", self.lowercase_var),
            ("Numbers (0–9)", self.numbers_var),
            ("Symbols (!@#$…)", self.symbols_var),
            ("Exclude ambiguous characters (0, O, I, l, 1)", self.exclude_ambiguous_var),
        )
        for row, (label, variable) in enumerate(checkboxes):
            ttk.Checkbutton(
                choices_frame, text=label, variable=variable, command=self._update_strength_preview
            ).grid(row=row, column=0, sticky="w", pady=2)

        ttk.Button(self, text="Generate Password", command=self.generate).grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(0, 12)
        )
        password_entry = ttk.Entry(self, textvariable=self.password_var, width=44, state="readonly")
        password_entry.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Button(self, text="Copy to Clipboard", command=self.copy_password).grid(
            row=4, column=2, sticky="ew", padx=(8, 0)
        )

        self.strength_bar = ttk.Progressbar(self, maximum=100, length=250)
        self.strength_bar.grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Label(self, textvariable=self.strength_var).grid(row=5, column=2, sticky="w", padx=(8, 0), pady=(12, 0))

        ttk.Label(self, textvariable=self.status_var, foreground="#555555", wraplength=430).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(10, 12)
        )

        history_frame = ttk.LabelFrame(self, text="Session history — last 5 passwords", padding=10)
        history_frame.grid(row=7, column=0, columnspan=3, sticky="ew")
        self.history_list = tk.Listbox(history_frame, height=5, width=52, exportselection=False)
        self.history_list.grid(row=0, column=0, sticky="ew")
        self.history_list.bind("<<ListboxSelect>>", self._copy_history_selection)
        ttk.Label(history_frame, text="Select an entry to copy it.", foreground="#555555").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )

    def _options_from_controls(self) -> PasswordOptions:
        try:
            length = int(self.length_var.get())
        except (tk.TclError, ValueError) as error:
            raise ValueError("Password length must be a whole number.") from error
        return PasswordOptions(
            length=length,
            include_uppercase=self.uppercase_var.get(),
            include_lowercase=self.lowercase_var.get(),
            include_numbers=self.numbers_var.get(),
            include_symbols=self.symbols_var.get(),
            exclude_ambiguous=self.exclude_ambiguous_var.get(),
        )

    def _update_strength_preview(self) -> None:
        try:
            options = self._options_from_controls()
            options.validate()
            diversity = len(options.selected_sets())
            strength, value = password_strength(options.length, diversity)
            self.strength_var.set(f"Strength: {strength}")
            self.strength_bar.configure(value=value, style=f"{strength}.Horizontal.TProgressbar")
        except (ValueError, tk.TclError):
            self.strength_var.set("Strength: —")
            self.strength_bar.configure(value=0)

    def generate(self) -> None:
        try:
            options = self._options_from_controls()
            password = generate_password(options)
        except ValueError as error:
            self.status_var.set(str(error))
            messagebox.showerror("Cannot generate password", str(error), parent=self)
            return

        self.password_var.set(password)
        strength, value = password_strength(options.length, len(options.selected_sets()))
        self.strength_var.set(f"Strength: {strength}")
        self.strength_bar.configure(value=value, style=f"{strength}.Horizontal.TProgressbar")
        self._add_to_history(password)

        if self._copy_text(password):
            self.status_var.set("Password generated and copied to the clipboard.")
        else:
            self.status_var.set("Password generated. Clipboard copy was unavailable; use the Copy button after installing pyperclip.")

    def _add_to_history(self, password: str) -> None:
        self.history.insert(0, password)
        self.history = self.history[:5]
        self.history_list.delete(0, tk.END)
        for item in self.history:
            self.history_list.insert(tk.END, item)

    def _copy_text(self, text: str) -> bool:
        if pyperclip is None:
            return False
        try:
            pyperclip.copy(text)
        except pyperclip.PyperclipException:
            return False
        return True

    def copy_password(self) -> None:
        password = self.password_var.get()
        if password == "Click Generate Password":
            self.status_var.set("Generate a password before copying it.")
            return
        if self._copy_text(password):
            self.status_var.set("Password copied to the clipboard.")
        else:
            self.status_var.set("Clipboard support is unavailable. Install pyperclip and try again.")

    def _copy_history_selection(self, _event: tk.Event[tk.Misc]) -> None:
        selection = self.history_list.curselection()
        if not selection:
            return
        password = self.history_list.get(selection[0])
        self.password_var.set(password)
        if self._copy_text(password):
            self.status_var.set("Selected history password copied to the clipboard.")
        else:
            self.status_var.set("Selected password loaded. Clipboard support is unavailable.")


def main() -> None:
    app = PasswordGeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
