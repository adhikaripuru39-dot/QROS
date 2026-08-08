"""Decision log (ADR) support per Constitution Article IX."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Decision:
    """An Architectural/Governance Decision Record entry."""

    log_id: str
    date: str
    title: str
    context: str
    decision_text: str
    status: str = "ACCEPTED"  # PROPOSED | ACCEPTED | SUPERSEDED
    supersedes: str | None = None


def load(path: Path) -> list[Decision]:
    if not Path(path).exists():
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Decision(**d) for d in data]


def record_decision(path: Path, decision: Decision, append: bool = True) -> None:
    """Persist a decision record (appending to the file)."""
    path = Path(path)
    existing = load(path) if append and path.exists() else []
    existing.append(decision)
    path.write_text(
        json.dumps([asdict(d) for d in existing], indent=2, sort_keys=True),
        encoding="utf-8",
    )


def export_markdown(path: Path, decisions: list[Decision]) -> None:
    """Render decisions as Markdown into ``path``."""
    lines: list[str] = ["# QROS Architectural Decision Record\n"]
    for d in decisions:
        lines.append(f"## {d.log_id} — {d.title}")
        lines.append(f"- **Date**: {d.date}")
        lines.append(f"- **Status**: {d.status}"
                     + (f"  · supersedes {d.supersedes}" if d.supersedes else ""))
        lines.append(f"\n**Context:** {d.context}")
        lines.append(f"\n**Decision:** {d.decision_text}\n")
    Path(path).write_text("\n".join(lines), encoding="utf-8")