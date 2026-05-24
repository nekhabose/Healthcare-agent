from .base import BaseProtocol


class PneumoniaProtocol(BaseProtocol):
    condition_key = "pneumonia"

    condition_specific_guidance = """\
Pneumonia red flags — escalate IMMEDIATELY (urgent) if:
- Difficulty breathing or rapid breathing at rest
- Lips or fingernails turning blue
- Chest pain with breathing
- High fever (above 103°F / 39.4°C) that is not improving

High escalation (provider call within 2 hours) if:
- Cough significantly worsening or producing green/yellow/blood-tinged sputum
- Fever returning after being gone for 24+ hours
- Confusion or unusual mental changes (especially in elderly patients)

Always ask about: fever pattern, cough changes, appetite, and energy level.
Confirm the patient is completing their full antibiotic course if prescribed."""

    @property
    def checklist(self) -> list[str]:
        return [
            "Ask how they have been feeling overall since coming home.",
            "Ask about their breathing — better, same, or worse than in the hospital?",
            "Ask about fever — current temperature if they have a thermometer.",
            "Ask about their cough — frequency, sputum color, any blood.",
            "Review antibiotic adherence if prescribed.",
            "Confirm follow-up appointment with primary care is scheduled within 7–10 days.",
            "Ask about appetite and hydration.",
            "Provide care team contact and instruct to go to ER for breathing difficulty.",
        ]
