"""
EscalationTool — fire an escalation event and persist it.

The tool persists the Escalation DB record and hands off to
NotificationService so the care team is alerted via SNS/SES.
The agent layer stays unaware of infrastructure details.
"""
import uuid
from typing import Any

from .base import BaseTool


class EscalationTool(BaseTool):
    name = "escalate_to_care_team"
    description = (
        "Alert the care team about a concerning finding from the patient check-in. "
        "Use severity='urgent' for chest pain / breathing difficulty / stroke signs. "
        "Use severity='high' for any symptom ≥7/10 or missed critical medication. "
        "Use severity='medium' for non-adherence or missed follow-up appointments."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "enum": ["urgent", "high", "medium"],
                "description": (
                    "urgent=life-threatening, contact 911 guidance + immediate page; "
                    "high=provider call within 2 hours; "
                    "medium=flag for next business day"
                ),
            },
            "reason": {
                "type": "string",
                "description": "Clear clinical reason for the escalation",
            },
            "symptoms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of specific symptoms reported",
            },
        },
        "required": ["severity", "reason"],
    }

    def __init__(
        self,
        session_id: uuid.UUID,
        patient_id: uuid.UUID,
        escalation_callback: Any,   # async callable(session_id, patient_id, severity, reason, symptoms)
    ) -> None:
        self._session_id = session_id
        self._patient_id = patient_id
        self._callback = escalation_callback

    async def execute(self, *, severity: str, reason: str,
                      symptoms: list[str] | None = None) -> str:
        await self._callback(
            session_id=self._session_id,
            patient_id=self._patient_id,
            severity=severity,
            reason=reason,
            symptoms=symptoms or [],
        )

        severity_messages = {
            "urgent": (
                "Care team has been alerted immediately. "
                "Tell the patient to call 911 or go to the nearest emergency room right now."
            ),
            "high": (
                "Care team has been alerted. A provider will call the patient within 2 hours. "
                "Advise the patient to rest and call back if symptoms worsen."
            ),
            "medium": (
                "Care coordinator has been notified. "
                "Advise the patient that someone will follow up with them soon."
            ),
        }
        return severity_messages.get(severity, "Care team has been notified.")
