"""Tests for PDT compliance manager."""

from services.risk_engine.pdt_compliance import PDTComplianceManager


def test_pdt_unlocked():
    manager = PDTComplianceManager({"pdt": {"enabled": True}})
    assert manager.is_pdt_unlocked(25000) is True
    assert manager.is_pdt_unlocked(1000) is False
