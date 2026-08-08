"""Constitution version and amendment-register data (Article XI)."""

from __future__ import annotations

VERSION = "1.0 (Founding Edition — Ratified)"

# Ratifying amendment that installs the Founding Edition as the ratified baseline.
RATIFICATION_AMENDMENT: dict = {
    "id": "AMEND-001",
    "article": "Article XI (Amendment Process)",
    "provision": "Founding draft edition",
    "change": "Ratify Version 1.0 Founding Edition as the platform baseline.",
    "rationale": "The founding release was labeled 'Draft for Ratification'; the rebuilt "
    "platform requires an authoritative ratified baseline from which all "
    "subsequent amendments are versioned.",
    "status": "RATIFIED",
}

AMENDMENTS: list[dict] = [RATIFICATION_AMENDMENT]


def registered_amendments() -> list[dict]:
    """The complete versioned amendment register (Article XI)."""
    return list(AMENDMENTS)