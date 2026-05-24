"""
CareAgent — orchestrates the post-discharge conversation.

Responsibilities:
- Builds the tool registry for this session.
- Selects the condition-specific protocol.
- Drives the Claude multi-turn conversation loop.
- Persists every conversation turn.
- Hands transcribed patient speech in via inject_patient_input().

The agent is intentionally decoupled from Twilio and the DB;
those concerns are injected through callbacks so the agent
remains unit-testable without infrastructure.
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

import anthropic

from config import get_settings
from models.db import Discharge, Patient
from .protocols.factory import ProtocolFactory
from .tools.escalation import EscalationTool
from .tools.medication import MedicationTool
from .tools.registry import ToolRegistry
from .tools.scheduling import SchedulingTool
from .tools.symptom import SymptomTool

logger = logging.getLogger(__name__)
settings = get_settings()

EscalationCallback = Callable[..., Coroutine[Any, Any, None]]
TurnCallback = Callable[[str, str], Coroutine[Any, Any, None]]     # (role, content)
SendToCallCallback = Callable[[str], Coroutine[Any, Any, None]]    # (text)


@dataclass
class AgentContext:
    session_id: uuid.UUID
    patient: Patient
    discharge: Discharge
    escalation_callback: EscalationCallback
    turn_callback: TurnCallback
    send_to_call_callback: SendToCallCallback

    # Shared mutable state passed into tools
    recorded_symptoms: list[dict[str, Any]] = field(default_factory=list)
    adherence_log: list[dict[str, Any]] = field(default_factory=list)
    scheduling_log: list[dict[str, Any]] = field(default_factory=list)


class CareAgent:
    def __init__(self, ctx: AgentContext) -> None:
        self._ctx = ctx
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._registry = self._build_registry()
        self._protocol = ProtocolFactory.get(ctx.discharge.hrrp_condition)
        self._patient_input_queue: asyncio.Queue[str] = asyncio.Queue()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Drive the full conversation until the agent says goodbye."""
        messages: list[dict[str, Any]] = []
        system_prompt = self._build_system_prompt()

        opening = self._build_opening()
        await self._emit_turn("agent", opening)
        await self._ctx.send_to_call_callback(opening)
        messages.append({"role": "assistant", "content": opening})

        while True:
            patient_text = await self._wait_for_patient_input()
            if patient_text is None:
                break

            await self._emit_turn("patient", patient_text)
            messages.append({"role": "user", "content": patient_text})

            messages = await self._agent_turn(messages, system_prompt)

            # Stop if the last agent message is a closing
            last_agent = self._last_agent_text(messages)
            if last_agent and self._is_closing(last_agent):
                break

    async def inject_patient_input(self, text: str) -> None:
        """Called by the WebSocket handler when patient speech arrives."""
        await self._patient_input_queue.put(text)

    async def end_call(self) -> None:
        """Signal the conversation loop to stop gracefully."""
        await self._patient_input_queue.put(None)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        ctx = self._ctx
        registry.register(SymptomTool(ctx.recorded_symptoms))
        registry.register(MedicationTool(ctx.adherence_log))
        registry.register(EscalationTool(
            session_id=ctx.session_id,
            patient_id=ctx.patient.id,
            escalation_callback=ctx.escalation_callback,
        ))
        registry.register(SchedulingTool(ctx.scheduling_log))
        return registry

    def _build_system_prompt(self) -> str:
        ctx = self._ctx
        meds = self._format_medications(ctx.discharge.medications or [])
        appts = self._format_appointments(ctx.discharge.followup_appointments or [])
        return self._protocol.build_system_prompt(
            hospital_name=ctx.discharge.hospital_name,
            patient_first_name=ctx.patient.first_name,   # decrypted by caller
            discharge_date=str(ctx.discharge.discharge_date),
            diagnosis=ctx.discharge.primary_diagnosis_name or "recent illness",
            medications=meds,
            followup_appointments=appts,
            instructions_summary=ctx.discharge.instructions_summary or "Follow up as directed.",
        )

    def _build_opening(self) -> str:
        name = self._ctx.patient.first_name
        hospital = self._ctx.discharge.hospital_name
        return (
            f"Hello, may I please speak with {name}? "
            f"... Hi {name}, this is an automated care check-in call from {hospital}. "
            "We're calling to see how you're doing since coming home from the hospital. "
            "Is now a good time to answer a few questions? It should only take about five minutes."
        )

    async def _agent_turn(
        self, messages: list[dict[str, Any]], system_prompt: str
    ) -> list[dict[str, Any]]:
        """Run one agent turn, handling tool calls recursively until end_turn."""
        response = await self._client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            system=system_prompt,
            tools=self._registry.definitions,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_results = await self._handle_tool_calls(response.content)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            return await self._agent_turn(messages, system_prompt)

        agent_text = self._extract_text(response.content)
        if agent_text:
            await self._emit_turn("agent", agent_text)
            await self._ctx.send_to_call_callback(agent_text)
            messages.append({"role": "assistant", "content": agent_text})

        return messages

    async def _handle_tool_calls(
        self, content: list[Any]
    ) -> list[dict[str, Any]]:
        results = []
        for block in content:
            if block.type != "tool_use":
                continue
            result = await self._registry.execute(block.name, **block.input)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })
        return results

    async def _wait_for_patient_input(self) -> str | None:
        return await self._patient_input_queue.get()

    async def _emit_turn(self, role: str, content: str) -> None:
        try:
            await self._ctx.turn_callback(role, content)
        except Exception:
            logger.exception("Failed to persist conversation turn role=%s", role)

    @staticmethod
    def _extract_text(content: list[Any]) -> str:
        return " ".join(
            block.text for block in content
            if hasattr(block, "text") and block.text
        )

    @staticmethod
    def _last_agent_text(messages: list[dict[str, Any]]) -> str | None:
        for msg in reversed(messages):
            if msg["role"] == "assistant" and isinstance(msg["content"], str):
                return msg["content"]
        return None

    @staticmethod
    def _is_closing(text: str) -> bool:
        closing_phrases = ("thank you", "take care", "goodbye", "have a good", "stay well")
        return any(phrase in text.lower() for phrase in closing_phrases)

    @staticmethod
    def _format_medications(medications: list[dict[str, Any]]) -> str:
        if not medications:
            return "No medications listed."
        return "; ".join(
            f"{m.get('name', 'Unknown')} {m.get('dose', '')} {m.get('frequency', '')}".strip()
            for m in medications
        )

    @staticmethod
    def _format_appointments(appointments: list[dict[str, Any]]) -> str:
        if not appointments:
            return "No follow-up appointments scheduled."
        return "; ".join(
            f"{a.get('specialty', 'Provider')} on {a.get('scheduled_date', 'TBD')}"
            for a in appointments
        )
