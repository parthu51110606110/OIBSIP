# SkyCast Weather

SkyCast is a beginner-friendly Python desktop weather app. It accepts a city or postal code, shows current weather, a real hourly forecast for the next six hours, and a five-day outlook. It also has Celsius/Fahrenheit conversion, approximate IP-based location detection, weather icons, and in-window error messages.

The app uses [Open-Meteo](https://open-meteo.com/) as the **equivalent free weather API** allowed by the project brief. Unlike OpenWeatherMap's free five-day endpoint, which returns forecast slots every three hours, Open-Meteo supplies a genuine hour-by-hour forecast and requires no API key. Current-condition icons come from OpenWeatherMap's documented public icon URL format.

## Features

- City or postal-code search, with empty-input validation
- Current temperature, humidity, condition, and wind speed
- Hour-by-hour forecast for the next 6 hours and a 5-day forecast
- °C/°F toggle (wind changes between km/h and mph too)
- Downloaded condition icon with a Unicode fallback if the image cannot load
- Optional approximate location detection using `ipinfo.io`
- Friendly in-window messages for unknown locations, timeouts, connectivity problems, and provider errors
- Automated offline unit tests for parsing, conversion, validation, timeouts, unknown locations, and service errors

## Install and run (Windows)

1. Install Python 3.11 or later from [python.org](https://www.python.org/downloads/). During setup, tick **Add Python to PATH**.
2. Open PowerShell in this project folder.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install the two dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Start the app:

   ```powershell
   py weather_app.py
   ```

No API key is needed. If Windows reports that `py` is unknown after installing Python, close and reopen PowerShell, then repeat step 3.

## Manual test checklist

1. Run `py weather_app.py`; a window titled **SkyCast Weather** should open.
2. Click **Get weather** with a blank input. A red, in-window message should ask for a city or postal code; no terminal error should appear.
3. Search for `London` or your own city. Confirm the location, current temperature, condition, humidity, wind speed, six hourly rows, and five daily rows populate.
4. Click **Show °F**. Temperatures should change to °F and wind to mph. Click it again to return to °C and km/h.
5. Search for `not-a-real-place-12345`. A red in-window “No location was found” message should appear, while the last valid forecast stays visible.
6. Click **Use my location**. If the IP provider is available, an approximate city forecast should appear. If it is unavailable or blocked, the app should show a helpful in-window message instead.
7. Disconnect from the internet and search again. The app should show a connection error in the window and remain open.

## Automated checks

Run these from the same activated environment:

```powershell
py -m unittest -v
py -m py_compile weather_client.py weather_app.py test_weather_client.py
```

The tests do not call the internet and do not need a real location or API key. They mock the weather service responses.

## Project files

- `weather_app.py` — Tkinter interface and background loading
- `weather_client.py` — API requests, validation, response parsing, conversions, and friendly errors
- `test_weather_client.py` — offline automated checks
- `requirements.txt` — installable dependencies
