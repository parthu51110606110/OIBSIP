"""A desktop weather application powered by the free Open-Meteo API.

Run this file with Python 3.10 or newer.  The app intentionally has no API-key
setup: Open-Meteo supplies the weather data and OpenWeatherMap's public icon
URLs supply condition artwork when Pillow is installed.
"""

from __future__ import annotations

import io
import json
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    import requests
except ImportError:  # The app still runs with the standard-library fallback.
    requests = None  # type: ignore[assignment]

import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
IPINFO_URL = "https://ipinfo.io/json"
REQUEST_TIMEOUT_SECONDS = 12


class WeatherAppError(Exception):
    """Base class for errors safe to show directly in the application UI."""


class InputError(WeatherAppError):
    pass


class CityNotFoundError(WeatherAppError):
    pass


class NetworkTimeoutError(WeatherAppError):
    pass


class NetworkConnectionError(WeatherAppError):
    pass


class ServiceError(WeatherAppError):
    pass


class _HttpStatusError(Exception):
    """Small, provider-neutral HTTP status exception for the fallback client."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class _StandardLibraryResponse:
    def __init__(self, response: Any) -> None:
        self.status_code = getattr(response, "status", 200)
        self.content = response.read()

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise _HttpStatusError(self.status_code)

    def json(self) -> dict[str, Any]:
        return json.loads(self.content.decode("utf-8"))


class _StandardLibrarySession:
    """Minimal requests-like session used when `requests` is not installed."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def get(self, url: str, params: dict[str, Any] | None = None, timeout: int = 12) -> _StandardLibraryResponse:
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{query}"
        request = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return _StandardLibraryResponse(response)
        except urllib.error.HTTPError as error:
            raise _HttpStatusError(error.code) from error


@dataclass(frozen=True)
class CurrentWeather:
    temperature_c: float
    humidity: int
    description: str
    wind_kmh: float
    weather_code: int
    is_day: bool


@dataclass(frozen=True)
class HourlyForecast:
    time: str
    temperature_c: float
    weather_code: int


@dataclass(frozen=True)
class DailyForecast:
    date: str
    high_c: float
    low_c: float
    weather_code: int


@dataclass(frozen=True)
class WeatherReport:
    location_name: str
    current: CurrentWeather
    hourly: list[HourlyForecast]
    daily: list[DailyForecast]
    icon_bytes: bytes | None = None


# WMO weather interpretation codes returned by Open-Meteo.
WMO_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Light freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light rain showers",
    81: "Rain showers",
    82: "Heavy rain showers",
    85: "Light snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}


def description_for(code: int) -> str:
    """Return a readable description even if the provider introduces a code."""
    return WMO_DESCRIPTIONS.get(code, "Unknown conditions")


def icon_code_for(code: int, is_day: bool = True) -> str:
    """Map a WMO code to OpenWeatherMap's public icon code convention."""
    suffix = "d" if is_day else "n"
    if code == 0:
        return f"01{suffix}"
    if code == 1:
        return f"02{suffix}"
    if code in (2, 3):
        return f"03{suffix}" if code == 2 else "04d"
    if code in (45, 48):
        return "50d"
    if code in (71, 73, 75, 77, 85, 86):
        return "13d"
    if code in (95, 96, 99):
        return "11d"
    return "10d"


def icon_url_for(code: int, is_day: bool = True) -> str:
    return f"https://openweathermap.org/img/wn/{icon_code_for(code, is_day)}@2x.png"


def fallback_symbol(code: int, is_day: bool = True) -> str:
    """An offline/Pillow-free visual fallback for the main weather icon."""
    if code == 0:
        return "☀" if is_day else "☾"
    if code in (1, 2, 3):
        return "☁"
    if code in (45, 48):
        return "≋"
    if code in (71, 73, 75, 77, 85, 86):
        return "❄"
    if code in (95, 96, 99):
        return "⚡"
    return "☂"


def celsius_to_fahrenheit(value: float) -> float:
    return value * 9 / 5 + 32


class WeatherService:
    """Fetch and normalise weather data independently of the Tkinter UI."""

    def __init__(self, session: Any | None = None) -> None:
        self.session = session or (requests.Session() if requests is not None else _StandardLibrarySession())
        self.session.headers.update({"User-Agent": "BeginnerWeatherApp/1.0"})

    def _request_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()
        except Exception as error:
            status = getattr(error, "status_code", None)
            if requests is not None and isinstance(error, requests.exceptions.HTTPError):
                status = error.response.status_code if error.response is not None else None
            if status == 401:
                raise ServiceError("The weather service rejected this request (invalid API key or access denied).") from error
            if isinstance(error, _HttpStatusError) or (requests is not None and isinstance(error, requests.exceptions.HTTPError)):
                raise ServiceError("The weather service is unavailable right now. Please try again later.") from error
            if isinstance(error, (TimeoutError, socket.timeout)) or (
                requests is not None and isinstance(error, requests.exceptions.Timeout)
            ):
                raise NetworkTimeoutError("The weather service took too long to respond. Please try again.") from error
            if isinstance(error, (ConnectionError, urllib.error.URLError)) or (
                requests is not None and isinstance(error, requests.exceptions.ConnectionError)
            ):
                raise NetworkConnectionError("Cannot reach the weather service. Check your internet connection.") from error
            raise ServiceError("The weather service sent an unexpected response. Please try again.") from error

        if not isinstance(data, dict):
            raise ServiceError("The weather service sent an unexpected response. Please try again.")
        if data.get("error"):
            raise ServiceError(str(data.get("reason", "The weather service could not complete the request.")))
        return data

    def search_location(self, query: str) -> dict[str, Any]:
        if not query or not query.strip():
            raise InputError("Enter a city name or ZIP/postal code first.")
        data = self._request_json(
            GEOCODING_URL,
            {"name": query.strip(), "count": 1, "language": "en", "format": "json"},
        )
        results = data.get("results")
        if not isinstance(results, list) or not results:
            raise CityNotFoundError("Location not found. Try a city plus country, for example: Paris, France.")
        location = results[0]
        if not isinstance(location, dict) or "latitude" not in location or "longitude" not in location:
            raise ServiceError("The location service returned incomplete data. Please try another location.")
        return location

    def detect_location(self) -> dict[str, Any]:
        """Use ipinfo.io's free endpoint to find the approximate current location."""
        data = self._request_json(IPINFO_URL)
        raw_coordinates = data.get("loc", "")
        try:
            latitude_text, longitude_text = raw_coordinates.split(",", maxsplit=1)
            latitude, longitude = float(latitude_text), float(longitude_text)
        except (AttributeError, TypeError, ValueError):
            raise ServiceError("Could not determine your location automatically. Search for a city instead.")
        return {
            "name": data.get("city") or "Your current location",
            "admin1": data.get("region") or "",
            "country": data.get("country") or "",
            "latitude": latitude,
            "longitude": longitude,
        }

    def get_icon_bytes(self, url: str) -> bytes | None:
        """Fetch an icon opportunistically; weather results remain usable without it."""
        if not PIL_AVAILABLE:
            return None
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.content
        except Exception:
            return None

    def fetch(self, query: str) -> WeatherReport:
        return self.fetch_for_location(self.search_location(query))

    def fetch_for_location(self, location: dict[str, Any]) -> WeatherReport:
        parameters = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,is_day",
            "hourly": "temperature_2m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "timezone": "auto",
            "forecast_days": 5,
        }
        data = self._request_json(FORECAST_URL, parameters)
        try:
            current_data = data["current"]
            current = CurrentWeather(
                temperature_c=float(current_data["temperature_2m"]),
                humidity=int(current_data["relative_humidity_2m"]),
                description=description_for(int(current_data["weather_code"])),
                wind_kmh=float(current_data["wind_speed_10m"]),
                weather_code=int(current_data["weather_code"]),
                is_day=bool(current_data["is_day"]),
            )
            hourly = self._next_six_hours(data["hourly"], str(current_data["time"]))
            daily = self._five_days(data["daily"])
        except (KeyError, TypeError, ValueError) as error:
            raise ServiceError("The weather service returned incomplete forecast data. Please try again.") from error

        location_name = self._format_location(location)
        return WeatherReport(
            location_name=location_name,
            current=current,
            hourly=hourly,
            daily=daily,
            icon_bytes=self.get_icon_bytes(icon_url_for(current.weather_code, current.is_day)),
        )

    @staticmethod
    def _format_location(location: dict[str, Any]) -> str:
        pieces = [location.get("name"), location.get("admin1"), location.get("country")]
        return ", ".join(str(piece) for piece in pieces if piece and str(piece).strip())

    @staticmethod
    def _next_six_hours(hourly_data: dict[str, Any], current_time: str) -> list[HourlyForecast]:
        times = hourly_data["time"]
        temperatures = hourly_data["temperature_2m"]
        codes = hourly_data["weather_code"]
        if not (isinstance(times, list) and len(times) == len(temperatures) == len(codes)):
            raise ValueError("Mismatched hourly forecast data")

        try:
            now = datetime.fromisoformat(current_time)
            start_index = next(
                index for index, value in enumerate(times) if datetime.fromisoformat(value) >= now
            )
        except (StopIteration, ValueError):
            start_index = 0

        forecast = []
        for index in range(start_index, min(start_index + 6, len(times))):
            forecast.append(
                HourlyForecast(
                    time=str(times[index]),
                    temperature_c=float(temperatures[index]),
                    weather_code=int(codes[index]),
                )
            )
        if not forecast:
            raise ValueError("Empty hourly forecast data")
        return forecast

    @staticmethod
    def _five_days(daily_data: dict[str, Any]) -> list[DailyForecast]:
        dates = daily_data["time"]
        highs = daily_data["temperature_2m_max"]
        lows = daily_data["temperature_2m_min"]
        codes = daily_data["weather_code"]
        if not (isinstance(dates, list) and len(dates) == len(highs) == len(lows) == len(codes)):
            raise ValueError("Mismatched daily forecast data")
        forecast = [
            DailyForecast(str(dates[index]), float(highs[index]), float(lows[index]), int(codes[index]))
            for index in range(min(5, len(dates)))
        ]
        if not forecast:
            raise ValueError("Empty daily forecast data")
        return forecast


class WeatherApp(tk.Tk):
    """Tkinter interface. Network work runs off the main event loop."""

    BACKGROUND = "#eef4fb"
    CARD = "#ffffff"
    PRIMARY = "#1667b7"
    TEXT = "#17324d"
    MUTED = "#5f7285"

    def __init__(self) -> None:
        super().__init__()
        self.title("SkyCast Weather")
        self.geometry("1050x735")
        self.minsize(900, 650)
        self.configure(bg=self.BACKGROUND)
        self.service = WeatherService()
        self.report: WeatherReport | None = None
        self.use_fahrenheit = False
        self.icon_photo: ImageTk.PhotoImage | None = None
        self.city_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Search for a city or use your approximate IP location.")
        self._configure_styles()
        self._build_ui()
        self.bind("<Return>", lambda _event: self.get_weather())

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8))
        style.configure("Primary.TButton", foreground="white", background=self.PRIMARY)
        style.map("Primary.TButton", background=[("active", "#0d5599"), ("disabled", "#8db7dd")])
        style.configure("TEntry", padding=9, font=("Segoe UI", 11))

    def _build_ui(self) -> None:
        shell = tk.Frame(self, bg=self.BACKGROUND, padx=28, pady=22)
        shell.pack(fill="both", expand=True)

        tk.Label(shell, text="SkyCast", bg=self.BACKGROUND, fg=self.TEXT, font=("Segoe UI", 25, "bold")).pack(anchor="w")
        tk.Label(
            shell,
            text="Current conditions and a five-day outlook — no API key required.",
            bg=self.BACKGROUND,
            fg=self.MUTED,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(0, 16))

        controls = tk.Frame(shell, bg=self.BACKGROUND)
        controls.pack(fill="x", pady=(0, 6))
        self.city_entry = ttk.Entry(controls, textvariable=self.city_var, width=43)
        self.city_entry.pack(side="left", fill="x", expand=True)
        self.search_button = ttk.Button(controls, text="Get Weather", style="Primary.TButton", command=self.get_weather)
        self.search_button.pack(side="left", padx=(10, 7))
        self.location_button = ttk.Button(controls, text="Use My Location", command=self.use_my_location)
        self.location_button.pack(side="left")
        self.unit_button = ttk.Button(controls, text="Show °F", command=self.toggle_units)
        self.unit_button.pack(side="left", padx=(7, 0))

        self.status_label = tk.Label(
            shell,
            textvariable=self.status_var,
            bg=self.BACKGROUND,
            fg=self.MUTED,
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.status_label.pack(fill="x", pady=(0, 12))

        self.current_card = tk.Frame(shell, bg=self.CARD, padx=24, pady=20, highlightthickness=1, highlightbackground="#d7e2ed")
        self.current_card.pack(fill="x")
        self.location_label = tk.Label(self.current_card, text="No weather loaded", bg=self.CARD, fg=self.TEXT, font=("Segoe UI", 18, "bold"))
        self.location_label.grid(row=0, column=0, columnspan=3, sticky="w")
        self.updated_label = tk.Label(self.current_card, text="", bg=self.CARD, fg=self.MUTED, font=("Segoe UI", 9))
        self.updated_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(1, 12))
        self.icon_label = tk.Label(self.current_card, text="☀", bg=self.CARD, fg="#f3ae21", font=("Segoe UI Symbol", 48))
        self.icon_label.grid(row=2, column=0, rowspan=2, sticky="w", padx=(5, 20))
        self.temperature_label = tk.Label(self.current_card, text="—", bg=self.CARD, fg=self.TEXT, font=("Segoe UI", 36, "bold"))
        self.temperature_label.grid(row=2, column=1, sticky="sw")
        self.condition_label = tk.Label(self.current_card, text="Enter a location to begin", bg=self.CARD, fg=self.MUTED, font=("Segoe UI", 12))
        self.condition_label.grid(row=3, column=1, sticky="nw")
        self.details_label = tk.Label(self.current_card, text="Humidity  —     Wind  —", bg=self.CARD, fg=self.TEXT, font=("Segoe UI", 12))
        self.details_label.grid(row=2, column=2, rowspan=2, sticky="e", padx=(30, 4))
        self.current_card.columnconfigure(1, weight=1)

        forecast_area = tk.Frame(shell, bg=self.BACKGROUND)
        forecast_area.pack(fill="both", expand=True, pady=(17, 0))
        hourly_container = tk.Frame(forecast_area, bg=self.CARD, padx=18, pady=16, highlightthickness=1, highlightbackground="#d7e2ed")
        hourly_container.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(hourly_container, text="Next 6 Hours", bg=self.CARD, fg=self.TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 12))
        self.hourly_cards = tk.Frame(hourly_container, bg=self.CARD)
        self.hourly_cards.pack(fill="both", expand=True)

        daily_container = tk.Frame(forecast_area, bg=self.CARD, padx=18, pady=16, highlightthickness=1, highlightbackground="#d7e2ed")
        daily_container.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(daily_container, text="5-Day Forecast", bg=self.CARD, fg=self.TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 7))
        self.daily_rows = tk.Frame(daily_container, bg=self.CARD)
        self.daily_rows.pack(fill="both", expand=True)

        tk.Label(
            shell,
            text="Weather data: Open-Meteo • Icons: OpenWeatherMap • Location option: IPinfo",
            bg=self.BACKGROUND,
            fg=self.MUTED,
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(12, 0))

    def get_weather(self) -> None:
        query = self.city_var.get().strip()
        if not query:
            self._show_error("Enter a city name or ZIP/postal code first.")
            return
        self._run_request(lambda: self.service.fetch(query))

    def use_my_location(self) -> None:
        self._run_request(lambda: self.service.fetch_for_location(self.service.detect_location()))

    def _run_request(self, work: Any) -> None:
        self.search_button.configure(state="disabled")
        self.location_button.configure(state="disabled")
        self.status_label.configure(fg=self.MUTED)
        self.status_var.set("Fetching the latest weather…")
        threading.Thread(target=self._worker, args=(work,), daemon=True).start()

    def _worker(self, work: Any) -> None:
        try:
            report = work()
        except WeatherAppError as error:
            self.after(0, lambda: self._show_error(str(error)))
        except Exception:
            self.after(0, lambda: self._show_error("Something unexpected went wrong. Please try again."))
        else:
            self.after(0, lambda: self._show_report(report))

    def _set_idle(self) -> None:
        self.search_button.configure(state="normal")
        self.location_button.configure(state="normal")

    def _show_error(self, message: str) -> None:
        self._set_idle()
        self.status_label.configure(fg="#b42318")
        self.status_var.set(message)

    def _show_report(self, report: WeatherReport) -> None:
        self._set_idle()
        self.report = report
        self.status_label.configure(fg="#188038")
        self.status_var.set("Weather updated successfully.")
        self._render_report()

    def toggle_units(self) -> None:
        self.use_fahrenheit = not self.use_fahrenheit
        self.unit_button.configure(text="Show °C" if self.use_fahrenheit else "Show °F")
        if self.report:
            self._render_report()

    def _format_temperature(self, celsius: float) -> str:
        value = celsius_to_fahrenheit(celsius) if self.use_fahrenheit else celsius
        unit = "°F" if self.use_fahrenheit else "°C"
        return f"{value:.0f}{unit}"

    @staticmethod
    def _short_time(time_value: str) -> str:
        try:
            return datetime.fromisoformat(time_value).strftime("%I %p").lstrip("0")
        except ValueError:
            return time_value

    @staticmethod
    def _short_date(date_value: str) -> str:
        try:
            return datetime.fromisoformat(date_value).strftime("%a, %b %d")
        except ValueError:
            return date_value

    def _render_report(self) -> None:
        if not self.report:
            return
        report = self.report
        current = report.current
        self.location_label.configure(text=report.location_name)
        self.updated_label.configure(text=f"Updated for local time • {datetime.now().strftime('%I:%M %p').lstrip('0')}")
        self.temperature_label.configure(text=self._format_temperature(current.temperature_c))
        self.condition_label.configure(
            text=(
                f"{current.description}  •  "
                f"{current.temperature_c:.1f}°C / {celsius_to_fahrenheit(current.temperature_c):.1f}°F"
            )
        )
        wind = current.wind_kmh * 0.621371 if self.use_fahrenheit else current.wind_kmh
        wind_unit = "mph" if self.use_fahrenheit else "km/h"
        self.details_label.configure(text=f"Humidity  {current.humidity}%\nWind  {wind:.1f} {wind_unit}")
        self._set_main_icon(report.icon_bytes, current.weather_code, current.is_day)
        self._render_hourly(report.hourly)
        self._render_daily(report.daily)

    def _set_main_icon(self, raw_icon: bytes | None, code: int, is_day: bool) -> None:
        self.icon_photo = None
        if raw_icon and PIL_AVAILABLE:
            try:
                image = Image.open(io.BytesIO(raw_icon)).convert("RGBA").resize((80, 80))
                self.icon_photo = ImageTk.PhotoImage(image)
                self.icon_label.configure(image=self.icon_photo, text="")
                return
            except Exception:
                pass
        self.icon_label.configure(image="", text=fallback_symbol(code, is_day))

    def _render_hourly(self, forecast: list[HourlyForecast]) -> None:
        for child in self.hourly_cards.winfo_children():
            child.destroy()
        for item in forecast:
            card = tk.Frame(self.hourly_cards, bg="#f4f8fc", padx=7, pady=10)
            card.pack(side="left", fill="both", expand=True, padx=3)
            tk.Label(card, text=self._short_time(item.time), bg="#f4f8fc", fg=self.MUTED, font=("Segoe UI", 9, "bold")).pack()
            tk.Label(card, text=fallback_symbol(item.weather_code), bg="#f4f8fc", fg=self.PRIMARY, font=("Segoe UI Symbol", 22)).pack(pady=5)
            tk.Label(card, text=self._format_temperature(item.temperature_c), bg="#f4f8fc", fg=self.TEXT, font=("Segoe UI", 10, "bold")).pack()

    def _render_daily(self, forecast: list[DailyForecast]) -> None:
        for child in self.daily_rows.winfo_children():
            child.destroy()
        for item in forecast:
            row = tk.Frame(self.daily_rows, bg=self.CARD, pady=7)
            row.pack(fill="x")
            tk.Label(row, text=self._short_date(item.date), bg=self.CARD, fg=self.TEXT, font=("Segoe UI", 10, "bold"), width=13, anchor="w").pack(side="left")
            tk.Label(row, text=fallback_symbol(item.weather_code), bg=self.CARD, fg=self.PRIMARY, font=("Segoe UI Symbol", 17), width=3).pack(side="left")
            tk.Label(
                row,
                text=f"{self._format_temperature(item.low_c)}  /  {self._format_temperature(item.high_c)}",
                bg=self.CARD,
                fg=self.MUTED,
                font=("Segoe UI", 10),
            ).pack(side="right")


if __name__ == "__main__":
    try:
        app = WeatherApp()
    except tk.TclError as error:
        raise SystemExit(
            "Tkinter could not start. Install the standard Python distribution with Tcl/Tk support, "
            "then run this app again."
        ) from error
    app.city_entry.focus_set()
    app.mainloop()
