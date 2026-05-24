from .base import BaseProtocol


class OrthopedicProtocol(BaseProtocol):
    condition_key = "hip_knee"

    condition_specific_guidance = """\
Post-surgical orthopedic red flags — escalate IMMEDIATELY (urgent) if:
- Sudden severe pain at the surgical site
- Signs of blood clot (DVT): calf pain, redness, warmth, or swelling in one leg
- Signs of pulmonary embolism: sudden chest pain or difficulty breathing
- Signs of wound infection with spreading redness, pus, or fever above 101°F

High escalation (provider call within 2 hours) if:
- Wound reopening or significant drainage soaking the dressing
- Fever between 100.4–101°F persisting more than 24 hours
- Inability to do prescribed physical therapy exercises due to pain

Always confirm: blood thinner adherence (critical for DVT prevention), \
PT/OT attendance, and weight-bearing instructions."""

    @property
    def checklist(self) -> list[str]:
        return [
            "Ask how they are feeling since coming home from surgery.",
            "Ask about pain level at the surgical site (1–10).",
            "Ask about any redness, warmth, or swelling at the surgical site.",
            "Ask about any calf pain, swelling, or warmth (DVT check).",
            "Confirm they are taking blood thinners as prescribed.",
            "Confirm they have attended or scheduled physical therapy.",
            "Review pain medication adherence and ask about side effects.",
            "Confirm follow-up with orthopedic surgeon is scheduled.",
            "Provide care team contact and instruct to go to ER for breathing problems.",
        ]
