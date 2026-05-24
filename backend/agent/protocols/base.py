"""
BaseProtocol — abstract base for condition-specific conversation protocols.

Each protocol defines the system prompt suffix and ordered checklist
that the agent should follow for a given HRRP condition.
Subclasses override only what differs; shared preamble lives here.
"""
from abc import ABC, abstractmethod


SHARED_PREAMBLE = """\
You are a care coordinator for {hospital_name}, calling to check on {patient_first_name} \
after their recent hospital discharge on {discharge_date}.

Your goals:
1. Ask how the patient is feeling and note any symptoms.
2. Confirm they are taking their discharge medications as prescribed.
3. Confirm a follow-up appointment is scheduled.
4. Escalate immediately when you detect red-flag symptoms.

Rules:
- Speak warmly and in plain language (no medical jargon).
- Ask ONE question at a time.
- Never diagnose or treat — you gather information for the care team.
- When a patient reports a symptom, ALWAYS use the assess_symptom tool.
- When discussing each medication, use the check_medication_adherence tool.
- Use escalate_to_care_team immediately for chest pain, breathing difficulty, or stroke signs.
- Use schedule_followup if the patient has no appointment booked.
- End by thanking the patient and reminding them how to reach the care team.

Patient context:
- Primary diagnosis: {diagnosis}
- Discharge medications: {medications}
- Follow-up appointments: {followup_appointments}
- Key discharge instructions: {instructions_summary}
"""


class BaseProtocol(ABC):
    @property
    @abstractmethod
    def condition_key(self) -> str:
        """Matches the hrrp_condition field on Discharge (e.g. 'heart_failure')."""

    @property
    @abstractmethod
    def condition_specific_guidance(self) -> str:
        """
        Additional system-prompt text appended after the shared preamble.
        Describe the specific symptoms and thresholds the agent must watch for.
        """

    @property
    def checklist(self) -> list[str]:
        """
        Ordered list of topics the agent should cover.
        Returned to the agent as a numbered list in the system prompt.
        """
        return [
            "Ask how the patient is feeling overall.",
            "Ask about any new or worsening symptoms.",
            "Review each discharge medication one by one.",
            "Confirm follow-up appointment details.",
            "Ask about transportation or other barriers to follow-up.",
            "Thank the patient and provide the care team contact number.",
        ]

    def build_system_prompt(self, **context: str) -> str:
        checklist_text = "\n".join(
            f"{i + 1}. {item}" for i, item in enumerate(self.checklist)
        )
        base = SHARED_PREAMBLE.format(**context)
        return (
            f"{base}\n\n"
            f"Condition-specific guidance:\n{self.condition_specific_guidance}\n\n"
            f"Conversation checklist (follow in order):\n{checklist_text}"
        )
