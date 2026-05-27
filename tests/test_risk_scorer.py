import pytest

from services.risk import RiskInput, RiskScoringService


def test_high_risk_hrrp_with_readmissions():
    result = RiskScoringService.score(RiskInput(
        prior_readmissions_90d=2,
        hrrp_condition="heart_failure",
        medication_count=7,
        age=78,
        has_followup_appointment=False,
        lives_alone=True,
    ))
    assert result.level == "high"
    assert result.score >= 60


def test_low_risk_young_healthy():
    result = RiskScoringService.score(RiskInput(
        prior_readmissions_90d=0,
        hrrp_condition=None,
        medication_count=2,
        age=45,
        has_followup_appointment=True,
        lives_alone=False,
    ))
    assert result.level == "low"
    assert result.score < 30


def test_medium_risk_no_followup():
    result = RiskScoringService.score(RiskInput(
        prior_readmissions_90d=0,
        hrrp_condition=None,
        medication_count=3,
        age=68,
        has_followup_appointment=False,
        lives_alone=True,
    ))
    assert result.level in ("medium", "high")


def test_score_capped_at_100():
    result = RiskScoringService.score(RiskInput(
        prior_readmissions_90d=10,
        hrrp_condition="copd",
        medication_count=10,
        age=90,
        has_followup_appointment=False,
        lives_alone=True,
        prior_ed_visits_90d=5,
    ))
    assert result.score == 100


def test_hrrp_condition_adds_points():
    without_hrrp = RiskScoringService.score(RiskInput(age=70))
    with_hrrp = RiskScoringService.score(RiskInput(age=70, hrrp_condition="pneumonia"))
    assert with_hrrp.score - without_hrrp.score == 25


def test_factors_are_populated():
    result = RiskScoringService.score(RiskInput(
        prior_readmissions_90d=1,
        hrrp_condition="ami",
        has_followup_appointment=False,
    ))
    assert any("HRRP" in f for f in result.factors)
    assert any("readmission" in f.lower() for f in result.factors)
