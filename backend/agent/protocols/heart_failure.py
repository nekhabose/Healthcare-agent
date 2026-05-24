from .base import BaseProtocol


class HeartFailureProtocol(BaseProtocol):
    condition_key = "heart_failure"

    condition_specific_guidance = """\
Heart failure red flags — escalate IMMEDIATELY (urgent) if:
- Sudden shortness of breath at rest or waking up breathless at night
- Weight gain more than 2 pounds in one day or 5 pounds in one week
- Swelling in legs, ankles, or feet that is new or rapidly worsening
- Chest pain or pressure of any kind

High escalation (contact provider within 2 hours) if:
- Increasing shortness of breath with mild activity (previously tolerated)
- Persistent fatigue that prevents normal activities
- Dizziness or lightheadedness

Always ask: "Have you been weighing yourself daily?" and "Have you noticed any swelling?"
Confirm the patient knows their target weight and when to call the doctor."""

    @property
    def checklist(self) -> list[str]:
        return [
            "Ask how the patient is feeling since coming home.",
            "Ask if they have been weighing themselves daily and what the numbers are.",
            "Ask about shortness of breath at rest or with activity.",
            "Ask about any new leg or ankle swelling.",
            "Review each heart failure medication (especially diuretics and beta-blockers).",
            "Confirm follow-up with cardiologist is scheduled.",
            "Remind patient of their daily weight threshold for calling the doctor.",
            "Confirm they know the care team contact number.",
        ]
