# Secure Password Generator

A beginner-friendly Python GUI that generates cryptographically secure passwords. It uses `secrets`, not `random`, and includes all requested advanced features.

## Features

- Password length control from 8 to 128 characters
- Uppercase, lowercase, numbers, and symbols checkboxes; at least two types are required
- Secure `secrets`-based generation that guarantees one character from each selected type
- Visual Weak / Medium / Strong indicator based on length and selected character diversity
- Automatically copies a newly generated password to the clipboard, plus a manual Copy button
- Ambiguous-character exclusion for `0`, `O`, `I`, `l`, and `1`
- In-memory session history of the five most recent passwords only; nothing is saved to disk
- Clear validation messages for incorrect settings

## Run it locally

1. Install [Python 3.8 or later](https://www.python.org/downloads/). During installation on Windows, select **Add Python to PATH**.
2. Open PowerShell in this folder.
3. Install the one extra package:

   ```powershell
   py -m pip install -r requirements.txt
   ```

4. Start the program:

   ```powershell
   py password_generator.py
   ```

5. Select at least two character types, choose a length of 8 or greater, and click **Generate Password**. Each generated password is copied automatically.

## Run the automated checks

From this same folder, run:

```powershell
py -m unittest test_password_generator.py
```

The tests cover validation, requested-character guarantees, ambiguous-character exclusion, and the strength labels. If your computer uses `python` instead of `py`, replace `py` with `python` in every command.

> Security note: Clipboard contents can be read by other applications. Paste the password where needed, then replace or clear your clipboard if appropriate.

## Verification performed

- Compiled the application to catch Python syntax errors.
- Ran automated checks for minimum length, invalid-selection rejection, required character-category presence, ambiguous-character exclusion, and strength labels.
- Started the Tkinter program successfully. The current workspace did not have `pyperclip` installed, so its clipboard action could not be tested here; install from `requirements.txt` before using the application.

## Upload to GitHub (step by step)

### 1. Create an empty repository on GitHub

1. Sign in at [github.com](https://github.com/).
2. Click the **+** menu in the top-right, then choose **New repository**.
3. Name it `secure-password-generator` (or choose your own name).
4. Choose **Public** to share it or **Private** to keep it personal.
5. Do **not** select “Add a README file”, “Add .gitignore”, or a license—the project already contains a README.
6. Click **Create repository** and leave the page open.

### 2. Initialize and commit from PowerShell

Open PowerShell in the folder holding these three files, then run the following one at a time:

```powershell
git init
git add password_generator.py requirements.txt README.md test_password_generator.py
git commit -m "Add secure Tkinter password generator"
git branch -M main
```

### 3. Connect and push

Copy the HTTPS repository address shown by GitHub. It looks like `https://github.com/YOUR-USERNAME/secure-password-generator.git`. Then run:

```powershell
git remote add origin https://github.com/YOUR-USERNAME/secure-password-generator.git
git push -u origin main
```

When GitHub asks you to sign in, complete the browser sign-in. GitHub no longer accepts an account password for Git over HTTPS; approve the sign-in or use a personal access token if asked.

### 4. Confirm it uploaded

Refresh the GitHub repository page. You should see the application, its dependency list, README, and automated test file. The project can then be cloned and run by anyone who follows **Run it locally** above.

## Learning references

- [Python `secrets` documentation](https://docs.python.org/3/library/secrets.html) explains why `secrets` is preferred over `random` for passwords.
- [Pyperclip documentation](https://pyperclip.readthedocs.io/) describes clipboard integration with `pyperclip.copy()`.
- [Tkinter password-generator tutorial](https://www.youtube.com/watch?v=TUKEoM21j40) is a GUI-oriented learning reference.
