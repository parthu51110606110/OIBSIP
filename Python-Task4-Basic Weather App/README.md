# SkyCast Weather App

SkyCast is a Python/Tkinter desktop weather app. It accepts a city name or ZIP/postal code, shows current weather, a six-hour forecast, a five-day forecast, condition icons, and a Celsius/Fahrenheit switch. The **Use My Location** button requests an approximate location from your public IP address.

It uses Open-Meteo instead of OpenWeatherMap for weather data. Open-Meteo is an equivalent free API and needs no API key, so you can run the project immediately. The app maps the returned WMO weather codes to OpenWeatherMap's public icon URLs and falls back to a built-in symbol if an icon cannot load.

## What you need

- Windows, macOS, or Linux
- Python 3.10 or newer, including Tkinter (the standard Python installer includes it on Windows)
- An internet connection for live weather

If `py --version` says that `py` is not recognized, install Python from [python.org/downloads](https://www.python.org/downloads/). During installation, leave the default Tcl/Tk option selected and tick **Add Python to PATH**. Then open a fresh terminal and run `py --version` again.

## Easiest way to run it (Windows)

You do **not** need to make a virtual environment or install packages first. Follow these exact small steps:

1. Open PowerShell in this folder whare you save the files,Then give the commands
2. Copy and paste this line. Then press **Enter**:

   ```powershell
   cd "C:\Users\Aryan\Documents\Codex\2026-09-15\basic-weather-app-objective-build-a-3\outputs\weather_app"
   ```

3. Type this and press **Enter**:

   ```powershell
   dir
   ```

   You must see `weather_app.py`, `test_weather_app.py`, and `requirements.txt`. If you do not see those names, stop: you are in the wrong folder.

4. Type this and press **Enter** to check the code:

   ```powershell
   py -m unittest -v
   ```

   You should see `Ran 5 tests` and `OK`.

5. Type this and press **Enter** to open the weather app:

   ```powershell
   py weather_app.py
   ```

6. A window named **SkyCast Weather** opens. Type `Delhi` in the white box and click **Get Weather**.

### Optional: better downloaded weather icons

The app already works without this. If you want it to download OpenWeatherMap icon images instead of using built-in symbols, run this after step 3:

```powershell
py -m pip install -r requirements.txt
```

## Manual check list

1. Search **Delhi**. The current card should show a location, a temperature, humidity, wind, a condition description, six hourly tiles, and five daily rows.
2. Click **Show °F**. Every temperature should change to Fahrenheit and wind should change from km/h to mph. Click **Show °C** to change back.
3. Search **London, UK**. The card and forecasts should update, with no terminal messages required.
4. Delete the search text and click **Get Weather**. A red, in-window message should say that a city or postal code is required.
5. Search `A city that does not exist`. A red, in-window “Location not found” message should appear.
6. With the internet connected, click **Use My Location**. It should update with an approximate IP-based location. If your network blocks IP location services, the app shows an in-window error and the city search still works.
7. Optional network-error test: temporarily disconnect the internet and search any city. After the timeout, an in-window connection/timeout message should appear; reconnect and search again.

## Project files

- `weather_app.py` — the complete GUI and API client
- `test_weather_app.py` — offline automated tests with mocked API responses
- `requirements.txt` — Python dependencies

## API notes

- Weather and city/ZIP lookup: [Open-Meteo Forecast API](https://open-meteo.com/en/docs) and [Geocoding API](https://open-meteo.com/en/docs/geocoding-api)
- Condition artwork: [OpenWeatherMap weather icons](https://openweathermap.org/weather-conditions)
- Approximate IP location: [IPinfo](https://ipinfo.io/)

Open-Meteo's `current`, `hourly`, and `daily` fields are parsed into small Python data classes. Network timeout, connection failure, bad service responses, unknown city, empty input, and a 401-style access error are converted into understandable GUI messages.


- `weather_app.py` — Tkinter interface and background loading
- `weather_client.py` — API requests, validation, response parsing, conversions, and friendly errors
- `test_weather_client.py` — offline automated checks
- `requirements.txt` — installable dependencies
