from .base import BaseProtocol


class GeneralProtocol(BaseProtocol):
    """Default protocol for non-HRRP discharges — uses base checklist only."""

    condition_key = "general"

    condition_specific_guidance = """\
General post-discharge red flags — escalate IMMEDIATELY (urgent) if:
- Chest pain, pressure, or tightness
- Difficulty breathing or sudden shortness of breath
- Signs of stroke (face droop, arm weakness, speech difficulty)
- Severe bleeding or loss of consciousness

High escalation (provider call within 2 hours) if:
- New fever above 101°F
- Worsening pain at any surgical or treatment site
- Inability to keep down food or fluids for more than 24 hours
- Any symptom rated 7/10 or higher

Confirm the patient understands their discharge instructions and \
knows when to seek emergency care vs call the care team."""
