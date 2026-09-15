"""Automated tests for the non-visual password generation logic.

Run with: python -m unittest test_password_generator.py
"""

import unittest

import password_generator as generator


class PasswordGeneratorTests(unittest.TestCase):
    def test_password_has_requested_length_and_every_category(self):
        options = generator.PasswordOptions(32, True, True, True, True)
        password = generator.generate_password(options)

        self.assertEqual(len(password), 32)
        self.assertTrue(any(character.isupper() for character in password))
        self.assertTrue(any(character.islower() for character in password))
        self.assertTrue(any(character.isdigit() for character in password))
        self.assertTrue(
            any(character in generator.CHARACTER_SETS["Symbols"] for character in password)
        )

    def test_password_has_each_selected_pair(self):
        options = generator.PasswordOptions(16, True, False, True, False)
        password = generator.generate_password(options)

        self.assertTrue(any(character.isupper() for character in password))
        self.assertTrue(any(character.isdigit() for character in password))

    def test_ambiguous_characters_can_be_excluded(self):
        options = generator.PasswordOptions(24, True, True, True, True, True)
        password = generator.generate_password(options)

        self.assertFalse(set(password) & generator.AMBIGUOUS_CHARACTERS)

    def test_invalid_options_are_rejected(self):
        with self.assertRaises(ValueError):
            generator.PasswordOptions(7, True, True, False, False).validate()
        with self.assertRaises(ValueError):
            generator.PasswordOptions(8, True, False, False, False).validate()

    def test_strength_labels(self):
        self.assertEqual(generator.password_strength(8, 2)[0], "Weak")
        self.assertEqual(generator.password_strength(12, 2)[0], "Medium")
        self.assertEqual(generator.password_strength(16, 3)[0], "Strong")


if __name__ == "__main__":
    unittest.main()
