"""
MedicationTool — log medication adherence per the patient's report.
"""
from typing import Any

from .base import BaseTool


class MedicationTool(BaseTool):
    name = "check_medication_adherence"
    description = (
        "Log whether the patient is taking a specific medication as prescribed. "
        "Returns guidance on what to say and whether pharmacist outreach is needed."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "medication_name": {
                "type": "string",
                "description": "Name of the medication",
            },
            "taking_as_prescribed": {
                "type": "boolean",
                "description": "Whether the patient is taking it correctly",
            },
            "barrier": {
                "type": "string",
                "description": "If not taking, the reason (cost, side effects, confusion, forgot)",
            },
        },
        "required": ["medication_name", "taking_as_prescribed"],
    }

    def __init__(self, adherence_log: list[dict[str, Any]]) -> None:
        self._log = adherence_log

    async def execute(self, *, medication_name: str,
                      taking_as_prescribed: bool, barrier: str = "") -> str:
        self._log.append({
            "medication": medication_name,
            "adherent": taking_as_prescribed,
            "barrier": barrier,
        })

        if taking_as_prescribed:
            return f"Adherence confirmed for '{medication_name}'. No action needed."

        barrier_lower = barrier.lower()
        if "cost" in barrier_lower or "afford" in barrier_lower or "expensive" in barrier_lower:
            return (
                f"Non-adherence: '{medication_name}' — barrier: cost. "
                "Tell the patient about patient assistance programs and offer to connect them "
                "with a care coordinator. Flag for pharmacy team follow-up."
            )
        if "side effect" in barrier_lower or "nausea" in barrier_lower:
            return (
                f"Non-adherence: '{medication_name}' — barrier: side effects. "
                "Advise them not to stop without speaking to their doctor. "
                "Use escalate_to_care_team with severity='medium' to flag for provider review."
            )
        return (
            f"Non-adherence: '{medication_name}' — barrier: {barrier or 'unspecified'}. "
            "Gently encourage taking the medication and explain its importance. "
            "Flag for care coordinator follow-up."
        )
