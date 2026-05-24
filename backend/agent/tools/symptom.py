"""
SymptomTool — assess and record a patient-reported symptom.

Determines escalation level based on symptom type and severity,
then delegates to EscalationTool when threshold is crossed.
"""
from typing import Any

from .base import BaseTool

# Red-flag symptoms trigger urgent escalation regardless of severity score
URGENT_SYMPTOMS = frozenset({
    "chest pain", "chest pressure", "chest tightness",
    "difficulty breathing", "shortness of breath",
    "stroke", "sudden weakness", "sudden confusion",
    "severe headache", "loss of consciousness", "unresponsive",
})

# Severity at or above this value → high escalation
HIGH_SEVERITY_THRESHOLD = 7


class SymptomTool(BaseTool):
    name = "assess_symptom"
    description = (
        "Record a symptom the patient has reported. "
        "Determines escalation level and returns guidance on what to say next."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "symptom": {
                "type": "string",
                "description": "Symptom name (e.g. 'shortness of breath', 'chest pain', 'swelling')",
            },
            "severity": {
                "type": "integer",
                "description": "Patient-reported severity 1–10",
                "minimum": 1,
                "maximum": 10,
            },
            "duration": {
                "type": "string",
                "description": "How long the symptom has been present",
            },
            "context": {
                "type": "string",
                "description": "Additional details the patient provided",
            },
        },
        "required": ["symptom", "severity"],
    }

    def __init__(self, recorded_symptoms: list[dict[str, Any]]) -> None:
        # Shared list mutated during the conversation so the agent has memory
        self._recorded = recorded_symptoms

    async def execute(self, *, symptom: str, severity: int,
                      duration: str = "", context: str = "") -> str:
        self._recorded.append(
            {"symptom": symptom, "severity": severity, "duration": duration, "context": context}
        )

        normalized = symptom.lower().strip()
        is_urgent = any(u in normalized for u in URGENT_SYMPTOMS)

        if is_urgent or severity >= 9:
            return (
                f"ESCALATION_REQUIRED:urgent | "
                f"Symptom='{symptom}' Severity={severity}/10. "
                "Tell the patient to call 911 or go to the ER immediately. "
                "Then use escalate_to_care_team with severity='urgent'."
            )
        if severity >= HIGH_SEVERITY_THRESHOLD:
            return (
                f"ESCALATION_REQUIRED:high | "
                f"Symptom='{symptom}' Severity={severity}/10. "
                "Advise the patient to contact their doctor today. "
                "Use escalate_to_care_team with severity='high'."
            )
        return (
            f"Symptom recorded: '{symptom}' — {severity}/10. "
            "Continue monitoring; no immediate escalation needed. "
            "Advise patient to call if it worsens."
        )
