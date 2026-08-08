"""QROS command line interface — expose the research framework.

Return codes: 0 ok, 1 gate/audit/lock failure, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from qros.governance.policy import DEFAULT_POLICY, render_summary
from qros.hypothesis.registry import HypothesisDoc, HypothesisRegistry
from qros.pipeline.stages import all_stages
from qros.tracking.experiment import ExperimentRecord, ExperimentTracker


def _root(args) -> Path:
    return Path(getattr(args, "root", "."))


def _hyp(args) -> int:
    reg = HypothesisRegistry(_root(args) / "registry" / "hypotheses")
    if args.hyp_command == "list":
        for h in reg.list():
            print(h)
        return 0
    if args.hyp_command == "audit":
        try:
            ok = reg.audit(args.hyp_id)
        except Exception as e:  # noqa: BLE001
            print(f"[LOCK FAILURE] {e}", file=sys.stderr)
            return 1
        print(f"audit {args.hyp_id}: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    if args.hyp_command == "register":
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        doc = HypothesisDoc(fields=data)
        try:
            digest = reg.register(doc)
        except Exception as e:  # noqa: BLE001
            print(f"[HYP ERROR] {e}", file=sys.stderr)
            return 1
        print(f"registered {doc.hypothesis_id} lock={digest[:16]}...")
        return 0
    return 2


def _stage(args) -> int:
    if args.stage_command == "list":
        for s in all_stages():
            print(f"{s.number:2d}. {s.name}")
        return 0
    return 2


def _exp(args) -> int:
    tracker = ExperimentTracker(_root(args) / "registry" / "experiments")
    if args.exp_command == "log":
        data = json.loads(Path(args.json).read_text(encoding="utf-8"))
        rec = ExperimentRecord(**data)
        try:
            exp_id = tracker.log(rec)
        except Exception as e:  # noqa: BLE001
            print(f"[EXP ERROR] {e}", file=sys.stderr)
            return 1
        print(f"logged {exp_id}")
        return 0
    if args.exp_command == "list":
        for e in tracker.find(args.hyp_id):
            print(e.experiment_id, e.approval_status)
        return 0
    return 2


def _policy(args) -> int:
    print(json.dumps(render_summary(DEFAULT_POLICY), indent=2, sort_keys=True))
    return 0


def _edge(args) -> int:
    if args.edge_command == "classify":
        from qros.edges.taxonomy import classify_edge

        kw = {}
        if args.cointegration_p is not None:
            kw["cointegration_p"] = args.cointegration_p
        if args.momentum_t is not None:
            kw["momentum_t"] = args.momentum_t
        if args.ou_half_life is not None:
            kw["ou_half_life"] = args.ou_half_life
        result = classify_edge(**kw)
        print(result.category.value)
        return 0
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qros", description="QROS research framework CLI")
    parser.add_argument("--root", default=".", help="QROS repository root")
    sub = parser.add_subparsers(dest="command")

    hyp = sub.add_parser("hyp")
    hyp_sub = hyp.add_subparsers(dest="hyp_command")
    p_list = hyp_sub.add_parser("list")
    p_audit = hyp_sub.add_parser("audit")
    p_audit.add_argument("hyp_id")
    p_reg = hyp_sub.add_parser("register")
    p_reg.add_argument("file")

    stage = sub.add_parser("stage")
    stage_sub = stage.add_subparsers(dest="stage_command")
    stage_sub.add_parser("list")

    exp = sub.add_parser("exp")
    exp_sub = exp.add_subparsers(dest="exp_command")
    p_log = exp_sub.add_parser("log")
    p_log.add_argument("--json", required=True)
    p_list2 = exp_sub.add_parser("list")
    p_list2.add_argument("hyp_id")

    sub.add_parser("policy")

    edge = sub.add_parser("edge")
    edge_sub = edge.add_subparsers(dest="edge_command")
    p_classify = edge_sub.add_parser("classify")
    p_classify.add_argument("--cointegration-p", type=float, default=None)
    p_classify.add_argument("--momentum-t", type=float, default=None)
    p_classify.add_argument("--ou-half-life", type=float, default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dispatch = {
        "hyp": _hyp,
        "stage": _stage,
        "exp": _exp,
        "policy": _policy,
        "edge": _edge,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        build_parser().print_help()
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())