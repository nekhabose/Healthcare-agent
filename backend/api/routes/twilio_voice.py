"""
Twilio voice routes — TwiML response + WebSocket conversation handler.
"""
import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.twiml.voice_response import Connect, VoiceResponse

from api.deps import get_db, get_notifier_dep
from config import get_settings
from repositories.discharge import DischargeRepository
from repositories.patient import PatientRepository
from repositories.session import SessionRepository
from services.notification import BaseNotifier
from services.outreach import OutreachService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/twilio", tags=["twilio"])


@router.post("/twiml")
async def twiml_response(session_id: str):
    """Return TwiML that connects the call to our ConversationRelay WebSocket."""
    response = VoiceResponse()
    connect = Connect()
    connect.conversation_relay(
        url=f"wss://{settings.domain}/twilio/ws/{session_id}",
        welcome_greeting="Please hold for just a moment.",
        language="en-US",
        voice="en-US-Journey-F",
        transcription_provider="google",
    )
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")


@router.post("/status")
async def call_status_callback(
    request_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Twilio status callback — update session status when call ends."""
    call_sid = request_data.get("CallSid")
    call_status = request_data.get("CallStatus")
    if not call_sid:
        return {"ok": True}

    session_repo = SessionRepository(db)
    session = await session_repo.get_by_twilio_sid(call_sid)
    if session:
        status_map = {
            "completed": "completed",
            "no-answer": "no_answer",
            "busy": "no_answer",
            "failed": "failed",
        }
        mapped = status_map.get(call_status, "completed")
        await session_repo.update(session, status=mapped)

    return {"ok": True}


@router.websocket("/ws/{session_id}")
async def conversation_websocket(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    notifier: BaseNotifier = Depends(get_notifier_dep),
):
    """
    WebSocket endpoint for Twilio ConversationRelay.

    Receives transcribed patient speech, feeds it to CareAgent,
    sends agent responses back to Twilio for TTS playback.
    """
    await websocket.accept()
    session_uuid = uuid.UUID(session_id)

    # Load session context from DB
    session_repo = SessionRepository(db)
    patient_repo = PatientRepository(db)
    discharge_repo = DischargeRepository(db)

    session = await session_repo.get(session_uuid)
    if not session:
        await websocket.close(code=1008)
        return

    patient = await patient_repo.get(session.patient_id)
    discharge = await discharge_repo.get(session.discharge_id)

    async def send_to_call(text: str) -> None:
        """Send agent text to Twilio for TTS playback."""
        try:
            await websocket.send_json({"type": "text", "token": text, "last": False})
        except Exception:
            logger.warning("Failed to send to call session_id=%s", session_id)

    outreach_service = OutreachService(db=db, notifier=notifier, send_to_call_fn=send_to_call)

    # Get the call SID from the initial Twilio message
    initial_data = await websocket.receive_json()
    call_sid = initial_data.get("start", {}).get("callSid", "")

    agent = await outreach_service.start_call(
        session_id=session_uuid,
        patient=patient,
        discharge=discharge,
        twilio_call_sid=call_sid,
    )

    agent_task = asyncio.create_task(agent.run())

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "prompt":
                patient_text = data.get("voicePrompt", "").strip()
                if patient_text:
                    await agent.inject_patient_input(patient_text)

            elif msg_type == "disconnect":
                await agent.end_call()
                break

    except WebSocketDisconnect:
        await agent.end_call()
    finally:
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
        await outreach_service.complete_call(session_uuid)
