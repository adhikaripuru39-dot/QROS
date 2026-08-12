# QROS — Stage 1 Compliance Checklist
For every future Claude Code task. Run **G0 before starting any task**. Each task self-attests and records results in the decision log.

## G0 — DO NOT PROCEED list (blocking; before anything else)
Before **scope, inputs, outputs, and edge confirmation are documented AND approved**, the following are **forbidden** and must halt work immediately:

- [ ] DO NOT build or modify any engine, module, research, backtest, or execution code.
- [ ] DO NOT write or run any live trading, order dispatch, position-sizing, or risk-limit logic.
- [ ] DO NOT claim ratification, production readiness, or approval of anything.
- [ ] DO NOT register a HYP as tested, or freeze a dataset snapshot for experimentation.
- [ ] DO NOT relax or lower any threshold or quality gate to let a result pass.
- [ ] DO NOT proceed past Stage 0 unless **scope, inputs, outputs, and edge confirmation are documented and approved**.
- [ ] DO NOT assume the Constitution is ratified (it is **draft** until its own document says otherwise).
- [ ] DO NOT treat any pre-existing code as compliance-assumed.

> If any checkbox would be violated by the requested task, **stop** and report the blocker; do not attempt the task.

## Pre-task (before starting)
- [ ] Task is governance/documentation only, or has an approved stage assignment (`STAGE_SEQUENCE_MAP.md`).
- [ ] Source governing sections are cited (Constitution article, Part, stage number).
- [ ] Scope, inputs, outputs, and edge confirmation for this task are documented (or explicitly deferred with an owner).
- [ ] Constitution treated as draft; no ratification/approval claim made.

## During-task (while working)
- [ ] No prohibited work executed (see G0).
- [ ] Any threshold value cited matches `governance/policy.py` / handbook literal — never a remembered or scratch value (ADR-001).
- [ ] Any numbers referenced are traceable to a source document.
- [ ] No retrospective editing of a hypothesis or experiment record to fit results (Part 5, Part 9).

## Post-task (before finishing)
- [ ] Outputs are consistent with the charter and stage map.
- [ ] Every allowed/prohibited claim is traceable to a governing source.
- [ ] No implementation artifact was created in this task.
- [ ] Ratification/approval/readiness claims: **none** made (or each explicitly sourced).
- [ ] Result recorded in `docs/DECISION_LOG.md` (Constitution Art. IX).

## Sign-off
- Owner: ____________ · Date: ____________
- Gate G0 passed: [ ] YES [ ] NO (if NO, task must not proceed)
