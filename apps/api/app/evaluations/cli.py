import argparse
from pathlib import Path

from app.evaluations.evaluator import Phase4Evaluator
from app.evaluations.io import load_benchmark, load_gate_policy, load_run
from app.evaluations.models import GateResultStatus


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate a Phase 4 observation run against the frozen benchmark."
    )
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = Phase4Evaluator().evaluate(
        benchmark=load_benchmark(args.benchmark),
        policy=load_gate_policy(args.policy),
        run=load_run(args.run),
    )
    print(report.model_dump_json(indent=2))
    if report.status is GateResultStatus.PASS:
        return 0
    if report.status is GateResultStatus.FAIL:
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
