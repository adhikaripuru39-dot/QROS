"""Tests for hypothesis/registry.py (Part 5 immutable 22-field HYP)."""

from __future__ import annotations

import pytest

from qros.hypothesis.registry import (
    HypothesisDoc,
    HypothesisRegistry,
    HypothesisValidationError,
    ImmutableLockError,
)


def _reg(tmp_path) -> HypothesisRegistry:
    return HypothesisRegistry(tmp_path / "hyp")


def test_valid_doc_passes(make_hyp_spec):
    fields = make_hyp_spec()
    doc = HypothesisDoc(fields=fields, hypothesis_id=fields["HYP-01"])
    assert doc.validate() == []


def test_missing_field_fails(make_hyp_spec):
    fields = make_hyp_spec()
    del fields["HYP-05"]
    doc = HypothesisDoc(fields=fields, hypothesis_id=fields["HYP-01"])
    errors = doc.validate()
    assert any("HYP-05" in e for e in errors)


def test_register_locks_and_audits(make_hyp_spec, tmp_path):
    reg = _reg(tmp_path)
    fields = make_hyp_spec("HYP-EQUITY-MICROSTRUCTURE-2026-0042")
    doc = HypothesisDoc(fields=fields, hypothesis_id=fields["HYP-01"])
    digest = reg.register(doc)
    assert len(digest) == 64
    assert reg.audit("HYP-EQUITY-MICROSTRUCTURE-2026-0042") is True
    assert reg.list() == ["HYP-EQUITY-MICROSTRUCTURE-2026-0042"]


def test_tamper_detected_raises(make_hyp_spec, tmp_path):
    reg = _reg(tmp_path)
    fields = make_hyp_spec("HYP-EQUITY-MICROSTRUCTURE-2026-0042")
    reg.register(HypothesisDoc(fields=fields, hypothesis_id=fields["HYP-01"]))
    doc_path = reg._doc_path("HYP-EQUITY-MICROSTRUCTURE-2026-0042")
    import json

    data = json.loads(doc_path.read_text(encoding="utf-8"))
    data["HYP-02"] = "tampered"
    doc_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ImmutableLockError):
        reg.audit("HYP-EQUITY-MICROSTRUCTURE-2026-0042")