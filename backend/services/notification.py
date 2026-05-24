"""
NotificationService — sends care team alerts via AWS SNS/SES.

Abstracts the transport so tests can inject a no-op implementation
and production can swap SES for any other provider without touching
business logic.
"""
import json
import logging
import uuid
from abc import ABC, abstractmethod

import boto3

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseNotifier(ABC):
    @abstractmethod
    async def send_escalation(
        self,
        session_id: uuid.UUID,
        patient_id: uuid.UUID,
        severity: str,
        reason: str,
        symptoms: list[str],
    ) -> None: ...


class SNSNotifier(BaseNotifier):
    def __init__(self) -> None:
        self._sns = boto3.client("sns", region_name=settings.aws_region)

    async def send_escalation(
        self,
        session_id: uuid.UUID,
        patient_id: uuid.UUID,
        severity: str,
        reason: str,
        symptoms: list[str],
    ) -> None:
        # Note: patient identifiers in the SNS message are UUIDs, never PHI
        payload = {
            "type": "ESCALATION",
            "severity": severity,
            "patient_id": str(patient_id),
            "session_id": str(session_id),
            "reason": reason,
            "symptoms": symptoms,
        }
        subject_prefix = {
            "urgent": "[URGENT] CareGuard",
            "high": "[HIGH] CareGuard",
            "medium": "[MEDIUM] CareGuard",
        }.get(severity, "CareGuard")

        try:
            self._sns.publish(
                TopicArn=settings.sns_escalation_topic_arn,
                Subject=f"{subject_prefix} — Patient escalation",
                Message=json.dumps(payload),
                MessageAttributes={
                    "severity": {"DataType": "String", "StringValue": severity}
                },
            )
            logger.info(
                "Escalation SNS published session_id=%s severity=%s",
                session_id, severity,
            )
        except Exception:
            logger.exception("SNS publish failed session_id=%s", session_id)
            raise


class NoOpNotifier(BaseNotifier):
    """Used in tests and local development."""

    async def send_escalation(self, session_id, patient_id, severity, reason, symptoms) -> None:
        logger.info(
            "NoOpNotifier escalation session_id=%s severity=%s reason=%s",
            session_id, severity, reason,
        )


def get_notifier() -> BaseNotifier:
    if settings.is_production:
        return SNSNotifier()
    return NoOpNotifier()
