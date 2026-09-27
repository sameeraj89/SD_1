"""The Claude engine's request shape, checked against a fake client (no network)."""

import json
from types import SimpleNamespace

import pytest

from saptadrishti import spec
from saptadrishti.engine import ClaudeEngine, RefusalError


class FakeMessages:
    def __init__(self, payload, stop_reason="end_turn"):
        self.payload, self.stop_reason, self.calls = payload, stop_reason, []

    def create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(model="claude-opus-5", stop_reason=self.stop_reason,
                               content=[SimpleNamespace(type="text", text=json.dumps(self.payload))])


def engine(payload, stop_reason="end_turn"):
    msgs = FakeMessages(payload, stop_reason)
    client = SimpleNamespace(beta=SimpleNamespace(messages=msgs))
    return ClaudeEngine(client=client), msgs


CTX = {"profile_label": "Core", "audience": "reader", "as_of": "2026-09-27", "subject": "",
       "purpose": "", "requisition": "", "standing_disclosures": [], "external_inputs": []}


def test_lens_call_shape():
    eng, msgs = engine({"reading": "r", "findings": []})
    out = eng.read_lens("veracity", spec.charter_for("veracity", "general"), "[D1 p1 L1] hello", CTX)
    assert out == {"reading": "r", "findings": []}
    kw = msgs.calls[0]
    assert kw["model"] == "claude-opus-5"
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert kw["fallbacks"] and kw["betas"] == ["server-side-fallback-2026-06-01"]
    blocks = kw["messages"][0]["content"]
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}  # frozen text cached across lenses
    assert "Veracity" in blocks[1]["text"] and "Prudence" not in blocks[1]["text"]
    assert "served claude-opus-5" in eng.identity()


def test_prefix_identical_across_lenses():
    eng, msgs = engine({"reading": "r", "findings": []})
    for lens in spec.LENSES:
        eng.read_lens(lens, spec.charter_for(lens, "general"), "[D1 p1 L1] hello", CTX)
    prefixes = {json.dumps(c["messages"][0]["content"][0]) + c["system"] for c in msgs.calls}
    assert len(prefixes) == 1


def test_refusal_is_raised():
    eng, _ = engine({}, stop_reason="refusal")
    with pytest.raises(RefusalError):
        eng.read_lens("prudence", "c", "[D1 p1 L1] x", CTX)
