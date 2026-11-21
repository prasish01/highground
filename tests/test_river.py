"""Tests for the HBRC Hilltop river gauge. No network: httpx.get is faked."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from highground import river
from highground.river import (
    RiverStatus,
    build_url,
    get_river_status,
    parse_hilltop_xml,
    status_from_readings,
)

FIXTURES = Path(__file__).parent / "fixtures"
REAL = (FIXTURES / "hilltop_fernhill_stage_real.xml").read_text()
RISING = (FIXTURES / "hilltop_rising_sample.xml").read_text()
ERROR = (FIXTURES / "hilltop_error.xml").read_text()


class FakeResponse:
    def __init__(self, text: str, status: int = 200):
        self.text = text
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise river.httpx.HTTPStatusError("bad", request=None, response=None)


def fake_get(monkeypatch, text: str, status: int = 200, seen: dict | None = None):
    def _get(url, timeout):
        if seen is not None:
            seen.update(url=url, timeout=timeout)
        return FakeResponse(text, status)

    monkeypatch.setattr(river.httpx, "get", _get)


def test_parse_real_hbrc_response():
    readings = parse_hilltop_xml(REAL)
    assert len(readings) == 285
    first_t, first_v = readings[0]
    last_t, last_v = readings[-1]
    assert first_t < last_t
    assert last_v == pytest.approx(2.732)  # 2732 mm -> metres
    assert first_v == pytest.approx(2.771)
    # NZ local time, made timezone-aware (NZDT is UTC+13 in November)
    assert last_t.utcoffset() == timedelta(hours=13)


def test_real_data_is_not_rising():
    status = status_from_readings(parse_hilltop_xml(REAL))
    assert status == RiverStatus(
        site="Ngaruroro River at Fernhill",
        level_m=2.732,
        observed_at=parse_hilltop_xml(REAL)[-1][0],
        rising=False,
    )


def test_sample_rising_river():
    status = status_from_readings(parse_hilltop_xml(RISING))
    assert status is not None
    assert status.rising is True
    assert status.level_m > 3.0


def test_small_wobble_is_not_rising():
    t = datetime(2026, 2, 12, 16, 0)
    readings = [(t, 2.730), (t + timedelta(hours=1), 2.735)]  # +5 mm: sensor noise
    assert status_from_readings(readings).rising is False


def test_no_reading_an_hour_back_is_not_rising():
    t = datetime(2026, 2, 12, 16, 0)
    readings = [(t, 2.0), (t + timedelta(minutes=10), 3.0)]
    assert status_from_readings(readings).rising is False


def test_empty_readings():
    assert status_from_readings([]) is None


def test_error_response_raises():
    with pytest.raises(ValueError, match="No Measurements"):
        parse_hilltop_xml(ERROR)


def test_not_xml_raises():
    with pytest.raises(ValueError):
        parse_hilltop_xml("error code: 522")


def test_url_uses_percent_20_not_plus():
    url = build_url()
    assert "Site=Ngaruroro%20River%20at%20Fernhill" in url
    assert "+" not in url
    assert "Measurement=Stage" in url
    assert url.startswith("https://data.hbrc.govt.nz/Envirodata/Telemetry.hts?")


def test_get_river_status_ok(monkeypatch):
    seen: dict = {}
    fake_get(monkeypatch, RISING, seen=seen)
    status = get_river_status(timeout_s=2.0)
    assert status is not None and status.rising
    assert seen["timeout"] == 2.0


@pytest.mark.parametrize(
    "text,status_code",
    [
        (ERROR, 200),  # Hilltop error message
        ("error code: 522", 522),  # Cloudflare timeout (seen in practice)
        ("<Hilltop><Agency>HBRC</Agency></Hilltop>", 200),  # no readings
    ],
)
def test_get_river_status_bad_responses_return_none(monkeypatch, text, status_code):
    fake_get(monkeypatch, text, status_code)
    assert get_river_status() is None


def test_get_river_status_offline_returns_none(monkeypatch):
    def offline(*args, **kwargs):
        raise river.httpx.ConnectError("Wi-Fi off")

    monkeypatch.setattr(river.httpx, "get", offline)
    assert get_river_status() is None
