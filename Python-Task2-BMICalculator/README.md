# BMI Calculator

A desktop Python BMI calculator with named user records, SQLite persistence, colour-coded feedback, and a Matplotlib trend chart.

## Run it

1. Install Matplotlib once, if needed:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Confirm that your Python installation includes Tkinter (this should open a small demonstration window):

   ```powershell
   python -m tkinter
   ```

   If this fails, install a standard Python distribution with Tcl/Tk support before continuing.

3. Start the desktop app:

   ```powershell
   python .\bmi_calculator.py
   ```

Records are stored privately on this computer in `bmi_records.db` beside the program. Enter a name, weight in kilograms, and height in metres, then choose **Calculate & Save**. Use **Show Trend** to open the selected user's chart.

## Checks

Run the non-GUI automated tests:

```powershell
python -m unittest -v
```

The calculator rejects missing, non-numeric, zero, and negative weight/height values. It uses these standard cutoffs: underweight below 18.5, normal from 18.5 to below 25, overweight from 25 to below 30, and obese at 30 or above.

BMI is a screening measure and is not medical advice or a diagnosis.
