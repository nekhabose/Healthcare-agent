"""Tests for the provider-agnostic LLM layer."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.llm.claude import ClaudeClient
from agent.llm.deepseek import DeepSeekClient
from agent.llm.factory import build_llm_client
from agent.llm.types import (
    Message,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from config import Settings
from exceptions import ValidationError


# -------------------- DeepSeek translation --------------------

def test_deepseek_user_text_to_native():
    msg = Message(role="user", content=[TextBlock(text="Hi")])
    out = DeepSeekClient._message_to_native(msg)
    assert out == [{"role": "user", "content": "Hi"}]


def test_deepseek_tool_result_becomes_tool_role_message():
    msg = Message(role="user", content=[
        ToolResultBlock(tool_use_id="t1", content="severity: high"),
    ])
    out = DeepSeekClient._message_to_native(msg)
    assert out == [{"role": "tool", "tool_call_id": "t1", "content": "severity: high"}]


def test_deepseek_assistant_mixed_blocks_become_single_message():
    msg = Message(role="assistant", content=[
        TextBlock(text="That sounds serious."),
        ToolUseBlock(id="t1", name="assess_symptom",
                     input={"symptom": "chest pain", "severity": 9}),
    ])
    out = DeepSeekClient._message_to_native(msg)
    assert len(out) == 1
    assert out[0]["role"] == "assistant"
    assert out[0]["content"] == "That sounds serious."
    assert out[0]["tool_calls"][0]["function"]["name"] == "assess_symptom"
    args = json.loads(out[0]["tool_calls"][0]["function"]["arguments"])
    assert args == {"symptom": "chest pain", "severity": 9}


def test_deepseek_tool_definition_wrapped_in_function():
    tool = {
        "name": "assess_symptom",
        "description": "Record a symptom",
        "input_schema": {"type": "object", "properties": {}},
    }
    native = DeepSeekClient._tool_to_native(tool)
    assert native == {
        "type": "function",
        "function": {
            "name": "assess_symptom",
            "description": "Record a symptom",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def test_deepseek_native_response_with_tool_call_parses_correctly():
    response = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(
            content="Calling the tool now.",
            tool_calls=[SimpleNamespace(
                id="call_1",
                function=SimpleNamespace(
                    name="assess_symptom",
                    arguments='{"symptom":"chest pain","severity":9}',
                ),
            )],
        ),
        finish_reason="tool_calls",
    )])
    out = DeepSeekClient._from_native(response)
    assert out.stop_reason == "tool_use"
    assert out.text == "Calling the tool now."
    assert len(out.tool_uses) == 1
    assert out.tool_uses[0].name == "assess_symptom"
    assert out.tool_uses[0].input["severity"] == 9


def test_deepseek_native_response_text_only():
    response = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content="All done. Take care.", tool_calls=None),
        finish_reason="stop",
    )])
    out = DeepSeekClient._from_native(response)
    assert out.stop_reason == "end_turn"
    assert out.text == "All done. Take care."
    assert out.tool_uses == []


# -------------------- Claude translation --------------------

def test_claude_text_block_to_native():
    msg = Message(role="user", content=[TextBlock(text="Hello")])
    out = ClaudeClient._to_native(msg)
    assert out == {"role": "user", "content": [{"type": "text", "text": "Hello"}]}


def test_claude_tool_use_block_to_native():
    msg = Message(role="assistant", content=[
        ToolUseBlock(id="t1", name="foo", input={"x": 1}),
    ])
    out = ClaudeClient._to_native(msg)
    assert out["content"][0] == {
        "type": "tool_use", "id": "t1", "name": "foo", "input": {"x": 1},
    }


def test_claude_native_response_parses():
    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="OK"),
            SimpleNamespace(type="tool_use", id="t1", name="foo", input={"x": 1}),
        ],
        stop_reason="tool_use",
    )
    out = ClaudeClient._from_native(response)
    assert out.stop_reason == "tool_use"
    assert out.text == "OK"
    assert out.tool_uses[0].name == "foo"


# -------------------- Factory --------------------

def test_factory_returns_claude_client():
    settings = Settings(llm_provider="claude", anthropic_api_key="test")
    client = build_llm_client(settings)
    assert isinstance(client, ClaudeClient)


def test_factory_returns_deepseek_client():
    settings = Settings(llm_provider="deepseek", deepseek_api_key="test")
    client = build_llm_client(settings)
    assert isinstance(client, DeepSeekClient)


def test_factory_is_case_insensitive():
    settings = Settings(llm_provider="DeepSeek", deepseek_api_key="test")
    client = build_llm_client(settings)
    assert isinstance(client, DeepSeekClient)


def test_factory_raises_on_unknown_provider():
    settings = Settings(llm_provider="gpt-99")
    with pytest.raises(ValidationError):
        build_llm_client(settings)
