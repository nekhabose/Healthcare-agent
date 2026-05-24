"""
SchedulingTool — flag that a follow-up appointment needs to be made.

Actual scheduling happens through the care coordinator dashboard.
This tool records the intent and urgency so the dashboard surfaces it.
"""
from typing import Any

from .base import BaseTool


class SchedulingTool(BaseTool):
    name = "schedule_followup"
    description = (
        "Record that the patient needs a follow-up appointment. "
        "Use this when the patient has no appointment scheduled or asks for help booking one."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "appointment_type": {
                "type": "string",
                "description": "e.g. 'primary care', 'cardiology', 'pharmacy review', 'wound care'",
            },
            "urgency": {
                "type": "string",
                "enum": ["within_24h", "within_7d", "within_14d", "within_30d"],
                "description": "How soon the appointment is needed",
            },
            "notes": {
                "type": "string",
                "description": "Any additional context for the scheduler",
            },
        },
        "required": ["appointment_type", "urgency"],
    }

    def __init__(self, scheduling_log: list[dict[str, Any]]) -> None:
        self._log = scheduling_log

    async def execute(self, *, appointment_type: str,
                      urgency: str, notes: str = "") -> str:
        self._log.append(
            {"type": appointment_type, "urgency": urgency, "notes": notes}
        )

        urgency_phrases = {
            "within_24h": "within the next 24 hours",
            "within_7d": "within the next week",
            "within_14d": "within the next two weeks",
            "within_30d": "within the next month",
        }
        phrase = urgency_phrases.get(urgency, urgency)
        return (
            f"Appointment request logged: {appointment_type} — needed {phrase}. "
            "Tell the patient a care coordinator will call them to schedule this appointment."
        )
