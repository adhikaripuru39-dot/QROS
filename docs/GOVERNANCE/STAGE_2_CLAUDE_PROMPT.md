# QROS - Stage 2 Claude Code Prompt

Use this prompt after Stage 1 has been accepted and Stage 2 scope has been approved.

```text
You are working on QROS under a strict governance-first workflow.

Task: Produce the Stage 2 Data Foundation package only. Do not build any engine, strategy, research, hypothesis, feature, or execution code.

Authority:
- QROS Constitution (Draft for Ratification)
- Founding Governance Documents
- Master Handbook Parts 1-3
- Stage 1 Governance Lock artifacts

Required output:
1. A Stage 2 data-foundation scope document.
2. A canonical data-boundary map for Parts 1-3.
3. A data contract specification covering inputs, outputs, provenance, identifiers, timestamps, and validation rules.
4. A checklist for what must be true before any implementation can begin.
5. A short do-not-proceed list that blocks any move into hypotheses, features, research, or execution.

Rules:
- No implementation code of any kind.
- No strategy, hypothesis, backtest, or live-execution work.
- No claim of ratification, production readiness, or approval unless the governing documents explicitly support it.
- Keep the output specification-only and governance-first.
- If any requested item would require implementation, stop and flag it instead of improvising.

Deliverables:
- `STAGE_2_SCOPE.md`
- `STAGE_2_CHECKLIST.md`
- `STAGE_2_DATA_CONTRACT.md`
- `STAGE_2_BOUNDARY_MAP.md`

Stop after producing the governance package.
```
