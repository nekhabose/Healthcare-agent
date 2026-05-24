import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Discharge(Base):
    __tablename__ = "discharges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)

    discharge_date: Mapped[date] = mapped_column(Date, nullable=False)
    hospital_name: Mapped[str] = mapped_column(String, nullable=False)
    primary_diagnosis_code: Mapped[str | None] = mapped_column(String)   # ICD-10
    primary_diagnosis_name: Mapped[str | None] = mapped_column(String)
    # One of: heart_failure | ami | pneumonia | copd | hip_knee | cabg | general
    hrrp_condition: Mapped[str | None] = mapped_column(String, index=True)

    discharge_summary_s3_key: Mapped[str | None] = mapped_column(String)
    medications: Mapped[list | None] = mapped_column(JSONB)
    followup_appointments: Mapped[list | None] = mapped_column(JSONB)
    discharge_instructions: Mapped[str | None] = mapped_column(Text)
    instructions_summary: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="discharges")
    sessions: Mapped[list["OutreachSession"]] = relationship(back_populates="discharge", lazy="selectin")
