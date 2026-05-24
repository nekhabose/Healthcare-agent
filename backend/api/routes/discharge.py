"""
Discharge webhook route — receives Epic FHIR Subscription events on patient discharge.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Request

from api.deps import get_discharge_service
from services.discharge import DischargeService
from tasks.outreach import schedule_outreach_calls

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/discharge")
async def handle_discharge_event(
    request: Request,
    background_tasks: BackgroundTasks,
    discharge_service: DischargeService = Depends(get_discharge_service),
):
    """
    Epic fires this webhook when a patient Encounter.status changes to 'finished'.
    We acknowledge immediately (202) and process in the background.
    """
    payload = await request.json()

    # Extract Epic patient ID from FHIR Subscription notification
    epic_patient_id = _extract_patient_id(payload)
    hospital_name = request.headers.get("X-Hospital-Name", "Your Hospital")

    background_tasks.add_task(
        _process_discharge,
        epic_patient_id=epic_patient_id,
        hospital_name=hospital_name,
        discharge_service=discharge_service,
    )

    return {"status": "accepted"}


async def _process_discharge(
    epic_patient_id: str,
    hospital_name: str,
    discharge_service: DischargeService,
) -> None:
    patient_id, discharge_id = await discharge_service.handle_discharge_event(
        epic_patient_id, hospital_name
    )
    schedule_outreach_calls.delay(patient_id, discharge_id)


def _extract_patient_id(payload: dict) -> str:
    # FHIR Subscription R4 format: {"subject": {"reference": "Patient/abc123"}}
    reference = payload.get("subject", {}).get("reference", "")
    if "/" in reference:
        return reference.split("/")[-1]
    return reference
