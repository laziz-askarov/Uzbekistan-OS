from pathlib import Path

from app.evaluations.models import BenchmarkManifest, EvaluationRun, GatePolicy


def load_benchmark(path: Path) -> BenchmarkManifest:
    return BenchmarkManifest.model_validate_json(path.read_text(encoding="utf-8"))


def load_gate_policy(path: Path) -> GatePolicy:
    return GatePolicy.model_validate_json(path.read_text(encoding="utf-8"))


def load_run(path: Path) -> EvaluationRun:
    return EvaluationRun.model_validate_json(path.read_text(encoding="utf-8"))
