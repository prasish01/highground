from datetime import UTC, datetime, timedelta, timezone

import pytest

from highground.cap import as_replay, parse_cap
from highground.farm import DATA_DIR, load_farm
from highground.geo import area_ha, distance_to_line_m, haversine_m, point_in_polygon
from highground.plan import facts, template_plan
from highground.risk import NZ_TZ, band, format_time, recommend, score_paddock, to_nz

NZDT = timezone(timedelta(hours=13))


@pytest.fixture
def farm():
    return load_farm()


@pytest.fixture
def warning():
    return parse_cap((DATA_DIR / "replay_warning.xml").read_text(encoding="utf-8"))


# --- geometry ---------------------------------------------------------------


def test_haversine_one_degree_latitude_is_about_111_km():
    assert haversine_m((0, 0), (0, 1)) == pytest.approx(111_195, rel=1e-3)


def test_distance_to_line_is_zero_on_the_line():
    line = [(176.70, -39.60), (176.80, -39.60)]
    assert distance_to_line_m((176.75, -39.60), line) == pytest.approx(0, abs=0.5)


def test_point_in_polygon():
    square = [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert point_in_polygon((0.5, 0.5), square)
    assert not point_in_polygon((1.5, 0.5), square)


def test_sample_paddocks_are_about_nine_hectares(farm):
    for p in farm.paddocks:
        assert 7 < area_ha(p.ring) < 11


# --- CAP parsing ------------------------------------------------------------


def test_replay_warning_parses_as_red_heavy_rain(warning):
    assert warning.level == "red"
    assert warning.event == "Heavy Rain"
    assert len(warning.areas) == 1


def test_replay_shifts_onset_and_keeps_duration(warning):
    now = datetime(2026, 11, 21, 9, 0, tzinfo=NZDT)
    replay = as_replay(warning, now)
    assert replay.is_replay
    assert replay.onset == now + timedelta(hours=7)
    assert replay.expires - replay.onset == warning.expires - warning.onset


def test_warning_covers_the_sample_farm(farm, warning):
    assert all(warning.covers(p.centre) for p in farm.paddocks)


# --- risk scoring -----------------------------------------------------------


def test_band_thresholds():
    assert (band(0.1), band(0.5), band(0.9)) == ("green", "amber", "red")


def test_low_paddock_by_river_scores_higher_than_high_paddock(farm, warning):
    by_name = {p.name: p for p in farm.paddocks}
    low = score_paddock(by_name["Paddock 1"], farm.river, farm.river_elevation_m, warning)
    high = score_paddock(by_name["Paddock 7"], farm.river, farm.river_elevation_m, warning)
    assert low.score > high.score
    assert low.band == "red"
    assert high.band == "green"


def test_no_warning_means_no_red_paddocks(farm):
    risks = [score_paddock(p, farm.river, farm.river_elevation_m, None) for p in farm.paddocks]
    assert all(r.band != "red" for r in risks)


def test_rising_river_never_lowers_a_score(farm, warning):
    for p in farm.paddocks:
        calm = score_paddock(p, farm.river, farm.river_elevation_m, warning)
        rising = score_paddock(p, farm.river, farm.river_elevation_m, warning, river_rising=True)
        assert rising.score >= calm.score


# --- recommendation ---------------------------------------------------------


def test_recommends_paddock_7_with_a_deadline_three_hours_before_onset(farm, warning):
    now = datetime(2026, 11, 21, 12, 0, tzinfo=NZDT)
    replay = as_replay(warning, now)  # onset 7pm
    risks = [score_paddock(p, farm.river, farm.river_elevation_m, replay) for p in farm.paddocks]
    rec = recommend(farm.paddocks, risks, farm.herd_size, farm.ha_per_cow, replay)
    assert rec is not None
    assert rec.name == "Paddock 7"
    assert rec.deadline == datetime(2026, 11, 21, 16, 0, tzinfo=NZDT)
    assert rec.message == "Move the herd to Paddock 7 by 4pm"


def test_paddock_without_water_is_never_recommended(farm, warning):
    risks = [score_paddock(p, farm.river, farm.river_elevation_m, warning) for p in farm.paddocks]
    rec = recommend(farm.paddocks, risks, farm.herd_size, farm.ha_per_cow, warning)
    assert rec.name != "Paddock 8"


def test_no_recommendation_when_herd_does_not_fit(farm, warning):
    risks = [score_paddock(p, farm.river, farm.river_elevation_m, warning) for p in farm.paddocks]
    assert recommend(farm.paddocks, risks, 10_000, 0.02, warning) is None


def test_deadline_is_nz_time_when_now_is_utc(farm, warning):
    # 00:00 UTC on 21 Nov = 1pm NZDT. Onset 7 h later = 8pm NZDT; deadline 3 h before = 5pm.
    now_utc = datetime(2026, 11, 21, 0, 0, tzinfo=UTC)
    replay = as_replay(warning, now_utc)
    risks = [score_paddock(p, farm.river, farm.river_elevation_m, replay) for p in farm.paddocks]
    rec = recommend(farm.paddocks, risks, farm.herd_size, farm.ha_per_cow, replay)
    assert rec.message.endswith(" by 5pm")
    assert rec.deadline_label == "5pm"
    assert rec.deadline == datetime(2026, 11, 21, 17, 0, tzinfo=NZ_TZ)
    assert rec.deadline.utcoffset() == timedelta(hours=13)
    assert facts(farm.name, farm.herd_size, replay, risks, rec)["warning"]["onset"] == "8pm"


def test_deadline_uses_nz_winter_time(farm, warning):
    # NZST is UTC+12 in July. 00:00 UTC = noon; onset 7pm; deadline 4pm.
    replay = as_replay(warning, datetime(2026, 7, 1, 0, 0, tzinfo=UTC))
    risks = [score_paddock(p, farm.river, farm.river_elevation_m, replay) for p in farm.paddocks]
    rec = recommend(farm.paddocks, risks, farm.herd_size, farm.ha_per_cow, replay)
    assert rec.deadline_label == "4pm"


def test_to_nz_converts_other_zones_and_assumes_nz_for_naive_times():
    assert to_nz(datetime(2026, 11, 21, 3, 0, tzinfo=UTC)).hour == 16
    assert to_nz(datetime(2026, 11, 21, 3, 0)).tzinfo == NZ_TZ


def test_format_time():
    assert format_time(datetime(2026, 1, 1, 16, 0)) == "4pm"
    assert format_time(datetime(2026, 1, 1, 0, 30)) == "12:30am"


# --- plan -------------------------------------------------------------------


def test_template_plan_uses_only_given_facts(farm, warning):
    risks = [score_paddock(p, farm.river, farm.river_elevation_m, warning) for p in farm.paddocks]
    rec = recommend(farm.paddocks, risks, farm.herd_size, farm.ha_per_cow, warning)
    plan = template_plan(facts(farm.name, farm.herd_size, warning, risks, rec))
    assert plan["moves"][0]["action"] == rec.message
    assert len(plan["checklist"]) <= 8
