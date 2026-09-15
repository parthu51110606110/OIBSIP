"""Offline tests for the weather application's response parsing and errors."""

import unittest

from weather_app import (
    CityNotFoundError,
    InputError,
    NetworkTimeoutError,
    WeatherService,
    celsius_to_fahrenheit,
    description_for,
    icon_code_for,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.content = b""

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.headers = {}

    def get(self, _url, **_kwargs):
        return FakeResponse(next(self.payloads))


class TimeoutSession:
    def __init__(self):
        self.headers = {}

    def get(self, _url, **_kwargs):
        raise TimeoutError()


class WeatherServiceTests(unittest.TestCase):
    def setUp(self):
        self.forecast_payload = {
            "current": {
                "time": "2026-09-15T09:00",
                "temperature_2m": 27.5,
                "relative_humidity_2m": 65,
                "weather_code": 2,
                "wind_speed_10m": 14.2,
                "is_day": 1,
            },
            "hourly": {
                "time": [f"2026-09-15T{hour:02d}:00" for hour in range(8, 16)],
                "temperature_2m": [26, 27, 28, 29, 30, 31, 30, 29],
                "weather_code": [1, 2, 2, 3, 61, 61, 3, 2],
            },
            "daily": {
                "time": [f"2026-09-{day:02d}" for day in range(15, 20)],
                "temperature_2m_max": [32, 33, 34, 31, 30],
                "temperature_2m_min": [24, 25, 25, 23, 22],
                "weather_code": [2, 61, 3, 0, 80],
            },
        }

    def test_fetch_builds_current_hourly_and_daily_report(self):
        geocoding_payload = {
            "results": [{"name": "Delhi", "admin1": "Delhi", "country": "India", "latitude": 28.61, "longitude": 77.21}]
        }
        service = WeatherService(FakeSession([geocoding_payload, self.forecast_payload]))
        service.get_icon_bytes = lambda _url: None

        report = service.fetch("Delhi")

        self.assertEqual(report.location_name, "Delhi, Delhi, India")
        self.assertEqual(report.current.description, "Partly cloudy")
        self.assertEqual(report.current.humidity, 65)
        self.assertEqual(len(report.hourly), 6)
        self.assertEqual(report.hourly[0].time, "2026-09-15T09:00")
        self.assertEqual(len(report.daily), 5)
        self.assertEqual(report.daily[0].high_c, 32.0)

    def test_empty_input_is_rejected_before_a_network_call(self):
        service = WeatherService(FakeSession([]))
        with self.assertRaises(InputError):
            service.fetch("   ")

    def test_unknown_city_has_a_clear_error(self):
        service = WeatherService(FakeSession([{}]))
        with self.assertRaises(CityNotFoundError):
            service.fetch("A city that does not exist")

    def test_timeout_has_a_clear_error(self):
        service = WeatherService(TimeoutSession())
        with self.assertRaises(NetworkTimeoutError):
            service.fetch("Delhi")

    def test_small_helper_functions(self):
        self.assertEqual(celsius_to_fahrenheit(0), 32)
        self.assertEqual(description_for(95), "Thunderstorm")
        self.assertEqual(icon_code_for(0, False), "01n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
