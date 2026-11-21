"""Tests for the saved replay warning and CAP parsing edge cases (no network)."""

from datetime import UTC, datetime, timedelta

from highground.cap import as_replay, parse_cap, parse_rss_links
from highground.farm import DATA_DIR, load_farm

REPLAY = (DATA_DIR / "replay_warning.xml").read_text(encoding="utf-8")

CAP_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>test-1</identifier>
  <sent>2026-02-12T06:00:00+13:00</sent>
  <info>
    <event>{event}</event>
    <severity>{severity}</severity>
    {onset}
    <expires>2026-02-13T12:00:00+13:00</expires>
    <headline>{headline}</headline>
    {params}
    <area>
      <areaDesc>t</areaDesc>
      <polygon>-39.5,176.5 -39.5,177 -39.8,177 -39.5,176.5</polygon>
    </area>
  </info>
</alert>"""


def cap(
    event="Heavy Rain",
    severity="Moderate",
    headline="Heavy Rain Warning",
    params="",
    onset="<onset>2026-02-12T18:00:00+13:00</onset>",
):
    return CAP_TEMPLATE.format(
        event=event, severity=severity, headline=headline, params=params, onset=onset
    )


def colour_param(value: str) -> str:
    return f"<parameter><valueName>ColourCode</valueName><value>{value}</value></parameter>"


# --- the saved replay warning ---------------------------------------------------


def test_replay_warning_parses_as_red_heavy_rain():
    w = parse_cap(REPLAY)
    assert w.level == "red"
    assert "Heavy Rain" in w.event
    assert w.expires > w.onset
    assert w.areas, "replay warning needs at least one polygon"


def test_replay_warning_covers_every_sample_paddock():
    w = parse_cap(REPLAY)
    farm = load_farm()
    for p in farm.paddocks:
        assert w.covers(p.centre), f"{p.id} not inside the warning area"
        for corner in p.ring:
            assert w.covers(corner), f"{p.id} corner {corner} outside the warning area"


def test_replay_warning_is_honestly_labelled():
    """A made-up warning must say SAMPLE; a real one must come from MetService."""
    w = parse_cap(REPLAY)
    if "<status>Exercise</status>" in REPLAY:
        assert "SAMPLE" in w.headline
    else:
        assert "metservice" in REPLAY.lower()


def test_replay_is_flagged_and_shifted_to_now():
    w = parse_cap(REPLAY)
    now = datetime(2026, 11, 21, 9, 0, tzinfo=UTC)
    r = as_replay(w, now, onset_in=timedelta(hours=7))
    assert r.is_replay is True
    assert r.onset == now + timedelta(hours=7)
    assert r.expires - r.onset == w.expires - w.onset
    assert r.level == w.level


# --- level mapping edge cases (MetService-style fields) ----------------------------


def test_colour_code_parameter_wins():
    xml = cap(severity="Extreme", params=colour_param("Orange"))
    assert parse_cap(xml).level == "orange"


def test_colour_in_event_text():
    assert parse_cap(cap(event="Heavy Rain Warning - Orange")).level == "orange"


def test_word_containing_red_is_not_red():
    """'hundred', 'considered' and 'covered' contain 'red' but are not a red warning."""
    xml = cap(headline="Up to two hundred mm considered possible in covered areas")
    assert parse_cap(xml).level == "yellow"


def test_severity_fallback():
    assert parse_cap(cap(severity="Extreme")).level == "red"
    assert parse_cap(cap(severity="Severe")).level == "orange"
    assert parse_cap(cap(severity="Minor")).level == "yellow"


def test_missing_onset_uses_sent_time():
    w = parse_cap(cap(onset=""))
    assert w.onset == datetime.fromisoformat("2026-02-12T06:00:00+13:00")


# --- RSS feed --------------------------------------------------------------------


def test_rss_with_no_warnings_gives_no_links():
    # Real MetService feed content on 2026-11-21 (no active warnings).
    rss = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"><channel><title>Metservice Public CAP Alerts</title>
<link>https://www.metservice.com</link></channel></rss>"""
    assert parse_rss_links(rss) == []


def test_rss_links_are_extracted():
    rss = """<rss version="2.0"><channel><title>t</title>
<item><title>a</title><link>https://alerts.metservice.com/cap/alert?id=1</link></item>
<item><title>b</title><link> https://alerts.metservice.com/cap/alert?id=2 </link></item>
</channel></rss>"""
    assert parse_rss_links(rss) == [
        "https://alerts.metservice.com/cap/alert?id=1",
        "https://alerts.metservice.com/cap/alert?id=2",
    ]
