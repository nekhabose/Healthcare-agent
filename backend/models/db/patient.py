import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    epic_patient_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    mrn: Mapped[str | None] = mapped_column(String)

    # PHI — encrypted at application layer before persistence
    first_name_enc: Mapped[str] = mapped_column(String, nullable=False)
    last_name_enc: Mapped[str] = mapped_column(String, nullable=False)
    phone_enc: Mapped[str] = mapped_column(String, nullable=False)

    date_of_birth: Mapped[date | None] = mapped_column(Date)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[str | None] = mapped_column(String)  # high | medium | low

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    discharges: Mapped[list["Discharge"]] = relationship(back_populates="patient", lazy="selectin")
