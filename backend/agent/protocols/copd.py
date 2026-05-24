from .base import BaseProtocol


class COPDProtocol(BaseProtocol):
    condition_key = "copd"

    condition_specific_guidance = """\
COPD red flags — escalate IMMEDIATELY (urgent) if:
- Severe shortness of breath that is not relieved by rescue inhaler
- Lips or fingernails turning blue (cyanosis)
- Inability to speak in full sentences due to breathlessness

High escalation (provider call within 2 hours) if:
- Increased use of rescue inhaler (more than every 4 hours)
- Sputum becoming thicker, darker, or more than usual
- New fever suggesting infection
- Unable to perform daily activities (eating, dressing) due to shortness of breath

Always confirm: inhaler technique, medication schedule, and smoking cessation support."""

    @property
    def checklist(self) -> list[str]:
        return [
            "Ask how their breathing has been since leaving the hospital.",
            "Ask if they have needed to use their rescue inhaler more than usual.",
            "Ask about any changes in cough or sputum (color, amount).",
            "Review inhaler medications — confirm correct use and schedule.",
            "Ask about smoking status and offer cessation resources if applicable.",
            "Confirm follow-up with pulmonologist or primary care is scheduled.",
            "Remind patient to keep rescue inhaler accessible at all times.",
            "Provide care team contact and ER instructions for breathing emergencies.",
        ]
