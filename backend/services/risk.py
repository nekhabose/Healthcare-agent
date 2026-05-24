"""
RiskScoringService — rule-based readmission risk scorer.

Scores 0–100. Converts to risk_level: high ≥60, medium ≥30, low <30.
Designed as a pure function so it can be replaced with an ML model
without touching any other layer.
"""
from dataclasses import dataclass

HRRP_CONDITIONS = frozenset({
    "heart_failure", "ami", "pneumonia", "copd", "hip_knee", "cabg"
})


@dataclass
class RiskInput:
    prior_readmissions_90d: int = 0
    hrrp_condition: str | None = None
    medication_count: int = 0
    age: int = 0
    has_followup_appointment: bool = True
    lives_alone: bool = False
    prior_ed_visits_90d: int = 0


@dataclass
class RiskResult:
    score: int
    level: str        # high | medium | low
    factors: list[str]


class RiskScoringService:
    HIGH_THRESHOLD = 60
    MEDIUM_THRESHOLD = 30

    @classmethod
    def score(cls, data: RiskInput) -> RiskResult:
        score = 0
        factors: list[str] = []

        if data.prior_readmissions_90d > 0:
            pts = min(data.prior_readmissions_90d * 15, 30)
            score += pts
            factors.append(f"Prior readmissions: {data.prior_readmissions_90d} (+{pts}pts)")

        if data.hrrp_condition in HRRP_CONDITIONS:
            score += 25
            factors.append(f"HRRP condition: {data.hrrp_condition} (+25pts)")

        if data.medication_count > 5:
            score += 10
            factors.append(f"Polypharmacy: {data.medication_count} medications (+10pts)")

        if data.age > 75:
            score += 10
            factors.append(f"Age: {data.age} (+10pts)")
        elif data.age > 65:
            score += 5
            factors.append(f"Age: {data.age} (+5pts)")

        if not data.has_followup_appointment:
            score += 15
            factors.append("No follow-up appointment scheduled (+15pts)")

        if data.lives_alone:
            score += 10
            factors.append("Lives alone (+10pts)")

        if data.prior_ed_visits_90d > 0:
            pts = min(data.prior_ed_visits_90d * 5, 15)
            score += pts
            factors.append(f"Prior ED visits: {data.prior_ed_visits_90d} (+{pts}pts)")

        score = min(score, 100)
        level = (
            "high" if score >= cls.HIGH_THRESHOLD
            else "medium" if score >= cls.MEDIUM_THRESHOLD
            else "low"
        )
        return RiskResult(score=score, level=level, factors=factors)
