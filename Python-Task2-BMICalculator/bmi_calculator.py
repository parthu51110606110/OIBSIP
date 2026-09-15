"""BMI Calculator desktop application.

Run this file with Python to open the Tkinter interface.  BMI records are
stored locally in ``bmi_records.db`` beside this file.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Iterable


DATABASE_PATH = Path(__file__).with_name("bmi_records.db")


class ValidationError(ValueError):
    """Raised when a form value cannot be used for a BMI calculation."""


class StorageError(RuntimeError):
    """Raised when a BMI record cannot be read from or written to storage."""


@dataclass(frozen=True)
class BMIRecord:
    """One saved BMI measurement."""

    user_name: str
    weight_kg: float
    height_m: float
    bmi: float
    category: str
    recorded_at: str


def parse_positive_number(value: str, field_name: str) -> float:
    """Return a positive number from a form field, or a helpful validation error."""
    try:
        number = float(value.strip())
    except (AttributeError, ValueError):
        raise ValidationError(f"{field_name} must be a number.") from None

    if number <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return number


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate BMI from kilograms and metres."""
    if weight_kg <= 0 or height_m <= 0:
        raise ValidationError("Weight and height must both be greater than zero.")
    return weight_kg / height_m**2


def classify_bmi(bmi: float) -> tuple[str, str]:
    """Return the standard BMI category and its display colour."""
    if bmi < 18.5:
        return "Underweight", "#1976d2"
    if bmi < 25:
        return "Normal", "#2e7d32"
    if bmi < 30:
        return "Overweight", "#ed6c02"
    return "Obese", "#c62828"


class BMIRepository:
    """SQLite storage for BMI records, with errors normalised for the GUI."""

    def __init__(self, database_path: Path | str = DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self._create_table()

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row
            return connection
        except sqlite3.Error as error:
            raise StorageError(f"Could not open the BMI database: {error}") from error

    def _create_table(self) -> None:
        query = """
            CREATE TABLE IF NOT EXISTS bmi_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                height_m REAL NOT NULL,
                bmi REAL NOT NULL,
                category TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            )
        """
        connection = self._connect()
        try:
            with connection:
                connection.execute(query)
        except sqlite3.Error as error:
            raise StorageError(f"Could not prepare the BMI database: {error}") from error
        finally:
            connection.close()

    def save(self, record: BMIRecord) -> None:
        query = """
            INSERT INTO bmi_records
                (user_name, weight_kg, height_m, bmi, category, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    query,
                    (
                        record.user_name,
                        record.weight_kg,
                        record.height_m,
                        record.bmi,
                        record.category,
                        record.recorded_at,
                    ),
                )
        except sqlite3.Error as error:
            raise StorageError(f"Could not save the BMI record: {error}") from error
        finally:
            connection.close()

    def records_for(self, user_name: str) -> list[BMIRecord]:
        query = """
            SELECT user_name, weight_kg, height_m, bmi, category, recorded_at
            FROM bmi_records
            WHERE user_name = ? COLLATE NOCASE
            ORDER BY recorded_at ASC, id ASC
        """
        connection = self._connect()
        try:
            with connection:
                rows = connection.execute(query, (user_name,)).fetchall()
        except sqlite3.Error as error:
            raise StorageError(f"Could not read BMI history: {error}") from error
        finally:
            connection.close()

        return [
            BMIRecord(
                user_name=row["user_name"],
                weight_kg=row["weight_kg"],
                height_m=row["height_m"],
                bmi=row["bmi"],
                category=row["category"],
                recorded_at=row["recorded_at"],
            )
            for row in rows
        ]


class BMICalculatorApp(tk.Tk):
    """The BMI Calculator window."""

    def __init__(self, repository: BMIRepository | None = None) -> None:
        super().__init__()
        self.repository = repository or BMIRepository()
        self.title("BMI Calculator")
        self.minsize(620, 540)
        self.columnconfigure(0, weight=1)

        self.name_var = tk.StringVar()
        self.weight_var = tk.StringVar()
        self.height_var = tk.StringVar()
        self.result_var = tk.StringVar(value="Enter your details to calculate BMI.")
        self.history_var = tk.StringVar(value="No records loaded yet.")
        self._build_interface()

    def _build_interface(self) -> None:
        container = ttk.Frame(self, padding=24)
        container.grid(sticky="nsew")
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="BMI Calculator", font=("Segoe UI", 20, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        ttk.Label(
            container,
            text="BMI is a screening measure, not a medical diagnosis.",
            foreground="#555555",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 18))

        fields = (
            ("Name", self.name_var, "For example: Alex"),
            ("Weight (kg)", self.weight_var, "For example: 70"),
            ("Height (m)", self.height_var, "For example: 1.75"),
        )
        for row, (label, variable, hint) in enumerate(fields, start=2):
            ttk.Label(container, text=label + ":").grid(row=row, column=0, sticky="w", pady=6)
            entry = ttk.Entry(container, textvariable=variable, width=34)
            entry.grid(row=row, column=1, sticky="ew", pady=6)
            entry.insert(0, "")
            entry.configure(takefocus=True)
            ttk.Label(container, text=hint, foreground="#666666").grid(
                row=row, column=2, sticky="w", padx=(10, 0)
            )

        button_row = ttk.Frame(container)
        button_row.grid(row=5, column=0, columnspan=3, sticky="w", pady=(14, 18))
        ttk.Button(button_row, text="Calculate & Save", command=self.calculate_and_save).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(button_row, text="Show Trend", command=self.show_trend).grid(row=0, column=1)

        self.result_label = tk.Label(
            container,
            textvariable=self.result_var,
            anchor="w",
            justify="left",
            font=("Segoe UI", 12, "bold"),
            fg="#333333",
        )
        self.result_label.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 18))

        ttk.Separator(container).grid(row=7, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        ttk.Label(container, text="Saved history", font=("Segoe UI", 12, "bold")).grid(
            row=8, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(container, textvariable=self.history_var, justify="left", wraplength=550).grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

    def _form_record(self) -> BMIRecord:
        name = self.name_var.get().strip()
        if not name:
            raise ValidationError("Please enter a name to save a BMI record.")
        weight = parse_positive_number(self.weight_var.get(), "Weight")
        height = parse_positive_number(self.height_var.get(), "Height")
        bmi = calculate_bmi(weight, height)
        category, _ = classify_bmi(bmi)
        return BMIRecord(
            user_name=name,
            weight_kg=weight,
            height_m=height,
            bmi=bmi,
            category=category,
            recorded_at=datetime.now().isoformat(timespec="seconds"),
        )

    def calculate_and_save(self) -> None:
        try:
            record = self._form_record()
            self.repository.save(record)
            _, colour = classify_bmi(record.bmi)
        except ValidationError as error:
            self.result_label.configure(fg="#c62828")
            self.result_var.set(str(error))
            return
        except StorageError as error:
            messagebox.showerror("Database error", str(error), parent=self)
            return

        self.result_label.configure(fg=colour)
        self.result_var.set(
            f"BMI: {record.bmi:.2f} — {record.category}. Record saved for {record.user_name}."
        )
        self._refresh_history(record.user_name)

    def _refresh_history(self, user_name: str) -> None:
        try:
            records = self.repository.records_for(user_name)
        except StorageError as error:
            messagebox.showerror("Database error", str(error), parent=self)
            return
        self.history_var.set(self._history_text(records))

    @staticmethod
    def _history_text(records: Iterable[BMIRecord]) -> str:
        items = list(records)
        if not items:
            return "No saved records for this name yet."
        latest = items[-1]
        return (
            f"{len(items)} record(s) for {latest.user_name}. Latest: "
            f"{latest.recorded_at.replace('T', ' ')} — BMI {latest.bmi:.2f} ({latest.category})."
        )

    def show_trend(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            self.result_label.configure(fg="#c62828")
            self.result_var.set("Enter a name to view that person's BMI trend.")
            return
        try:
            records = self.repository.records_for(name)
        except StorageError as error:
            messagebox.showerror("Database error", str(error), parent=self)
            return
        if not records:
            self.result_label.configure(fg="#c62828")
            self.result_var.set(f"No saved records found for {name}.")
            return

        try:
            self._open_chart(name, records)
        except (ImportError, RuntimeError, tk.TclError) as error:
            messagebox.showerror(
                "Chart unavailable",
                "Could not display the chart. Ensure matplotlib is installed.\n\n" + str(error),
                parent=self,
            )

    def _open_chart(self, name: str, records: list[BMIRecord]) -> None:
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        window = tk.Toplevel(self)
        window.title(f"BMI Trend — {name}")
        window.minsize(700, 450)

        dates = [datetime.fromisoformat(record.recorded_at) for record in records]
        values = [record.bmi for record in records]
        figure = Figure(figsize=(7, 4.5), dpi=100, constrained_layout=True)
        axes = figure.add_subplot()
        axes.plot(dates, values, marker="o", color="#1565c0", linewidth=2)
        axes.axhspan(18.5, 25, color="#c8e6c9", alpha=0.5, label="Normal BMI range")
        axes.set_title(f"BMI trend for {name}")
        axes.set_xlabel("Date")
        axes.set_ylabel("BMI")
        axes.grid(True, alpha=0.3)
        axes.legend()
        figure.autofmt_xdate()

        canvas = FigureCanvasTkAgg(figure, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


def main() -> None:
    """Launch the desktop application."""
    try:
        app = BMICalculatorApp()
    except StorageError as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("BMI Calculator", str(error), parent=root)
        root.destroy()
        return
    app.mainloop()


if __name__ == "__main__":
    main()
