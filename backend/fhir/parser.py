"""
DischargeParser — transforms raw FHIR R4 JSON into a ParsedDischarge dataclass.

Isolated here so the rest of the codebase never touches raw FHIR JSON.
All HRRP condition detection lives in _detect_hrrp_condition().
"""
import logging
from datetime import date, datetime
from typing import Any

from .client import HRRP_ICD_MAP
from .schemas import ParsedDischarge

logger = logging.getLogger(__name__)


class DischargeParser:
    @classmethod
    def parse(cls, raw: dict[str, Any]) -> ParsedDischarge:
        patient = cls._parse_patient(raw.get("patient", {}))
        medications = cls._parse_medications(raw.get("medications", {}))
        conditions = raw.get("conditions", {}).get("entry", [])
        appointments = cls._parse_appointments(raw.get("appointments", {}))
        instructions = cls._parse_instructions(raw.get("documents", {}))
        hrrp = cls._detect_hrrp_condition(conditions)

        primary_dx_code, primary_dx_name = cls._primary_diagnosis(conditions)

        return ParsedDischarge(
            epic_patient_id=patient["epic_id"],
            mrn=patient.get("mrn"),
            first_name=patient["first_name"],
            last_name=patient["last_name"],
            phone=patient["phone"],
            date_of_birth=patient.get("dob"),
            age=patient.get("age", 0),
            discharge_date=date.today(),
            primary_diagnosis_code=primary_dx_code,
            primary_diagnosis_name=primary_dx_name,
            hrrp_condition=hrrp,
            medications=medications,
            followup_appointments=appointments,
            discharge_instructions=instructions,
            instructions_summary=cls._summarize(instructions),
        )

    # ------------------------------------------------------------------
    # Private parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_patient(resource: dict[str, Any]) -> dict[str, Any]:
        name = (resource.get("name") or [{}])[0]
        given = " ".join(name.get("given", []))
        family = name.get("family", "")

        telecom = resource.get("telecom", [])
        phone = next((t["value"] for t in telecom if t.get("system") == "phone"), "")

        identifiers = resource.get("identifier", [])
        mrn = next(
            (i["value"] for i in identifiers if i.get("type", {}).get("text") == "MRN"),
            None,
        )

        dob: date | None = None
        age = 0
        if dob_str := resource.get("birthDate"):
            try:
                dob = date.fromisoformat(dob_str)
                age = (date.today() - dob).days // 365
            except ValueError:
                logger.warning("Could not parse birthDate: %s", dob_str)

        return {
            "epic_id": resource.get("id", ""),
            "mrn": mrn,
            "first_name": given,
            "last_name": family,
            "phone": phone,
            "dob": dob,
            "age": age,
        }

    @staticmethod
    def _parse_medications(bundle: dict[str, Any]) -> list[dict[str, Any]]:
        meds = []
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "MedicationRequest":
                continue
            med_name = (
                resource.get("medicationCodeableConcept", {}).get("text")
                or resource.get("medicationReference", {}).get("display", "Unknown")
            )
            dosage = (resource.get("dosageInstruction") or [{}])[0]
            meds.append({
                "name": med_name,
                "dose": dosage.get("doseAndRate", [{}])[0].get("doseQuantity", {}).get("value"),
                "frequency": dosage.get("timing", {}).get("code", {}).get("text"),
                "instructions": dosage.get("text"),
            })
        return meds

    @staticmethod
    def _parse_appointments(bundle: dict[str, Any]) -> list[dict[str, Any]]:
        appts = []
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "Appointment":
                continue
            participants = resource.get("participant", [])
            provider = next(
                (p.get("actor", {}).get("display") for p in participants
                 if p.get("actor", {}).get("reference", "").startswith("Practitioner")),
                None,
            )
            specialty = (resource.get("serviceType") or [{}])[0].get("text")
            start = resource.get("start", "")[:10] if resource.get("start") else None
            appts.append({
                "provider": provider,
                "specialty": specialty,
                "scheduled_date": start,
                "location": resource.get("comment"),
            })
        return appts

    @staticmethod
    def _parse_instructions(bundle: dict[str, Any]) -> str | None:
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "DocumentReference":
                continue
            for content in resource.get("content", []):
                if data := content.get("attachment", {}).get("data"):
                    import base64
                    try:
                        return base64.b64decode(data).decode("utf-8", errors="replace")
                    except Exception:
                        pass
        return None

    @staticmethod
    def _detect_hrrp_condition(entries: list[dict[str, Any]]) -> str | None:
        for entry in entries:
            resource = entry.get("resource", {})
            for coding in resource.get("code", {}).get("coding", []):
                code = coding.get("code", "")
                for prefix, condition in HRRP_ICD_MAP.items():
                    if code.startswith(prefix):
                        return condition
        return None

    @staticmethod
    def _primary_diagnosis(entries: list[dict[str, Any]]) -> tuple[str | None, str | None]:
        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "Condition":
                continue
            codings = resource.get("code", {}).get("coding", [])
            code = codings[0].get("code") if codings else None
            name = resource.get("code", {}).get("text") or (codings[0].get("display") if codings else None)
            return code, name
        return None, None

    @staticmethod
    def _summarize(instructions: str | None, max_chars: int = 500) -> str | None:
        if not instructions:
            return None
        cleaned = " ".join(instructions.split())
        return cleaned[:max_chars] + "..." if len(cleaned) > max_chars else cleaned
