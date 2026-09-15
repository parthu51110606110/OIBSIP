"""Automated checks for the BMI calculator's business and storage logic."""

from pathlib import Path
import tempfile
import unittest

from bmi_calculator import (
    BMIRecord,
    BMIRepository,
    StorageError,
    ValidationError,
    calculate_bmi,
    classify_bmi,
    parse_positive_number,
)


class BMICalculationTests(unittest.TestCase):
    def test_calculates_bmi(self) -> None:
        self.assertAlmostEqual(calculate_bmi(70, 1.75), 22.8571428571)

    def test_standard_bmi_categories_at_boundaries(self) -> None:
        self.assertEqual(classify_bmi(18.49)[0], "Underweight")
        self.assertEqual(classify_bmi(18.5)[0], "Normal")
        self.assertEqual(classify_bmi(24.99)[0], "Normal")
        self.assertEqual(classify_bmi(25)[0], "Overweight")
        self.assertEqual(classify_bmi(29.99)[0], "Overweight")
        self.assertEqual(classify_bmi(30)[0], "Obese")

    def test_rejects_non_numeric_and_non_positive_values(self) -> None:
        for value in ("", "not a number", "-4", "0"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    parse_positive_number(value, "Weight")

    def test_rejects_non_positive_bmi_inputs(self) -> None:
        with self.assertRaises(ValidationError):
            calculate_bmi(0, 1.75)
        with self.assertRaises(ValidationError):
            calculate_bmi(70, -1.75)


class BMIRepositoryTests(unittest.TestCase):
    def test_saves_and_reads_case_insensitive_user_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = BMIRepository(Path(temporary_directory) / "test_records.db")
            first = BMIRecord("Taylor", 70, 1.75, 22.86, "Normal", "2026-09-01T09:00:00")
            second = BMIRecord("Taylor", 72, 1.75, 23.51, "Normal", "2026-09-02T09:00:00")
            repository.save(first)
            repository.save(second)

            history = repository.records_for("taylor")

        self.assertEqual([record.bmi for record in history], [22.86, 23.51])
        self.assertEqual(history[-1].recorded_at, "2026-09-02T09:00:00")

    def test_reports_a_storage_error_when_database_cannot_be_opened(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            unavailable_path = Path(temporary_directory) / "missing" / "records.db"
            with self.assertRaises(StorageError):
                BMIRepository(unavailable_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
