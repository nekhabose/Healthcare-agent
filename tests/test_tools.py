import uuid
from unittest.mock import AsyncMock

import pytest

from backend.agent.tools.escalation import EscalationTool
from backend.agent.tools.medication import MedicationTool
from backend.agent.tools.registry import ToolRegistry
from backend.agent.tools.scheduling import SchedulingTool
from backend.agent.tools.symptom import SymptomTool
from backend.exceptions import ToolExecutionError


# --- SymptomTool ---

@pytest.mark.asyncio
async def test_symptom_chest_pain_triggers_urgent():
    log = []
    tool = SymptomTool(log)
    result = await tool.execute(symptom="chest pain", severity=5)
    assert "urgent" in result.lower()
    assert len(log) == 1


@pytest.mark.asyncio
async def test_symptom_high_severity_triggers_high():
    log = []
    tool = SymptomTool(log)
    result = await tool.execute(symptom="swelling", severity=8)
    assert "high" in result.lower()


@pytest.mark.asyncio
async def test_symptom_mild_no_escalation():
    log = []
    tool = SymptomTool(log)
    result = await tool.execute(symptom="mild fatigue", severity=3)
    assert "ESCALATION_REQUIRED" not in result
    assert len(log) == 1


# --- MedicationTool ---

@pytest.mark.asyncio
async def test_medication_adherent_returns_confirmation():
    log = []
    tool = MedicationTool(log)
    result = await tool.execute(medication_name="Lisinopril", taking_as_prescribed=True)
    assert "confirmed" in result.lower()
    assert log[0]["adherent"] is True


@pytest.mark.asyncio
async def test_medication_cost_barrier_suggests_assistance():
    log = []
    tool = MedicationTool(log)
    result = await tool.execute(
        medication_name="Furosemide",
        taking_as_prescribed=False,
        barrier="too expensive",
    )
    assert "assistance" in result.lower() or "cost" in result.lower()


# --- EscalationTool ---

@pytest.mark.asyncio
async def test_escalation_calls_callback():
    callback = AsyncMock()
    tool = EscalationTool(
        session_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        escalation_callback=callback,
    )
    result = await tool.execute(severity="urgent", reason="Chest pain", symptoms=["chest pain"])
    callback.assert_awaited_once()
    assert "911" in result or "emergency" in result.lower()


@pytest.mark.asyncio
async def test_escalation_medium_returns_coordinator_message():
    callback = AsyncMock()
    tool = EscalationTool(
        session_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        escalation_callback=callback,
    )
    result = await tool.execute(severity="medium", reason="Non-adherence")
    assert "coordinator" in result.lower()


# --- SchedulingTool ---

@pytest.mark.asyncio
async def test_scheduling_logs_appointment():
    log = []
    tool = SchedulingTool(log)
    result = await tool.execute(appointment_type="cardiology", urgency="within_7d")
    assert log[0]["type"] == "cardiology"
    assert "week" in result.lower()


# --- ToolRegistry ---

@pytest.mark.asyncio
async def test_registry_executes_registered_tool():
    registry = ToolRegistry()
    registry.register(SymptomTool([]))
    result = await registry.execute("assess_symptom", symptom="nausea", severity=4)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_registry_raises_for_unknown_tool():
    registry = ToolRegistry()
    with pytest.raises(ToolExecutionError):
        await registry.execute("nonexistent_tool")


def test_registry_definitions_includes_all_registered():
    registry = ToolRegistry()
    registry.register(SymptomTool([]))
    registry.register(MedicationTool([]))
    defs = registry.definitions
    names = [d["name"] for d in defs]
    assert "assess_symptom" in names
    assert "check_medication_adherence" in names
